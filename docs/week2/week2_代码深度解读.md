# Week2 代码深度解读：从 Pipeline 到 Agent 的跃迁

> **写于 2026-07-20**。帮你快速进入 Week2 代码的核心，不只是"跑通了什么"，而是"每一层在解决什么问题、为什么这样设计、深度在哪"。
>
> **阅读方式**：按顺序读，每节的"代码入口 → 核心概念 → 深度点 → 对照阅读"四步走。

---

## 0. 总览：四天代码的关系图

```
Day1: RAG 基础层 (day1_rag_basics.py)
  │  文档分块 → Chroma 向量库 → 纯向量检索 → LLM 生成
  │  问题：中文 Embedding 弱，top1 常召回错误文档
  │
  ├──→ Day2: 混合检索 + 重排序 (day2_hybrid_rerank.py)
  │      复用 Day1 向量库
  │      + BM25 关键词检索（jieba 分词）
  │      + RRF 两路排名融合
  │      + Cross-Encoder 重排序（BAAI/bge-reranker-base）
  │      解决：中文召回弱的问题
  │
  ├──→ Day4: Agentic RAG (day4_agentic_rag.py)
  │      复用 Day1 向量库 + Day2 混合检索
  │      + 3 个工具（plan / search / submit）
  │      + Todo-driven Agent 循环
  │      跃迁：pipeline 固定检索 → Agent 自主决策检索
  │
  └──→ Day5: 三合一调度 Agent (week2_agentic_rag_agent.py)
         复用 Day1 + Day2 + Week1 query_orders
         + 5 个工具（plan / query_orders / query_customer / search_kb / submit）
         集成：结构化查询 + 语义检索 + Agent 编排，Week1-2 总集成
```

**关键认知**：这不是四个独立脚本，是一条能力递增的链。每往上一层，复用了下一层的全部能力。

---

## 1. Day1 — RAG 基础层（363 行）

### 代码入口

`scripts/week2/day1_rag_basics.py`

### 三层结构

| 层 | 函数 | 做了什么 |
|----|------|---------|
| 知识库层 | `load_documents()` + `chunk_text()` | 加载 4 个 txt → 500 字滑动窗口分块 |
| 向量库层 | `get_or_build_vectorstore()` + `retrieve()` | Chroma 持久化 + top-k 余弦检索 |
| 生成层 | `rag_answer()` | 检索片段拼 context → LLM 基于片段回答 |

### 需要理解的核心概念

1. **Embedding 的本质**：文本 → 高维向量（768 维浮点数数组）。"加急订单"和"紧急订单"向量距离近，"加急订单"和"合同编号PO-2026"向量距离远。这就是语义检索的数学基础。

2. **分块策略是 RAG 的第一道坎**：500 字 + 100 重叠是教学简化版。生产环境用 `RecursiveCharacterTextSplitter`（段落→句子→字符层级切分）或 `SemanticChunker`（按 embedding 相似度断句），Recall 从 0.67 跳到 0.91。

3. **Chroma 的选择理由**：嵌入式向量库，零配置，持久化到本地文件。对比：Milvus 要 Docker、Qdrant 要服务端、FAISS 无持久化。教学场景 Chroma 最优。

### 深度点（生产环境才需要关心的）

- **Embedding 模型选型**：当前用 Chroma 默认的 `all-MiniLM-L6-v2`（英文为主，中文弱）。代码注释里写了升级路径：`bge-small-zh-v1.5`（95MB，中文专用）→ `bge-m3`（多语言 1024 维）→ `qwen3-embedding`（最新）。
- **Provider 主备架构**：`call_with_fallback()` 按 `PROVIDERS` 列表顺序逐个试，这是 Week1 的遗产，Week2 全部复用。豆包主 → DeepSeek 备 → Kimi 禁用。
- **`trust_env=False`**：`httpx.Client(trust_env=False)` 绕系统代理，避免 cc-switch 退出后走死代理 SSL EOF。这是踩过的坑。

### 对照阅读

先看 `demo()` 的三个部分输出格式，再看对应函数的实现。三部分分别验证：向量库能否复用、纯检索召回什么、端到端 RAG 能否基于片段回答。

---

## 2. Day2 — 混合检索 + 重排序（374 行）

### 代码入口

`scripts/week2/day2_hybrid_rerank.py`

### 四层架构

