# 补缺 · Week2：RAG 进阶

> **定位**：本文补 Week2 走读时跳过/未展开的理论点。Week2 代码（`scripts/week2/`）已覆盖：基础 RAG（Chroma + embedding）、混合检索（BM25 + 向量 + RRF）、Cross-Encoder 重排、Provider fallback。这里补的是"会跑 RAG 但没讲透"的 8 个点。
>
> **配套代码**：
> - 第 5 节 RAGAS 理论 → `scripts/week4/ragas_eval.py`（4 指标手写实现）
> - 第 6 节 Agentic RAG 选型表 → `scripts/week4/rubric_checked_rag.py`（Rubric-checked 落地代码）
>
> **本文与 week1 补缺的关系**：week1 补的是 API/Prompt 工程化，本文补的是 RAG 工程化。两者都是"从 demo 到生产"的中间层。

---

## 1. RAG 三大范式演进

Week2 实现的是"Advanced RAG"的雏形，但没讲三大范式的整体脉络。理解演进才能定位自己代码在哪一级。

### 1.1 三代范式对比

| 维度 | Naive RAG（2020） | Advanced RAG（2023） | Modular RAG（2024+） |
|------|------------------|---------------------|---------------------|
| **检索** | 单路向量检索 | 混合检索 + 重排 | 可编排、可迭代检索 |
| **流程** | 线性：查→拼→生成 | 线性 + 前后处理 | 非线性：可路由/循环/反思 |
| **索引** | 一次性建库 | 分块优化 + 元数据 | 多级索引、增量更新 |
| **决策** | 无 | 固定 top_k | 模型决定查不查、查几次 |
| **典型** | 早期 LangChain RetrievalQA | week2 当前代码 | Agentic RAG（见第 6 节） |

### 1.2 week2 在哪一级

week2 `day2_hybrid_rerank.py` 做了：BM25 + 向量 + RRF 融合 + Cross-Encoder 重排。这是**典型 Advanced RAG**。但流程仍是线性的（查询→检索→重排→生成），没有"检索结果不好就重查"的循环--那一步跨到 Modular RAG，正是第 6 节 Agentic RAG 要补的。

### 1.3 为什么不直接上 Modular

Naive → Advanced 的收益最大、最稳（检索质量直接涨）。Advanced → Modular 的收益边际递减，且引入不确定的循环（可能死循环、可能多花 token）。**week2 先把 Advanced 做扎实，week4 再用 Agentic RAG 补"什么时候该跨到 Modular"。**

---

## 2. Embedding 选型深度

Week2 用了某个 embedding 模型建库，但没讲选型逻辑。这节补：维度、模型、中英文、指令模板。

### 2.1 选型的四个维度

| 维度 | 选项 | 取舍 |
|------|------|------|
| **语言** | 中文模型 / 多语言模型 / 英文模型 | 中文场景必须用中文优化模型，英文模型在中文上召回率暴跌 |
| **维度** | 768 / 1024 / 1536 / 3072 | 维度高=表达力强但存储/检索慢；生产常用 1024 |
| **指令** | 带 instruction 前缀 / 不带 | bge 系列区分 query 和 passage，要加前缀 |
| **部署** | 在线 API / 本地 onnx | 数据敏感或离线场景用本地 |

### 2.2 week2 现状（推测）

week2 `get_or_build_vectorstore()` 用 Chroma，embedding 用的是某个 SentenceTransformer 或 API 模型。选型时容易踩的坑：

- **混用 query/passage 前缀**：bge-large-zh 区分 `"为这个句子生成表示以用于检索相关文章："`（query）和 `"为这段 passages 生成表示："`（passage）。建库时用 passage 前缀，查询时用 query 前缀。混了召回率掉 10%+。
- **维度不匹配**：换 embedding 模型必须**重建**向量库，维度变了旧向量无效。week2 的 `COLLECTION_NAME="kb_contracts_delay"` 里存的是旧维度向量，换模型要换 collection 名。

### 2.3 中英文 embedding 模型速查

