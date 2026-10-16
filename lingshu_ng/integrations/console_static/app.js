// lingshu-ng 控制台前端 v2（原生 JS，无依赖，无外部资源）。
// 安全约定：所有服务端 / 用户数据只经 textContent / createTextNode / 属性赋值进入 DOM，全文件不用任何「HTML 字符串 → DOM」的 API；
// 图标用 createElementNS 逐个建 SVG 节点；令牌只存 sessionStorage，只以 Authorization 头发送（不进 URL、不进 cookie）；
// 写操作带 X-Lingshu-Console: 1。
(function () {
  "use strict";

  var TOKEN_KEY = "lingshu_ng_console_token";
  var LANG_KEY = "lingshu_ng_console_lang";
  var THEME_KEY = "lingshu_ng_console_theme";
  var SVG_NS = "http://www.w3.org/2000/svg";
  var LAYERS = ["anchor", "structure", "knowledge", "context", "self"];
  var VIEW_ORDER = ["overview", "search", "browse", "write", "exchange", "health"];

  var I18N = {
    zh: {
      console: "控制台", nav_workspace: "工作区", tab_overview: "概览", tab_search: "检索", tab_browse: "记忆浏览", tab_write: "写入",
      tab_exchange: "导入/导出", tab_health: "健康", logout: "退出", login_title: "需要令牌",
      login_hint: "此服务设置了 Bearer 令牌。令牌只保存在本标签页的 sessionStorage 中，关闭标签页即清除。",
      token: "令牌", login: "登录", bad_token: "令牌错误", loading: "加载中…", refresh: "刷新",
      sub_overview: "记忆库规模、能力档位与已加载组件一览。",
      sub_search: "按语义与关键词混合检索记忆，结果按相关度排序。",
      sub_browse: "按层与标签分页浏览全部记忆节点，点击任一行查看详情。",
      sub_write: "写入一条新记忆。系统会自动判定所属层，并与已有节点去重合并。",
      sub_exchange: "整库导出为 JSON 备份，或从备份恢复。",
      sub_health: "服务运行状态、请求量与鉴权模式。",
      total_nodes: "节点总数", db_path: "库路径", version: "版本", schema_version: "schema 版本",
      semantic_tier: "能力档位", layer_counts: "各层计数", layer_dist: "层分布", plugins: "插件", dependencies: "依赖",
      models: "模型", engine: "引擎", fallbacks: "退回记录", runtime_cfg: "运行时配置", name: "名称", dist: "发行包", source: "来源",
      provides: "提供", status: "状态", available: "可用", unavailable: "不可用", none: "（无）", no_plugins: "未加载插件",
      no_plugins_hint: "核心以纯标准库运行。安装 lingshu-ng-embed 等插件包后会自动出现在这里。",
      query: "查询", limit: "条数", search: "检索", search_ph: "输入要回忆的内容，例如「张总 喝什么」", no_hits: "没有命中",
      no_hits_hint: "换个说法，或减少关键词再试。", search_idle: "从这里开始检索", search_idle_hint: "支持中英文混合查询。按 / 可随时聚焦搜索框。",
      results_n: "{n} 条结果", took: "用时 {ms} ms", score: "分数", layer: "层",
      tags: "标签", entities: "实体", created: "创建时间", content: "原文", importance: "重要度",
      confidence: "置信度", all_layers: "全部", tag_filter: "按标签筛选（精确）", apply: "筛选", prev: "上一页",
      next: "下一页", page_info: "第 {a}–{b} 条，共 {n} 条", empty: "没有节点", empty_hint: "当前筛选条件下没有记忆。可以去「写入」添加第一条。",
      go_write: "去写入", details: "详情", per_page: "每页",
      negative: "否定 / 排除", write_title: "写入一条记忆（perceive）", tags_hint: "标签，逗号分隔",
      entities_hint: "实体，逗号分隔", importance_hint: "重要度 0–1（可空）", set_importance: "手动设置重要度", submit: "写入",
      content_ph: "例如：张总只喝乌龙茶，不喝咖啡。", submit_hint: "Ctrl / ⌘ + Enter 提交",
      written: "已写入：{id}（{action}，层 {layer}）", content_required: "正文不能为空", view_node: "查看节点",
      tips_title: "写好一条记忆", tip1_t: "一条一事", tip1: "每条只记一个事实，检索命中会更准。",
      tip2_t: "带上主体", tip2: "写清是谁、什么事，例如「张总」而不是「他」。", tip3_t: "标签与实体",
      tip3: "标签用于筛选；实体会进入关联图，帮助跨记忆联想。", layers_title: "五个层",
      l_anchor: "身份锚点，最稳定", l_structure: "结构与关系", l_knowledge: "事实与知识", l_context: "情境与近期事件", l_self: "自我状态与偏好",
      node_detail: "节点详情", modality: "模态", access_count: "访问次数", last_access: "最近访问",
      protected: "受保护", deletable: "可删除", yes: "是", no: "否", edges_out: "出边", edges_in: "入边",
      relation: "关系", peer: "对端", verified: "已验证", del: "删除节点", del_confirm_title: "确认删除？",
      del_confirm_text: "将删除节点 {id} 及其全部 {n} 条关联边，此操作不可撤销。", del_yes: "确认删除",
      danger_zone: "危险操作", danger_hint: "删除节点及其所有关联边，不可撤销。", not_deletable: "该节点受保护，不能删除。",
      cancel: "取消", deleted: "已删除 {id}（移除 {n} 条边）", export_title: "导出", export_hint:
      "导出整库为 JSON 备份（与 MemoryEngine.export_all 相同格式），在浏览器中下载。", export_btn: "导出并下载",
      exported: "已导出 {n} 个节点", import_title: "导入", import_hint:
      "选择 export 导出的 JSON 备份。同 id 的节点会被覆盖；共享层与治理表按规则隔离（不接受设计者密钥）。",
      choose_file: "选择文件", drop_title: "拖入备份文件，或点击选择", drop_hint: "仅支持 .json，文件只在浏览器内读取，确认后才上传。",
      file_summary: "文件 {f}：{n} 个节点、{e} 条边（meta.version = {v}）", file_stats: "{n} 个节点 · {e} 条边 · meta.version {v}",
      import_confirm: "我确认导入（同 id 节点将被覆盖）", import_btn: "导入", import_report: "导入报告",
      imported: "导入", overwritten: "覆盖", rejected_rows: "拒收行", quarantined: "隔离", dropped_columns: "丢弃列",
      orphan_edges: "孤儿边拒收", integrity: "完整性", bad_json: "文件不是合法 JSON：{e}", table: "表",
      count: "数", raw: "原始 JSON", healthz: "/healthz", uptime: "运行时长", started_at: "启动时间",
      req_total: "请求总数", req_recent: "最近 {w} 秒请求数", auth: "鉴权", auth_token: "Bearer 令牌",
      auth_loop: "无令牌（仅本机）", err: "错误", id: "ID", ok: "正常", fail: "异常",
      healthy: "服务运行正常", unhealthy: "服务异常", healthy_sub: "/healthz 返回正常，已运行 {d}。", unhealthy_sub: "/healthz 未返回正常，请检查服务日志。",
      auto_refresh: "每 10 秒自动刷新", updated_at: "更新于 {t}", connected: "已连接", disconnected: "未连接",
      copy: "复制", copied: "已复制", theme_light: "浅色", theme_dark: "深色", theme_system: "跟随系统",
      shortcuts: "键盘快捷键", sc_nav: "切换页面", sc_search: "聚焦检索", sc_help: "显示本帮助", sc_close: "关闭面板 / 对话框",
      sc_submit: "提交写入", retry: "重试"
    },
    en: {
      console: "Console", nav_workspace: "Workspace", tab_overview: "Overview", tab_search: "Search", tab_browse: "Browse", tab_write: "Write",
      tab_exchange: "Import / Export", tab_health: "Health", logout: "Sign out", login_title: "Token required",
      login_hint: "This server requires a Bearer token. It is kept only in this tab's sessionStorage and is cleared when the tab closes.",
      token: "Token", login: "Sign in", bad_token: "Wrong token", loading: "Loading…", refresh: "Refresh",
      sub_overview: "Size of the memory store, capability tier and loaded components.",
      sub_search: "Hybrid semantic and keyword recall, ranked by relevance.",
      sub_browse: "Page through every memory node by layer and tag. Click a row for details.",
      sub_write: "Write a new memory. The layer is assigned automatically and duplicates are merged.",
      sub_exchange: "Export the whole store as a JSON backup, or restore from one.",
      sub_health: "Service status, request volume and auth mode.",
      total_nodes: "Total nodes", db_path: "Database", version: "Version", schema_version: "Schema version",
      semantic_tier: "Capability tier", layer_counts: "Nodes per layer", layer_dist: "Layer distribution", plugins: "Plugins", dependencies: "Dependencies",
      models: "Models", engine: "Engine", fallbacks: "Fallbacks", runtime_cfg: "Runtime configuration", name: "Name", dist: "Distribution", source: "Source",
      provides: "Provides", status: "Status", available: "available", unavailable: "unavailable", none: "(none)", no_plugins: "No plugins loaded",
      no_plugins_hint: "The core runs on the standard library only. Plugin packages such as lingshu-ng-embed show up here once installed.",
      query: "Query", limit: "Limit", search: "Search", search_ph: "What do you want to recall? e.g. \u201cwhat does Mr. Zhang drink\u201d", no_hits: "No hits",
      no_hits_hint: "Try different wording or fewer keywords.", search_idle: "Start searching", search_idle_hint: "Mixed Chinese and English queries work. Press / to focus the search box anytime.",
      results_n: "{n} results", took: "{ms} ms", score: "Score", layer: "Layer",
      tags: "Tags", entities: "Entities", created: "Created", content: "Content", importance: "Importance",
      confidence: "Confidence", all_layers: "All", tag_filter: "Filter by tag (exact)", apply: "Apply", prev: "Previous",
      next: "Next", page_info: "{a}–{b} of {n}", empty: "No nodes", empty_hint: "Nothing matches these filters. Head to Write to add the first memory.",
      go_write: "Write a memory", details: "Details", per_page: "Per page",
      negative: "Negative / excluded", write_title: "Write a memory (perceive)", tags_hint: "Tags, comma separated",
      entities_hint: "Entities, comma separated", importance_hint: "Importance 0–1 (optional)", set_importance: "Set importance manually", submit: "Write",
      content_ph: "e.g. Mr. Zhang only drinks oolong tea, never coffee.", submit_hint: "Ctrl / ⌘ + Enter to submit",
      written: "Written: {id} ({action}, layer {layer})", content_required: "Content must not be empty", view_node: "View node",
      tips_title: "Writing good memories", tip1_t: "One fact each", tip1: "Store one fact per memory so recall hits precisely.",
      tip2_t: "Name the subject", tip2: "Say who and what \u2014 \u201cMr. Zhang\u201d, not \u201che\u201d.", tip3_t: "Tags and entities",
      tip3: "Tags are for filtering; entities join the association graph and link memories together.", layers_title: "The five layers",
      l_anchor: "Identity anchors, most stable", l_structure: "Structure and relations", l_knowledge: "Facts and knowledge", l_context: "Situations and recent events", l_self: "Self state and preferences",
      node_detail: "Node detail", modality: "Modality", access_count: "Access count", last_access: "Last access",
      protected: "Protected", deletable: "Deletable", yes: "yes", no: "no", edges_out: "Outgoing edges", edges_in: "Incoming edges",
      relation: "Relation", peer: "Peer", verified: "Verified", del: "Delete node", del_confirm_title: "Delete this node?",
      del_confirm_text: "Node {id} and all {n} attached edges will be deleted. This cannot be undone.", del_yes: "Delete",
      danger_zone: "Danger zone", danger_hint: "Deletes the node and every attached edge. Cannot be undone.", not_deletable: "This node is protected and cannot be deleted.",
      cancel: "Cancel", deleted: "Deleted {id} ({n} edges removed)", export_title: "Export", export_hint:
      "Export the whole database as a JSON backup (same format as MemoryEngine.export_all) and download it.", export_btn: "Export & download",
      exported: "Exported {n} nodes", import_title: "Import", import_hint:
      "Pick a JSON backup produced by export. Nodes with the same id are overwritten; shared layers and governance tables are quarantined (no designer key).",
      choose_file: "Choose file", drop_title: "Drop a backup file, or click to choose", drop_hint: ".json only. The file is read in the browser and uploaded only after you confirm.",
      file_summary: "File {f}: {n} nodes, {e} edges (meta.version = {v})", file_stats: "{n} nodes · {e} edges · meta.version {v}",
      import_confirm: "I confirm the import (nodes with the same id will be overwritten)", import_btn: "Import", import_report: "Import report",
      imported: "Imported", overwritten: "Overwritten", rejected_rows: "Rejected rows", quarantined: "Quarantined", dropped_columns: "Dropped columns",
      orphan_edges: "Orphan edges rejected", integrity: "Integrity", bad_json: "Not valid JSON: {e}", table: "Table",
      count: "Count", raw: "Raw JSON", healthz: "/healthz", uptime: "Uptime", started_at: "Started",
      req_total: "Total requests", req_recent: "Requests in last {w}s", auth: "Auth", auth_token: "Bearer token",
      auth_loop: "No token (loopback only)", err: "Error", id: "ID", ok: "OK", fail: "Failing",
      healthy: "All systems operational", unhealthy: "Service degraded", healthy_sub: "/healthz is OK. Up for {d}.", unhealthy_sub: "/healthz did not return OK. Check the service logs.",
      auto_refresh: "Auto-refresh every 10s", updated_at: "Updated {t}", connected: "Connected", disconnected: "Disconnected",
      copy: "Copy", copied: "Copied", theme_light: "Light", theme_dark: "Dark", theme_system: "System",
      shortcuts: "Keyboard shortcuts", sc_nav: "Switch page", sc_search: "Focus search", sc_help: "Show this help", sc_close: "Close panel / dialog",
      sc_submit: "Submit a memory", retry: "Retry"
    }
  };

  // 图标：24×24 描边路径（自绘，无外部资源）
  var ICONS = {
    grid: "M3 3h7v7H3z M14 3h7v7h-7z M14 14h7v7h-7z M3 14h7v7H3z",
    search: "M11 4a7 7 0 1 0 0 14a7 7 0 1 0 0-14z M21 21l-4.35-4.35",
    layers: "M12 2 2 7l10 5 10-5-10-5z M2 17l10 5 10-5 M2 12l10 5 10-5",
    pen: "M12 20h9 M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z",
    swap: "M7 4v16 M3 8l4-4 4 4 M17 20V4 M21 16l-4 4-4-4",
    pulse: "M22 12h-4l-3 9L9 3l-3 9H2",
    sun: "M12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8z M12 2v2 M12 20v2 M4.93 4.93l1.41 1.41 M17.66 17.66l1.41 1.41 M2 12h2 M20 12h2 M6.34 17.66l-1.41 1.41 M19.07 4.93l-1.41 1.41",
    moon: "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z",
    monitor: "M2 4h20v13H2z M8 21h8 M12 17v4",
    keyboard: "M2 6h20v12H2z M6 10h.01 M10 10h.01 M14 10h.01 M18 10h.01 M7 14h10",
    menu: "M4 6h16 M4 12h16 M4 18h16",
    x: "M18 6 6 18 M6 6l12 12",
    refresh: "M21 12a9 9 0 1 1-2.64-6.36 M21 3v6h-6",
    lock: "M5 11h14v10H5z M8 11V7a4 4 0 0 1 8 0v4",
    check: "M20 6 9 17l-5-5",
    checkCircle: "M22 11.08V12a10 10 0 1 1-5.93-9.14 M22 4 12 14.01l-3-3",
    alert: "M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20z M12 8v4 M12 16h.01",
    database: "M12 3c4.97 0 9 1.34 9 3s-4.03 3-9 3-9-1.34-9-3 4.03-3 9-3z M3 6v12c0 1.66 4.03 3 9 3s9-1.34 9-3V6 M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3",
    hash: "M4 9h16 M4 15h16 M10 3 8 21 M16 3l-2 18",
    cpu: "M4 4h16v16H4z M9 9h6v6H9z M9 1v3 M15 1v3 M9 20v3 M15 20v3 M20 9h3 M20 14h3 M1 9h3 M1 14h3",
    download: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4 M7 10l5 5 5-5 M12 15V3",
    upload: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4 M17 8l-5-5-5 5 M12 3v12",
    file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6",
    copy: "M9 9h13v13H9z M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1",
    trash: "M3 6h18 M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6 M10 11v6 M14 11v6 M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2",
    chevL: "M15 18l-6-6 6-6",
    chevR: "M9 18l6-6-6-6",
    inbox: "M22 12h-6l-2 3h-4l-2-3H2 M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z",
    clock: "M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20z M12 6v6l4 2",
    shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
    sparkle: "M12 3l1.9 5.8L20 10l-6.1 1.2L12 17l-1.9-5.8L4 10l6.1-1.2z",
    plug: "M9 2v6 M15 2v6 M6 8h12v4a6 6 0 0 1-12 0z M12 18v4",
    package: "M21 8 12 3 3 8v8l9 5 9-5z M3 8l9 5 9-5 M12 13v8",
    enter: "M9 10l-5 5 5 5 M20 4v7a4 4 0 0 1-4 4H4",
    filter: "M22 3H2l8 9.46V19l4 2v-8.54z"
  };

  var state = { lang: "zh", theme: "system", view: "overview", browse: { layer: "", tag: "", offset: 0, limit: 50 },
                search: { query: "", limit: 10, result: null, ms: null }, importData: null, importName: "", timers: [] };

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

  function icon(name, cls) {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", "i" + (cls ? " " + cls : ""));
    svg.setAttribute("aria-hidden", "true");
    var p = document.createElementNS(SVG_NS, "path");
    p.setAttribute("d", ICONS[name] || "");
    svg.appendChild(p);
    return svg;
  }
  function setIcon(btn, name) {
    Array.prototype.slice.call(btn.querySelectorAll("svg.i")).forEach(function (s) { s.parentNode.removeChild(s); });
    btn.insertBefore(icon(name), btn.firstChild);
  }

  function fmtTime(ts) {
    if (typeof ts !== "number" || !isFinite(ts)) { return ts === null || ts === undefined ? "" : String(ts); }
    try { return new Date(ts * 1000).toLocaleString(state.lang === "zh" ? "zh-CN" : "en-US", { hour12: false }); }
    catch (e) { return String(ts); }
  }
  function fmtRel(ts) {
    if (typeof ts !== "number" || !isFinite(ts)) { return ""; }
    var d = Date.now() / 1000 - ts, zh = state.lang === "zh";
    if (d < 0) { return fmtTime(ts); }
    if (d < 60) { return zh ? "刚刚" : "just now"; }
    if (d < 3600) { return Math.floor(d / 60) + (zh ? " 分钟前" : "m ago"); }
    if (d < 86400) { return Math.floor(d / 3600) + (zh ? " 小时前" : "h ago"); }
    if (d < 86400 * 30) { return Math.floor(d / 86400) + (zh ? " 天前" : "d ago"); }
    return fmtTime(ts);
  }
  function fmtNum(x, d) { return typeof x === "number" && isFinite(x) ? x.toFixed(d === undefined ? 3 : d) : (x === null || x === undefined ? "" : String(x)); }
  function fmtInt(x) {
    if (typeof x !== "number" || !isFinite(x)) { return x === null || x === undefined ? "—" : String(x); }
    try { return x.toLocaleString(state.lang === "zh" ? "zh-CN" : "en-US"); } catch (e) { return String(x); }
  }
  function fmtDur(s) {
    s = Math.floor(s || 0);
    var d = Math.floor(s / 86400), hh = Math.floor(s % 86400 / 3600), mm = Math.floor(s % 3600 / 60), ss = s % 60;
    if (d) { return d + "d " + hh + "h " + mm + "m"; }
    if (hh) { return hh + "h " + mm + "m " + ss + "s"; }
    if (mm) { return mm + "m " + ss + "s"; }
    return ss + "s";
  }
  function tagChips(tags, ents) {
    var out = [];
    (tags || []).forEach(function (x) { out.push(h("span", { class: "tag", title: x, text: x })); });
    (ents || []).forEach(function (x) { out.push(h("span", { class: "tag ent", title: x, text: x })); });
    return out;
  }
  function layerBadge(l) { return h("span", { class: "layer", "data-l": l || "", text: l || "—" }); }

  function copyText(s) {
    function fallback() {
      var ta = h("textarea", { class: "sr-only", readonly: "readonly" });
      ta.value = s; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); } catch (e) { /* 无 */ }
      document.body.removeChild(ta);
      return Promise.resolve();
    }
    if (navigator.clipboard && window.isSecureContext) { return navigator.clipboard.writeText(s).catch(fallback); }
    return fallback();
  }
  function copyBtn(getText, small) {
    var b = h("button", { type: "button", class: "ghost icon" + (small ? " sm" : ""), title: t("copy"), "aria-label": t("copy") });
    b.appendChild(icon("copy", "sm"));
    b.addEventListener("click", function (ev) {
      ev.stopPropagation();
      copyText(getText()).then(function () { setIcon(b, "check"); setTimeout(function () { setIcon(b, "copy"); }, 1200); toast(t("copied")); });
    });
    return b;
  }
  function jsonPre(obj) {
    var s = JSON.stringify(obj, null, 2);
    return h("div", { class: "code" }, h("pre", { class: "json", text: s }), h("span", { class: "copy" }, copyBtn(function () { return s; }, true)));
  }

  function toast(msg, isErr) {
    var box = $("toasts");
    var el = h("div", { class: "toast" + (isErr ? " err" : ""), role: isErr ? "alert" : "status" },
      h("span", { class: "ti" }, icon(isErr ? "alert" : "checkCircle")), h("span", { class: "tx", text: msg }));
    box.appendChild(el);
    while (box.children.length > 4) { box.removeChild(box.firstChild); }
    setTimeout(function () { el.classList.add("out"); setTimeout(function () { if (el.parentNode) { el.parentNode.removeChild(el); } }, 200); }, isErr ? 6500 : 3800);
  }

  // ------------------------------------------------------------------ 通用块
  function card(opts) {
    var head = null;
    if (opts.title) {
      head = h("div", { class: "card-head" }, opts.icon ? icon(opts.icon) : null, h(opts.h || "h3", { text: opts.title }),
        opts.sub ? h("span", { class: "sub", text: opts.sub }) : null,
        opts.right ? h("div", { class: "right" }, opts.right) : null);
    }
    return h("div", { class: "card" + (opts.cls ? " " + opts.cls : "") }, head,
      h("div", { class: "card-body" + (opts.flush ? " flush" : "") }, opts.body));
  }
  function pageHead(view, actions) {
    return h("div", { class: "page-head" },
      h("div", { class: "titles" }, h("h1", { text: t("tab_" + view) }), h("p", { text: t("sub_" + view) })),
      actions ? h("div", { class: "actions" }, actions) : null);
  }
  function emptyState(ic, title, hint, action) {
    return h("div", { class: "empty" }, h("div", { class: "ic" }, icon(ic)), h("b", { text: title }),
      hint ? h("p", { text: hint }) : null, action || null);
  }
  function errorBox(e, retry) {
    return h("div", { class: "alert err", role: "alert" }, icon("alert"),
      h("div", { class: "body" }, t("err") + "：" + (e && e.message ? e.message : String(e)),
        retry ? h("button", { type: "button", class: "link", text: t("retry"), onclick: retry }) : null));
  }
  function skeleton(kind) {
    if (kind === "stats") {
      return h("div", null, h("div", { class: "skel-grid" }, [1, 2, 3, 4].map(function () { return h("div", { class: "skel block" }); })),
        h("div", { class: "card pad" }, [1, 2, 3, 4, 5].map(function () { return h("div", { class: "skel line" }); })));
    }
    return h("div", { class: "card pad" }, [1, 2, 3, 4, 5, 6].map(function () { return h("div", { class: "skel line" }); }));
  }
  function refreshBtn(fn) {
    var b = h("button", { type: "button", onclick: fn }, icon("refresh"), t("refresh"));
    return b;
  }
  function stat(k, v, small, ic, foot) {
    return h("div", { class: "stat" }, h("div", { class: "k" }, ic ? h("span", { class: "ic" }, icon(ic, "sm")) : null, h("span", { text: k })),
      h("div", { class: "v" + (small ? " small" : ""), title: small && v ? String(v) : null, text: v === undefined || v === null || v === "" ? "—" : v }),
      foot ? h("div", { class: "foot", title: foot, text: foot }) : null);
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
    }, function (e) { setConn(false); throw new ApiError(0, e && e.message ? e.message : String(e)); });
  }

  // ------------------------------------------------------------------ 连接状态
  function setConn(ok, title, sub) {
    $("conn-dot").className = "dot " + (ok ? "ok" : "err");
    $("conn-title").textContent = title || (ok ? t("connected") : t("disconnected"));
    $("conn-sub").textContent = sub || "";
  }
  function pollConn() {
    api("GET", "/v1/health").then(function (hl) {
      setConn(true, t("connected") + " · v" + (hl.version || "?"), hl.auth === "token" ? t("auth_token") : t("auth_loop"));
    }).catch(function (e) { if (e.status !== 401) { setConn(false); } });
  }

  // ------------------------------------------------------------------ 登录
  function showLogin() {
    $("login-wrap").classList.remove("hidden");
    $("login").classList.remove("hidden");
    $("view").classList.add("hidden");
    $("logout").classList.add("hidden");
    setConn(false, t("login_title"), "");
    $("token-input").focus();
  }
  function hideLogin() {
    $("login-wrap").classList.add("hidden");
    $("login").classList.add("hidden");
    $("view").classList.remove("hidden");
    $("logout").classList.toggle("hidden", !getToken());
  }

  // ------------------------------------------------------------------ 路由
  var VIEWS = {};
  function stopTimers() { state.timers.forEach(function (x) { clearInterval(x); }); state.timers = []; }
  function viewFromHash() {
    var m = /^#\/([a-z]+)/.exec(location.hash || "");
    return m && VIEWS[m[1]] ? m[1] : null;
  }
  function navigate(view) {
    if (("#/" + view) !== location.hash) {
      try { history.pushState(null, "", "#/" + view); } catch (e) { /* 无 */ }
    }
    go(view);
  }
  function go(view) {
    if (!VIEWS[view]) { view = "overview"; }
    stopTimers();
    state.view = view;
    Array.prototype.forEach.call(document.querySelectorAll("#tabs button"), function (b) {
      var on = b.getAttribute("data-view") === view;
      b.classList.toggle("active", on);
      if (on) { b.setAttribute("aria-current", "page"); } else { b.removeAttribute("aria-current"); }
    });
    $("crumb").textContent = t("tab_" + view);
    document.title = t("tab_" + view) + " · lingshu-ng " + t("console");
    $("app").classList.remove("nav-open");
    var root = $("view");
    clear(root);
    root.className = "";
    void root.offsetWidth;
    root.className = "view-enter";
    VIEWS[view](root);
  }

  // ------------------------------------------------------------------ 概览
  VIEWS.overview = function (root) {
    root.appendChild(pageHead("overview"));
    var sk = skeleton("stats");
    root.appendChild(sk);
    Promise.all([api("GET", "/v1/status"), api("GET", "/v1/capabilities")]).then(function (res) {
      var st = res[0] || {}, cap = res[1] || {};
      hideLogin();
      clear(root);
      root.appendChild(pageHead("overview", refreshBtn(function () { go("overview"); })));
      var counts = st.counts || {};
      root.appendChild(h("div", { class: "grid" },
        stat(t("total_nodes"), fmtInt(st.total), false, "database", st.db ? String(st.db) : null),
        stat(t("version"), st.version, false, "package"),
        stat(t("schema_version"), st.schema_version, false, "hash"),
        stat(t("semantic_tier"), cap.semantic_tier, false, "sparkle")));

      // 层分布
      var total = 0;
      LAYERS.forEach(function (l) { total += counts[l] || 0; });
      var bar = h("div", { class: "dist-bar", role: "img", "aria-label": t("layer_dist") });
      var legend = h("div", { class: "dist-legend" });
      LAYERS.forEach(function (l) {
        var n = counts[l] === undefined ? 0 : counts[l];
        var pct = total ? n / total * 100 : 0;
        if (n > 0) {
          var seg = h("span", { class: "lc-" + l, title: l + " · " + n });
          seg.style.width = pct.toFixed(2) + "%";
          bar.appendChild(seg);
        }
        legend.appendChild(h("div", { class: "it lc-" + l, title: t("l_" + l) }, h("span", { class: "sw" }), h("span", { class: "nm", text: l }),
          h("span", { class: "ct", text: fmtInt(n) }), h("span", { class: "pc", text: total ? Math.round(pct) + "%" : "—" })));
      });
      root.appendChild(card({ title: t("layer_counts"), icon: "layers", sub: t("total_nodes") + " " + fmtInt(total), body: [bar, legend] }));

      // 插件
      var plugins = cap.plugins || {};
      var keys = Object.keys(plugins).sort();
      var pbody;
      if (!keys.length) { pbody = emptyState("plug", t("no_plugins"), t("no_plugins_hint")); }
      else {
        var tb = h("tbody");
        keys.forEach(function (k) {
          var p = plugins[k] || {};
          tb.appendChild(h("tr", null, h("td", null, h("b", { text: p.name || k })), h("td", { class: "mono nowrap", text: p.distribution || "" }),
            h("td", { class: "num", text: p.version || "" }), h("td", { class: "nowrap muted", text: p.source || "" }),
            h("td", null, tagChips(p.provides || [])),
            h("td", { class: "nowrap" }, p.error ? h("span", { class: "badge err", title: p.error }, h("span", { class: "dot err" }), t("fail"))
              : h("span", { class: "badge ok" }, h("span", { class: "dot ok" }), t("ok")))));
        });
        pbody = h("div", { class: "table-wrap" }, h("table", null, h("thead", null, h("tr", null, h("th", { text: t("name") }), h("th", { text: t("dist") }),
          h("th", { text: t("version") }), h("th", { text: t("source") }), h("th", { text: t("provides") }), h("th", { text: t("status") }))), tb));
        keys.forEach(function (k) {
          var p = plugins[k] || {};
          if (p.error) { pbody.appendChild(h("div", { class: "alert err" }, icon("alert"), h("div", { class: "body mono", text: (p.name || k) + ": " + p.error }))); }
        });
      }
      root.appendChild(card({ title: t("plugins"), icon: "plug", sub: String(keys.length), body: pbody, flush: keys.length > 0 }));

      // 依赖 + 运行时
      var deps = cap.dependencies || {};
      var dl = h("div", { class: "list" });
      var dk = Object.keys(deps).sort();
      dk.forEach(function (k) {
        var d = deps[k] || {};
        dl.appendChild(h("div", { class: "li" }, h("span", { class: "nm", text: k }), h("span", { class: "ver", text: d.version || "" }),
          h("span", { class: "badge" + (d.available ? " ok" : "") }, h("span", { class: "dot" + (d.available ? " ok" : "") }), d.available ? t("available") : t("unavailable"))));
      });
      if (!dk.length) { dl.appendChild(h("div", { class: "li muted", text: t("none") })); }
      root.appendChild(h("div", { class: "cols-2 even" },
        card({ title: t("dependencies"), icon: "package", body: dl, flush: true }),
        card({ title: t("runtime_cfg"), icon: "cpu", sub: t("models") + " · " + t("engine") + " · " + t("fallbacks"),
               body: jsonPre({ models: cap.models, engine: cap.engine, fallbacks: cap.fallbacks }) })));
    }).catch(function (e) {
      if (e.status !== 401) { clear(root); root.appendChild(pageHead("overview")); root.appendChild(errorBox(e, function () { go("overview"); })); }
    });
  };

  // ------------------------------------------------------------------ 检索
  function queryTerms(q) {
    var out = [];
    String(q || "").split(/\s+/).forEach(function (w) {
      w = w.trim();
      if (!w) { return; }
      out.push(w);
      if (/[\u3400-\u9fff]/.test(w) && w.length > 2) {
        for (var i = 0; i + 2 <= w.length; i++) { out.push(w.slice(i, i + 2)); }
      }
    });
    return out.filter(function (x, i, a) { return a.indexOf(x) === i; }).sort(function (a, b) { return b.length - a.length; });
  }
  function highlight(text, terms) {
    text = String(text === undefined || text === null ? "" : text);
    if (!terms.length) { return [text]; }
    var esc = terms.map(function (x) { return x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); });
    var re;
    try { re = new RegExp("(" + esc.join("|") + ")", "gi"); } catch (e) { return [text]; }
    var out = [], last = 0, m;
    while ((m = re.exec(text)) !== null) {
      if (m[0] === "") { re.lastIndex++; continue; }
      if (m.index > last) { out.push(text.slice(last, m.index)); }
      out.push(h("mark", { text: m[0] }));
      last = m.index + m[0].length;
    }
    if (last < text.length) { out.push(text.slice(last)); }
    return out;
  }

  VIEWS.search = function (root) {
    root.appendChild(pageHead("search"));
    var q = h("input", { type: "search", id: "q", value: state.search.query, placeholder: t("search_ph"), maxlength: "4096", autocomplete: "off", "aria-label": t("query") });
    var lim = h("input", { type: "number", min: "1", max: "200", value: String(state.search.limit), id: "q-limit" });
    var btn = h("button", { type: "submit", class: "primary lg" }, t("search"));
    var out = h("div");
    function run() {
      state.search.query = q.value;
      state.search.limit = parseInt(lim.value, 10) || 10;
      if (!q.value.trim()) { q.focus(); return; }
      clear(out); out.appendChild(skeleton());
      btn.disabled = true;
      var t0 = (window.performance && performance.now) ? performance.now() : Date.now();
      api("POST", "/v1/recall", { query: q.value, limit: state.search.limit }).then(function (r) {
        var t1 = (window.performance && performance.now) ? performance.now() : Date.now();
        state.search.result = r; state.search.ms = Math.round(t1 - t0);
        renderHits(out, r);
      }).catch(function (e) { clear(out); out.appendChild(errorBox(e, run)); }).then(function () { btn.disabled = false; });
    }
    var form = h("form", { onsubmit: function (ev) { ev.preventDefault(); run(); } },
      h("div", { class: "row" }, h("div", { class: "input-icon grow" }, icon("search"), q, h("kbd", { text: "/" })), btn),
      h("div", { class: "search-opts" }, h("label", { for: "q-limit", text: t("limit") }), lim));
    root.appendChild(h("div", { class: "card search-hero" }, form));
    root.appendChild(out);
    if (state.search.result) { renderHits(out, state.search.result); }
    else { out.appendChild(h("div", { class: "card" }, emptyState("search", t("search_idle"), t("search_idle_hint")))); }
    q.focus();
  };

  function renderHits(out, r) {
    clear(out);
    var hits = (r && r.hits) || [];
    var terms = queryTerms(state.search.query);
    if (!hits.length) {
      out.appendChild(h("div", { class: "card" }, emptyState("inbox", t("no_hits"), t("no_hits_hint"))));
    } else {
      var maxScore = 0;
      hits.forEach(function (n) { if (typeof n.score === "number" && n.score > maxScore) { maxScore = n.score; } });
      out.appendChild(h("div", { class: "search-meta" }, h("span", { text: t("results_n", { n: hits.length }) }),
        state.search.ms !== null ? h("span", { class: "faint", text: "·" }) : null,
        state.search.ms !== null ? h("span", { text: t("took", { ms: state.search.ms }) }) : null));
      var list = h("div", { class: "hits" });
      hits.forEach(function (n, i) {
        var meter = h("span");
        meter.style.width = (maxScore > 0 && typeof n.score === "number" ? Math.max(4, n.score / maxScore * 100) : 0).toFixed(1) + "%";
        list.appendChild(h("article", { class: "hit" },
          h("div", { class: "content" }, highlight(n.content, terms)),
          h("div", { class: "score" }, h("span", { class: "rank", text: "#" + (i + 1) }), h("b", { text: fmtNum(n.score, 4) }), h("div", { class: "meter" }, meter)),
          h("div", { class: "meta" }, layerBadge(n.layer), tagChips(n.tags),
            n.created_at !== undefined ? h("span", { class: "sep" }) : null,
            n.created_at !== undefined ? h("span", { title: fmtTime(n.created_at), text: fmtRel(n.created_at) }) : null,
            h("span", { class: "grow" }),
            h("button", { type: "button", class: "link", text: t("details"), onclick: function () { openNode(n.id); } }))));
      });
      out.appendChild(list);
    }
    if (r && r.negative && r.negative.length) {
      out.appendChild(card({ title: t("negative"), icon: "filter", body: jsonPre(r.negative) }));
    }
  }

  // ------------------------------------------------------------------ 浏览
  VIEWS.browse = function (root) {
    var b = state.browse;
    root.appendChild(pageHead("browse"));
    var seg = h("div", { class: "seg", role: "group", "aria-label": t("layer") });
    [""].concat(LAYERS).forEach(function (l) {
      seg.appendChild(h("button", { type: "button", class: l === b.layer ? "on" : "", "data-layer": l, "aria-pressed": l === b.layer ? "true" : "false",
        text: l || t("all_layers"), onclick: function () { b.layer = l; b.offset = 0; syncSeg(); load(); } }));
    });
    function syncSeg() {
      Array.prototype.forEach.call(seg.children, function (x) {
        var on = x.getAttribute("data-layer") === b.layer;
        x.classList.toggle("on", on); x.setAttribute("aria-pressed", on ? "true" : "false");
      });
    }
    var tag = h("input", { type: "search", id: "b-tag", value: b.tag, placeholder: t("tag_filter"), maxlength: "512", "aria-label": t("tags") });
    var lim = h("select", { id: "b-limit", "aria-label": t("per_page") }, [20, 50, 100, 200].map(function (n) {
      var o = h("option", { value: String(n), text: n + " / " + (state.lang === "zh" ? "页" : "page") }); if (n === b.limit) { o.selected = true; } return o; }));
    lim.addEventListener("change", function () { b.limit = parseInt(lim.value, 10) || 50; b.offset = 0; load(); });
    var form = h("form", { class: "toolbar", onsubmit: function (ev) {
      ev.preventDefault(); b.tag = tag.value.trim(); b.offset = 0; load();
    } }, seg, h("span", { class: "grow" }), h("div", { class: "input-icon" }, icon("filter"), tag), lim);
    var out = h("div");
    root.appendChild(h("div", { class: "card" }, form, out));

    function load() {
      clear(out); out.appendChild(h("div", { class: "card-body" }, [1, 2, 3, 4, 5, 6].map(function () { return h("div", { class: "skel line" }); })));
      var qs = new URLSearchParams();
      if (b.layer) { qs.set("layer", b.layer); }
      if (b.tag) { qs.set("tag", b.tag); }
      qs.set("offset", String(b.offset)); qs.set("limit", String(b.limit));
      api("GET", "/v1/nodes?" + qs.toString()).then(function (r) {
        hideLogin();
        clear(out);
        var nodes = r.nodes || [];
        if (!nodes.length) {
          out.appendChild(emptyState("inbox", t("empty"), t("empty_hint"),
            h("button", { type: "button", class: "sm", onclick: function () { navigate("write"); } }, icon("pen", "sm"), t("go_write"))));
        } else {
          var tb = h("tbody");
          nodes.forEach(function (n) {
            var tr = h("tr", { class: "clickable", tabindex: "0" }, h("td", { class: "content" }, h("div", { class: "clamp", text: n.content + (n.truncated ? " …" : "") })),
              h("td", null, layerBadge(n.layer)), h("td", null, tagChips(n.tags, n.entities)),
              h("td", { class: "num" }, fmtNum(n.importance, 2)), h("td", { class: "num", title: fmtTime(n.created_at), text: fmtRel(n.created_at) }),
              h("td", { class: "act" }, h("button", { type: "button", class: "link", text: t("details"), onclick: function (ev) { ev.stopPropagation(); openNode(n.id, load); } })));
            tr.addEventListener("click", function () { openNode(n.id, load); });
            tr.addEventListener("keydown", function (ev) { if (ev.key === "Enter") { openNode(n.id, load); } });
            tb.appendChild(tr);
          });
          out.appendChild(h("div", { class: "table-wrap" }, h("table", null, h("thead", null, h("tr", null, h("th", { text: t("content") }), h("th", { text: t("layer") }),
            h("th", { text: t("tags") + " / " + t("entities") }), h("th", { text: t("importance") }), h("th", { text: t("created") }), h("th"))), tb)));
        }
        var a = r.total ? r.offset + 1 : 0, z = Math.min(r.offset + nodes.length, r.total);
        var prev = h("button", { type: "button", class: "sm", disabled: r.offset <= 0, "aria-label": t("prev"), onclick: function () { b.offset = Math.max(0, b.offset - b.limit); load(); } }, icon("chevL", "sm"), t("prev"));
        var next = h("button", { type: "button", class: "sm", disabled: r.offset + nodes.length >= r.total, "aria-label": t("next"), onclick: function () { b.offset += b.limit; load(); } }, t("next"), icon("chevR", "sm"));
        out.appendChild(h("div", { class: "pager" }, h("span", { class: "info", text: t("page_info", { a: a, b: z, n: r.total }) }), prev, next));
      }).catch(function (e) { if (e.status !== 401) { clear(out); out.appendChild(h("div", { class: "card-body" }, errorBox(e, load))); } });
    }
    load();
  };

  // ------------------------------------------------------------------ 写入
  VIEWS.write = function (root) {
    root.appendChild(pageHead("write"));
    var content = h("textarea", { id: "w-content", maxlength: "100000", required: "required", placeholder: t("content_ph") });
    var counter = h("span", { class: "counter", text: "0 / 100000" });
    var tags = h("input", { type: "text", id: "w-tags", placeholder: t("tags_hint") });
    var ents = h("input", { type: "text", id: "w-ents", placeholder: t("entities_hint") });
    var tagPrev = h("div"), entPrev = h("div");
    var useImp = h("input", { type: "checkbox", id: "w-imp-on" });
    var imp = h("input", { type: "range", id: "w-imp", min: "0", max: "1", step: "0.05", value: "0.5", disabled: true, "aria-label": t("importance") });
    var impOut = h("output", { for: "w-imp", class: "faint", text: "—" });
    var msg = h("div");
    var btn = h("button", { type: "submit", class: "primary" }, icon("check", "sm"), t("submit"));

    content.addEventListener("input", function () { counter.textContent = fmtInt(content.value.length) + " / 100000"; });
    function prevChips(input, box, ent) {
      input.addEventListener("input", function () { clear(box); var l = splitList(input.value); if (l.length) { append(box, ent ? tagChips([], l) : tagChips(l)); } });
    }
    prevChips(tags, tagPrev, false); prevChips(ents, entPrev, true);
    useImp.addEventListener("change", function () { imp.disabled = !useImp.checked; impOut.textContent = useImp.checked ? Number(imp.value).toFixed(2) : "—"; impOut.className = useImp.checked ? "" : "faint"; });
    imp.addEventListener("input", function () { impOut.textContent = Number(imp.value).toFixed(2); });

    var form = h("form", { onsubmit: function (ev) {
      ev.preventDefault();
      clear(msg);
      if (!content.value.trim()) { msg.appendChild(h("div", { class: "alert err" }, icon("alert"), h("div", { class: "body", text: t("content_required") }))); content.focus(); return; }
      var body = { content: content.value };
      var tl = splitList(tags.value), el = splitList(ents.value);
      if (tl.length) { body.tags = tl; }
      if (el.length) { body.entities = el; }
      if (useImp.checked) { body.importance = parseFloat(imp.value); }
      btn.disabled = true;
      api("POST", "/v1/perceive", body).then(function (r) {
        msg.appendChild(h("div", { class: "alert ok", role: "status" }, icon("checkCircle"), h("div", { class: "body" },
          t("written", { id: r.node_id, action: r.action, layer: r.layer }), " ",
          h("button", { type: "button", class: "link", text: t("view_node"), onclick: function () { openNode(r.node_id); } }))));
        toast(t("written", { id: r.node_id, action: r.action, layer: r.layer }));
        content.value = ""; counter.textContent = "0 / 100000";
        content.focus();
      }).catch(function (e) { msg.appendChild(errorBox(e)); }).then(function () { btn.disabled = false; });
    } },
      h("div", { class: "field" }, h("div", { class: "label-row" }, h("label", { for: "w-content", text: t("content") }), counter), content),
      h("div", { class: "cols-2 even" },
        h("div", { class: "field" }, h("label", { for: "w-tags", text: t("tags") }), tags, tagPrev),
        h("div", { class: "field" }, h("label", { for: "w-ents", text: t("entities") }), ents, entPrev)),
      h("div", { class: "field" }, h("div", { class: "label-row" }, h("label", { class: "switch", for: "w-imp-on" }, useImp, h("span", { text: t("set_importance") })), impOut),
        h("div", { class: "range-row" }, imp)),
      h("div", { class: "form-foot" }, btn, h("span", { class: "muted" }, h("kbd", { text: "Ctrl" }), "+", h("kbd", { text: "Enter" }))),
      msg);
    content.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); if (form.requestSubmit) { form.requestSubmit(btn); } else { btn.click(); } }
    });

    var tips = h("div", { class: "tips" }, [["tip1_t", "tip1"], ["tip2_t", "tip2"], ["tip3_t", "tip3"]].map(function (p, i) {
      return h("div", { class: "tip" }, h("span", { class: "n", text: String(i + 1) }), h("div", null, h("b", { text: t(p[0]) }), h("span", { text: t(p[1]) })));
    }));
    var legend = h("div", { class: "layer-legend" }, LAYERS.map(function (l) { return h("div", { class: "it" }, layerBadge(l), h("span", { text: t("l_" + l) })); }));
    root.appendChild(h("div", { class: "cols-2" },
      card({ title: t("write_title"), icon: "pen", h: "h2", body: form }),
      h("div", null, card({ title: t("tips_title"), icon: "sparkle", body: tips }), card({ title: t("layers_title"), icon: "layers", body: legend }))));
    content.focus();
  };

  function splitList(s) {
    return String(s || "").split(/[,，]/).map(function (x) { return x.trim(); }).filter(function (x) { return x.length > 0; });
  }

  // ------------------------------------------------------------------ 导入 / 导出
  VIEWS.exchange = function (root) {
    root.appendChild(pageHead("exchange"));
    var emsg = h("div");
    var ebtn = h("button", { type: "button", class: "primary" }, icon("download", "sm"), t("export_btn"));
    ebtn.addEventListener("click", function () {
      ebtn.disabled = true; clear(emsg);
      api("GET", "/v1/export").then(function (r) {
        var blob = new Blob([JSON.stringify(r.backup, null, 2)], { type: "application/json" });
        var url = URL.createObjectURL(blob);
        var a = h("a", { href: url, download: "lingshu-ng-backup-" + new Date().toISOString().replace(/[:.]/g, "-") + ".json" });
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
        var msgx = t("exported", { n: (r.report && r.report.exported_nodes) || 0 });
        emsg.appendChild(h("div", { class: "alert ok", role: "status" }, icon("checkCircle"), h("div", { class: "body", text: msgx })));
        toast(msgx);
      }).catch(function (e) { emsg.appendChild(errorBox(e)); }).then(function () { ebtn.disabled = false; });
    });
    var exportCard = card({ title: t("export_title"), icon: "download", h: "h2", body: [h("p", { class: "muted", text: t("export_hint") }), h("div", { class: "steps-actions" }, h("div", null, ebtn), emsg)] });

    var file = h("input", { type: "file", id: "i-file", accept: ".json,application/json", "aria-label": t("choose_file") });
    var drop = h("label", { class: "dropzone", for: "i-file" }, h("span", { class: "ic" }, icon("upload")), h("b", { text: t("drop_title") }),
      h("span", { class: "muted", text: t("drop_hint") }), file);
    var summary = h("div");
    var chk = h("input", { type: "checkbox", id: "i-confirm" });
    var ibtn = h("button", { type: "button", class: "danger", disabled: true }, icon("upload", "sm"), t("import_btn"));
    var report = h("div");
    function sync() { ibtn.disabled = !(state.importData && chk.checked); }
    chk.addEventListener("change", sync);
    ["dragenter", "dragover"].forEach(function (evn) { drop.addEventListener(evn, function (ev) { ev.preventDefault(); drop.classList.add("over"); }); });
    ["dragleave", "drop"].forEach(function (evn) { drop.addEventListener(evn, function () { drop.classList.remove("over"); }); });
    drop.addEventListener("drop", function (ev) {
      ev.preventDefault();
      var f = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
      if (f) { readFile(f); }
    });
    file.addEventListener("change", function () { var f = file.files && file.files[0]; if (f) { readFile(f); } });
    function readFile(f) {
      state.importData = null; clear(summary); clear(report); chk.checked = false; sync();
      var rd = new FileReader();
      rd.onload = function () {
        try {
          var d = JSON.parse(String(rd.result));
          if (!d || typeof d !== "object" || Array.isArray(d)) { throw new Error("top-level must be an object"); }
          state.importData = d; state.importName = f.name;
          var nn = Array.isArray(d.nodes) ? d.nodes.length : 0, ne = Array.isArray(d.edges) ? d.edges.length : 0, v = d.meta && d.meta.version ? d.meta.version : "?";
          summary.appendChild(h("div", { class: "file-pill", title: t("file_summary", { f: f.name, n: nn, e: ne, v: v }) },
            h("span", { class: "ic" }, icon("file", "lg")), h("div", { class: "meta" }, h("b", { text: f.name }), h("span", { text: t("file_stats", { n: fmtInt(nn), e: fmtInt(ne), v: v }) })),
            h("span", { class: "badge accent", text: (f.size / 1024).toFixed(1) + " KB" })));
        } catch (e) { summary.appendChild(h("div", { class: "alert err" }, icon("alert"), h("div", { class: "body", text: t("bad_json", { e: e.message }) }))); }
        sync();
      };
      rd.readAsText(f);
    }
    ibtn.addEventListener("click", function () {
      if (!state.importData || !chk.checked) { return; }
      ibtn.disabled = true; clear(report);
      api("POST", "/v1/import", { backup: state.importData, confirm: true }).then(function (r) {
        renderImportReport(report, r);
        toast(t("import_report") + " ✓");
      }).catch(function (e) { report.appendChild(errorBox(e)); }).then(function () { chk.checked = false; sync(); });
    });
    var importCard = card({ title: t("import_title"), icon: "upload", h: "h2", body: [h("p", { class: "muted", text: t("import_hint") }),
      h("div", { class: "steps-actions" }, drop, summary,
        h("div", { class: "check" }, chk, h("label", { for: "i-confirm", text: t("import_confirm") })), h("div", null, ibtn), report)] });
    root.appendChild(h("div", { class: "cols-2 even" }, exportCard, importCard));
  };

  function renderImportReport(out, r) {
    clear(out);
    var imp = r.imported || {}, rej = r.rejected_rows || {}, qua = r.quarantined || {}, ovw = r.overwritten || {};
    var tables = Object.keys(imp).concat(Object.keys(rej), Object.keys(qua), Object.keys(ovw)).filter(function (x, i, a) { return a.indexOf(x) === i; }).sort();
    var tb = h("tbody");
    tables.forEach(function (k) {
      var nrej = rej[k], nq = qua[k];
      tb.appendChild(h("tr", null, h("td", { class: "mono", text: k }), h("td", { class: "num right", text: imp[k] === undefined ? "" : imp[k] }),
        h("td", { class: "num right" + (ovw[k] ? " warn" : ""), text: countOf(ovw[k]) }),
        h("td", { class: "num right" + (nrej ? " warn" : ""), text: countOf(nrej) }), h("td", { class: "num right" + (nq ? " warn" : ""), text: countOf(nq) })));
    });
    out.appendChild(h("div", { class: "section-title", text: t("import_report") }));
    out.appendChild(h("div", { class: "edge-list table-wrap" }, h("table", null, h("thead", null, h("tr", null, h("th", { text: t("table") }), h("th", { class: "right", text: t("imported") }),
      h("th", { class: "right", text: t("overwritten") }), h("th", { class: "right", text: t("rejected_rows") }), h("th", { class: "right", text: t("quarantined") }))), tb)));
    out.appendChild(h("dl", { class: "kv mt" },
      h("dt", { text: t("orphan_edges") }), h("dd", { class: "mono", text: r.orphan_edges_rejected }),
      h("dt", { text: t("dropped_columns") }), h("dd", { text: (r.dropped_columns || []).join(", ") || t("none") }),
      h("dt", { text: t("integrity") }), h("dd", null, r.integrity_ok ? h("span", { class: "badge ok" }, h("span", { class: "dot ok" }), t("ok"))
        : h("span", { class: "badge err" }, h("span", { class: "dot err" }), t("fail")))));
    out.appendChild(h("details", null, h("summary", { text: t("raw") }), jsonPre(r)));
  }
  function countOf(v) {
    if (v === undefined || v === null) { return ""; }
    if (Array.isArray(v)) { return String(v.length); }
    if (typeof v === "object") { return String(Object.keys(v).length); }
    return String(v);
  }

  // ------------------------------------------------------------------ 健康
  var autoRefresh = true;
  VIEWS.health = function (root) {
    root.appendChild(pageHead("health"));
    root.appendChild(skeleton("stats"));
    function load(silent) {
      Promise.all([fetch("/healthz", { cache: "no-store", credentials: "omit" }).then(function (r) { return r.json(); }).catch(function () { return { ok: false }; }),
                   api("GET", "/v1/health")]).then(function (res) {
        if (state.view !== "health") { return; }
        var hz = res[0] || {}, hl = res[1] || {};
        hideLogin();
        setConn(!!hz.ok, t("connected") + " · v" + (hl.version || "?"), hl.auth === "token" ? t("auth_token") : t("auth_loop"));
        clear(root);
        var sw = h("input", { type: "checkbox", id: "h-auto", checked: autoRefresh });
        sw.addEventListener("change", function () { autoRefresh = sw.checked; arm(); });
        root.appendChild(pageHead("health", refreshBtn(function () { load(); })));
        root.appendChild(h("div", { class: "card" }, h("div", { class: "hero-status" },
          h("div", { class: "big " + (hz.ok ? "ok" : "err") }, icon(hz.ok ? "checkCircle" : "alert")),
          h("div", null, h("h2", { text: hz.ok ? t("healthy") : t("unhealthy") }),
            h("p", { text: hz.ok ? t("healthy_sub", { d: fmtDur(hl.uptime_s) }) : t("unhealthy_sub") })),
          h("div", { class: "right" }, h("span", { text: t("updated_at", { t: new Date().toLocaleTimeString(state.lang === "zh" ? "zh-CN" : "en-US", { hour12: false }) }) }),
            h("label", { class: "switch", for: "h-auto" }, sw, h("span", { text: t("auto_refresh") }))))));
        root.appendChild(h("div", { class: "grid" },
          stat(t("version"), hl.version, false, "package"),
          stat(t("uptime"), fmtDur(hl.uptime_s), false, "clock", t("started_at") + " " + fmtTime(hl.started_at)),
          stat(t("req_total"), fmtInt(hl.requests_total), false, "swap"),
          stat(t("req_recent", { w: hl.recent_window_s }), fmtInt(hl.requests_recent), false, "pulse"),
          stat(t("auth"), hl.auth === "token" ? t("auth_token") : t("auth_loop"), true, "shield")));
      }).catch(function (e) {
        if (e.status !== 401 && !silent) { clear(root); root.appendChild(pageHead("health")); root.appendChild(errorBox(e, function () { load(); })); }
      });
    }
    function arm() {
      stopTimers();
      if (autoRefresh) { state.timers.push(setInterval(function () { if (!document.hidden) { load(true); } }, 10000)); }
    }
    load(); arm();
  };

  // ------------------------------------------------------------------ 节点详情（右侧抽屉）/ 删除
  var lastFocus = null;
  function closeModal() {
    if ($("modal").classList.contains("hidden")) { return; }
    $("modal").classList.add("hidden"); clear($("modal-body"));
    if (lastFocus && lastFocus.focus) { try { lastFocus.focus(); } catch (e) { /* 无 */ } }
  }

  function openNode(id, onChange) {
    var body = $("modal-body");
    if ($("modal").classList.contains("hidden")) { lastFocus = document.activeElement; }
    clear(body);
    $("modal-title").textContent = t("node_detail");
    body.appendChild(h("div", null, [1, 2, 3, 4, 5, 6, 7].map(function () { return h("div", { class: "skel line" }); })));
    $("modal").classList.remove("hidden");
    $("modal-close").focus();
    api("GET", "/v1/nodes/" + encodeURIComponent(id)).then(function (n) {
      clear(body);
      $("modal-title").textContent = t("node_detail");
      body.appendChild(h("div", { class: "detail-content", text: n.content }));
      body.appendChild(h("div", { class: "id-row" }, icon("hash", "sm"), h("span", { class: "grow", text: n.id }), copyBtn(function () { return n.id; }, true)));
      body.appendChild(h("div", { class: "section-title", text: t("details") }));
      body.appendChild(h("dl", { class: "kv" },
        h("dt", { text: t("layer") }), h("dd", null, layerBadge(n.layer)),
        h("dt", { text: t("tags") }), h("dd", null, (n.tags || []).length ? tagChips(n.tags) : h("span", { class: "faint", text: "—" })),
        h("dt", { text: t("entities") }), h("dd", null, (n.entities || []).length ? tagChips([], n.entities) : h("span", { class: "faint", text: "—" })),
        h("dt", { text: t("importance") }), h("dd", { class: "mono", text: fmtNum(n.importance) }),
        h("dt", { text: t("confidence") }), h("dd", { class: "mono", text: fmtNum(n.confidence) }),
        h("dt", { text: t("modality") }), h("dd", { text: n.modality }),
        h("dt", { text: t("access_count") }), h("dd", { class: "mono", text: n.access_count }),
        h("dt", { text: t("created") }), h("dd", { text: fmtTime(n.created_at) }),
        h("dt", { text: t("last_access") }), h("dd", { text: fmtTime(n.last_access) }),
        h("dt", { text: t("protected") }), h("dd", null, n.protected ? h("span", { class: "badge warn", text: t("yes") }) : h("span", { class: "badge", text: t("no") })),
        h("dt", { text: t("deletable") }), h("dd", null, n.deletable ? h("span", { class: "badge", text: t("yes") }) : h("span", { class: "badge warn", text: t("no") }))));
      var e = n.edges || {};
      body.appendChild(edgeTable(t("edges_out"), e.outgoing_total || 0, e.outgoing || [], onChange));
      body.appendChild(edgeTable(t("edges_in"), e.incoming_total || 0, e.incoming || [], onChange));
      var confirmSlot = h("div", { class: "slot" });
      var del = h("button", { type: "button", class: "danger", disabled: !n.deletable }, icon("trash", "sm"), t("del"));
      del.addEventListener("click", function () {
        clear(confirmSlot);
        var nEdges = (e.outgoing_total || 0) + (e.incoming_total || 0);
        var yes = h("button", { type: "button", class: "danger" }, icon("trash", "sm"), t("del_yes"));
        yes.addEventListener("click", function () {
          yes.disabled = true;
          api("DELETE", "/v1/nodes/" + encodeURIComponent(n.id)).then(function (r) {
            closeModal();
            toast(t("deleted", { id: r.id, n: r.edges_removed }));
            if (onChange) { onChange(); }
          }).catch(function (err) { confirmSlot.appendChild(errorBox(err)); yes.disabled = false; });
        });
        var no = h("button", { type: "button", text: t("cancel"), onclick: function () { clear(confirmSlot); del.focus(); } });
        confirmSlot.appendChild(h("div", { class: "confirm-box" }, h("strong", { text: t("del_confirm_title") }),
          h("p", { text: t("del_confirm_text", { id: n.id, n: nEdges }) }), h("div", { class: "row" }, yes, no)));
        no.focus();
      });
      body.appendChild(h("div", { class: "danger-zone" },
        h("div", { class: "txt" }, h("b", { text: t("danger_zone") }), h("span", { text: n.deletable ? t("danger_hint") : t("not_deletable") })), del, confirmSlot));
      body.appendChild(h("details", null, h("summary", { text: t("raw") }), jsonPre(n)));
    }).catch(function (err) { clear(body); body.appendChild(errorBox(err)); });
  }

  function edgeTable(title, total, edges, onChange) {
    var wrap = h("div", null, h("div", { class: "section-title" }, h("span", { text: title }), h("span", { class: "count", text: String(total) })));
    if (!edges.length) { wrap.appendChild(h("p", { class: "muted", text: t("none") })); return wrap; }
    var tb = h("tbody");
    edges.forEach(function (x) {
      var p = x.peer;
      tb.appendChild(h("tr", null, h("td", { class: "mono nowrap", text: x.relation }),
        h("td", { class: "content" }, p ? h("button", { type: "button", class: "link", text: p.content + (p.truncated ? " …" : ""),
          onclick: function () { openNode(p.id, onChange); } }) : h("span", { class: "muted mono", text: x.source_id + " → " + x.target_id })),
        h("td", { class: "num right", text: fmtNum(x.confidence, 2) }),
        h("td", { class: "nowrap" }, x.verified ? h("span", { class: "badge ok", text: t("yes") }) : h("span", { class: "badge", text: t("no") }))));
    });
    wrap.appendChild(h("div", { class: "edge-list table-wrap" }, h("table", null, h("thead", null, h("tr", null, h("th", { text: t("relation") }), h("th", { text: t("peer") }),
      h("th", { class: "right", text: t("confidence") }), h("th", { text: t("verified") }))), tb)));
    return wrap;
  }

  // ------------------------------------------------------------------ 快捷键帮助
  function showHelp() {
    if ($("help-dialog")) { return; }
    var rows = [[t("sc_nav"), ["1", "–", "6"]], [t("sc_search"), ["/"]], [t("sc_submit"), ["Ctrl", "Enter"]], [t("sc_help"), ["?"]], [t("sc_close"), ["Esc"]]];
    var closeB = h("button", { type: "button", class: "ghost icon sm", "aria-label": "close" }, icon("x"));
    var dlg = h("div", { class: "dialog", id: "help-dialog", role: "dialog", "aria-modal": "true" },
      h("div", { class: "box" }, h("div", { class: "hd" }, h("h2", { text: t("shortcuts") }), closeB),
        h("div", { class: "bd" }, rows.map(function (r) {
          return h("div", { class: "kbd-row" }, h("span", { text: r[0] }), h("span", null, r[1].map(function (k) { return k === "–" ? h("span", { class: "faint", text: k }) : h("kbd", { text: k }); })));
        }))));
    function close() { if (dlg.parentNode) { dlg.parentNode.removeChild(dlg); } }
    closeB.addEventListener("click", close);
    dlg.addEventListener("click", function (ev) { if (ev.target === dlg) { close(); } });
    document.body.appendChild(dlg);
    closeB.focus();
  }

  // ------------------------------------------------------------------ 主题 / 语言
  function systemDark() { return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches); }
  function applyTheme() {
    var dark = state.theme === "dark" || (state.theme === "system" && systemDark());
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    var name = state.theme === "light" ? "sun" : state.theme === "dark" ? "moon" : "monitor";
    setIcon($("theme"), name);
    $("theme").title = t("theme_" + state.theme);
    $("theme").setAttribute("aria-label", t("theme_" + state.theme));
  }
  function applyLang() {
    document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
    Array.prototype.forEach.call(document.querySelectorAll("[data-i18n]"), function (el) {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    $("lang").textContent = state.lang === "zh" ? "EN" : "中文";
    $("kbd-help").title = t("shortcuts");
    applyTheme();
  }

  // ------------------------------------------------------------------ 启动
  function typing(el) {
    if (!el) { return false; }
    var tg = (el.tagName || "").toLowerCase();
    return tg === "input" || tg === "textarea" || tg === "select" || el.isContentEditable;
  }

  function init() {
    try { var l = localStorage.getItem(LANG_KEY); if (l === "en" || l === "zh") { state.lang = l; } } catch (e) { /* 无 */ }
    try { var th = localStorage.getItem(THEME_KEY); if (th === "light" || th === "dark" || th === "system") { state.theme = th; } } catch (e) { /* 无 */ }
    Array.prototype.forEach.call(document.querySelectorAll("#tabs button"), function (b) {
      b.insertBefore(icon(b.getAttribute("data-icon")), b.firstChild);
      b.appendChild(h("kbd", { text: b.getAttribute("data-key") }));
      b.addEventListener("click", function () { navigate(b.getAttribute("data-view")); });
    });
    setIcon($("menu"), "menu");
    setIcon($("kbd-help"), "keyboard");
    setIcon($("modal-close"), "x");
    $("login-lock").appendChild(icon("lock", "lg"));
    applyLang();
    if (window.matchMedia) {
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      var onMq = function () { if (state.theme === "system") { applyTheme(); } };
      if (mq.addEventListener) { mq.addEventListener("change", onMq); } else if (mq.addListener) { mq.addListener(onMq); }
    }
    $("theme").addEventListener("click", function () {
      state.theme = state.theme === "system" ? "light" : state.theme === "light" ? "dark" : "system";
      try { localStorage.setItem(THEME_KEY, state.theme); } catch (e) { /* 无 */ }
      applyTheme();
      toast(t("theme_" + state.theme));
    });
    $("lang").addEventListener("click", function () {
      state.lang = state.lang === "zh" ? "en" : "zh";
      try { localStorage.setItem(LANG_KEY, state.lang); } catch (e) { /* 无 */ }
      applyLang(); go(state.view); pollConn();
    });
    $("menu").addEventListener("click", function () { $("app").classList.toggle("nav-open"); });
    $("app").addEventListener("click", function (ev) { if (ev.target === $("app")) { $("app").classList.remove("nav-open"); } });
    $("kbd-help").addEventListener("click", showHelp);
    $("logout").addEventListener("click", function () { setToken(""); showLogin(); });
    $("modal-close").addEventListener("click", closeModal);
    $("modal").addEventListener("click", function (ev) { if (ev.target === $("modal")) { closeModal(); } });
    window.addEventListener("popstate", function () { go(viewFromHash() || "overview"); });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") {
        var d = $("help-dialog");
        if (d) { d.parentNode.removeChild(d); return; }
        closeModal(); $("app").classList.remove("nav-open"); return;
      }
      if (ev.ctrlKey || ev.metaKey || ev.altKey || typing(ev.target)) { return; }
      if (!$("modal").classList.contains("hidden") || $("help-dialog") || !$("login").classList.contains("hidden")) { return; }
      if (ev.key === "/") { ev.preventDefault(); if (state.view !== "search") { navigate("search"); } else if ($("q")) { $("q").focus(); } return; }
      if (ev.key === "?") { ev.preventDefault(); showHelp(); return; }
      var i = "123456".indexOf(ev.key);
      if (i >= 0 && ev.key.length === 1) { ev.preventDefault(); navigate(VIEW_ORDER[i]); }
    });
    $("login-form").addEventListener("submit", function (ev) {
      ev.preventDefault();
      var v = $("token-input").value.trim();
      $("login-error").textContent = "";
      if (!v) { return; }
      setToken(v);
      api("GET", "/v1/health").then(function () {
        $("token-input").value = "";
        hideLogin(); go(state.view); pollConn();
      }).catch(function (e) { setToken(""); $("login-error").textContent = e.message || t("bad_token"); showLogin(); });
    });
    go(viewFromHash() || "overview");
    pollConn();
  }

  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init); } else { init(); }
})();