```
用户 query
    │
    ├──→ 向量检索（复用 Day1 retrieve，取 top-10）
    │
    ├──→ BM25 检索（jieba 分词 + rank_bm25，取 top-10）
    │
    ├──→ RRF 融合（两路排名按 1/(k+rank) 合并，取 top-10）
    │
    └──→ Cross-Encoder 重排（BAAI/bge-reranker-base 精排，取 top-3）
```

### 为什么 Day1 不够

Day1 的 Chroma 默认 MiniLM 对中文支持弱。实测：问"广州航天精工合同特殊条款"，Day1 top1 常返回"历史延期记录"而非目标合同。因为 MiniLM 对中文语义的向量表示不够精准。

### 每一层解决什么问题

| 层 | 解决的问题 | 擅长的 |
|----|-----------|--------|
| 向量检索 | 语义相似 | "延期赔付" ≈ "违约金条款" |
| BM25 | 关键词精确 | "广州航天" 必须字面命中 |
| RRF 融合 | 两路各说各的，排名尺度不同 | 不关心分数绝对值，只看排名位置 |
| Cross-Encoder 重排 | RRF 融合后还不够准 | query+doc 拼接推理，比双塔更准 |

### 深度点

1. **BM25 不是简单的关键词匹配**：`IDF × TF / (TF + k × (1-b + b × doc_len/avg_len))`。IDF 让稀有词权重更高（"航天"比"订单"更有区分度），TF 饱和曲线让词频增长不线性推高分数。

2. **RRF 为什么不用线性加权**：向量 distance 范围 0~2，BM25 score 范围 0~N（N 无上界），尺度不同无法直接加权。RRF 只看排名位置，`1/(60+rank)` 统一尺度。

3. **Cross-Encoder vs 双塔的根本区别**：
   - 双塔（Day1）：query 和 doc 各自独立编码成向量 → 比余弦距离。快（100ms/千篇），但 query 和 doc 之间没有交互。
   - Cross-Encoder：query+doc 拼接后一起过 Transformer → 输出 0-1 相关分。慢（100ms/对），但能看到 query 和 doc 的 token 级交互。
   - 生产流程：双塔召回 top-20（快）→ Cross-Encoder 重排取 top-3（准）。

4. **Reranker 加载的离线优先策略**（`load_reranker()`）：这是生产级细节——
   ```python
   # 先尝试离线加载（已缓存则秒载）
   os.environ["HF_HUB_OFFLINE"] = "1"
   # huggingface_hub 把 HF_HUB_OFFLINE 固化到 constants，
   # 运行时设 env 无效，必须 patch constants
   import huggingface_hub.constants as _hf_const
   _hf_const.HF_HUB_OFFLINE = True
   # 离线失败才走 Clash 代理 3450 下载
   ```
   这个坑在 memory 里有记录 [[HF 离线加载陷阱]]。

### 对照阅读

重点看 `demo()` 的"第二部分：检索对比"。它同一 query 跑 Day1 纯向量和 Day2 混合+重排，并判定 top1 是否改进。这是理解 Day2 价值的直观入口。

---

## 3. Day4 — Agentic RAG（543 行，本周核心跃迁）

### 代码入口

`scripts/week2/day4_agentic_rag.py`

### 跃迁的本质

```
Day1（传统 RAG）：  query → 固定检索 → 固定生成
                   路径是程序员写死的

Day4（Agentic RAG）：question → Agent 规划 → Agent 逐项检索 → Agent 判断够了 → 综合回答
                   策略是 Agent 自主决策的
```

### 三个工具的职责

| 工具 | 谁调 | 做什么 |
|------|------|--------|
| `plan_investigation` | Agent（第 1 步） | 把问题拆成 2-4 个搜索查询 |
| `search_knowledge_base` | Agent（逐项调） | 调 Day2 混合检索，返回完整文本 |
| `submit_final_answer` | Agent（最后） | 综合所有结果，引用来源 |

### Agent 循环（核心逻辑在 `run_agentic_rag()`）

```
Turn 1: LLM → tool_calls: [plan_investigation("拆成3个事项")]
        执行 → 返回规划结果 → 追加到 messages

Turn 2: LLM → tool_calls: [search_knowledge_base("事项1"),
                           search_knowledge_base("事项2"),
                           search_knowledge_base("事项3")]
        执行 → 返回检索结果 → 追加到 messages

Turn 3: LLM → tool_calls: [submit_final_answer("综合回答")]
        检测到 submit → 终止循环
```

这个循环和 Week1 Day2 的 ReAct 循环**完全同构**——区别只在工具从"查订单"变成了"规划+检索+提交"。

