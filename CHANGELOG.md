# 更新日志

版本号规则与弃用流程见 [docs/STABILITY_ng.md](docs/STABILITY_ng.md)；库结构升级 / 回滚见 [docs/UPGRADE.md](docs/UPGRADE.md)。

## 未发布

- `/metrics` 的 `lingshu_ng_info` 增加 `schema` 标签（库结构版本）。

## v1.38.0

- 控制台设计审查：CI 新增 `design-lint` 作业（impeccable 确定性规则扫描六个页面，零发现才过，`tools/design_lint.py`）；靛墨侧栏、层谱品牌标、指标事实带、正文对比度 ≥ 4.5:1、去掉全大写标签 / 中点拼接 / 切页动画；标题层级改为 h1 → h2。
- 文档精简：研究期报告与预登记移出主分支（存档于 tag v1.37.0），逐版 CHANGELOG 合并为本文件，README 重写。
- 新增 `lingshu-ng config --show`：列出全部 LINGSHU_NG_* 环境变量及生效值，令牌/密钥脱敏。
- 新增 `GET /readyz`：免鉴权就绪探针，库不可写回 503（`/healthz` 不变）。

## v1.37.0

- Web 控制台 v2.1：层名本地化、检索模式人话化、最近写入与空库引导、相关度百分比、写入可选层、移动端与深色对比度修复。
- /v1/health 增加 latency/responses 指标；健康页按路由展示延迟与状态码。
- 文档：doctor 退出码文档化并加测试。

## v1.36.0

- Web 控制台 v2：设计令牌与深浅色主题、侧栏布局、hash 路由、骨架屏/空状态。
- 检索结果卡片高亮、右侧抽屉详情、拖放导入、健康自动刷新、键盘快捷键、移动端适配。
- console-e2e 增加 v2 用例。

## v1.35.0

- 新增 `docs/UPGRADE.md`：schema 版本与升级/回滚矩阵（测试校验与代码一致）。
- CLI `lingshu-ng version --json`：版本、schema、python、可选件。
- 请求体大小上限可配置：`LINGSHU_NG_MAX_BODY`，已文档化。
- 控制台：插件表状态列不再折行；插件版本与核心对齐。

## v1.34.0

- `/metrics` 增请求时延直方图（按路由，固定桶）。
- 新增 `lingshu-ng doctor`：库 integrity_check、schema 版本、磁盘余量、令牌/绑定配置风险、可选件状态；JSON 输出，有故障退出码非零。
- 可复现构建：固定 `SOURCE_DATE_EPOCH` 下 wheel 与（归一化后的）sdist 两次构建逐字节一致；`tools/release/repro_check.py`，并加入 CI release-artifacts 作业。
- 新增 `docs/OPERATIONS.md` 运维手册（监控、备份 cron、令牌轮换、升级/回滚、故障排查）；`docs/ADOPTION.md` 选型说明。
- 修复 doctor 能力探测的静默宽 except（改记日志）。

## v1.33.0 — 可运维与供应链

### 可运维
- E6-2 结构化日志：`LINGSHU_NG_LOG_FORMAT=json` 时每行一个 JSON（`ts` UTC 毫秒 / `level` / `logger` / `msg`，异常带 `exc`），缺省 `text`；值非法时 CLI / 控制台启动即报错（退出码 2），不静默退回。
- E6-2 `GET /metrics`：Prometheus 文本格式 0.0.4，**与其他接口同样需要 Bearer 令牌**。指标：`lingshu_ng_info{version}`、`lingshu_ng_uptime_seconds`、`lingshu_ng_http_requests_total`、`lingshu_ng_http_responses_total{code}`、`lingshu_ng_http_rejected_busy_total`、`lingshu_ng_http_max_connections`、`lingshu_ng_memory_nodes`、`lingshu_ng_memory_nodes_by_layer{layer}`、`lingshu_ng_schema_version`。只含计数，不含记忆正文；`POST /metrics` 回 405。
- E6-3 `lingshu-ng backup` / `lingshu-ng restore`：SQLite 在线备份 API 物理快照（服务运行中可做），快照跑 `integrity_check` 并写 `*.manifest.json`（版本、行数、SHA-256）；恢复前校验快照、表结构与清单校验和，旧库另存为 `*.pre-restore-<时间戳>` 后原子替换；两个命令都写审计日志（`remote=cli`）。

