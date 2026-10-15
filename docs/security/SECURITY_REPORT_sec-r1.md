# lingshu_ng 企业级安全测试报告（sec-r1）

## 0. 范围与环境
- 被测代码：TanPowasd/LingShu-prime@c7dcf61 的 `Liyang/` 子树（`lingshu_ng.__version__ == "1.30.0"`）。本沙箱里没有 /workspace/work/ls/wt-rel，所以按任务说明从 GitHub 稀疏克隆了上游。只取了 Liyang/，没有碰 TanPowasd/ 目录。另有一个早先沙箱（之后被重置）里存在 wt-rel f291417e，在那里跑出的基线测试数完全一致（1838 passed / 24 skipped / 1 failed），由此推断两者在被测范围内一致，但没有逐字节比对。
- 工作副本：独立 git 仓库，根目录对应 Liyang/。沙箱的 /tmp 被重置过两次，所以仓库改放在项目 scratch 目录 `work/sec_audit/repo`，SQLite 临时库仍放 /tmp。没有 push，没有开 issue 或 PR。
- 运行环境：Linux，Python 3.12.15，未装 numpy、onnxruntime、tokenizers。因此 world/nn/gen/embed 插件的运行时路径没有测，只做了静态扫描。
- 下文的行号都指基线 c7dcf61 中的 Liyang/ 文件。
- 基线 tests_ng：1838 passed，24 skipped，1 failed。失败的是 `test_entry_modules::test_gen_entry_attrs_resolve_to_submodules`，原因是缺 numpy，属于环境问题。
- 修复后 tests_ng：1859 passed（新增 21 个安全用例），24 skipped，同样只有那 1 个 numpy 用例失败。没有回退。

## 1. 威胁模型（STRIDE 简表）
| 入口 | S 仿冒 | T 篡改 | R 抵赖 | I 泄露 | D 拒绝服务 | E 提权 |
|---|---|---|---|---|---|---|
| HTTP `integrations/http.py`（缺省 127.0.0.1，无令牌） | 浏览器里的任意网页可借用本机身份（CSRF / DNS 重绑定）**[S1]** | 跨站写入伪造记忆 **[S1]** | 无审计日志，写入不记来源 | 重绑定后可读取全部记忆原文、库的绝对路径 **[S1][O1]** | 慢速连接 **[S2]**、listen 积压 5 **[S3]**、深嵌套 **[S9]**、大 limit 放大 **[O3]**、线程数无上限 **[O4]** | 不适用（不执行代码） |
| HTTP（非回环地址 + Bearer 令牌） | 令牌用常数时间比较 ✓；没有 TLS，需要反向代理 | 同上 | 同上 | 令牌持有者可见路径 | 同上 | — |
| MCP stdio `integrations/mcp.py` | 信任边界是父进程，工具参数可能被 LLM 提示注入 | 写入记忆 | — | — | 深嵌套使进程退出 **[S5]**、超长行占内存 **[S11]** | — |
| CLI `integrations/cli.py` | 操作者本人 | `--db` 和 `LINGSHU_NG_DB` 都是操作者输入（不构成越权） | — | 正文出现在 argv **[O9]** | — | 没有调用 shell 或 subprocess |
| Python API（`MemoryEngine`） | 进程内可信 | SQL 全参数化 ✓ | — | — | 四次方正则 **[S6]** | — |
| SQLite 库文件 | — | 同机其他用户可改（若可写） | — | 新建库为 0644 **[S8]** | — | — |
| 导入/导出 JSON（`exchange.py`） | 没有设计者密钥时共享层和治理表被隔离 ✓ | 类型混淆毒化 **[S4]**；`INSERT OR REPLACE` 可覆盖已有节点 **[O2]** | 导入报告只返回给调用方，不落库 | 导出为明文 | 深嵌套 / 顶层类型错时崩溃 **[S4]** | 恶意列名被丢弃 ✓ |
| 插件 entry_points 和源码树发现（`plugins.py`、`_alias.py`） | 任何已安装的包都可注册为插件 **[O6]** | — | — | — | 插件导入失败时被隔离 ✓ | 插件导入即执行代码（设计如此）**[O6]** |
| 模型目录（`LINGSHU_NG_SEM`，缺省 `~/.cache/lingshu_ng/models`）和 embed 缓存 | 同用户可替换模型 **[O7]** | 缓存投毒 **[O7]** | — | 向量缓存 **[O7]** | — | ONNX/tokenizer JSON，未见 pickle ✓ |
| 可选 LLM 抽取（`chain/llm_extract.py`，默认关闭） | — | — | — | 记忆句子发往第三方；配成 http URL 时密钥明文 **[O5]** | — | — |
| 依赖供应链 | — | 版本区间不锁定、没有哈希 **[O11]** | — | — | — | Pillow 下沿版本有已知漏洞 **[S7]** |

