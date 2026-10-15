# rel-v1.31（lingshu-ng 1.31.0）— 企业版首发

独立仓库 https://github.com/Liyang1145/lingshu-ng 的第一个正式版本。主题：安全、兼容、可运维、可管理。检索算法与读数与 1.30 相同（不开调优轮，只作回归门）。

## 安全（sec-r1 + sec-r2，报告 docs/security/SECURITY_REPORT_sec-r1.md）
- sec-r1 12 项：HTTP 回环 Host 白名单（DNS 重绑定）、无令牌拒非本机 Origin（跨站写入）、读超时 30 s、积压 128、拒 Transfer-Encoding、深嵌套 JSON 400；MCP 深嵌套 / 超长行 / 空批量 / 非法工具名；导入逐值类型校验与 rejected_rows；三处四次方正则改占有量词；新建库 0600；Pillow 下沿 12.3。
- sec-r2（遗留项）：O2 导入覆盖已有节点计入 `overwritten`；O3 标签 / 实体单次 ≤1000 项、单项 ≤1024 字符；O5 可选 LLM 抽取只许 https 或本机 http，缓存 0600；O8 `Authorization` 方案名大小写不敏感。

## 本机 Web 控制台（ent-ui，新增，无不兼容变更）

- 新子命令 `lingshu-ng console --db PATH [--host 127.0.0.1] [--port 8766] [--token T] [--audit-log FILE]`，以及 `python -m lingshu_ng.integrations.console`。文档 `docs/CONSOLE.md`。
- 新增公开 API（只增不改）：`Service.list_nodes`、`Service.get_node`、`Service.delete_node`、`Service.export_backup`、`Service.import_backup`。`Server.__init__` / `make_server` 签名不变。
- HTTP 新路由：`GET /v1/health`、`GET /v1/nodes`、`GET|DELETE /v1/nodes/<id>`、`GET /v1/export`、`POST /v1/import`。`DELETE /v1/nodes/<id>` 与 `POST /v1/import` 在任何模式下都须带 `X-Lingshu-Console: 1`；控制台模式下所有非 GET 请求都须带。既有 `/v1/perceive`、`/v1/recall`、`/v1/status`、`/v1/capabilities`、`/healthz` 行为不变（JSON 响应多了 `Content-Security-Policy`、`X-Content-Type-Options` 等安全头）。
- 审计：perceive / delete / import 每次（含被拒的）记一行 JSON 到 logger `lingshu_ng.audit`（INFO），含时间、操作、节点 id、来源地址、状态码，不含记忆正文。
- `NodeRepo.page`（内部）：分页 + 层 / 标签过滤。
- 测试：`tests_ng/test_console.py`（31 例）。

## 兼容对接
- 新插件 `plugins/lingshu-ng-adapters`：mem0 `Memory`/`AsyncMemory` 兼容 API、LangChain ChatHistory/Retriever/VectorStore、LlamaIndex Retriever/Memory/MemoryBlock、官方 MCP memory server 9 个工具名。CI `adapters` 作业装真实 langchain-core / llama-index-core 跑标准套件。

## 部署与运维
- `Dockerfile`：python:3.12-slim、非 root（uid 10001）、`/data` 卷、HEALTHCHECK；CI `docker` 作业做冒烟（带令牌起服务、401、非 root、无令牌拒绝启动）。
- `docs/ENTERPRISE.md`：交付形态、支持矩阵、安全基线、部署、运维、已知限制。

## 质量
- CI 全矩阵 Linux / Windows / macOS × Python 3.11–3.13：修复 Windows 跨盘符 relpath、USERPROFILE、schema v7 迁移用例分数时间漂移（id 与排序仍逐项相等）。
- 插件测试分目录运行（同名 conftest 冲突）。
- 修复：Windows 3.11/3.12 粗时钟（约 15.6 ms）下同刻写入的多条近重复，去重合并目标取「同刻组里最旧」而非最新（排序次键 id 改倒序）；新增粗时钟回归用例。

## 未修 / 未承诺（如实列出）
- HTTP 每连接一线程、并发连接无硬上限；导出整库进内存、无流式；令牌无过期 / 轮换；无 TLS / 多租户 / RBAC（交给反向代理）。
- 审计只覆盖 HTTP 通道（MCP / CLI 写入不记）。
- 插件即代码的信任模型、模型目录同用户可替换、依赖未锁定哈希、若干三次方正则——见安全报告第 3 节。
- 控制台只做过 jsdom 端到端冒烟，未在真实浏览器矩阵上测。
