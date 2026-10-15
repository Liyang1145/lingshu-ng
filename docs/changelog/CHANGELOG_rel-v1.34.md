# lingshu-ng v1.34.0

- `/metrics` 增请求时延直方图（按路由，固定桶）。
- 新增 `lingshu-ng doctor`：库 integrity_check、schema 版本、磁盘余量、令牌/绑定配置风险、可选件状态；JSON 输出，有故障退出码非零。
- 可复现构建：固定 `SOURCE_DATE_EPOCH` 下 wheel 与（归一化后的）sdist 两次构建逐字节一致；`tools/release/repro_check.py`，并加入 CI release-artifacts 作业。
- 新增 `docs/OPERATIONS.md` 运维手册（监控、备份 cron、令牌轮换、升级/回滚、故障排查）；`docs/ADOPTION.md` 选型说明。
- 修复 doctor 能力探测的静默宽 except（改记日志）。