## 2. 已修复的发现（每项都是先写失败测试、再修复、再跑全量）
### S1 高：无令牌回环服务可被 DNS 重绑定读取、可被跨站写入
- 位置：`lingshu_ng/integrations/http.py:110-140`（do_GET/do_POST 没有 Host/Origin 校验），`:70-78`（无令牌时直接放行）
- 复现（修复前）：`python sec_audit/probe_http.py`
  - `POST /v1/perceive`，`Content-Type: text/plain`，`Origin: http://evil.example`，请求体 `{"content":"csrf-planted 攻击者写入"}`：返回 200 created。这是浏览器不需要预检的「简单请求」。
  - `GET /v1/status` 带 `Host: attacker.example:8765`：返回 200，内容含库的绝对路径。`POST /v1/recall`（limit=100000）带同样的外来 Host：返回 200，内容是记忆原文。
  - 响应里没有任何 CORS 头。
- 修复：服务只绑回环时，只接受 Host 为回环地址（127.0.0.1、localhost、[::1]）的请求，否则回 403。无令牌时，带非本机 Origin（包括 `null`）的请求一律回 403。`/healthz` 不受影响。
- 修复后：上面三个请求都返回 403；Origin 为 `http://127.0.0.1:port` 或 `http://localhost:3000` 时仍返回 200。
- 测试：`tests_ng/test_security_http.py::test_foreign_host_rejected_on_loopback`、`::test_cross_origin_write_rejected_without_token`

### S2 中：没有读超时，慢速连接无限占住线程
- 位置：`http.py:52`（`_Handler` 没有 timeout），`:81-84`（`rfile.read(n)` 会一直阻塞）
- 复现（修复前）：开 50 个连接，各发 `Content-Length: 100` 后不发正文。12 秒后 50 个仍全部占用，服务线程数为 52。只发半个请求行的连接 3 秒后仍开着。
- 修复：`_Handler.timeout = REQUEST_TIMEOUT = 30.0`。超时后由 http.server 捕获 TimeoutError 并关闭连接。
- 修复后：35 秒时 0 个连接仍开着。测试：`::test_slow_client_is_dropped`
- 剩余风险：每个连接一个线程，并发连接数仍没有上限（见 O4）。

### S3 中：listen 积压为 5，突发并发时连接被内核 RST
- 位置：`http.py:143-151`（`ThreadingHTTPServer` 默认 `request_queue_size = 5`）
- 复现（修复前）：同时发起 16 个连接时有 2 到 4 个 ConnectionResetError，64 个时 39 到 40 个，128 个时 77 个。
- 修复：在 `Server.__init__` 里设实例属性 `request_queue_size = 128`（设在实例上，不扩大公开 API 快照）。
- 修复后：16 和 64 个并发都是 0 错误。测试：`::test_burst_connections_not_reset`

### S4 中：导入时类型混淆会毒化库，畸形备份抛出非 ValueError 异常
- 位置：`lingshu_ng/exchange.py:136-161`（`_insert` 不校验值的类型），`:165-179`（`import_all` 不校验顶层类型）
- 复现（修复前）：`python sec_audit/probe_import.py`
  - 导入节点 `{"id":"n5","content":"imp-str 记忆","importance":"high","layer":"knowledge"}` 成功，之后 `recall('imp-str 记忆')` 抛 `TypeError: can't multiply sequence by non-int of type 'float'`。经 HTTP 时这个错误被映射成 400。
  - `content=12345`、`content=None`、`id=None` 都被导入，绕过了 #331 的入参校验。
  - 行值为对象时抛 `sqlite3.ProgrammingError`；顶层是 list 时抛 `AttributeError`；`{"nodes":5}` 抛 `TypeError`；深嵌套抛 `RecursionError`。
