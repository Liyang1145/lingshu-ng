# rel-v1.32（lingshu-ng 1.32.0，进行中）

## 运维与安全
- E5-1 HTTP 并发连接上限：`LINGSHU_NG_MAX_CONN`（缺省 64），满则立即回 503 + `Retry-After: 1`，不再无限开线程；`/v1/health` 增 `max_conn`、`rejected_busy`。
- E5-3 令牌免重启轮换：`LINGSHU_NG_TOKEN_FILE`（每行一个有效令牌，`#` 注释），按 mtime 自动重读，新旧令牌可并存过渡；文件读出空集时拒绝所有请求（失败关闭）；文件启动时不可读则拒绝启动。可与 `--token` 同时使用。
- 新增公开 API：`lingshu_ng.integrations.http.Server.valid_tokens`（只增不改）。
