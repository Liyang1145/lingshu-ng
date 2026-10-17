# lingshu-ng 运维手册

只写本仓已实现的行为；细节见 ENTERPRISE.md。

## 1. 监控
- 健康：`GET /v1/health`（含 `rejected_busy`）。
- 指标：`GET /metrics`（Prometheus 文本，需 Bearer 令牌）。抓取示例：
```yaml
scrape_configs:
  - job_name: lingshu-ng
    metrics_path: /metrics
    authorization: {credentials_file: /etc/prometheus/lingshu.token}
    static_configs: [{targets: ["127.0.0.1:8765"]}]
```
- 指标名：`lingshu_ng_info`、`lingshu_ng_uptime_seconds`、`lingshu_ng_http_requests_total`、`lingshu_ng_http_responses_total`（按状态码计错误）、`lingshu_ng_http_request_duration_seconds`（直方图，可用 histogram_quantile 求分位）、`lingshu_ng_http_rejected_busy_total`、`lingshu_ng_http_max_connections`、`lingshu_ng_memory_nodes`、`lingshu_ng_memory_nodes_by_layer`、`lingshu_ng_schema_version`、`lingshu_ng_db_size_bytes`（库文件含 WAL 字节数）、`lingshu_ng_audit_events_total`（进程启动以来审计日志行数）。`lingshu_ng_http_slow_requests_total`（按路由计超过 `LINGSHU_NG_SLOW_MS` 毫秒的请求，默认 1000，≤0 关闭）。
- 探针（无需鉴权）：`/healthz` 进程存活；`/readyz` 库可开且能拿写锁，否则 503。K8s 示例：
```yaml
livenessProbe:  {httpGet: {path: /healthz, port: 8765}, periodSeconds: 10}
readinessProbe: {httpGet: {path: /readyz,  port: 8765}, periodSeconds: 5, failureThreshold: 3}
```
- 日志：`LINGSHU_NG_LOG_FORMAT=json` 便于采集。
- 一键自检：`lingshu-ng doctor`（JSON 输出，有问题时退出码非零，可挂到定时探活）。
  - 退出码：`0` 全部通过（`ok=true`）；`1` 存在失败项（`ok=false`，见 `checks[].status`）。输出恒为 JSON（含 `ok` 与 `checks`），无需额外 `--json`。

## 2. 备份
```cron
0 3 * * * lingshu-ng backup --db /var/lib/lingshu/data.db /backup/data-$(date +\%F).db && find /backup -name 'data-*.db' -mtime +14 -delete
```
在线备份不停服务。恢复须先停服务：`lingshu-ng restore --db data.db <快照> --force`。建议定期在测试机演练恢复。

## 3. 令牌轮换（免重启）
1. 在 `LINGSHU_NG_TOKEN_FILE` 指向的文件追加新令牌（每行一个）。
2. 客户端切换到新令牌。
3. 删除旧令牌行即吊销。文件读出为空时拒绝所有请求（失败关闭）。

## 4. 升级与回滚
- 升级前：`lingshu-ng backup`，再 `pip install -U lingshu-ng`，重启后跑 `lingshu-ng doctor`。
- 回滚：停服务，`pip install lingshu-ng==<旧版本>`，用升级前的备份 `restore`（新 schema 的库旧版本可能拒绝打开，所以要用备份）。
- schema 升级：新版本首次打开旧库时自动迁移且不可逆；因此升级前必须备份，并先在备份副本上验证（`restore` 到临时路径后跑 `doctor`）。
- 发行物校验：Release 对应 CI 产物含 SHA256SUMS 与 SBOM；两次构建在固定 `SOURCE_DATE_EPOCH` 下字节一致（`python tools/release/repro_check.py`）。

## 5. 故障排查
| 现象 | 排查 |
|---|---|
| 503 + Retry-After | 并发满；调大 `LINGSHU_NG_MAX_CONN`（缺省 64）或限流上游；看 `http_rejected_busy_total` |
| 全部 401/拒绝 | 令牌错误，或令牌文件为空/读失败（失败关闭）；检查文件权限 |
| 启动退出码 2 | 环境变量取值非法（如 `LINGSHU_NG_LOG_FORMAT`），看启动报错 |
| 库打不开/报 schema | 版本不匹配；`lingshu-ng doctor`，必要时回滚并 restore |
| /metrics 401 | 抓取端未带令牌 |
| 磁盘紧张 | doctor 报告余量；清旧备份 |

## 请求体大小上限

`LINGSHU_NG_MAX_BODY`（字节，缺省 1048576，合法范围 1024–268435456，非法值回退缺省）限制普通写请求体，超限回 413；进程启动时读取，改后需重启。`/v1/import` 另有固定上限（32 MiB）。

## 容量规划与备份演练清单

- 容量：以 `lingshu_ng_db_size_bytes` 与 `lingshu_ng_memory_nodes` 的比值估算单条平均体积，按增长曲线预留磁盘（含 WAL 与备份副本，至少 3 倍库大小）；`doctor` 会报告磁盘余量。
- 备份演练（建议每季度）：1) `lingshu-ng backup` 生成备份；2) 在隔离目录 `lingshu-ng restore` 恢复；3) 对恢复库运行 `lingshu-ng doctor`，确认 integrity_check 通过；4) 对比 `lingshu_ng_memory_nodes` 与原库一致；5) 记录耗时作为恢复时间目标（RTO）依据。