- 修复：按 schema 声明类型逐值校验：TEXT 列必须是 str 或 None；REAL/INTEGER 列必须是数字或能解析成有限数字的字符串；主键不能为 NULL；dict/list 值一律拒收。不合格的行整行拒收，计入新的 `report["rejected_rows"]`。顶层不是对象、某张表不是数组、嵌套过深，统一抛 ValueError。
- 修复后：上述坏行都进 `rejected_rows`，召回正常；共享层和治理表的隔离、恶意列名丢弃、拒收 NaN 照旧。测试：`tests_ng/test_security_import.py`
- 行为变化：`{"nodes":"abc"}` 以前静默导入 0 条，现在抛 ValueError。

### S5 中：MCP 收到深嵌套行时进程退出
- 位置：`lingshu_ng/integrations/mcp.py:119-127`（`_reply` 只捕获 ValueError，RecursionError 会冒出 `run_stdio`）
- 复现（修复前）：`python sec_audit/probe_mcp.py`，依次发 initialize、一行 `"["*100000 + "]"*100000`、ping。进程以 rc=1 退出，ping 没有应答，stderr 有 RecursionError 堆栈。工具参数里的嵌套数组由客户端序列化后同样能触发。
- 修复：RecursionError 转成 -32700 错误，进程继续运行。
- 测试：`tests_ng/test_security_mcp.py::test_deep_nested_line_does_not_kill_server`

### S6 中（潜在，端到端未证可达）：三处四次方回溯正则
- 位置：`lingshu_ng/chain/v17.py:73`（`_SUFJ`）、`lingshu_ng/chain/sav.py:376`、`plugins/lingshu-ng-gen/src/lingshu_ng_gen/multi_seed.py:54`
- 发现方式：regexploit 静态扫描 536 个正则，报出 9 个，其中这 3 个是四次方。
- 复现（直接调用正则，输入为空白 n 个加 "0"）：
  - `v17._SUFJ.match`：n=100/200/400 时耗时 0.05/0.63/8.49 秒
  - sav.py:376 的 `re.sub`：0.046/0.58/8.54 秒
- 经引擎端到端（`enable_chain(True)`，7 种构造）每次都不到 0.02 秒，没能证明可达（实体名和单句长度受约束）。
- 修复：相邻的 `\s*` 改成占有量词 `\s*+`（需 Python 3.11+，与 requires-python 一致）。sav.py 那处提成模块私有常量 `_VALUE_TAIL`。
- 等价性：差分随机测试，每处 2 万例，结果与旧正则逐例相同。修复后 5000 个空白耗时不超过 0.025 秒。
- 测试：`tests_ng/test_security_redos.py`
- 未修的三次方正则：v17._COLDLEAD2、v15._CC、loose.py:516/543/549 和 shorthand 的 re-for 句式，400 个空白时 0.03 到 0.2 秒，见 O10。

### S7 中（可达性低）：插件依赖下沿允许有已知漏洞的 Pillow
- 位置：`plugins/lingshu-ng-{world,nn,gen}/pyproject.toml:14` 写的是 `Pillow>=12.2,<13`
- 证据：`pip-audit -r sec_audit/supply/req_floor.txt` 报 Pillow 12.2.0 有 13 条漏洞：PYSEC-2026-2253 至 2257、3451 至 3454、3493 至 3496，修复版本都是 12.3.0。其中包括：
  - CVE-2026-59199：坐标 API 堆越界写
  - CVE-2026-54059：PCF 字体
  - CVE-2026-54058：McIdas 越界读
- 区间上沿（numpy 2.5.4、onnxruntime 1.31.0、tokenizers 0.23.3、Pillow 12.3.0 及 16 个传递依赖）没有已知漏洞。
- 可达性：本代码只用 `Image.fromarray`、`frombuffer`、`resize`，不解析不可信的图片或字体，实际可达性低。
- 修复：下沿改为 `Pillow>=12.3,<13`，README 同步修改。测试：`tests_ng/test_security_deps.py`

### S8 低：新建库文件为 0644
- 位置：`lingshu_ng/store/db.py:84`（直接调用 `sqlite3.connect`，受 umask 影响）
- 复现（修复前）：库文件和 -wal 文件都是 0644，同机其他用户能读到记忆原文。
- 修复：只在文件不存在时先用 `os.open(O_CREAT|O_EXCL, 0o600)` 创建。-wal/-shm 由 SQLite 按库文件的权限创建。已有文件的权限不改。
- 测试：`tests_ng/test_security_dbperm.py`