### 供应链
- E6-1 `tools/release/sbom.py`：生成 CycloneDX 1.5 JSON SBOM（核心包 + 5 个插件包 + 插件声明的第三方依赖，依赖版本以区间记录；同一源码与时间戳下输出确定）。核心包依赖为空。
- E6-1 `tools/release/checksums.py`：SHA256SUMS 生成 / 校验（与 `sha256sum -c` 同格式）与 Release 说明用的 Markdown 表。
- CI 新增 `release-artifacts` 作业：每次构建 wheel / sdist + SBOM + SHA256SUMS，自校验后作为 CI 产物上传，校验和表写入作业摘要。

### 未修 / 未承诺
- `/metrics` 无请求时延直方图；多进程部署时各进程计数独立。
- SBOM 只列声明的依赖区间，不含安装环境实际解析版本与传递依赖（需要时用 `pip-audit` / `cyclonedx-py` 对安装环境另行生成）。
- 物理快照不可跨 schema 降级恢复；跨版本迁移仍用 `/v1/export` / `/v1/import`。
- 无 TLS / 多租户 / RBAC（交给反向代理）。

## v1.32.0 — 运维加固

### 运维与安全
- E5-1 HTTP 并发连接上限：`LINGSHU_NG_MAX_CONN`（缺省 64），满则立即回 503 + `Retry-After: 1`，不再无限开线程；`/v1/health` 增 `max_conn`、`rejected_busy`。
- E5-3 令牌免重启轮换：`LINGSHU_NG_TOKEN_FILE`（每行一个有效令牌，`#` 注释），按 mtime 自动重读，新旧令牌可并存过渡；文件读出空集时拒绝所有请求（失败关闭）；文件启动时不可读则拒绝启动。可与 `--token` 同时使用。
- 新增公开 API：`lingshu_ng.integrations.http.Server.valid_tokens`（只增不改）。
- E5-2 流式导出：`GET /v1/export` 改为临时文件逐块（64 KiB）写出，响应形状不变（`{"report", "backup"}`），不再把整份备份解析进内存。
- E5-4 审计覆盖 MCP 与 CLI：`lingshu_perceive`（含失败）与 `lingshu-ng perceive` 也写 `lingshu_ng.audit`，`remote` 字段为 `mcp` / `cli`，同样不含正文。
- E5-5 控制台真实浏览器端到端：`tests_e2e/`（Playwright + Chromium，未装则跳过）覆盖 CSP 下无脚本错误、写入、检索、浏览、详情、二次确认删除、XSS 负载只作文本、令牌登录（只进 sessionStorage）、中英切换、导出下载；CI 新增 `console-e2e` 作业。

### 未修 / 未承诺
- 无 TLS / 多租户 / RBAC（交给反向代理）；控制台端到端只测 Chromium。
- 令牌文件轮换按 mtime 判定：同一秒内改两次且文件系统 mtime 粒度粗时，可能要等下一次修改才生效。

## v1.31.0 — 企业版首发

独立仓库 https://github.com/Liyang1145/lingshu-ng 的第一个正式版本。主题：安全、兼容、可运维、可管理。检索算法与读数与 1.30 相同（不开调优轮，只作回归门）。

