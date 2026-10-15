# lingshu-ng-adapters 兼容报告（ent-compat，基于 Liyang/ = rel-v1.30.0）

只写实测读数；未测写未测。环境：Linux aarch64 沙箱，`LINGSHU_NG_SEM=off`，venv 内装 pytest + numpy + Pillow（无 onnxruntime / tokenizers），
SQLite 库全部在 /tmp（pytest tmp_path）或 `:memory:`。核心 `lingshu_ng/` 本分支**零改动**（diff 只在 `plugins/lingshu-ng-adapters/`）。

## 对齐对象（2026-10 调研，签名以实装库 inspect 为准）

| 接口 | 版本 / 来源 | 最小方法集 |
|---|---|---|
| mem0 `Memory` / `AsyncMemory` | mem0ai 2.2.1（PyPI；mem0/memory/main.py、storage.py） | add(messages, *, user_id, agent_id, run_id, metadata, timestamp, expiration_date, infer, memory_type, prompt) / get(memory_id) / get_all(*, filters, top_k=20, show_expired, **kw) / search(query, *, top_k=20, filters, threshold=0.1, rerank, explain, reference_date, show_expired, **kw) / update(memory_id, text, metadata, expiration_date, data) / delete / delete_all(user_id, agent_id, run_id) / history / reset |
| LangChain | langchain-core 1.6.10 | BaseChatMessageHistory：抽象 `clear`，实际需 `messages` + `add_messages`；BaseRetriever：抽象 `_get_relevant_documents(query, *, run_manager)`；VectorStore：抽象 `similarity_search`、`from_texts`，实用面 `add_texts`/`delete`/`get_by_ids` |
| LlamaIndex | llama-index-core 0.14.25 | BaseRetriever：`_retrieve(query_bundle)`；BaseMemory：`from_defaults`/`get`/`get_all`/`put`/`set`/`reset`；BaseMemoryBlock：`_aget`/`_aput` |
| MCP 记忆服务器 | modelcontextprotocol/servers `src/memory/index.ts`（main） | create_entities / create_relations / add_observations / delete_entities / delete_observations / delete_relations / read_graph / search_nodes / open_nodes + 资源 `memory://knowledge-graph` |
| OpenAI Assistants / Responses 记忆 | 无标准记忆接口 | 跳过 |

## 各适配器

### mem0（`lingshu_ng_adapters.mem0`，纯标准库，不依赖 mem0）
- 覆盖：Memory / AsyncMemory 的 add、get、get_all、search、update、delete、delete_all、history、reset，另 from_config、close。
- 读数：`test_mem0.py` 32 passed、1 skipped（无 mem0 环境；skip 的是「与现装 mem0 比对」）；装 mem0ai 2.2.1 的 venv：33 passed（含现装比对）。
  签名契约 18 条（2 类 × 9 方法，形参名/种类/缺省值/同步异步与 mem0ai 2.2.1 逐项相等）。
- 未覆盖 / 不同：infer=True 不调 LLM（原文写入 + 作用域内去重）；procedural_memory ⇒ NotImplementedError；prompt / rerank 无作用；
  reference_date ⇒ ValueError（同 mem0 OSS）；score 为组合召回分非余弦；history 旁表不随核心 export_all 导出；reset 只清本命名空间；
  mem0 的图记忆（graph store）、多模态解析（vision）、telemetry、Platform 客户端 `MemoryClient` 未覆盖；Windows/macOS 未测。

### LangChain（`lingshu_ng_adapters.langchain`，需 langchain-core）
- 覆盖：LingshuChatMessageHistory（messages / add_messages / add_message / clear / 基类异步）、LingshuRetriever（_get_relevant_documents，支持 invoke(k=)）、
  LingshuVectorStore（add_texts / add_documents / delete / get_by_ids / similarity_search / _with_score / _with_relevance_scores / from_texts / as_retriever / 基类异步）。