| 模型 | 维度 | 语言 | 特点 |
|------|------|------|------|
| `BAAI/bge-large-zh-v1.5` | 1024 | 中文 | 开源中文 SOTA 之一，区分 query/passage |
| `BAAI/bge-m3` | 1024 | 多语言 | 同时支持稠密/稀疏/多向量，一个模型三路 |
| `text-embedding-3-small`（OpenAI） | 1536 | 多语言 | 在线 API，中文也不错 |
| 豆包 `doubao-embedding` | 2048 | 中文 | 火山 API，和 week2 Provider 同栈 |

### 2.4 一个常被忽略的点：归一化

向量检索常用余弦相似度。如果 embedding 模型**输出未归一化**，Chroma 算的"距离"和"相似度"关系会乱。bge 系列默认输出已归一化，但自训或部分 API 可能没归一化。生产前检查：`np.linalg.norm(vec)` 是否接近 1。

---

## 3. 分块策略

Week2 `chunk_text(text, chunk_size=500, overlap=100)` 是**固定长度分块**。简单够用，但会切断语义。这节补四种分块策略。

### 3.1 四种策略对比

| 策略 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| **固定长度** | 每 N 字符切，重叠 overlap | 简单、可控 | 切断句子/条款 |
| **递归字符** | 按分隔符优先级切（段落→句→字） | 尽量保完整句 | 仍可能跨条款 |
| **语义分块** | 用 embedding 相邻句相似度，突变处切 | 语义连贯 | 慢、参数敏感 |
| **结构感知** | 按文档结构切（Markdown 标题/合同条款号） | 最贴合业务 | 要解析结构 |

### 3.2 week2 合同文本应该用哪种

week2 的合同数据是**条款式文本**（"第一条…第二条…"）。固定长度 500 字很可能把"第三条 逾期…"切成两半。**正确做法是结构感知分块**：

```python
import re

def chunk_by_clause(text):
    """
    按合同条款号切块。匹配 "第一条" "第二条" 等。
    week2 合同是中文条款式，这比 chunk_text(500,100) 准得多。
    """
    # 匹配 "第X条" 作为条款边界
    parts = re.split(r"(第[一二三四五六七八九十百]+条)", text)
    chunks = []
    # parts 形如 ['', '第一条', '内容...', '第二条', '内容...']
    i = 1
    while i < len(parts):
        clause_no = parts[i].strip()
        clause_text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        chunks.append({
            "text": f"{clause_no} {clause_text}",
            "clause": clause_no,  # 元数据，可进 Chroma metadata
        })
        i += 2
    return chunks
```

### 3.3 分块大小怎么定

经验值：
- **问答场景**：200~500 字/块，太小丢上下文，太大稀释信号。
- **摘要场景**：可以大块（1000+），因为要整段理解。
- **overlap**：块大小的 10%~20%，避免边界信息丢失。

week2 的 500/100 对合同条款偏大，**结构感知分块后单条款通常 100~300 字，更合适**。

### 3.4 与重排的关系

分块质量直接决定重排上限。**分块切错了，再好的 Cross-Encoder 也救不回来**--因为重排是在候选集里选，候选集烂了选不出好的。所以 RAG 调优顺序：**分块 > 检索 > 重排 > prompt**，从前往后调。

---

## 4. 向量库选型：Chroma vs Milvus

Week2 用 Chroma（嵌入式、单文件）。教学够用，生产要换。这节讲为什么、换什么。

### 4.1 两种向量库定位

| 维度 | Chroma | Milvus |
|------|--------|--------|
| **部署** | 嵌入式（进程内）/ 单机 | 独立服务（分布式） |
| **规模** | 百万级向量 | 十亿级 |
| **索引** | HNSW | HNSW / IVF / DiskANN 等多选 |
| **元数据过滤** | 支持 | 支持（更强） |
| **运维** | 无 | 重（etcd + MinIO + Milvus 多组件） |
| **适合** | demo、原型、小项目 | 生产、大规模、高并发 |

### 4.2 什么时候必须换

- **向量数 > 100 万**：Chroma 查询延迟明显上升。
- **多进程/多机访问**：Chroma 嵌入式，多进程写会锁冲突。
- **需要持久化与服务解耦**：Chroma 跟应用进程绑，应用挂了库也下线。
- **需要复杂过滤**：Milvus 的标量字段过滤更强。

week2 数据量（几份合同）离换库很远，**但要知道生产该往哪走**。

