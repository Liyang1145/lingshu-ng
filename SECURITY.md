# 安全策略

- 支持版本：最新的 1.x 发布版。
- 报告漏洞：请不要公开开 issue，使用 GitHub「Security → Report a vulnerability」私下报告。
- 我们会在 7 天内回复，并在修复发布后公开说明。
- 安全测试报告与威胁模型：docs/security/SECURITY_REPORT_sec-r1.md；部署安全基线：docs/ENTERPRISE.md。
- 依赖：核心零第三方依赖；插件依赖下沿已排除已知漏洞版本（CI 守卫 tests_ng/test_security_deps.py）。

## 威胁模型摘要
- 信任边界：HTTP（缺省仅回环；非回环须 Bearer 令牌并放在 TLS 反向代理后）、MCP stdio（信任父进程，工具参数视为不可信）、导入 JSON（视为不可信，已隔离与校验）、插件（导入即执行代码，仅安装可信包）。
- 缺省防护：Host/Origin 校验防 DNS 重绑定与 CSRF、请求体与并发上限、SQL 全参数化、不调用 shell。
- 逐入口 STRIDE 表见 docs/security/SECURITY_REPORT_sec-r1.md。