### 安全（sec-r1 + sec-r2，报告 docs/security/SECURITY_REPORT_sec-r1.md）
- sec-r1 12 项：HTTP 回环 Host 白名单（DNS 重绑定）、无令牌拒非本机 Origin（跨站写入）、读超时 30 s、积压 128、拒 Transfer-Encoding、深嵌套 JSON 400；MCP 深嵌套 / 超长行 / 空批量 / 非法工具名；导入逐值类型校验与 rejected_rows；三处四次方正则改占有量词；新建库 0600；Pillow 下沿 12.3。
- sec-r2（遗留项）：O2 导入覆盖已有节点计入 `overwritten`；O3 标签 / 实体单次 ≤1000 项、单项 ≤1024 字符；O5 可选 LLM 抽取只许 https 或本机 http，缓存 0600；O8 `Authorization` 方案名大小写不敏感。

### 本机 Web 控制台（ent-ui，新增，无不兼容变更）

- 新子命令 `lingshu-ng console --db PATH [--host 127.0.0.1] [--port 8766] [--token T] [--audit-log FILE]`，以及 `python -m lingshu_ng.integrations.console`。文档 `docs/CONSOLE.md`。
- 新增公开 API（只增不改）：`Service.list_nodes`、`Service.get_node`、`Service.delete_node`、`Service.export_backup`、`Service.import_backup`。`Server.__init__` / `make_server` 签名不变。
- HTTP 新路由：`GET /v1/health`、`GET /v1/nodes`、`GET|DELETE /v1/nodes/<id>`、`GET /v1/export`、`POST /v1/import`。`DELETE /v1/nodes/<id>` 与 `POST /v1/import` 在任何模式下都须带 `X-Lingshu-Console: 1`；控制台模式下所有非 GET 请求都须带。既有 `/v1/perceive`、`/v1/recall`、`/v1/status`、`/v1/capabilities`、`/healthz` 行为不变（JSON 响应多了 `Content-Security-Policy`、`X-Content-Type-Options` 等安全头）。
- 审计：perceive / delete / import 每次（含被拒的）记一行 JSON 到 logger `lingshu_ng.audit`（INFO），含时间、操作、节点 id、来源地址、状态码，不含记忆正文。
- `NodeRepo.page`（内部）：分页 + 层 / 标签过滤。
- 测试：`tests_ng/test_console.py`（31 例）。

### 兼容对接
- 新插件 `plugins/lingshu-ng-adapters`：mem0 `Memory`/`AsyncMemory` 兼容 API、LangChain ChatHistory/Retriever/VectorStore、LlamaIndex Retriever/Memory/MemoryBlock、官方 MCP memory server 9 个工具名。CI `adapters` 作业装真实 langchain-core / llama-index-core 跑标准套件。

### 部署与运维
- `Dockerfile`：python:3.12-slim、非 root（uid 10001）、`/data` 卷、HEALTHCHECK；CI `docker` 作业做冒烟（带令牌起服务、401、非 root、无令牌拒绝启动）。
- `docs/ENTERPRISE.md`：交付形态、支持矩阵、安全基线、部署、运维、已知限制。

### 质量
- CI 全矩阵 Linux / Windows / macOS × Python 3.11–3.13：修复 Windows 跨盘符 relpath、USERPROFILE、schema v7 迁移用例分数时间漂移（id 与排序仍逐项相等）。
- 插件测试分目录运行（同名 conftest 冲突）。
- 修复：Windows 3.11/3.12 粗时钟（约 15.6 ms）下同刻写入的多条近重复，去重合并目标取「同刻组里最旧」而非最新（排序次键 id 改倒序）；新增粗时钟回归用例。

### 未修 / 未承诺（如实列出）
- HTTP 每连接一线程、并发连接无硬上限；导出整库进内存、无流式；令牌无过期 / 轮换；无 TLS / 多租户 / RBAC（交给反向代理）。
- 审计只覆盖 HTTP 通道（MCP / CLI 写入不记）。
- 插件即代码的信任模型、模型目录同用户可替换、依赖未锁定哈希、若干三次方正则——见安全报告第 3 节。
- 控制台端到端只在 Chromium 上测（未测 Firefox / Safari）。

