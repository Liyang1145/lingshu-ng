# lingshu-ng-adapters

把 lingshu_ng（灵枢记忆引擎 ng，纯标准库核心）当作现有生态里的**记忆后端直接替换**接入。核心仍零外部依赖；
本包必需依赖只有 `lingshu-ng`，LangChain / LlamaIndex 两组是可选 extra。

```bash
pip install lingshu-ng-adapters                 # mem0 兼容 API + MCP 记忆服务器（无第三方依赖）
pip install 'lingshu-ng-adapters[langchain]'    # + langchain-core
pip install 'lingshu-ng-adapters[llamaindex]'   # + llama-index-core
```

| 你原来用的 | 换成 | 覆盖 |
|---|---|---|
| `from mem0 import Memory` / `AsyncMemory` | `from lingshu_ng_adapters.mem0 import Memory` / `AsyncMemory` | `add` `get` `get_all` `search` `update` `delete` `delete_all` `history` `reset` `from_config`；签名与 mem0ai 2.2.1 逐参数一致（测试比对） |
| LangChain `BaseChatMessageHistory` 实现（Redis/SQL…） | `lingshu_ng_adapters.langchain.LingshuChatMessageHistory(session_id, path=...)` | `messages` `add_messages` `add_message` `clear` + 基类异步方法；可直接给 `RunnableWithMessageHistory` |
| LangChain `BaseRetriever` | `LingshuRetriever(engine=..., k=4)` | `_get_relevant_documents`（`invoke(q, k=…)`、`ainvoke`、`batch`）；通过 langchain-tests `RetrieversIntegrationTests` |
| LangChain `VectorStore`（Chroma/FAISS…） | `LingshuVectorStore(engine=...)` / `LingshuVectorStore.from_texts(...)` | `add_texts` `add_documents` `delete` `get_by_ids` `similarity_search(_with_score/_with_relevance_scores)` `from_texts` `as_retriever` + 异步；通过 langchain-tests `VectorStoreIntegrationTests` |
| LlamaIndex `BaseRetriever` | `lingshu_ng_adapters.llamaindex.LingshuRetriever(engine, similarity_top_k=4)` | `_retrieve`（`retrieve` / `aretrieve`） |
| LlamaIndex `BaseMemory`（ChatMemoryBuffer…） | `LingshuChatMemory.from_defaults(path=..., session_id=...)` | `from_defaults` `get` `get_all` `put` `set` `reset` + 基类异步 |
| LlamaIndex 新版 `Memory` 的长期记忆块 | `Memory.from_defaults(memory_blocks=[LingshuMemoryBlock(engine=e)])` | `_aget` `_aput` |
| `npx -y @modelcontextprotocol/server-memory` | `lingshu-ng-mcp-memory --db mem.sqlite`（或 `python -m lingshu_ng_adapters.mcp_memory`） | 官方 9 个工具同名同参同返回形状 + `memory://knowledge-graph` 资源；`--import-jsonl memory.jsonl` 迁移旧数据 |

## 与原实现的有意差异

- **零 LLM 写入**：mem0 `add(infer=True)` 不调用 LLM 抽取事实，而是把每条非 system 消息原文写入；同一作用域内相同正文不重复写（等价 mem0 的 NONE 事件）。`memory_type="procedural_memory"` ⇒ `NotImplementedError`；`prompt` 被忽略。
- **作用域隔离**：`user_id` / `agent_id` / `run_id` 是精确标签；不同作用域的同一句话是两条记忆（核心 M5 去重不看标签，适配器写入时关闭它、改在作用域内去重）。
- **mem0 旧调用兼容**：`search` / `get_all` 额外接受 mem0 0.x/1.x 的顶层 `user_id=` / `limit=`（mem0 2.x 对此抛 `ValueError`）。
- **分数**：`score` 是 lingshu_ng 组合召回分（词面 + 可选本地语义 / 重排），不是向量余弦；`LingshuVectorStore` 召回不足 `k` 条时按写入顺序以 0 分补足（kNN 约定，`fill_k=False` 关闭）。外部 `embedding` 参数被接受但不参与检索；`max_marginal_relevance_search` 与 `*_by_vector` 未实现。
- **MCP**：`search_nodes` 缺省与官方一样做子串匹配；`--recall-search` 时另并入引擎召回。`resources/subscribe` 接受但不推送 `notifications/resources/updated`。
- **变更历史**（mem0 `history`）存在同库旁表 `ngad_history`，核心 `export_all` 不导出它。
- `reset()` 只清本适配器命名空间写入的记忆，不动同库其它来源写入的节点。

## 测试

```bash
python -m pytest plugins/lingshu-ng-adapters/tests_adapters -q
```

无 langchain-core / llama-index-core 时只跑缺库报错契约（子进程屏蔽导入，断言抛 `MissingDependencyError` 且信息含 `pip install`）；
装了 `langchain-tests` + `pytest-asyncio` 时另跑 LangChain 官方标准套件。
