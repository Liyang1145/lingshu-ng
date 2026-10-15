# lingshu-ng 企业部署指南

适用版本：1.31 起。本文是运维视角的一页纸：怎么装、怎么跑、怎么守、支持到哪。

## 1. 交付形态

| 形态 | 依赖 | 用途 |
|---|---|---|
| `pip install lingshu-ng` | 无第三方依赖（纯标准库，AST 守卫保证） | 进程内嵌入：`from lingshu_ng.engine import MemoryEngine` |
| `lingshu-ng serve` | 同上 | 本机 / 内网 HTTP 服务（`/v1/perceive`、`/v1/recall`、`/v1/status`、`/v1/capabilities`、`/healthz`） |
| `lingshu-ng mcp` | 同上 | MCP stdio 服务器，给 Claude Desktop / Cursor 等客户端 |
| `lingshu-ng console` | 同上 | 本地 Web 控制台（见 [CONSOLE.md](CONSOLE.md)） |
| Docker 镜像（仓库根 `Dockerfile`） | python:3.12-slim + 核心 | 容器化 HTTP 服务，非 root（uid 10001），数据卷 `/data` |
| `lingshu-ng-adapters` 插件 | 可选 langchain-core / llama-index-core | mem0 兼容 API、LangChain、LlamaIndex、官方 MCP memory 工具名（见 plugins/lingshu-ng-adapters/README.md） |
| `lingshu-ng-embed` 等插件 | numpy / onnxruntime / tokenizers / Pillow | 可选语义重排与实验线，不装不影响核心 |

## 2. 支持矩阵

- Python 3.11 / 3.12 / 3.13；Linux、Windows、macOS（CI 每次提交全矩阵跑核心测试）。
- 3.9 / 3.10 不支持（`requires-python >=3.11`，pip 会拒装）。
- 数据库：SQLite（WAL）。新版可自动升级旧库；升级后旧版本无法再打开，升级前请先 `export`。

## 3. 安全基线（默认即安全）

- 默认只绑 `127.0.0.1`；绑任何非回环地址必须设置 `LINGSHU_NG_TOKEN`，否则拒绝启动。
- 只绑本机时只认回环 `Host`（挡 DNS 重绑定）；无令牌时拒绝非本机 `Origin`（挡跨站写入）。
- 请求体上限 1 MiB、读超时 30 s、listen 积压 128、拒绝 `Transfer-Encoding`、深嵌套 JSON 回 400。
- 令牌常数时间比较；可用 `LINGSHU_NG_TOKEN_FILE`（每行一个令牌）免重启轮换：先加新令牌并存，客户端切换后删旧令牌即吊销；文件读出空集时拒绝所有请求（失败关闭）。
- 并发连接上限 `LINGSHU_NG_MAX_CONN`（缺省 64），满则立即回 503 + `Retry-After: 1`，`/v1/health` 报 `rejected_busy`。
- 不做 TLS——对外暴露必须放在反向代理（TLS + 访问控制）之后。
- 新建库文件权限 0600；导入按 schema 类型逐值校验，坏行拒收并计入报告，覆盖已有节点计入 `overwritten`。
- 标签 / 实体单次最多 1000 项、单项 ≤1024 字符；查询截断 4096 字符；limit ≤100000。
- 可选 LLM 抽取默认关闭；开启后只允许 https（或本机 http）端点。
- 完整测试报告与威胁模型：[security/SECURITY_REPORT_sec-r1.md](security/SECURITY_REPORT_sec-r1.md)。漏洞请按 [SECURITY.md](../SECURITY.md) 私下报告。

## 4. 推荐部署

**单机嵌入**：应用进程内直接用 `MemoryEngine(path)`，库放应用私有目录。

**团队内网服务**（Docker）：
```bash
docker build -t lingshu-ng .
docker run -d --name lingshu -p 127.0.0.1:8765:8765 -v lingshu-data:/data \
  -e LINGSHU_NG_TOKEN="$(openssl rand -hex 32)" --restart unless-stopped lingshu-ng
```
前面挂 Nginx / Caddy 做 TLS，并限制来源网段。

**本机管理界面**：`lingshu-ng console --db PATH`（缺省 127.0.0.1:8766）提供浏览 / 检索 / 写入 / 删除 / 导入导出 / 健康页面，安全措施与 `serve` 相同，另加 CSP、`X-Lingshu-Console` 头和写操作审计日志（logger `lingshu_ng.audit`）。容器内可改用 `CMD ["lingshu-ng", "console", "--host", "0.0.0.0", "--port", "8766"]`（同样必须给令牌）。见 [`CONSOLE.md`](CONSOLE.md)。

**备份**：`lingshu-ng` 的 `export_all` 产出 JSON 全量备份；或在服务停写时复制 `memory.sqlite`（含 `-wal`）。

## 5. 运维要点

- 健康检查：`GET /healthz`（免鉴权）。镜像自带 HEALTHCHECK。
- 日志：标准 `logging`，logger 前缀 `lingshu_ng`；`LINGSHU_NG_LOG=DEBUG` 也不会打印记忆原文或令牌。
- 能力自检：`GET /v1/capabilities` 或 `engine.capabilities()`，列出哪些可选件启用 / 为什么退回。
- 备份（不停机）：`lingshu-ng backup --db data.db /backup/data-20261016.db`——SQLite 在线备份 API 拷贝，
  快照跑 `integrity_check`，旁边写 `*.manifest.json`（版本、行数、SHA-256）。适合放进 cron。
- 恢复（先停服务）：`lingshu-ng restore --db data.db /backup/data-20261016.db --force`——先校验快照与清单校验和，
  旧库自动另存为 `data.db.pre-restore-<时间戳>`，再原子替换。两个命令都写 `lingshu_ng.audit`（`remote=cli`）。
- 逻辑备份（跨版本迁移）仍用 `/v1/export` / `/v1/import`。
- 多进程同时写同一库：SQLite 写锁串行，未做压测承诺；高并发写请走单个服务进程。
- 供应链：`python tools/release/sbom.py -o lingshu-ng.cdx.json` 生成 CycloneDX 1.5 SBOM（核心零第三方依赖，插件依赖以版本区间列出）；`python tools/release/checksums.py --check SHA256SUMS` 校验发布产物。CI 作业 `release-artifacts` 每次构建 wheel/sdist + SBOM + SHA256SUMS 并作为产物上传，Release 说明附校验和表。

## 6. 已知限制（如实列出）

- 不提供多租户隔离、RBAC、TLS；需要时由反向代理 / 上层应用承担。
- sec-r1 列出的信息级遗留项（插件即代码、模型目录可被同用户替换等）属设计边界，见安全报告第 3 节。
- 检索质量对比的结论分层与未胜项见 docs/VS_UPSTREAM_cb3a6ea.md，不作「整体更优」承诺。