### 4.3 其他选项速查

| 向量库 | 一句话定位 |
|--------|----------|
| **Qdrant** | Rust 写的，性能好，单机也强，过滤语法友好 |
| **Weaviate** | 自带混合检索（向量+BM25），省去自己 RRF |
| **pgvector** | PostgreSQL 扩展，业务数据已在 PG 时最省事 |
| **FAISS** | 库不是服务，纯内存，适合研究/批量 |

### 4.4 与 week2 的迁移代价

week2 用 Chroma 的 `collection.add(embeddings=..., documents=..., metadatas=...)` 和 `collection.query(query_embeddings=...)`。迁 Milvus 主要改：
- 连接方式：`MilvusClient(uri=...)` 代替 `chromadb.PersistentClient`
- schema：Milvus 要显式建 collection schema（字段+索引类型）
- 查询：`client.search(collection, data=[query_vec], filter=...)` 

**接口抽象好就能换**：week2 如果把 `get_or_build_vectorstore()` 的返回收敛成统一接口（`add`/`query`/`delete`），换库只改实现。

---

## 5. RAGAS 评估理论（代码见 ragas_eval.py）

Week2 没做评估，只是"问几个问题看看答得对不对"。这节补 RAGAS 的 4 个指标理论，**代码在 `scripts/week4/ragas_eval.py`**。

### 5.1 为什么需要 RAGAS

人工看几个问题判断 RAG 好不好，问题是：
- **主观**：你觉得答得好，别人可能觉得差。
- **不可复现**：换模型/换分块，没法量化对比。
- **覆盖不全**：你测的 5 个问题不代表所有场景。

RAGAS 用 LLM 当裁判（LLM-as-a-Judge），给出 4 个客观分数，**让 RAG 调优可量化**。

### 5.2 RAG 的四个角与四个指标

RAG 一次调用有四个要素：
- **Question (Q)**：用户问题
- **Context (C)**：检索到的文档（可能多段）
- **Answer (A)**：模型生成的回答
- **Ground Truth (G)**：标准答案（人工标注）

四个指标各盯一条边：

```
        Q ──────────────── A
        │ ╲              ╱ │
 context │  ╲ context  ╱   │ answer
 recall  │   ╲       ╱    │ relevancy
        │    ╲     ╱     │
        │     ╲   ╱      │
        ↓      ╲ ╱       ↓
        C ←───────────── G
         context_precision
         (faithfulness 也用 C→A)
```

| 指标 | 盯哪条 | 含义 | 公式直觉 |
|------|--------|------|---------|
| **faithfulness** | C → A | 回答是否**忠于**检索内容（不幻觉） | A 中的陈述能被 C 支持的比例 |
| **answer_relevancy** | Q → A | 回答是否**切题**（不跑题） | A 反推出 Q 的概率，越像越切题 |
| **context_precision** | C vs G | 检索到的文档里，**有用的排前面**吗 | 相关文档在 top-k 的命中率（按位置加权） |
| **context_recall** | G → C | 标准答案的信息**检索到了吗** | G 中的陈述能在 C 找到的比例 |

### 5.3 四个指标的判别逻辑（手写实现的关键）

**faithfulness**：
1. 把 Answer 拆成原子陈述（"逾期 0.5%/日" "累计超 5 天可解约"）。
2. 对每个陈述，让 LLM 判断"能否从 Context 推出"。
3. 分数 = 能推出的陈述数 / 总陈述数。

**answer_relevancy**：
1. 让 LLM 根据 Answer 反推可能的问题（生成 N 个）。
2. 算这些反推问题与原 Question 的余弦相似度。
3. 分数 = 平均相似度。（week4 代码用 LLM 直接打分简化，避免再算 embedding）

**context_precision**：
1. 对检索到的每个 Context 片段，让 LLM 判断"它对答出 Ground Truth 有用吗"（二分）。
2. 按位置加权：排第 1 的有用给满分，排第 k 的有用给 1/k。
3. 公式：`Mean(相关位次加权)` ≈ `∑ (是否相关 @ i / i) / ∑ (1/i)`。