### 深度点

1. **工具定义是 OpenAI Function Calling 格式**：`TOOLS` 列表里的每个工具是一个 JSON Schema，`type: "function"`, `function: {name, description, parameters}`。这和 Week1 Day2 的 `query_orders` 工具定义格式一致。

2. **检索结果回传完整文本**（不是预览）：第一版只回传 120 字预览，模型在"盲搜"——不知道 chunk 里有什么，只能猜。修复后回传完整文本，模型能引用条款原文和金额。这是 Agent 和传统 RAG 的关键差异：Agent 需要看到完整信息才能做决策。

3. **Agent 需要硬约束**：System Prompt 写"规划 N 项，最多检索 N+1 次"。第一版没这个，Agent 从"延期赔付"查到"表面处理阳极氧化"，18 次还不停。因为知识库小（10 条向量），每次检索返回的基本是同一批 chunk，Agent 发现"没看到完整条款"就不断换词重试。硬约束让 Agent 知道"够了"。

4. **`search_knowledge_base` 优先用 Day2 混合检索**：`execute_tool` 里判断 `_RERANKER is not None`，已初始化就用 `retrieve_hybrid`（Day2），未初始化回退 `retrieve`（Day1）。这是优雅的渐进增强设计。

5. **和 Week1 Day2 的对比**：
   - Week1：`query_orders` 查结构化 CSV（字段固定、SQL 可查）
   - Day4：`search_knowledge_base` 查非结构化知识库（语义检索、内容不可预测）
   - Agent 循环逻辑完全一致，但检索的数据源从结构化跃迁到了语义化

### 对照阅读

先读 `run_agentic_rag()` 的 while 循环（249 行起），理解 Agent 循环的终止条件（`submit_final_answer` 或 `MAX_TURNS`）。再读 `execute_tool()` 看三个工具的执行逻辑。最后看 `demo()` 的 3 个场景，验证 Agent 是否：规划正确 → 检索到位 → 回答有源。

---

## 4. Day5 — 三合一调度 Agent（604 行，Week1-2 总集成）

### 代码入口

`scripts/week2/week2_agentic_rag_agent.py`

### 集成了什么

```
Week1 Day2 query_orders（查订单结构化数据）
    +
Day2 混合检索（查合同/案例非结构化知识库）
    +
Day4 Todo-driven Agent 循环骨架
    +
新增 query_customer（查客户等级/信用/延期率）
    =
5 工具调度 Agent
```

### 五个工具

| 工具 | 数据源 | 来源 |
|------|--------|------|
| `plan_investigation` | — | Day4 |
| `query_orders` | 订单 CSV（结构化） | Week1 Day2 |
| `query_customer` | 客户 CSV（结构化） | 新增 |
| `search_knowledge_base` | 合同 txt + 延期记录（非结构化） | Day2 |
| `submit_final_answer` | — | Day4 |

### 37 行新增的 `query_customer`

```python
def query_customer(customer=None, customer_id=None):
    customers = _load_customers()  # 从 CSV 加载 15 条客户
    # 按客户名模糊匹配 或 id 精确查询
    # 返回 {total, customers: [{id, 客户名, 等级, 信用分, 历史延期率}]}
```

设计原则和 Week1 `query_orders` 一致：简单函数 + 参数过滤 + 返回字典。

### Agent System Prompt 的演进

Day4 的 Prompt 只有 3 个工具（plan/search/submit），Day5 增加到 5 个，加了"工具选用指引"：

```
问"有哪些订单/某客户订单/快超期订单" → query_orders
问"客户等级/信用/延期率" → query_customer
问"合同条款/赔付规定/质检要求/加急规定/历史案例" → search_knowledge_base
复合问题 → 拆成多项，分别用不同工具
```

这是 Prompt Engineering 的实践：告诉模型"什么场景用什么工具"比让它自己猜更可靠。

### 深度点

1. **参数白名单**：`execute_tool` 里 `valid_keys = {"customer", "status", ...}` 过滤，防止模型传多余字段导致 `query_orders(**args)` 报错。这是防御性设计。

2. **双路检索切换**：同 Day4，`_RERANKER is not None` 判断用 Day2 混合检索还是 Day1 纯向量。Day2 未初始化（如 reranker 下载失败）时自动降级，不阻塞 Agent 循环。