### S9 低：HTTP 收到深嵌套 JSON 时无响应断开，堆栈写到 stderr
- 位置：`http.py:132-139`
- 复现（修复前）：1MB 的嵌套括号请求体，连接直接断开，stderr 打出 RecursionError 堆栈（绕过了 logging）。
- 修复后：返回 400。测试：`::test_deep_nested_json_is_400`

### S10 低：Transfer-Encoding 被静默忽略
- 位置：`http.py:80-85`（只看 Content-Length）
- 复现（修复前）：chunked 请求的正文被当成 `{}` 处理，返回 400 缺 query，残留字节当成下一个请求解析。直连时没能走私出写入；反向代理组合下没有测。
- 修复：带 Transfer-Encoding 的请求回 501 并关闭连接。测试：`::test_transfer_encoding_rejected`

### S11 低：MCP 单行没有上限
- 位置：`mcp.py:135`（`for line in stdin`）
- 复现（修复前）：一行 200MB 时子进程 maxrss 为 433MB，仍然照常处理。
- 修复：`MAX_LINE = 8<<20` 字符，用 `readline(limit)` 读取，超限行丢弃余下部分并回 -32600，后续消息继续处理。
- 测试：`::test_oversized_line_rejected_and_stream_continues`

### S12 低：MCP 协议细节
- 位置：`mcp.py:76`、`:124`
- 复现（修复前）：空批量 `[]` 没有应答；`params.name=["a"]` 时回 -32603 并打堆栈。
- 修复：空批量回 -32600；工具名不是字符串时回 -32602。
- 测试：`::test_empty_batch_is_invalid_request`、`::test_unhashable_tool_name_is_invalid_params`

## 3. 未修复或仅记录的发现
- **O1 低/信息**：`service.py:87` 的 `/v1/status` 返回库的绝对路径；`/v1/capabilities` 返回模型目录路径。S1 修复后只有本机或令牌持有者能看到。没改，因为改返回形状可能影响调用方。
- **O2 低**：`exchange.py:159` 导入用 `INSERT OR REPLACE`，没有设计者密钥也能覆盖已有的 knowledge/context 节点。实测导入同 id 后内容变成「被导入覆盖」。这可能是有意设计（用于恢复），建议在报告里加一个覆盖计数，或提供只追加的选项。
- **O3 低**：`inputs.py:25` 的 `MAX_LIMIT=100000`，加上单条正文最多 100k 字符，单次 recall 响应理论上可以极大（实测 203 条为 1.2MB，耗时 0.08 秒）。`tags` 和 `entities` 数组没有数量上限（60000 个标签写入成功）。没修。
- **O4 低**：ThreadingHTTPServer 每个连接一个线程，没有并发上限。S2 的 30 秒超时只缓解了慢速连接。
- **O5 信息**：`chain/llm_extract.py:36,147,167`。设 `LINGSHU_NG_CHAIN_LLM=1`（默认关闭）后，记忆句子会发往 `LINGSHU_NG_CHAIN_LLM_URL`（默认 api.cline.bot）。URL 可以配成 http://，此时 Bearer 密钥明文传输。没有密钥时用占位值 "x"。缓存 `~/.cache/lingshu_ng/llm_cache` 存的是模型输出（含原句片段），使用默认文件权限。COSTLOG 不含原文。
- **O6 信息**：`plugins.py:163,185`、`_alias.py:40`。任何已安装的包，只要在 `lingshu_ng.plugins` 组注册，就会在首次查询或 capabilities() 时被导入执行。源码树发现会扫描 `<lingshu_ng 的上级目录>/plugins/lingshu-ng-*/src`，如果 lingshu_ng 装在 site-packages 里，扫描的就是 site-packages/plugins（往那里写文件需要 site-packages 写权限，等于已失陷）。设 `LINGSHU_NG_SOURCE_PLUGINS=0` 可关闭。
- **O7 信息**：没设 `LINGSHU_NG_SEM` 时，只要 `~/.cache/lingshu_ng/models` 存在就会自动启用里面的模型，同用户可以替换模型来影响排序。加载走 onnxruntime 和 tokenizers JSON。embed 插件的分数缓存和向量缓存（sha1 作键）对目录写者开放，可被投毒。另外 `onnx_embed.py:45` 对 numpy.libs 下的 openblas 做了 `ctypes.CDLL`。
- **O8 信息**：令牌比较区分方案名大小写，`bearer xxx` 返回 401。RFC 7235 规定方案名不区分大小写，这是互操作问题，不影响安全。
- **O9 信息**：CLI `perceive` 的正文在 argv 里，ps 可见。DatabaseOpenError 没被捕获，会打印堆栈（rc=1）。`--db` 的路径穿越、`;rm -rf /`、`file:` URI 都实测过：没有命令执行，也不做 URI 解析，属于操作者自己的输入，不构成越权。
- **O10 低**：三次方正则（见 S6）没有改。
- **O11 信息**：四个插件的依赖都用区间，没有锁定，也没有哈希；构建后端 `setuptools>=77` 没有上限；tokenizers 会传递引入 huggingface-hub、httpx2、hf-xet 等网络库（只在 embed 插件里）。核心 `lingshu-ng` 的 dependencies 为空。

