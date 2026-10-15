# lingshu-ng 选型说明（ADOPTION）

本文只写可在本仓验证的事实；对其他产品（mem0、LangChain memory、Zep 等）不做未经实测的断言，其能力请以各自官方文档为准。

## 本仓可验证的能力
| 能力 | 依据 |
|---|---|
| 核心纯标准库（零第三方依赖） | AST 守卫测试 tests_ng |
| 单文件 SQLite 存储，可备份/恢复（integrity_check） | `lingshu-ng backup/restore`，tests_ng/test_backup_cli.py |
| HTTP/MCP/CLI 三入口，写入均记审计（不含正文） | docs/ENTERPRISE.md |
| 令牌鉴权、令牌文件免重启轮换、并发上限 503 | docs/ENTERPRISE.md |
| Web 控制台与浏览器端到端测试 | docs/CONSOLE.md，CI console-e2e |
| JSON 日志、/metrics | docs/ENTERPRISE.md |
| SBOM 与发布校验和 | CI release-artifacts |
| 对上游 API 的兼容矩阵 | docs/VS_UPSTREAM_cb3a6ea.md |
| 稳定性与规模数据 | docs/STABILITY_ng.md、docs/PERF_ng.md |
| 安全审查与修复记录 | docs/security/ |
| Linux/Windows/macOS × Python 3.11–3.13 CI | .github/workflows/ci.yml |

## 适合
需要自托管、可审计、无外部依赖、可白箱审查的记忆层。

## 未胜项 / 限制
- 不提供托管服务与商业 SLA。
- 未做与 mem0/Zep 等的同数据集横向实测，故不声称检索质量更优。
- 语义/向量等增强以可选插件提供，缺失时退回基础检索（见 capabilities()）。
- Release 未附 wheel 资产（上传通道不可用）。
- 单机 SQLite，不含多节点复制。

## 评估建议
1. 用自己的数据跑 `lingshu-ng doctor`（见 E8-2 落地后）与备份/恢复演练。
2. 按 docs/ENTERPRISE.md 配置令牌与绑定，查看 /metrics。
3. 对比时请用自己的业务语料，自行实测。
