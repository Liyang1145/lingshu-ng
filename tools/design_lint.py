"""控制台设计审查门：用 impeccable（Apache-2.0，https://github.com/pbakaus/impeccable）的确定性检测规则
扫描控制台每个页面（对比度、标题层级、嵌套卡片、过度使用字体等 AI 生成界面的常见问题），有任何发现即失败。

impeccable 只在 CI / 开发机上经 npx 临时运行，不是 lingshu-ng 的依赖，也不随包发布。

用法：python tools/design_lint.py            （需要 Node.js 与一个 Chromium 内核浏览器；
      可用 IMPECCABLE_BROWSER 指定浏览器可执行文件）
"""
import json
import os
import subprocess
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("LINGSHU_NG_SEM", "off")

IMPECCABLE = "impeccable@4.6.0"
ROUTES = ["", "#/search", "#/browse", "#/write", "#/exchange", "#/health"]
DEMO = [("项目周会定在每周二上午十点，地点三号会议室。", ["会议", "日程"]),
        ("客户张总偏好邮件沟通，不接受晚上九点后的电话。", ["客户", "偏好"]),
        ("合同续签截止日期为 11 月 30 日。", ["合同", "截止"]),
        ("The quarterly review is scheduled for the first Monday of December.", ["review"])]


def main() -> int:
    from lingshu_ng.integrations import console as lc
    db = os.path.join(tempfile.mkdtemp(prefix="lsng-lint-"), "demo.db")
    srv = lc.make_console_server(db, "127.0.0.1", 0, None)
    for text, tags in DEMO:
        srv.service.perceive({"content": text, "tags": tags})
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    failed = 0
    try:
        for r in ROUTES:
            url = base + r
            p = subprocess.run(["npx", "-y", IMPECCABLE, "detect", "--json", url],
                               capture_output=True, text=True, timeout=300)
            out = p.stdout.strip()
            try:
                findings = json.loads(out) if out else []
            except ValueError:
                print(f"[design-lint] {url}: 无法解析输出\n{out}\n{p.stderr}", file=sys.stderr)
                return 2
            if p.returncode not in (0, 1) and not findings:
                print(f"[design-lint] {url}: impeccable 运行失败（{p.returncode}）\n{p.stderr}", file=sys.stderr)
                return 2
            print(f"[design-lint] {r or '#/overview'}: {len(findings)} 项")
            for f in findings:
                print("  - " + json.dumps(f, ensure_ascii=False)[:400])
            failed += len(findings)
    finally:
        srv.shutdown()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