## 4. 测了但没有发现问题的项
- **SQL 注入**：所有动态标识符都来自白名单（schema 常量或 PRAGMA table_info），值全部参数化。没有用 LIKE/FTS/MATCH。hypothesis 跑了 300 例（内容、查询、标签、实体、limit 混合 14 种注入负载）：integrity_check 为 ok，nodes 表还在，14/14 原样回读，没有超过 1 秒的调用，没有 TypeError/ValueError 以外的异常。公开 API 没有元数据过滤参数，`search(layers=)` 的值走 `MemoryLayer.coerce` 枚举。
- **危险调用扫描**：在 lingshu_ng 和 plugins 源码里搜 pickle、marshal、eval(、exec(、subprocess、os.system、popen、`__import__`、yaml.load、torch.load、np.load、shelve、mktemp，零命中（注释里的「pickle 路径」字样除外）。importlib.import_module 只用于固定名字或插件声明的 provides。
- **资源上限**：`MAX_QUERY_CHARS=4096` 截断生效；limit 对 bool、NaN、非整数报 TypeError；超过 MAX_LIMIT 时截断；HTTP 正文超过 1MiB 回 413；负数或非数字的 Content-Length 回 400。
- **日志**：CLI 在 `LINGSHU_NG_LOG=DEBUG` 下，stderr 不含记忆原文，也不含 `LINGSHU_NG_TOKEN`。HTTP 访问日志只在 debug 级别记请求行。500 错误只向客户端返回异常类型名。
- **非回环绑定**：`0.0.0.0`、`::`、空串、`192.168.1.5` 不带令牌时都拒绝启动（包括 CLI，rc=2）。令牌：缺失或错误回 401，正确回 200，`/healthz` 免鉴权。

## 5. 未测
Windows 平台；装了 numpy、onnxruntime、Pillow 后插件运行时的输入面；反向代理与本服务组合下的请求走私；多进程共享同一 WAL 库时的并发；长时间 fuzz（只跑了 hypothesis 300 例，没有覆盖率引导）；完整锁定环境的 pip-audit（只解析了声明区间的上下沿）；SBOM 是手写的，没有用 CycloneDX 官方 schema 校验；chain 各版本经引擎端到端的 ReDoS 可达性没有穷举。

## 6. 供应链产物（工作副本 `sec_audit/supply/`）
- `pip_audit_ranges.json`、`pip_audit_floor.json`：pip-audit 结果
- `gen_sbom.py`、`sbom.cdx.json`：CycloneDX 1.5，25 个组件（核心、4 个插件、4 个直接第三方依赖、16 个传递依赖），每个第三方组件都标注了 declared_range 和「未钉死」

## 7. 修复提交（工作副本 sec-audit，基于基线 8df1974）
1. `ef35332` sec(http)：Host 白名单、Origin 校验、超时、积压、拒绝 Transfer-Encoding、深嵌套回 400
2. `af28262` sec(mcp)
3. `c7741a2` sec(exchange)
4. `c6bd045` sec(http)：request_queue_size 改为实例属性
5. `7c8e936` sec(redos)
6. `f1bef69` sec(store)：0600
7. `f6cbc74` sec(deps)：Pillow>=12.3

在上游仓库应用：`git am --directory=Liyang ALL_FIXES.patch`。已在一个 Liyang 布局的空仓库里验证过能干净应用。
