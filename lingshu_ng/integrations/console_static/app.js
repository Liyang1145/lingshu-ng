// lingshu-ng 控制台前端（原生 JS，无依赖，无外部资源）。
// 安全约定：所有服务端 / 用户数据只经 textContent / createTextNode / 属性赋值进入 DOM，全文件不用任何「HTML 字符串 → DOM」的 API；
// 令牌只存 sessionStorage，只以 Authorization 头发送（不进 URL、不进 cookie）；写操作带 X-Lingshu-Console: 1。
(function () {
  "use strict";

  var TOKEN_KEY = "lingshu_ng_console_token";
  var LANG_KEY = "lingshu_ng_console_lang";
  var LAYERS = ["anchor", "structure", "knowledge", "context", "self"];

  var I18N = {
    zh: {
      console: "控制台", tab_overview: "概览", tab_search: "检索", tab_browse: "记忆浏览", tab_write: "写入",
      tab_exchange: "导入/导出", tab_health: "健康", logout: "退出", login_title: "需要令牌",
      login_hint: "此服务设置了 Bearer 令牌。令牌只保存在本标签页的 sessionStorage 中，关闭标签页即清除。",
      token: "令牌", login: "登录", bad_token: "令牌错误", loading: "加载中…", refresh: "刷新",
      total_nodes: "节点总数", db_path: "库路径", version: "版本", schema_version: "schema 版本",
      semantic_tier: "能力档位", layer_counts: "各层计数", plugins: "插件", dependencies: "依赖",
      models: "模型", engine: "引擎", fallbacks: "退回记录", name: "名称", dist: "发行包", source: "来源",
      provides: "提供", status: "状态", available: "可用", unavailable: "不可用", none: "（无）",
      query: "查询", limit: "条数", search: "检索", no_hits: "没有命中", score: "分数", layer: "层",
      tags: "标签", entities: "实体", created: "创建时间", content: "原文", importance: "重要度",
      confidence: "置信度", all_layers: "全部层", tag_filter: "标签（精确）", apply: "筛选", prev: "上一页",
      next: "下一页", page_info: "第 {a}–{b} 条，共 {n} 条", empty: "没有节点", details: "详情",
      negative: "否定 / 排除", write_title: "写入一条记忆（perceive）", tags_hint: "标签，逗号分隔",
      entities_hint: "实体，逗号分隔", importance_hint: "重要度 0–1（可空）", submit: "写入",
      written: "已写入：{id}（{action}，层 {layer}）", content_required: "正文不能为空",
      node_detail: "节点详情", modality: "模态", access_count: "访问次数", last_access: "最近访问",
      protected: "受保护", deletable: "可删除", yes: "是", no: "否", edges_out: "出边", edges_in: "入边",
      relation: "关系", peer: "对端", verified: "已验证", del: "删除节点", del_confirm_title: "确认删除？",
      del_confirm_text: "将删除节点 {id} 及其全部 {n} 条关联边，此操作不可撤销。", del_yes: "确认删除",
      cancel: "取消", deleted: "已删除 {id}（移除 {n} 条边）", export_title: "导出", export_hint:
      "导出整库为 JSON 备份（与 MemoryEngine.export_all 相同格式），在浏览器中下载。", export_btn: "导出并下载",
      exported: "已导出 {n} 个节点", import_title: "导入", import_hint:
      "选择 export 导出的 JSON 备份。同 id 的节点会被覆盖；共享层与治理表按规则隔离（不接受设计者密钥）。",
      choose_file: "选择文件", file_summary: "文件 {f}：{n} 个节点、{e} 条边（meta.version = {v}）",
      import_confirm: "我确认导入（同 id 节点将被覆盖）", import_btn: "导入", import_report: "导入报告",
      imported: "导入", rejected_rows: "拒收行", quarantined: "隔离", dropped_columns: "丢弃列",
      orphan_edges: "孤儿边拒收", integrity: "完整性", bad_json: "文件不是合法 JSON：{e}", table: "表",
      count: "数", raw: "原始 JSON", healthz: "/healthz", uptime: "运行时长", started_at: "启动时间",
      req_total: "请求总数", req_recent: "最近 {w} 秒请求数", auth: "鉴权", auth_token: "Bearer 令牌",
      auth_loop: "无令牌（仅本机）", err: "错误", id: "ID", ok: "正常", fail: "异常"
    },
    en: {
      console: "Console", tab_overview: "Overview", tab_search: "Search", tab_browse: "Browse", tab_write: "Write",
      tab_exchange: "Import / Export", tab_health: "Health", logout: "Sign out", login_title: "Token required",
      login_hint: "This server requires a Bearer token. It is kept only in this tab's sessionStorage and is cleared when the tab closes.",
      token: "Token", login: "Sign in", bad_token: "Wrong token", loading: "Loading…", refresh: "Refresh",
      total_nodes: "Total nodes", db_path: "Database", version: "Version", schema_version: "Schema version",
      semantic_tier: "Capability tier", layer_counts: "Nodes per layer", plugins: "Plugins", dependencies: "Dependencies",
      models: "Models", engine: "Engine", fallbacks: "Fallbacks", name: "Name", dist: "Distribution", source: "Source",
      provides: "Provides", status: "Status", available: "available", unavailable: "unavailable", none: "(none)",
      query: "Query", limit: "Limit", search: "Search", no_hits: "No hits", score: "Score", layer: "Layer",
      tags: "Tags", entities: "Entities", created: "Created", content: "Content", importance: "Importance",
      confidence: "Confidence", all_layers: "All layers", tag_filter: "Tag (exact)", apply: "Apply", prev: "Previous",
      next: "Next", page_info: "{a}–{b} of {n}", empty: "No nodes", details: "Details",
      negative: "Negative / excluded", write_title: "Write a memory (perceive)", tags_hint: "Tags, comma separated",
      entities_hint: "Entities, comma separated", importance_hint: "Importance 0–1 (optional)", submit: "Write",
      written: "Written: {id} ({action}, layer {layer})", content_required: "Content must not be empty",
      node_detail: "Node detail", modality: "Modality", access_count: "Access count", last_access: "Last access",
      protected: "Protected", deletable: "Deletable", yes: "yes", no: "no", edges_out: "Outgoing edges", edges_in: "Incoming edges",
      relation: "Relation", peer: "Peer", verified: "Verified", del: "Delete node", del_confirm_title: "Delete this node?",
      del_confirm_text: "Node {id} and all {n} attached edges will be deleted. This cannot be undone.", del_yes: "Delete",
      cancel: "Cancel", deleted: "Deleted {id} ({n} edges removed)", export_title: "Export", export_hint:
      "Export the whole database as a JSON backup (same format as MemoryEngine.export_all) and download it.", export_btn: "Export & download",
      exported: "Exported {n} nodes", import_title: "Import", import_hint:
      "Pick a JSON backup produced by export. Nodes with the same id are overwritten; shared layers and governance tables are quarantined (no designer key).",
      choose_file: "Choose file", file_summary: "File {f}: {n} nodes, {e} edges (meta.version = {v})",
      import_confirm: "I confirm the import (nodes with the same id will be overwritten)", import_btn: "Import", import_report: "Import report",
      imported: "Imported", rejected_rows: "Rejected rows", quarantined: "Quarantined", dropped_columns: "Dropped columns",
      orphan_edges: "Orphan edges rejected", integrity: "Integrity", bad_json: "Not valid JSON: {e}", table: "Table",
      count: "Count", raw: "Raw JSON", healthz: "/healthz", uptime: "Uptime", started_at: "Started",
      req_total: "Total requests", req_recent: "Requests in last {w}s", auth: "Auth", auth_token: "Bearer token",
      auth_loop: "No token (loopback only)", err: "Error", id: "ID", ok: "OK", fail: "Failing"
    }
  };

  var state = { lang: "zh", view: "overview", browse: { layer: "", tag: "", offset: 0, limit: 50 },
                search: { query: "", limit: 10, result: null }, importData: null, importName: "" };

  // ------------------------------------------------------------------ 工具
  function t(key, vars) {
    var s = (I18N[state.lang] && I18N[state.lang][key]) || I18N.zh[key] || key;
    if (vars) {
      Object.keys(vars).forEach(function (k) { s = s.split("{" + k + "}").join(String(vars[k])); });
    }
    return s;
  }

  // 建元素：属性逐个 setAttribute / 赋 property；子节点字符串一律转 TextNode（自动转义）
  function h(tag, attrs) {
    var el = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        var v = attrs[k];
        if (v === null || v === undefined || v === false) { return; }
        if (k === "class") { el.className = v; }
        else if (k === "text") { el.textContent = String(v); }
        else if (k.slice(0, 2) === "on" && typeof v === "function") { el.addEventListener(k.slice(2), v); }
        else if (k === "value") { el.value = v; }
        else if (k === "checked" || k === "disabled") { el[k] = !!v; }
        else { el.setAttribute(k, String(v)); }
      });
    }
    for (var i = 2; i < arguments.length; i++) { append(el, arguments[i]); }
    return el;
  }
  function append(el, c) {
    if (c === null || c === undefined || c === false) { return; }
    if (Array.isArray(c)) { c.forEach(function (x) { append(el, x); }); return; }
    el.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  function clear(el) { while (el.firstChild) { el.removeChild(el.firstChild); } }
  function $(id) { return document.getElementById(id); }

  function fmtTime(ts) {
    if (typeof ts !== "number" || !isFinite(ts)) { return ts === null || ts === undefined ? "" : String(ts); }
    try { return new Date(ts * 1000).toLocaleString(state.lang === "zh" ? "zh-CN" : "en-US"); }
    catch (e) { return String(ts); }
  }
  function fmtNum(x, d) { return typeof x === "number" && isFinite(x) ? x.toFixed(d === undefined ? 3 : d) : (x === null || x === undefined ? "" : String(x)); }
  function fmtDur(s) {
    s = Math.floor(s || 0);
    var d = Math.floor(s / 86400), hh = Math.floor(s % 86400 / 3600), mm = Math.floor(s % 3600 / 60), ss = s % 60;
    return (d ? d + "d " : "") + hh + "h " + mm + "m " + ss + "s";
  }
  function tagChips(tags, ents) {
    var out = [];
    (tags || []).forEach(function (x) { out.push(h("span", { class: "tag", text: x })); });
    (ents || []).forEach(function (x) { out.push(h("span", { class: "tag ent", text: x })); });
    return out;
  }
  function jsonPre(obj) { return h("pre", { class: "json", text: JSON.stringify(obj, null, 2) }); }

  var toastTimer = null;
  function toast(msg, isErr) {
    var el = $("toast");
    el.textContent = msg;
    el.className = "toast" + (isErr ? " err" : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.className = "toast hidden"; }, 4500);
  }

  // ------------------------------------------------------------------ API
  function getToken() { try { return sessionStorage.getItem(TOKEN_KEY) || ""; } catch (e) { return ""; } }
  function setToken(v) { try { if (v) { sessionStorage.setItem(TOKEN_KEY, v); } else { sessionStorage.removeItem(TOKEN_KEY); } } catch (e) { /* 无 */ } }

  function ApiError(status, message) { this.status = status; this.message = message; }

  function api(method, path, body) {
    var headers = { "Accept": "application/json", "X-Lingshu-Console": "1" };
    var tok = getToken();
    if (tok) { headers["Authorization"] = "Bearer " + tok; }
    var opt = { method: method, headers: headers, credentials: "omit", cache: "no-store", redirect: "error",
                referrerPolicy: "no-referrer" };
    if (body !== undefined) { headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
    return fetch(path, opt).then(function (r) {
      return r.text().then(function (txt) {
        var data = null;
        try { data = txt ? JSON.parse(txt) : null; } catch (e) { data = null; }
        if (r.status === 401) { showLogin(); throw new ApiError(401, t("bad_token")); }
        if (!r.ok) {
          var msg = data && data.error && data.error.message ? data.error.message : ("HTTP " + r.status);
          throw new ApiError(r.status, msg);
        }
        return data;
      });
    });
  }

  function errorBox(e) {
    return h("p", { class: "error", role: "alert", text: t("err") + "：" + (e && e.message ? e.message : String(e)) });
  }

  // ------------------------------------------------------------------ 登录
  function showLogin() {
    $("login").classList.remove("hidden");
    $("view").classList.add("hidden");
    $("logout").classList.add("hidden");
    $("token-input").focus();
  }
  function hideLogin() {
    $("login").classList.add("hidden");
    $("view").classList.remove("hidden");
    $("logout").classList.toggle("hidden", !getToken());
  }

  // ------------------------------------------------------------------ 视图
  var VIEWS = {};
  function go(view) {
    state.view = view;
    Array.prototype.forEach.call(document.querySelectorAll("#tabs button"), function (b) {
      b.classList.toggle("active", b.getAttribute("data-view") === view);
    });
    var root = $("view");
    clear(root);
    root.appendChild(h("p", { class: "muted", text: t("loading") }));
    VIEWS[view](root);
  }

  VIEWS.overview = function (root) {
    Promise.all([api("GET", "/v1/status"), api("GET", "/v1/capabilities")]).then(function (res) {
      var st = res[0] || {}, cap = res[1] || {};
      hideLogin();
      clear(root);
      var counts = st.counts || {};
      var grid = h("div", { class: "grid" },
        stat(t("total_nodes"), st.total),
        stat(t("version"), st.version),
        stat(t("schema_version"), st.schema_version),
        stat(t("semantic_tier"), cap.semantic_tier),
        stat(t("db_path"), st.db, true));
      var lc = h("div", { class: "grid" }, LAYERS.map(function (l) { return stat(l, counts[l] === undefined ? 0 : counts[l]); }));
      var plugins = cap.plugins || {};
      var pt = h("table", null, h("thead", null, h("tr", null, h("th", { text: t("name") }), h("th", { text: t("dist") }),
        h("th", { text: t("version") }), h("th", { text: t("source") }), h("th", { text: t("provides") }), h("th", { text: t("status") }))));
      var tb = h("tbody");
      Object.keys(plugins).sort().forEach(function (k) {
        var p = plugins[k] || {};
        tb.appendChild(h("tr", null, h("td", { text: p.name || k }), h("td", { class: "mono", text: p.distribution || "" }),
          h("td", { class: "mono", text: p.version || "" }), h("td", { text: p.source || "" }),
          h("td", null, tagChips(p.provides || [])), h("td", { class: p.error ? "error" : "ok", text: p.error || t("ok") })));
      });
      if (!Object.keys(plugins).length) { tb.appendChild(h("tr", null, h("td", { colspan: "6", class: "muted", text: t("none") }))); }
      pt.appendChild(tb);
      var deps = cap.dependencies || {};
      var dt = h("table", null, h("thead", null, h("tr", null, h("th", { text: t("name") }), h("th", { text: t("version") }), h("th", { text: t("status") }))));
      var db = h("tbody");
      Object.keys(deps).sort().forEach(function (k) {
        var d = deps[k] || {};
        db.appendChild(h("tr", null, h("td", { class: "mono", text: k }), h("td", { class: "mono", text: d.version || "" }),
          h("td", { class: d.available ? "ok" : "muted", text: d.available ? t("available") : t("unavailable") })));
      });
      dt.appendChild(db);
      root.appendChild(h("div", { class: "card" }, h("div", { class: "row" }, h("h2", { class: "grow", text: t("tab_overview") }),
        h("button", { type: "button", text: t("refresh"), onclick: function () { go("overview"); } })), grid));
      root.appendChild(h("div", { class: "card" }, h("h3", { text: t("layer_counts") }), lc));
      root.appendChild(h("div", { class: "card" }, h("h3", { text: t("plugins") }), pt));
      root.appendChild(h("div", { class: "card" }, h("h3", { text: t("dependencies") }), dt));
      root.appendChild(h("div", { class: "card" }, h("h3", { text: t("models") + " / " + t("engine") + " / " + t("fallbacks") }),
        jsonPre({ models: cap.models, engine: cap.engine, fallbacks: cap.fallbacks })));
    }).catch(function (e) { if (e.status !== 401) { clear(root); root.appendChild(errorBox(e)); } });
  };

  function stat(k, v, small) {
    return h("div", { class: "stat" }, h("div", { class: "k", text: k }),
      h("div", { class: "v" + (small ? " small" : ""), text: v === undefined || v === null ? "—" : v }));
  }

  VIEWS.search = function (root) {
    clear(root);
    var q = h("input", { type: "text", class: "grow", id: "q", value: state.search.query, placeholder: t("query"), maxlength: "4096" });
    var lim = h("input", { type: "number", min: "1", max: "200", value: String(state.search.limit), id: "q-limit" });
    var out = h("div");
    var form = h("form", { class: "row", onsubmit: function (ev) {
      ev.preventDefault();
      state.search.query = q.value;
      state.search.limit = parseInt(lim.value, 10) || 10;
      if (!q.value.trim()) { return; }
      clear(out); out.appendChild(h("p", { class: "muted", text: t("loading") }));
      api("POST", "/v1/recall", { query: q.value, limit: state.search.limit }).then(function (r) {
        state.search.result = r; renderHits(out, r);
      }).catch(function (e) { clear(out); out.appendChild(errorBox(e)); });
    } }, h("label", { for: "q", text: t("query") }), q, h("label", { for: "q-limit", text: t("limit") }), lim,
      h("button", { type: "submit", class: "primary", text: t("search") }));
    root.appendChild(h("div", { class: "card" }, h("h2", { text: t("tab_search") }), form, out));
    if (state.search.result) { renderHits(out, state.search.result); }
    q.focus();
  };

  function renderHits(out, r) {
    clear(out);
    var hits = (r && r.hits) || [];
    if (!hits.length) { out.appendChild(h("p", { class: "muted", text: t("no_hits") })); }
    else {
      var tb = h("tbody");
      hits.forEach(function (n) {
        tb.appendChild(h("tr", null, h("td", { class: "num", text: fmtNum(n.score, 4) }),
          h("td", { class: "content", text: n.content }), h("td", null, h("span", { class: "layer", text: n.layer })),
          h("td", null, tagChips(n.tags)), h("td", { class: "num", text: fmtTime(n.created_at) }),
          h("td", null, h("button", { type: "button", class: "link", text: t("details"), onclick: function () { openNode(n.id); } }))));
      });
      out.appendChild(h("table", null, h("thead", null, h("tr", null, h("th", { text: t("score") }), h("th", { text: t("content") }),
        h("th", { text: t("layer") }), h("th", { text: t("tags") }), h("th", { text: t("created") }), h("th"))), tb));
    }
    if (r && r.negative && r.negative.length) {
      out.appendChild(h("h3", { text: t("negative") }));
      out.appendChild(jsonPre(r.negative));
    }
  }

  VIEWS.browse = function (root) {
    clear(root);
    var b = state.browse;
    var sel = h("select", { id: "b-layer" }, h("option", { value: "", text: t("all_layers") }),
      LAYERS.map(function (l) { var o = h("option", { value: l, text: l }); if (l === b.layer) { o.selected = true; } return o; }));
    var tag = h("input", { type: "text", id: "b-tag", value: b.tag, placeholder: t("tag_filter"), maxlength: "512" });
    var lim = h("select", { id: "b-limit" }, [20, 50, 100, 200].map(function (n) {
      var o = h("option", { value: String(n), text: String(n) }); if (n === b.limit) { o.selected = true; } return o; }));
    var out = h("div");
    var form = h("form", { class: "row", onsubmit: function (ev) {
      ev.preventDefault(); b.layer = sel.value; b.tag = tag.value; b.limit = parseInt(lim.value, 10) || 50; b.offset = 0; load();
    } }, h("label", { for: "b-layer", text: t("layer") }), sel, h("label", { for: "b-tag", text: t("tags") }), tag,
      h("label", { for: "b-limit", text: t("limit") }), lim, h("button", { type: "submit", class: "primary", text: t("apply") }));
    root.appendChild(h("div", { class: "card" }, h("h2", { text: t("tab_browse") }), form, out));

    function load() {
      clear(out); out.appendChild(h("p", { class: "muted", text: t("loading") }));
      var qs = new URLSearchParams();
      if (b.layer) { qs.set("layer", b.layer); }
      if (b.tag) { qs.set("tag", b.tag); }
      qs.set("offset", String(b.offset)); qs.set("limit", String(b.limit));
      api("GET", "/v1/nodes?" + qs.toString()).then(function (r) {
        hideLogin();
        clear(out);
        var nodes = r.nodes || [];
        if (!nodes.length) { out.appendChild(h("p", { class: "muted", text: t("empty") })); }
        else {
          var tb = h("tbody");
          nodes.forEach(function (n) {
            tb.appendChild(h("tr", null, h("td", { class: "content", text: n.content + (n.truncated ? " …" : "") }),
              h("td", null, h("span", { class: "layer", text: n.layer })), h("td", null, tagChips(n.tags, n.entities)),
              h("td", { class: "num", text: fmtNum(n.importance, 2) }), h("td", { class: "num", text: fmtTime(n.created_at) }),
              h("td", null, h("button", { type: "button", class: "link", text: t("details"), onclick: function () { openNode(n.id, load); } }))));
          });
          out.appendChild(h("table", null, h("thead", null, h("tr", null, h("th", { text: t("content") }), h("th", { text: t("layer") }),
            h("th", { text: t("tags") + " / " + t("entities") }), h("th", { text: t("importance") }), h("th", { text: t("created") }), h("th"))), tb));
        }
        var a = r.total ? r.offset + 1 : 0, z = Math.min(r.offset + nodes.length, r.total);
        out.appendChild(h("div", { class: "pager" },
          h("button", { type: "button", text: t("prev"), disabled: r.offset <= 0, onclick: function () { b.offset = Math.max(0, b.offset - b.limit); load(); } }),
          h("span", { class: "muted", text: t("page_info", { a: a, b: z, n: r.total }) }),
          h("button", { type: "button", text: t("next"), disabled: r.offset + nodes.length >= r.total, onclick: function () { b.offset += b.limit; load(); } })));
      }).catch(function (e) { if (e.status !== 401) { clear(out); out.appendChild(errorBox(e)); } });
    }
    load();
  };

  VIEWS.write = function (root) {
    clear(root);
    var content = h("textarea", { id: "w-content", maxlength: "100000", required: "required" });
    var tags = h("input", { type: "text", id: "w-tags", placeholder: t("tags_hint") });
    var ents = h("input", { type: "text", id: "w-ents", placeholder: t("entities_hint") });
    var imp = h("input", { type: "number", id: "w-imp", min: "0", max: "1", step: "0.05", placeholder: t("importance_hint") });
    var msg = h("div");
    var btn = h("button", { type: "submit", class: "primary", text: t("submit") });
    var form = h("form", { onsubmit: function (ev) {
      ev.preventDefault();
      clear(msg);
      if (!content.value.trim()) { msg.appendChild(h("p", { class: "error", text: t("content_required") })); return; }
      var body = { content: content.value };
      var tl = splitList(tags.value), el = splitList(ents.value);
      if (tl.length) { body.tags = tl; }
      if (el.length) { body.entities = el; }
      if (imp.value !== "") { body.importance = parseFloat(imp.value); }
      btn.disabled = true;
      api("POST", "/v1/perceive", body).then(function (r) {
        msg.appendChild(h("p", { class: "ok" }, t("written", { id: r.node_id, action: r.action, layer: r.layer }), " ",
          h("button", { type: "button", class: "link", text: t("details"), onclick: function () { openNode(r.node_id); } })));
        content.value = "";
      }).catch(function (e) { msg.appendChild(errorBox(e)); }).then(function () { btn.disabled = false; });
    } },
      h("div", { class: "field" }, h("label", { for: "w-content", text: t("content") }), content),
      h("div", { class: "row" }, h("div", { class: "field grow" }, h("label", { for: "w-tags", text: t("tags") }), tags),
        h("div", { class: "field grow" }, h("label", { for: "w-ents", text: t("entities") }), ents),
        h("div", { class: "field" }, h("label", { for: "w-imp", text: t("importance") }), imp)),
      btn, msg);
    root.appendChild(h("div", { class: "card" }, h("h2", { text: t("write_title") }), form));
  };

  function splitList(s) {
    return String(s || "").split(/[,，]/).map(function (x) { return x.trim(); }).filter(function (x) { return x.length > 0; });
  }

  VIEWS.exchange = function (root) {
    clear(root);
    var emsg = h("div");
    var ebtn = h("button", { type: "button", class: "primary", text: t("export_btn"), onclick: function () {
      ebtn.disabled = true; clear(emsg);
      api("GET", "/v1/export").then(function (r) {
        var blob = new Blob([JSON.stringify(r.backup, null, 2)], { type: "application/json" });
        var url = URL.createObjectURL(blob);
        var a = h("a", { href: url, download: "lingshu-ng-backup-" + new Date().toISOString().replace(/[:.]/g, "-") + ".json" });
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
        emsg.appendChild(h("p", { class: "ok", text: t("exported", { n: (r.report && r.report.exported_nodes) || 0 }) }));
      }).catch(function (e) { emsg.appendChild(errorBox(e)); }).then(function () { ebtn.disabled = false; });
    } });
    root.appendChild(h("div", { class: "card" }, h("h2", { text: t("export_title") }), h("p", { class: "muted", text: t("export_hint") }), ebtn, emsg));

    var file = h("input", { type: "file", id: "i-file", accept: ".json,application/json" });
    var summary = h("div");
    var chk = h("input", { type: "checkbox", id: "i-confirm" });
    var ibtn = h("button", { type: "button", class: "danger", text: t("import_btn"), disabled: true });
    var report = h("div");
    function sync() { ibtn.disabled = !(state.importData && chk.checked); }
    chk.addEventListener("change", sync);
    file.addEventListener("change", function () {
      state.importData = null; clear(summary); clear(report); chk.checked = false; sync();
      var f = file.files && file.files[0];
      if (!f) { return; }
      var rd = new FileReader();
      rd.onload = function () {
        try {
          var d = JSON.parse(String(rd.result));
          if (!d || typeof d !== "object" || Array.isArray(d)) { throw new Error("top-level must be an object"); }
          state.importData = d; state.importName = f.name;
          summary.appendChild(h("p", { text: t("file_summary", { f: f.name, n: Array.isArray(d.nodes) ? d.nodes.length : 0,
            e: Array.isArray(d.edges) ? d.edges.length : 0, v: d.meta && d.meta.version ? d.meta.version : "?" }) }));
        } catch (e) { summary.appendChild(h("p", { class: "error", text: t("bad_json", { e: e.message }) })); }
        sync();
      };
      rd.readAsText(f);
    });
    ibtn.addEventListener("click", function () {
      if (!state.importData || !chk.checked) { return; }
      ibtn.disabled = true; clear(report);
      api("POST", "/v1/import", { backup: state.importData, confirm: true }).then(function (r) {
        renderImportReport(report, r);
        toast(t("import_report") + " ✓");
      }).catch(function (e) { report.appendChild(errorBox(e)); }).then(function () { chk.checked = false; sync(); });
    });
    root.appendChild(h("div", { class: "card" }, h("h2", { text: t("import_title") }), h("p", { class: "muted", text: t("import_hint") }),
      h("div", { class: "row" }, h("label", { for: "i-file", text: t("choose_file") }), file), summary,
      h("div", { class: "row" }, chk, h("label", { for: "i-confirm", text: t("import_confirm") })), ibtn, report));
  };

  function renderImportReport(out, r) {
    clear(out);
    out.appendChild(h("h3", { text: t("import_report") }));
    var imp = r.imported || {}, rej = r.rejected_rows || {}, qua = r.quarantined || {};
    var tables = Object.keys(imp).concat(Object.keys(rej), Object.keys(qua)).filter(function (x, i, a) { return a.indexOf(x) === i; }).sort();
    var tb = h("tbody");
    tables.forEach(function (k) {
      var nrej = rej[k], nq = qua[k];
      tb.appendChild(h("tr", null, h("td", { class: "mono", text: k }), h("td", { class: "num", text: imp[k] === undefined ? "" : imp[k] }),
        h("td", { class: "num" + (nrej ? " warn" : ""), text: countOf(nrej) }), h("td", { class: "num" + (nq ? " warn" : ""), text: countOf(nq) })));
    });
    out.appendChild(h("table", null, h("thead", null, h("tr", null, h("th", { text: t("table") }), h("th", { text: t("imported") }),
      h("th", { text: t("rejected_rows") }), h("th", { text: t("quarantined") }))), tb));
    out.appendChild(h("dl", { class: "kv" },
      h("dt", { text: t("orphan_edges") }), h("dd", { text: r.orphan_edges_rejected }),
      h("dt", { text: t("dropped_columns") }), h("dd", { text: (r.dropped_columns || []).join(", ") || t("none") }),
      h("dt", { text: t("integrity") }), h("dd", { class: r.integrity_ok ? "ok" : "error", text: r.integrity_ok ? t("ok") : t("fail") })));
    out.appendChild(h("details", null, h("summary", { text: t("raw") }), jsonPre(r)));
  }
  function countOf(v) {
    if (v === undefined || v === null) { return ""; }
    if (Array.isArray(v)) { return String(v.length); }
    if (typeof v === "object") { return String(Object.keys(v).length); }
    return String(v);
  }

  VIEWS.health = function (root) {
    Promise.all([fetch("/healthz", { cache: "no-store", credentials: "omit" }).then(function (r) { return r.json(); }).catch(function () { return { ok: false }; }),
                 api("GET", "/v1/health")]).then(function (res) {
      var hz = res[0] || {}, hl = res[1] || {};
      hideLogin();
      clear(root);
      root.appendChild(h("div", { class: "card" }, h("div", { class: "row" }, h("h2", { class: "grow", text: t("tab_health") }),
        h("button", { type: "button", text: t("refresh"), onclick: function () { go("health"); } })),
        h("div", { class: "grid" },
          stat(t("healthz"), hz.ok ? t("ok") : t("fail")),
          stat(t("version"), hl.version),
          stat(t("uptime"), fmtDur(hl.uptime_s)),
          stat(t("started_at"), fmtTime(hl.started_at), true),
          stat(t("req_total"), hl.requests_total),
          stat(t("req_recent", { w: hl.recent_window_s }), hl.requests_recent),
          stat(t("auth"), hl.auth === "token" ? t("auth_token") : t("auth_loop"), true))));
    }).catch(function (e) { if (e.status !== 401) { clear(root); root.appendChild(errorBox(e)); } });
  };

  // ------------------------------------------------------------------ 节点详情 / 删除
  function closeModal() { $("modal").classList.add("hidden"); clear($("modal-body")); }

  function openNode(id, onChange) {
    var body = $("modal-body");
    clear(body);
    $("modal-title").textContent = t("node_detail");
    body.appendChild(h("p", { class: "muted", text: t("loading") }));
    $("modal").classList.remove("hidden");
    api("GET", "/v1/nodes/" + encodeURIComponent(id)).then(function (n) {
      clear(body);
      $("modal-title").textContent = t("node_detail") + " · " + n.id;
      body.appendChild(h("div", { class: "detail-content", text: n.content }));
      body.appendChild(h("dl", { class: "kv" },
        h("dt", { text: t("id") }), h("dd", { class: "mono", text: n.id }),
        h("dt", { text: t("layer") }), h("dd", null, h("span", { class: "layer", text: n.layer })),
        h("dt", { text: t("tags") }), h("dd", null, tagChips(n.tags)),
        h("dt", { text: t("entities") }), h("dd", null, tagChips([], n.entities)),
        h("dt", { text: t("importance") }), h("dd", { class: "mono", text: fmtNum(n.importance) }),
        h("dt", { text: t("confidence") }), h("dd", { class: "mono", text: fmtNum(n.confidence) }),
        h("dt", { text: t("modality") }), h("dd", { text: n.modality }),
        h("dt", { text: t("access_count") }), h("dd", { class: "mono", text: n.access_count }),
        h("dt", { text: t("created") }), h("dd", { text: fmtTime(n.created_at) }),
        h("dt", { text: t("last_access") }), h("dd", { text: fmtTime(n.last_access) }),
        h("dt", { text: t("protected") }), h("dd", { text: n.protected ? t("yes") : t("no") }),
        h("dt", { text: t("deletable") }), h("dd", { text: n.deletable ? t("yes") : t("no") })));
      var e = n.edges || {};
      body.appendChild(edgeTable(t("edges_out") + " (" + (e.outgoing_total || 0) + ")", e.outgoing || [], onChange));
      body.appendChild(edgeTable(t("edges_in") + " (" + (e.incoming_total || 0) + ")", e.incoming || [], onChange));
      var confirmSlot = h("div");
      var del = h("button", { type: "button", class: "danger", text: t("del"), disabled: !n.deletable, onclick: function () {
        clear(confirmSlot);
        var nEdges = (e.outgoing_total || 0) + (e.incoming_total || 0);
        var yes = h("button", { type: "button", class: "danger", text: t("del_yes") });
        yes.addEventListener("click", function () {
          yes.disabled = true;
          api("DELETE", "/v1/nodes/" + encodeURIComponent(n.id)).then(function (r) {
            closeModal();
            toast(t("deleted", { id: r.id, n: r.edges_removed }));
            if (onChange) { onChange(); }
          }).catch(function (err) { confirmSlot.appendChild(errorBox(err)); yes.disabled = false; });
        });
        confirmSlot.appendChild(h("div", { class: "confirm-box" }, h("strong", { text: t("del_confirm_title") }),
          h("p", { text: t("del_confirm_text", { id: n.id, n: nEdges }) }), h("div", { class: "row" }, yes,
            h("button", { type: "button", text: t("cancel"), onclick: function () { clear(confirmSlot); } }))));
      } });
      body.appendChild(h("div", { class: "row" }, del));
      body.appendChild(confirmSlot);
      body.appendChild(h("details", null, h("summary", { text: t("raw") }), jsonPre(n)));
    }).catch(function (err) { clear(body); body.appendChild(errorBox(err)); });
  }

  function edgeTable(title, edges, onChange) {
    var wrap = h("div", null, h("h3", { text: title }));
    if (!edges.length) { wrap.appendChild(h("p", { class: "muted", text: t("none") })); return wrap; }
    var tb = h("tbody");
    edges.forEach(function (x) {
      var p = x.peer;
      tb.appendChild(h("tr", null, h("td", { class: "mono", text: x.relation }),
        h("td", { class: "content" }, p ? h("button", { type: "button", class: "link", text: p.content + (p.truncated ? " …" : ""),
          onclick: function () { openNode(p.id, onChange); } }) : h("span", { class: "muted", text: x.source_id + " → " + x.target_id })),
        h("td", { class: "num", text: fmtNum(x.confidence, 2) }), h("td", { text: x.verified ? t("yes") : t("no") })));
    });
    wrap.appendChild(h("table", null, h("thead", null, h("tr", null, h("th", { text: t("relation") }), h("th", { text: t("peer") }),
      h("th", { text: t("confidence") }), h("th", { text: t("verified") }))), tb));
    return wrap;
  }

  // ------------------------------------------------------------------ 语言
  function applyLang() {
    document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
    document.title = "lingshu-ng " + t("console");
    Array.prototype.forEach.call(document.querySelectorAll("[data-i18n]"), function (el) {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    $("lang").textContent = state.lang === "zh" ? "EN" : "中文";
  }

  // ------------------------------------------------------------------ 启动
  function init() {
    try { var l = localStorage.getItem(LANG_KEY); if (l === "en" || l === "zh") { state.lang = l; } } catch (e) { /* 无 */ }
    applyLang();
    Array.prototype.forEach.call(document.querySelectorAll("#tabs button"), function (b) {
      b.addEventListener("click", function () { go(b.getAttribute("data-view")); });
    });
    $("lang").addEventListener("click", function () {
      state.lang = state.lang === "zh" ? "en" : "zh";
      try { localStorage.setItem(LANG_KEY, state.lang); } catch (e) { /* 无 */ }
      applyLang(); go(state.view);
    });
    $("logout").addEventListener("click", function () { setToken(""); showLogin(); });
    $("modal-close").addEventListener("click", closeModal);
    $("modal").addEventListener("click", function (ev) { if (ev.target === $("modal")) { closeModal(); } });
    document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") { closeModal(); } });
    $("login-form").addEventListener("submit", function (ev) {
      ev.preventDefault();
      var v = $("token-input").value.trim();
      $("login-error").textContent = "";
      if (!v) { return; }
      setToken(v);
      api("GET", "/v1/health").then(function () {
        $("token-input").value = "";
        hideLogin(); go(state.view);
      }).catch(function (e) { setToken(""); $("login-error").textContent = e.message || t("bad_token"); showLogin(); });
    });
    go("overview");
  }

  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init); } else { init(); }
})();