- 读数（langchain-core 1.6.10 + langchain-tests 1.1.9 + pytest-asyncio 1.4.0）：`test_langchain.py` 38 passed，其中官方标准套件 30 条
  （VectorStoreIntegrationTests 25 + RetrieversIntegrationTests 5）全过；自写 8 条（含 RunnableWithMessageHistory 串接、跨实例持久）。
  无 langchain-core：1 passed（缺库报错契约）+ 模块 skip。
- 未覆盖：max_marginal_relevance_search、similarity_search_by_vector 等需向量的方法；外部 embedding 不参与检索；BaseChatMessageHistory 的 LangGraph 持久化（checkpointer）未做。

### LlamaIndex（`lingshu_ng_adapters.llamaindex`，需 llama-index-core）
- 覆盖：LingshuRetriever（_retrieve；retrieve/aretrieve）、LingshuChatMemory（BaseMemory 全部 6 个抽象方法 + 基类异步）、LingshuMemoryBlock（_aget/_aput，接新版 `Memory.from_defaults(memory_blocks=...)`）。
- 读数（llama-index-core 0.14.25）：`test_llamaindex.py` 7 passed（含新版 Memory 短期溢出 → 写入 lingshu → 召回注入的端到端）。无库：1 passed + 模块 skip。
- 未覆盖：token 级截断（get 按条数 max_messages）、MemoryBlock.atruncate（基类缺省整块丢弃）、VectorStoreIndex / BasePydanticVectorStore 适配（未做）、ChatStore 接口（未做）。

### MCP（`lingshu_ng_adapters.mcp_memory`，纯标准库）
- 覆盖：官方 9 个工具同名、入参必填键、annotations、structuredContent / 文本形状、错误文案（`Entity with name X not found`、`Deleted 1 of 2 …`）逐条对照；
  资源 list/read/subscribe；官方 memory.jsonl 导入；同一引擎同时提供 ng 的 lingshu_perceive / recall / status / capabilities。
- 读数：`test_mcp_memory.py` 11 passed（含 stdio 子进程两次启动跨进程持久）。
- 未覆盖：`notifications/resources/updated` 推送（订阅接受但不推送）；MCP HTTP/SSE 传输（只做 stdio）；官方 server 的跨进程文件锁语义由 SQLite 写锁替代（未做并发压力测）。

## Python 版本矩阵

| Python | tests_ng（核心全量） | tests_adapters（无第三方库） | tests_adapters（+ langchain-core / llama-index-core / langchain-tests） |
|---|---|---|---|
| 3.13.5 | 1865 passed, 5 skipped（47.8 s） | 43 passed, 3 skipped | 88 passed, 1 skipped |
| 3.12.15 | 1865 passed, 5 skipped（54.0 s）＝ 未加插件的 main 基线读数相同 | 43 passed, 3 skipped | 88 passed, 1 skipped；mem0ai 2.2.1 环境 test_mem0 33 passed |
| 3.11.17 | 1865 passed, 5 skipped（53.0 s） | 43 passed, 3 skipped | 88 passed, 1 skipped |
| 3.10.22 | 收集中断（2 errors：tomllib 缺失）；`--continue-on-collection-errors`：1857 passed, 5 skipped, 2 errors | 43 passed, 3 skipped | 88 passed, 1 skipped |
| 3.9.25 | 收集中断（3 errors：tomllib ×2、sys.stdlib_module_names ×1）；`--continue-on-collection-errors`：1848 passed, 5 skipped, 3 errors | 43 passed, 3 skipped | 未测 |
| Windows / macOS | 未测 | 未测 | 未测 |

说明：核心与本插件 `requires-python = ">=3.11"`（pip 在 3.9/3.10 上拒装）；3.9/3.10 的错误只在测试基础设施（tomllib / sys.stdlib_module_names），
不是引擎运行期错误，但不在承诺范围内。安装态：干净 venv（3.12）`pip install Liyang/ plugins/lingshu-ng-adapters` 后，入口点发现插件
（`plugins.installed()` 含 adapters，`provider("adapter:mem0")` 解析到类），在无关目录跑 tests_adapters 43 passed, 3 skipped，
`lingshu-ng-mcp-memory` 命令可用。