## v1.0 – v1.30（研究期，2026-10-12 至 10-15）

这一阶段在合作仓 LingShu-prime 的 `Liyang/` 目录内迭代，以 `rel-vX.Y` 命名。逐版的完整说明、读数与未胜项存档于 tag `v1.37.0` 的 `docs/changelog/`。下表只保留每版主题；**带「升级须知」的版本改了库结构或安装方式**。

| 版本 | 主题 |
|---|---|
| v1.30 | 常驻内存——分词 / 二元组缓存改为紧凑表示，无库结构变化 |
| v1.29 | 库体积——删除 term_df、倒排块 grams 1 字节窄编码，schema v7。**升级须知：schema 6 → 7** |
| v1.28 | 冷 import 延迟加载 |
| v1.27 | 晋升路径的精确等价优化 |
| v1.26 | 写入与晋升的精确等价优化 |
| v1.25 | node_index.terms 去重，库结构 schema 5 → 6。**升级须知：schema 5 → 6** |
| v1.24 | 拆包——核心零外部依赖，依赖第三方库的部分拆为 4 个独立插件包。**升级须知：拆包，核心零依赖；extras 删除，改装 lingshu-ng-embed / world / nn / gen 插件包** |
| v1.23 | 倒排分块 blob，库结构 schema 4 → 5；长请求回退以块缓存压回。**升级须知：schema 4 → 5，旧库自动迁移并重建派生索引** |
| v1.22 | 开发可用性生态——命令行 / HTTP / MCP 集成面、版本与弃用策略、召回 p95 回退修复、库体积原型 |
| v1.21 | 晋升延迟、内存、冷 import、孤儿模块、写入剖析。**升级须知：schema 3 → 4，旧库自动迁移** |
| v1.20 | 规模、输入安全、易用性、上游同口径对照 |
| v1.19 | semrank 缺省模型目录 |
| v1.18 | 确定性 · 不支持方法语义 · 打包 · 数据安全 · API 文档。**升级须知：发行包改名 lingshu-ng，只含 lingshu_ng，不再安装旧 lingshu 包；库比代码新时拒绝打开** |
| v1.17 | 依赖结构 · 兼容覆盖 · 多 Python 版本 |
| v1.16 | 稳定性 · 可复跑 · 兼容性 |
| v1.15 | 带语义模型时说话人先验重排窗口 sp_n 20 → 40 |
| v1.14 | 版本链零 LLM 抽取缺省升为 v27 = v26 + A,V,AM,D,Q,H |
| v1.13 | 版本链零 LLM 抽取缺省升为 v26 = v25 + W,T,C,M |
| v1.12 | 版本链零 LLM 抽取缺省升为 v24 = v23 + K,G,N,Q,A,P |
| v1.11 | 英文带模型缺省开启 F4 说话人意图先验——H-CM10 未暴露保留集判定通过 |
| v1.10 | 中文可选语义通路 v11c 的冷查询延迟修复——rel-v1.6 未验收项 |
| v1.9 | 版本链零 LLM 抽取缺省升为 v21 = v20 + B + G |
| v1.8 | 英文可选语义第二路 F3 的带模型查询延迟修复——rel-v1.5 未验收项 |
| v1.7 | 版本链零 LLM 抽取缺省升为 v18 规则集＝v19 缺省 |
| v1.6 | 中文联想通路自适应稠密补入设为默认 |
| v1.5 | 英文稠密融合 F3 设为带模型默认 |
| v1.4 | 版本链零 LLM 抽取 v16 |
| v1.3 | 版本链零 LLM 抽取 v15 |
| v1.2 | 版本链零 LLM 抽取 v13.1 + 可选受限 LLM 抽取 B |
| v1.1 | 英文可选稠密–稀疏融合（需本地句向量模型） |
| v1.0 | 首次集成：英文词级通路 gen-v3.2、中文联想通路 v7.1、版本链（可选） |
