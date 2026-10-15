# -*- coding: utf-8 -*-
"""E5-5：控制台真实浏览器端到端（Playwright + Chromium）。

不属于零依赖核心测试：未装 playwright 时整文件跳过。CI 作业 console-e2e 安装后运行。
覆盖：CSP 下页面无脚本错误、写入、检索、浏览、详情、二次确认删除、XSS 负载只作文本、令牌登录、中英切换、导出下载。
"""
import json
import os
import threading

import pytest

pw = pytest.importorskip("playwright.sync_api")

from lingshu_ng.integrations import console as lconsole  # noqa: E402

XSS = '<img src=x onerror="window.PWN=1">'


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setenv("LINGSHU_NG_SEM", "off")
    monkeypatch.delenv("LINGSHU_NG_TOKEN", raising=False)
    made = []

    def make(token=None):
        s = lconsole.make_console_server(str(tmp_path / f"e{len(made)}.db"), "127.0.0.1", 0, token)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        made.append(s)
        return s, f"http://127.0.0.1:{s.server_address[1]}/"
    yield make
    for s in made:
        s.shutdown(); s.server_close(); s.service.close()


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def _page(browser):
    ctx = browser.new_context(accept_downloads=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    return ctx, page, errors


def test_full_flow(server, browser):
    s, url = server()
    ctx, page, errors = _page(browser)
    page.goto(url)
    page.wait_for_selector("text=节点总数")
    # 写入（含 XSS 负载）
    page.click("#tabs button[data-view=write]")
    page.fill("#w-content", "浏览器端到端测试：灵枢控制台 " + XSS)
    page.fill("#w-tags", "e2e, 控制台")
    page.click("#view button[type=submit]")
    page.wait_for_selector("text=已写入")
    # 检索
    page.click("#tabs button[data-view=search]")
    page.fill("#q", "灵枢控制台")
    page.click("#view button[type=submit]")
    page.wait_for_selector("td.content")
    assert XSS in page.inner_text("td.content")                      # 作为文本显示
    assert page.evaluate("window.PWN") is None and page.locator("#view img").count() == 0
    # 浏览 + 详情 + 二次确认删除
    page.click("#tabs button[data-view=browse]")
    page.wait_for_selector("text=第 1–1 条，共 1 条")
    page.click("#view button.link")
    page.wait_for_selector(".detail-content")
    page.click("button.danger:has-text('删除节点')")
    page.wait_for_selector(".confirm-box")
    page.click(".confirm-box button.danger")
    page.wait_for_selector("text=没有节点")
    assert s.service.engine.store.nodes.count() == 0
    # 中英切换
    page.click("#lang")
    page.wait_for_selector("#tabs button[data-view=browse]:has-text('Browse')")
    assert not errors, errors
    ctx.close()


def test_export_download(server, browser, tmp_path):
    s, url = server()
    s.service.perceive({"content": "导出下载测试"})
    ctx, page, errors = _page(browser)
    page.goto(url)
    page.click("#tabs button[data-view=exchange]")
    with page.expect_download() as dl:
        page.click("#view button.primary")
    p = tmp_path / "bk.json"
    dl.value.save_as(str(p))
    d = json.loads(p.read_text(encoding="utf-8"))
    assert len(d["nodes"]) == 1 and not errors
    ctx.close()


def test_token_login(server, browser):
    s, url = server(token="e2e-secret")
    ctx, page, errors = _page(browser)
    page.goto(url)
    page.wait_for_selector("#login:not(.hidden)")
    page.fill("#token-input", "wrong")
    page.click("#login-form button[type=submit]")
    page.wait_for_selector("#login-error:not(:empty)")
    page.fill("#token-input", "e2e-secret")
    page.click("#login-form button[type=submit]")
    page.wait_for_selector("text=节点总数")
    assert page.evaluate("document.cookie") == ""
    assert page.evaluate("sessionStorage.getItem('lingshu_ng_console_token')") == "e2e-secret"
    assert page.evaluate("localStorage.getItem('lingshu_ng_console_token')") is None
    ctx.close()
