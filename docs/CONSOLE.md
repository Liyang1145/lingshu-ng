# lingshu-ng 本机 Web 控制台（ent-ui）

控制台是 lingshu_ng 的本地管理界面，纯标准库实现，不引入任何依赖。前端是一页 HTML，加一个原生 JS 文件和一个 CSS 文件，都放在包内 `lingshu_ng/integrations/console_static/`，由 `importlib.resources` 读取。页面不引用 CDN、外部字体、图片或任何外部资源。

后端没有另起一个服务，用的就是 `lingshu_ng.integrations.http` 里的 `Server` / `_Handler`。`lingshu-ng serve` 已有的安全措施，控制台全部原样继承。

## 1. 启动

```bash
# 只绑本机（缺省 127.0.0.1:8766），无令牌
lingshu-ng console --db ./mem.db

# 等价入口
python -m lingshu_ng.integrations.console --db ./mem.db

# 设令牌（页面里登录）；绑非回环地址时必须设令牌，否则拒绝启动（退出码 2，不会建库文件）
lingshu-ng console --db ./mem.db --token "$(openssl rand -hex 24)"
LINGSHU_NG_TOKEN=... lingshu-ng console --db ./mem.db --host 0.0.0.0

# 审计日志写文件（JSON 行，新建为 0600）；不给就写 stderr
lingshu-ng console --db ./mem.db --audit-log ./audit.jsonl
```

| 参数 | 缺省 | 说明 |
|---|---|---|
| `--db PATH` | 环境变量 `LINGSHU_NG_DB` | SQLite 库文件。两者都没有时拒绝启动 |
| `--host` | `127.0.0.1` | 绑定地址 |
| `--port` | `8766` | 端口（`serve` 缺省 8765，两者可同时跑）；`0` 表示由系统分配 |
| `--token` | 环境变量 `LINGSHU_NG_TOKEN` | Bearer 令牌 |
| `--audit-log FILE` | 无（写 stderr） | 审计日志文件 |

启动后用浏览器打开 `http://127.0.0.1:8766/`。

## 2. 功能

界面中英双语，缺省中文，右上角切换。语言与主题偏好存在 localStorage，令牌不存这里。

### 界面（v1.36 起）

- 左侧导航 + 顶部面包屑；窄屏（≤860 px）导航收进左上角菜单按钮。
- 主题：浅色 / 深色 / 跟随系统，右上角切换并记住选择。
- 每页地址带 hash（`#/search`、`#/browse` …），可收藏、可刷新、浏览器前进后退可用。
- 加载时显示骨架屏；空结果与出错都有说明和「重试」。
- 检索结果按卡片排列，标出命中的关键词（中文按二字片段匹配），显示排名、相对分数条和耗时。
- 记忆浏览按层分段切换，整行可点开详情；节点详情从右侧抽屉滑出，ID 一键复制，删除放在「危险操作」区并二次确认。
- 写入页有字数统计、标签 / 实体即时预览、可选的重要度滑块，Ctrl/⌘ + Enter 提交。
- 导入支持把文件直接拖进来，先显示文件摘要再确认导入。
- 健康页显示总状态，默认每 10 秒自动刷新（页面在后台时暂停），可关闭。
- 键盘：`1`–`6` 切页，`/` 聚焦检索，`?` 显示快捷键，`Esc` 关闭抽屉或对话框。
- 不加载任何外部字体、图片或脚本；图标是页面内建的 SVG 路径，CSP 不变。

| 页 | 内容 | 调用的 API |
|---|---|---|
| 概览 | 节点总数、各层计数（中文层名与说明）、库文件、版本、schema 版本、检索模式（`semantic_tier` 映射为“标准检索 / 重排增强 / 向量增强…”，原值见悬停与高级区）、最近写入 5 条、插件列表、依赖；模型 / 引擎 / 退回记录收进“高级”折叠区；空库时显示三步上手引导 | `GET /v1/status`、`GET /v1/capabilities`、`GET /v1/nodes?limit=5` |
| 检索 | 输入查询和条数；命中展示原文、分数、层、标签、创建时间；点「详情」看节点 | `POST /v1/recall` |
| 记忆浏览 | 按层 / 标签（精确匹配）筛选，分页（20/50/100/200 条），最新写入在前；列表只显示正文前 300 字 | `GET /v1/nodes` |
| 节点详情（右侧抽屉） | 全文、标签、实体、重要度、置信度、访问次数、是否受保护 / 可删除、出边和入边（含对端预览，可点开跳转） | `GET /v1/nodes/<id>` |
| 删除 | 详情抽屉里点「删除节点」，再点「确认删除」（二次确认），节点和它的全部关联边一起删除 | `DELETE /v1/nodes/<id>` |
| 写入 | perceive 表单：正文、标签、实体（逗号分隔）、存入层（知识 / 情境，缺省知识）、重要度；结果用人话说明（新建 / 合并到相似记忆 / 重复未改动） | `POST /v1/perceive` |
| 导入 / 导出 | 导出：整库 JSON 备份，浏览器里下载。导入：选文件后先显示节点数 / 边数摘要，勾选确认后才能导入；导入后显示报告（各表导入数、覆盖数 `overwritten`、`rejected_rows`、`quarantined`、丢弃列、孤儿边、完整性） | `GET /v1/export`、`POST /v1/import` |
| 健康 | `/healthz`、运行时长、启动时间、请求总数、最近 300 秒请求数、并发上限与繁忙拒绝数、鉴权方式；按路由的调用次数与平均 / P50 / P95 延迟（直方图桶上界估计，偏保守）；按状态码的响应计数 | `GET /healthz`、`GET /v1/health` |

