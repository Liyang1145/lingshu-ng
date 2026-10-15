# rel-v1.33（lingshu-ng 1.33.0）— 可运维与供应链

## 可运维
- E6-2 结构化日志：`LINGSHU_NG_LOG_FORMAT=json` 时每行一个 JSON（`ts` UTC 毫秒 / `level` / `logger` / `msg`，异常带 `exc`），缺省 `text`；值非法时 CLI / 控制台启动即报错（退出码 2），不静默退回。
- E6-2 `GET /metrics`：Prometheus 文本格式 0.0.4，**与其他接口同样需要 Bearer 令牌**。指标：`lingshu_ng_info{version}`、`lingshu_ng_uptime_seconds`、`lingshu_ng_http_requests_total`、`lingshu_ng_http_responses_total{code}`、`lingshu_ng_http_rejected_busy_total`、`lingshu_ng_http_max_connections`、`lingshu_ng_memory_nodes`、`lingshu_ng_memory_nodes_by_layer{layer}`、`lingshu_ng_schema_version`。只含计数，不含记忆正文；`POST /metrics` 回 405。
- E6-3 `lingshu-ng backup` / `lingshu-ng restore`：SQLite 在线备份 API 物理快照（服务运行中可做），快照跑 `integrity_check` 并写 `*.manifest.json`（版本、行数、SHA-256）；恢复前校验快照、表结构与清单校验和，旧库另存为 `*.pre-restore-<时间戳>` 后原子替换；两个命令都写审计日志（`remote=cli`）。

## 供应链
- E6-1 `tools/release/sbom.py`：生成 CycloneDX 1.5 JSON SBOM（核心包 + 5 个插件包 + 插件声明的第三方依赖，依赖版本以区间记录；同一源码与时间戳下输出确定）。核心包依赖为空。
- E6-1 `tools/release/checksums.py`：SHA256SUMS 生成 / 校验（与 `sha256sum -c` 同格式）与 Release 说明用的 Markdown 表。
- CI 新增 `release-artifacts` 作业：每次构建 wheel / sdist + SBOM + SHA256SUMS，自校验后作为 CI 产物上传，校验和表写入作业摘要。

## 未修 / 未承诺
- `/metrics` 无请求时延直方图；多进程部署时各进程计数独立。
- SBOM 只列声明的依赖区间，不含安装环境实际解析版本与传递依赖（需要时用 `pip-audit` / `cyclonedx-py` 对安装环境另行生成）。
- 物理快照不可跨 schema 降级恢复；跨版本迁移仍用 `/v1/export` / `/v1/import`。
- 无 TLS / 多租户 / RBAC（交给反向代理）。