**context_recall**：
1. 把 Ground Truth 拆成原子陈述。
2. 对每个陈述，让 LLM 判断"能否从 Context 找到"。
3. 分数 = 能找到的陈述数 / 总陈述数。

### 5.4 RAGAS 的局限

- **LLM-as-Judge 偏差**：裁判模型可能偏爱自己同族的生成模型。
- **依赖 Ground Truth**：context_recall / context_precision 都要 G，标注成本高。
- **faithfulness 对"正确但 C 里没有"的答错打低分**：如果模型用自身知识答对了但 C 没说，faithfulness 低但答案对--这是 RAGAS 的设计取舍（RAG 就该用 C）。
- **成本**：每个指标都要多次 LLM 调用，评估 100 个问题可能花几块钱。

### 5.5 week2 评估该用什么 ground truth

week2 的合同数据**天然适合做 ground truth**，因为条款有精确数字：
- "深圳逾期 0.5%/日，超 5 工作日可解约" → G 明确
- "广州 1%/日，全检报废" → G 明确
- "东莞 0.3%/日，500 件 95 折" → G 明确

`scripts/week4/ragas_eval.py` 会用这 3~4 个精确 Q&A 对评估 week2 的 RAG，**具体实现见代码**。

---

## 6. Agentic RAG 四模式选型表（Option B 核心）

这是本文的重头。Week2 是线性 Advanced RAG，"检索完就生成"。Agentic RAG 让**模型参与检索决策**--什么时候查、查几次、查够了没。

### 6.1 四模式总览

| 模式 | 别名 | 核心机制 | 什么时候用 | 什么时候别用 |
|------|------|---------|-----------|-------------|
| **① Skills-guided** | 路由式 | 模型先判断问题类型，选对应"技能"（含检索/计算/直接答） | 问题类型清晰、可枚举 | 问题类型模糊、跨类型 |
| **② Rubric-checked** | Evaluator-optimizer | 生成后用 grader 按 rubric 打分，不达标重检索/重生 | 对事实准确性要求高 | 容忍度高、追求低延迟 |
| **③ Todo-driven** | 计划式 | 先拆 Todo，逐项检索+消化，最后汇总 | 多跳问题、要综合多文档 | 单跳简单问题 |
| **④ Retrieve-offload** | Orchestrator-workers | 主 Agent 不检索，派多个子 Agent 并行检索不同源，汇总 | 数据源多、可并行 | 单一数据源 |

### 6.2 选型决策树

```
你的问题是不是单跳？（一个检索就能答）
├─ 是 → 线性 RAG（week2 够用，别上 Agentic）
└─ 否 → 问题类型能不能枚举？
    ├─ 能 → ① Skills-guided（路由）
    └─ 不能 → 对事实准确率要求多高？
        ├─ 很高（合规/法律/医疗）→ ② Rubric-checked  ✅ week2 合同场景
        └─ 一般 → 要综合几个文档？
            ├─ 多个 → ③ Todo-driven（多跳）
            └─ 单个但数据源多 → ④ Retrieve-offload
```

### 6.3 四模式详解

#### ① Skills-guided（路由式）

模型第一跳不检索，而是**分类**：这问题该走哪条"技能管道"。

```
用户问："深圳逾期 8 天赔多少？"
→ 模型分类：这是"赔付计算"类，需要 [检索条款 + 计算]
→ 路由到 calc_overdue 技能：先 search_contract，再算 0.5%×8×200000=8000
```

- **实现**：week3 的 `analyze_intent` 节点已经是雏形（意图分析）。
- **适合**：合同助手这种"问题类型固定（查条款/算赔付/查库存）"的场景。
- **week2 可以加**：在 `retrieve_hybrid` 前加一层意图分类，"查条款"走合同库、"查历史"走历史记录库。

#### ② Rubric-checked（Evaluator-optimizer）⭐ week2 合同场景首选

生成答案后，**用另一个 LLM（grader）按评分细则（rubric）检查**，不达标就重做。

```
Answer: "深圳逾期 8 天赔付约 8000 元。"
Grader 检查 rubric:
  [1] 是否说明日费率？ ✅ 0.5%/日
  [2] 是否给出计算过程？ ❌ 没写 0.5%×8×200000
  [3] 是否提及解约权？ ❌ 漏了"超 5 工作日可解约"
→ 不达标，反馈给生成器重生
Answer(重): "逾期按 0.5%/日，8 天共 4%，200000×4%=8000 元；累计超 5 工作日客户可解约。"
Grader: ✅ 全过
```

