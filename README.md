# lingshu-ng

自托管的 AI 记忆层：单文件 SQLite 存储，核心只用 Python 标准库，带 HTTP / MCP / 命令行三种接入方式和一个本机 Web 控制台。

它是 [FuRongJun-1999/lingshu](https://github.com/FuRongJun-1999/lingshu) 身体侧记忆引擎的独立重写，保留上游的设计取向：写入不调用任何模型、存原句召回原句、向量等只作可重建的派生索引、结果可追溯且确定。旧 API 的调用方可以通过兼容门面 `lingshu_ng.compat` 无改动切换。

## 特点

- **零依赖核心**：`pip install lingshu-ng` 不装任何第三方包，AST 守卫测试保证核心里不出现非标准库导入。
- **五层记忆**：锚点、结构、知识、情境、自我；写入时自动去重、合并近重复，召回时给出相关度与来源。
- **三种接入**：进程内 Python API、HTTP/JSON 服务、MCP stdio 服务器；另有 mem0 / LangChain / LlamaIndex 适配器插件。
- **默认安全**：只绑本机；绑外网必须设令牌；令牌可免重启轮换；并发上限、请求体上限、审计日志（不记正文）。
- **可运维**：`doctor` 自检、在线备份与校验恢复、`/metrics`、JSON 日志、SBOM 与可复现构建。
- **白箱、可验证**：Linux / Windows / macOS × Python 3.11–3.13 的 CI 矩阵，控制台有真实浏览器端到端测试与设计审查门。

## 安装

需要 Python 3.11 或更高。

```bash
pip install lingshu-ng                  # 核心，零依赖
pip install lingshu-ng-adapters         # 可选：mem0 / LangChain / LlamaIndex / MCP 记忆工具适配
pip install lingshu-ng-embed            # 可选：本地 ONNX 语义重排（numpy、onnxruntime、tokenizers；模型权重自备）
```

从源码安装：`pip install -e .`，插件在 [`plugins/`](plugins/) 下，各自 `pip install ./plugins/<名字>`。

## 快速上手

Python：

```python
from lingshu_ng.engine import MemoryEngine

mem = MemoryEngine("mem.db")
mem.perceive("客户张总偏好邮件沟通，不接受晚上九点后的电话。", tags=["客户", "偏好"])
for node, score in mem.recall("怎么联系张总", limit=5)["hits"]:
    print(round(score, 3), node.content)
```

命令行：

```bash
lingshu-ng perceive --db mem.db "项目周会改到周四下午三点" --tag 会议
lingshu-ng recall   --db mem.db "周会什么时候" --limit 5
lingshu-ng serve    --db mem.db                     # HTTP 服务，127.0.0.1:8765
lingshu-ng mcp      --db mem.db                     # MCP stdio，给 Claude Desktop / Cursor 等
lingshu-ng console  --db mem.db                     # Web 控制台，http://127.0.0.1:8766/
lingshu-ng doctor   --db mem.db                     # 只读自检
```

Docker：仓库根的 `Dockerfile` 构建非 root 镜像，数据卷 `/data`，必须通过 `LINGSHU_NG_TOKEN` 提供令牌。

## 文档

| 文档 | 内容 |
|---|---|
| [docs/API_ng.md](docs/API_ng.md) | Python API、兼容门面、`capabilities()`、异常、环境变量 |
| [docs/INTEGRATION_ng.md](docs/INTEGRATION_ng.md) | 命令行、HTTP 接口、MCP 工具 |
| [docs/CONSOLE.md](docs/CONSOLE.md) | Web 控制台：启动、安全模型、界面说明 |
| [docs/ENTERPRISE.md](docs/ENTERPRISE.md) | 部署形态、支持矩阵、安全基线 |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | 监控、备份、令牌轮换、升级回滚、故障排查 |
| [docs/UPGRADE.md](docs/UPGRADE.md) | 库结构版本与升级 / 回滚矩阵 |
| [docs/STABILITY_ng.md](docs/STABILITY_ng.md) | 版本号规则、弃用流程、公开 API 清单 |
| [docs/PERF_ng.md](docs/PERF_ng.md) | 性能读数与剖析 |
| [docs/ADOPTION.md](docs/ADOPTION.md) | 选型说明：能做什么、不做什么 |
| [docs/COMPAT_MATRIX.md](docs/COMPAT_MATRIX.md)、[docs/VS_UPSTREAM_cb3a6ea.md](docs/VS_UPSTREAM_cb3a6ea.md) | 对上游 API 的兼容覆盖，与上游同口径的对照 |
| [docs/security/](docs/security/) | 安全审查报告与修复记录 |
| [docs/RESEARCH.md](docs/RESEARCH.md) | 研究期的测评结论摘要 |
| [CHANGELOG.md](CHANGELOG.md) | 更新日志 |

## 测试

```bash
pip install -e . pytest
LINGSHU_NG_SEM=off python -m pytest tests_ng -q          # 核心
python -m pytest plugins/lingshu-ng-adapters -q           # 某个插件
python -m pytest tests_e2e -q                             # 控制台浏览器端到端（需 playwright + chromium）
```

缺可选依赖或模型时，相关用例会带原因跳过，其余必须通过。测试结尾会打印本机实际生效的检索档位。

## 已知限制

- 单机 SQLite，不含多节点复制；不做 TLS、多租户与 RBAC，对外暴露请放在反向代理之后。
- 没有与 mem0、Zep 等产品在同一数据集上的横向检索对比，不声称检索质量更优。
- 库文件体积约为上游的 2.6 倍（10k 条 17.5 MB 对 6.8 MB），晋升操作仍慢于上游，详见 [docs/VS_UPSTREAM_cb3a6ea.md](docs/VS_UPSTREAM_cb3a6ea.md)。
- 控制台端到端测试只覆盖 Chromium。

## 许可

MIT，与上游相同，见 [LICENSE](LICENSE)。安全问题请按 [SECURITY.md](SECURITY.md) 报告。