3. **知识库数据的业务设计**：`customers.csv`（15 条客户，A/B/C 三级，信用分 65-92，延期率 4%-28%）+ `contracts/`（3 份合同特殊条款）+ `历史延期记录.txt`（5 个真实案例，含订单号、金额、复盘措施）。数据量不大但结构完整，能让 Agent 做出有意义的综合判断。

4. **MAX_TURNS 从 8 提升到 10**：Day4 只有 3 个工具，Day5 有 5 个，规划更长、工具调用更多，需要更多轮数。

### 对照阅读

先看 `demo()` 的 3 个场景，理解每个场景验证什么（深圳赔付 = 三工具协同，航天质检 = 客户+合同，超期订单 = 订单+合同风险）。然后看 `run_agent()` 的循环和 `execute_tool()` 的 5 路分支。最后看 `AGENT_SYSTEM_PROMPT` 的"工具选用指引"和 Day4 的差异。

---

## 5. 贯穿四天的设计模式

### 5.1 Provider 主备架构（全部复用 Week1）

```python
PROVIDERS = [
    火山豆包(coding),  # 主用
    DeepSeek,          # 备用1
    Kimi(coding),      # 备用2（会员过期禁用）
]
```

每个文件的 `_chat_with_tools()` / `call_with_fallback()` 都按这个顺序逐个试。这是 Week1 Day1 的遗产，Week2 没改一行。

### 5.2 数据层的渐进式设计

```
Day1: 合同 txt × 3 + 延期记录 txt × 1 → Chroma 向量库
Day2: 复用 Day1 向量库 → + BM25 索引 → + Reranker
Day4: 复用 Day2 检索 → Agent 层包装
Day5: + customers.csv（结构化）+ orders CSV（Week1 遗产）
```

向量库是只读的（建一次，后续复用），BM25 索引和 Reranker 是启动时动态构建的。

### 5.3 Agent 循环的同构性

Week1 Day2、Day4、Day5 三个 Agent 循环的核心骨架一模一样：

```python
messages = [system_prompt, user_question]
for turn in range(MAX_TURNS):
    resp = llm.chat(messages, tools=TOOLS)
    if resp has tool_calls:
        for each tool_call:
            result = execute_tool(name, args)
            messages.append(tool_result)
        if submit detected: break
    else:
        messages.append(prompt_to_follow_workflow)  # 提醒按流程走
```

区别只在：工具列表不同、终止条件不同（Day4/5 用 `submit_final_answer`，Week1 用"模型不再返回 tool_calls"）。

---

## 6. 阅读顺序建议（按理解深度递增）

| 顺序 | 文件 | 时间 | 重点理解 |
|------|------|------|---------|
| 1 | `day1_rag_basics.py` | 15min | RAG 三步：分块→向量化→检索生成 |
| 2 | `docs/week2/day1_guide.md` | 10min | Embedding 选型、分块策略 |
| 3 | `day2_hybrid_rerank.py` | 20min | 为什么 Day1 不够、BM25/RRF/Reranker 各补什么 |
| 4 | `day4_agentic_rag.py` | 25min | Pipeline → Agent 跃迁、Todo-driven 循环 |
| 5 | `docs/week2/day4_guide.md` | 10min | 4 个踩坑记录很重要 |
| 6 | `week2_agentic_rag_agent.py` | 20min | 5 工具协同、Week1-2 总集成 |
| 7 | `docs/阅读导航_week1_week2.md` | 15min | 理论对照（LangChain/Anthropic 原文定位） |

**不要跳着读**。Day1→Day2→Day4→Day5 是能力递增链，跳了 Day2 就看不懂 Day4 为什么 `search_knowledge_base` 用混合检索；跳了 Day4 就看不懂 Day5 的 Agent 循环骨架从哪来的。

---

## 7. 如果你想进一步深入

以下每个方向都是 Week2 代码的"下一步"：

- **分块策略升级**：当前固定 500 字 → 换 `RecursiveCharacterTextSplitter` + `SemanticChunker`（代码注释里有升级路径）
- **Embedding 升级**：当前 MiniLM → 换 `bge-small-zh-v1.5`，对比中英文 query 的 recall 改善
- **RAG 评估**：引入 RAGAS 框架，量化 faithfulness / answer_relevancy / context_precision / context_recall
- **Filesystem Backend**：Day4/5 检索结果直接塞 messages（context 膨胀）→ 改写成文件系统 offload（Week3 Deep Agents 的核心机制）
- **并行 Subagent**：Day5 的工具是串行调用的 → 改为 subagent 并行查订单+查客户+查合同（Anthropic orchestrator-workers 模式）