- **实现**：`scripts/week4/rubric_checked_rag.py` 完整实现。
- **为什么 week2 该用**：合同条款涉及钱和解约权，**漏一条就出事**。Rubric 把"不能漏"变成可检查的规则。
- **代价**：每个问题多 1~3 次 LLM 调用，延迟和成本翻倍。

#### ③ Todo-driven（计划式）

模型先把问题拆成 Todo 列表，逐项检索消化。

```
用户问："对比深圳和广州的逾期条款差异。"
Todo:
  [1] 查深圳逾期条款 → 检索 → 0.5%/日，5 工作日解约
  [2] 查广州逾期条款 → 检索 → 1%/日，3 日解约
  [3] 对比 → 生成差异
```

- **实现**：deepagents 已了解，本质是 Todo 列表 + 逐项执行。
- **适合**：多跳、需要综合对比的问题。
- **week2 用不上**：单文档查询居多，拆 Todo 反而啰嗦。

#### ④ Retrieve-offload（Orchestrator-workers）

主 Agent 不直接检索，派多个子 Agent 并行查不同源。

```
用户问："查这个客户的合同 + 历史延期记录 + 当前库存。"
主 Agent:
  ├─ 子 Agent A → 查合同库
  ├─ 子 Agent B → 查历史记录库
  └─ 子 Agent C → 查库存系统
  ← 汇总三个结果生成答案
```

- **实现**：LangGraph 的多节点并行，或 deepagents 的 subagents。
- **适合**：数据源真的多且独立。
- **week2 用不上**：只有合同库一个源，并行无意义。

### 6.4 为什么 week2 只落地 ②

| 模式 | week2 合同场景适配 | 决策 |
|------|-------------------|------|
| ① Skills-guided | 问题类型可枚举，但 week3 已有意图分析雏形，重复 | 跳过（week3 覆盖） |
| ② Rubric-checked | **事实准确性刚需，漏条款出事** | ✅ 落地 |
| ③ Todo-driven | 单文档为主，多跳少 | 跳过 |
| ④ Retrieve-offload | 单数据源 | 跳过 |

**结论**：week2 落地 Rubric-checked 一个就够（`scripts/week4/rubric_checked_rag.py`）。其他三个理解原理、知道选型即可，不为教学硬造不适配的代码。

---

## 7. Filesystem Backend + Subagents（深文件场景）

这是 ④ Retrieve-offload 的一种特例：当"数据源"是**大量文件**时，怎么做。

### 7.1 问题

假设 RAG 库不是 3 份合同，而是 3000 份文档（产品手册、工时记录、历史订单）。全塞一个 Chroma 库：
- 检索信号被稀释，top-k 里混进无关文档。
- 分块数爆炸，建库慢。
- 单次检索拿不全跨文档的信息。

### 7.2 Filesystem Backend 思路

不把所有文档灌进一个向量库，而是：
1. **文件系统即后端**：文档保留在文件系统，按目录/文件名建**一级索引**（轻量，只存文件名+摘要）。
2. **先选文件，再检索**：模型先根据问题判断"该读哪几个文件"，再只在这几个文件里做 RAG。
3. **Subagents 并行**：每个被选中的文件派一个子 Agent 去深读，主 Agent 汇总。

### 7.3 流程

```
用户问："深圳合同和广州合同的质检条款差异？"
一级路由（选文件）：
  → 选中 contracts/深圳精密五金.txt, contracts/广州航天精工.txt
Subagent A 读深圳文件 → 抽出"3 工作日返工"
Subagent B 读广州文件 → 抽出"全检报废不返工"
主 Agent 汇总 → 生成差异对比
```

### 7.4 什么时候值得

- **文档量 > 几百** 且 **问题集中在少数文档**：选文件比全库检索准。
- **文档之间结构差异大**：每个文件单独建子库/单独 prompt。
- **week2 不值得**：3 份合同，全库检索又快又准，加这层纯属过度设计。

### 7.5 与 LangGraph 的关系