## 3. 安全模型

威胁模型沿用 `docs/security/SECURITY_REPORT_sec-r1.md`。控制台多了浏览器这个入口，所以在原有防护上又加了几层。

**继承自 http.py（与 `serve` 完全相同）**

- 缺省只绑 `127.0.0.1`。绑非回环地址必须给令牌，否则拒绝启动。
- 只绑回环时只认回环 `Host`（`127.0.0.1` / `localhost` / `[::1]`），其他一律 403。这一条防 DNS 重绑定，静态页面也受它约束。
- 无令牌时，带非本机 `Origin` 的请求一律 403，包括 `Origin: null`。
- 有令牌时，除 `/healthz` 和三个静态资源外，每个请求都必须带 `Authorization: Bearer <令牌>`，比较用常数时间。
- 每个连接读超时 30 秒；listen 积压 128；带 `Transfer-Encoding` 的请求回 501；深嵌套 JSON 回 400。
- 请求体上限：普通请求 1 MiB（`MAX_BODY`），`/v1/import` 为 32 MiB（`MAX_IMPORT_BODY`），超限回 413。
- 500 只向客户端返回异常类型名，堆栈只进服务端日志。

**控制台新增**

- **CSRF 头**：控制台模式下，所有非 GET 请求都必须带 `X-Lingshu-Console: 1`，否则 403。破坏性路由（`DELETE /v1/nodes/<id>`、`POST /v1/import`）在 `serve` 模式下也要求这个头。跨站页面要带自定义头就得先过 CORS 预检，而本服务不应答 `OPTIONS`（501），所以跨站请求发不出来。这一层叠加在 Origin 校验之上。
- **令牌处理**：有令牌时页面先显示登录框。令牌只存在当前标签页的 `sessionStorage`，关闭标签页即清除，只经 `Authorization` 头发送。令牌不进 URL、cookie、localStorage。服务端也不设任何 cookie。`fetch` 一律带 `credentials: "omit"` 和 `referrerPolicy: "no-referrer"`。
- **CSP**：页面响应带 `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`。没有内联脚本、内联事件处理器或内联样式，所以策略里不需要 `unsafe-inline` / `unsafe-eval`。JSON API 响应带 `default-src 'none'; frame-ancestors 'none'`。所有响应都带 `X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`Referrer-Policy: no-referrer`、`Cache-Control: no-store`。
- **XSS**：前端只通过 `textContent` / `createTextNode` / 属性赋值把数据放进 DOM，整个前端不使用 `innerHTML`、`outerHTML`、`insertAdjacentHTML`、`document.write`、`eval` 这类会把字符串当 HTML 或代码解析的 API。测试会静态检查这一点。HTML 模板本身不含任何用户数据。
- **审计**：每次写操作都记一行 JSON 到 logger `lingshu_ng.audit`（INFO 级），被拒绝的写操作也记。写操作指 perceive、delete、import。字段有 `ts`（UTC，ISO-8601）、`op`、`remote`（来源地址）、`status`（HTTP 状态码），另有按操作不同的 `node_id`、`action`、`layer`、`edges_removed`、导入计数、`error`（异常类型名）。**不含记忆正文和标签文本**，perceive 只记正文字符数与标签个数。读操作（recall、列表、详情、导出）不记审计。
- **导入**：API 要求请求体里显式写 `"confirm": true`，页面上也要勾选确认。导入不接受设计者密钥，共享层和治理表按 `exchange.import_all` 的规则隔离，类型错误的行进 `rejected_rows`。注意：同 id 的 knowledge / context 节点**会被覆盖**，覆盖数见报告里的 `overwritten`（sec-r2 O2），页面上单列显示。备份先写进 0700 临时目录下的 0600 文件，导入完即删除。
- **删除**：共享层（anchor / structure）、受保护节点、级联会触及共享层边的节点，都回 409 拒绝。节点不存在回 404。

**仍然不做的事（与 `serve` 相同）**：不做 TLS，不做多用户和角色。要对外暴露，请放在反向代理（TLS 加访问控制）之后，并设置令牌。令牌没有过期机制，轮换需要重启。

## 4. API 列表

除特别说明外，请求体和响应都是 UTF-8 JSON。错误体为 `{"error": {"code", "message"}}`。

| 方法 | 路径 | 鉴权 | `X-Lingshu-Console` | 说明 |
|---|---|---|---|---|
| GET | `/` 、`/console` | 否（受 Host / Origin 约束） | — | 控制台页面（仅 console 模式） |
| GET | `/console/app.js`、`/console/app.css` | 否（同上） | — | 静态资源（仅 console 模式） |
| GET | `/healthz` | 否 | — | `{"ok": true}`，形状不变 |
| GET | `/v1/health` | 是 | — | `{ok, version, started_at, uptime_s, requests_total, requests_recent, recent_window_s, console, auth, max_conn, rejected_busy, responses: {状态码: 次数}, latency: {路由: {count, avg_ms, p50_ms, p95_ms}}}` |
| GET | `/v1/status` | 是 | — | 版本、schema 版本、库路径、各层计数、总数 |
| GET | `/v1/capabilities` | 是 | — | 生效档位、插件、依赖、模型 |
| POST | `/v1/perceive` | 是 | console 模式必需 | `{content, tags?, entities?, importance?, confidence?, layer?, skip_dedup?}` → `{node_id, action, layer, reason}` |
| POST | `/v1/recall` | 是 | console 模式必需 | `{query, limit?}` → `{hits: [{id, content, score, layer, tags, importance, confidence, created_at}], negative}` |
| GET | `/v1/nodes?layer=&tag=&offset=&limit=` | 是 | — | `{nodes: [{id, layer, tags, entities, importance, confidence, created_at, content(前 300 字), truncated}], total, offset, limit}`；`limit` 取 1–200（缺省 50），`offset` ≥ 0；未知或重复参数回 400 |
| GET | `/v1/nodes/<id>` | 是 | — | 详情：`{id, content, modality, layer, tags, entities, entity_id, importance, confidence, access_count, created_at, last_access, temporal_coordinate, condition_space, protected, deletable, edges: {outgoing, incoming, outgoing_total, incoming_total}}`；每个方向最多 200 条边。`<id>` 需百分号编码，最长 512 字符；`tag` 过滤最长 `inputs.MAX_ITEM_CHARS`（1024）字符 |
| DELETE | `/v1/nodes/<id>` | 是 | **任何模式都必需** | `{deleted, id, layer, edges_removed}`；404 不存在，409 层规则或保护名单拒绝 |
| GET | `/v1/export` | 是 | — | `{report: {exported_nodes, tables, skipped_tables, not_exported_tables}, backup: <与 MemoryEngine.export_all 相同>}` |
| POST | `/v1/import` | 是 | **任何模式都必需** | `{backup: {...}, confirm: true}` → 导入报告 `{imported, overwritten, rejected_rows, quarantined, dropped_columns, orphan_edges_rejected, dangling_rows, integrity_ok, skipped_tables}`；请求体上限 32 MiB |

对应的 `Service` 方法分别是 `list_nodes`、`get_node`、`delete_node`、`export_backup`、`import_backup`，HTTP 以外也能直接调用。入参校验复用 `lingshu_ng.inputs`：`limit` / `offset` 用 `inputs.limit` 的整数口径，`id` 用 `inputs.content` 拒孤立代理码位；未知字段一律 400。新增的异常类有 `service.NotFound` 和 `service.Conflict`，都是 `BadRequest` 的子类。

## 5. 测试

`tests_ng/test_console.py` 覆盖以下内容：

- 路由与方法：404、405。
- Host、Origin、CSRF 头、令牌（401）。
- 非回环地址无令牌时拒绝启动。
- Transfer-Encoding 与请求体上限的继承。
- CSP 等安全头。
- HTML / JS 静态审查：无内联脚本、无外部资源、无 HTML 字符串注入类 API、令牌不进 cookie / URL / localStorage。
- XSS 负载作为数据原样往返。
- 各 API 的功能，包括分页、过滤、详情与边、删除级联、受保护节点 409、导出导入往返、`rejected_rows`。
- 健康计数。
- 审计日志不含正文。
- 入口与 package-data 声明。

```bash
python -m pytest -q tests_ng/test_console.py
```