LangGraph 的 `Send` API 可以动态派发子节点：主节点决定读哪些文件后，用 `Send` 给每个文件派一个 reader 节点，并行执行后汇总。week4 多 Agent 阶段可以练这个，week2 不做。

---

## 8. 幻觉 Mitigation（缓解）

RAG 的核心承诺是"减少幻觉"，但 RAG **不能消灭**幻觉，只能缓解。这节补缓解手段。

### 8.1 RAG 里幻觉的三种来源

| 来源 | 表现 | 缓解 |
|------|------|------|
| **检索失败** | C 里没有答案，模型用自身知识硬答 | 检索质量（第 3/4 节）+ "答不出就说答不出" |
| **生成漂移** | C 有答案，模型生成时跑偏 | Rubric-checked（第 6 节②）+ 低温 |
| **指令覆盖** | 用户/检索内容里有指令劫持模型 | Prompt Injection 防护（week1 补缺第 7 节） |

### 8.2 五层缓解

**第 1 层：检索端**
- 提高召回（混合检索、重排）--week2 已做。
- 设相似度阈值：检索分太低就判定"没找到"，不让模型硬答。

```python
def retrieve_with_threshold(collection, query, top_k=3, min_score=0.3):
    hits = retrieve(collection, query, top_k=top_k)
    good = [h for h in hits if 1 - h["distance"] >= min_score]  # Chroma 距离转相似度
    return good  # 可能为空
```

**第 2 层：Prompt 端**
- 明确"只根据 C 回答，C 没有就说不知道"。
- week2 `RAG_SYSTEM_PROMPT` 已有这层，但可以更强：加"禁止使用训练知识补充"。

**第 3 层：生成端**
- `temperature` 调低（0.1~0.3），减少创造性漂移。
- 限制 `max_tokens`，避免模型自由发挥编故事。

**第 4 层：后验端**
- Rubric-checked（第 6 节②）：grader 检查答案是否每句都有 C 支撑。**这是对幻觉最硬的拦截。**
- faithfulness 指标（第 5 节）：离线评估幻觉率，量化追踪。

**第 5 层：产品端**
- 答案附**引用**（"据深圳合同第三条"），让用户能核验。
- 低置信度时降级输出："未在合同中找到明确条款，建议人工确认。"

### 8.3 week2 现状与补强

| 层 | week2 现状 | 补强建议 |
|----|-----------|---------|
| 检索端 | 混合+重排 ✅ | 加相似度阈值 |
| Prompt 端 | "只根据片段回答" ✅ | 加"禁止用训练知识" |
| 生成端 | temperature=0.3 ✅ | 可降到 0.1 |
| 后验端 | ❌ 无 | week4 的 rubric_checked_rag.py 补 |
| 产品端 | ❌ 无引用 | 返回时带 source 字段（week2 已有 source，但没展示给用户） |

**week4 的 rubric_checked_rag.py 同时补了第 4 层后验**，这是对 week2 幻觉问题最直接的工程补强。

---

## 小结：week2 补缺的 8 个点怎么串起来

```
三大范式 ──── 定位 week2 在 Advanced RAG ──── 指向 Modular(Agentic)
                                                    │
Embedding/分块/向量库 ──── 检索质量三件套（Advanced 内部优化）
                                                    │
RAGAS ──── 量化评估 ──── 代码: ragas_eval.py
                                                    │
Agentic RAG 4模式 ──── 选型 ──── week2 选 ② Rubric ──── 代码: rubric_checked_rag.py
                                                    │
Filesystem+Subagents ──── ④ 的特例（深文件，week2 不做） 
                                                    │
幻觉 Mitigation ──── 5层缓解 ──── Rubric 是第4层 ──── 与 ragas_eval 的 faithfulness 闭环
```

**核心结论**：week2 的 Advanced RAG 已扎实，补缺不是推翻重做，而是：
1. **可量化**（RAGAS）--知道现在多好。
2. **可提升准确性**（Rubric-checked）--对合同场景刚需。
3. **知道演进方向**（Agentic 4 模式、Modular 范式）--week4 多 Agent 时有全局视野。

两份配套代码（`ragas_eval.py`、`rubric_checked_rag.py`）分别落地"量化"和"提升"。
