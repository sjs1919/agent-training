# 第二周 Day 4 学习指南 - Agentic RAG 进阶层（Todo-driven 模式）

> **日期**：2026-07-16（周四）
> **知识块**：② Agent 核心机制 + ⑤ RAG 检索增强
> **产出**：`scripts/week2/day4_agentic_rag.py`
> **一句话**：从"pipeline 固定检索"跃迁到"Agent 自主决定检索"。

## 今日目标

把检索决策权从代码交给 Agent。不再是"每次必检索、路径写死"，而是 Agent 自己判断：**要不要检索、检索什么、检索几次、结果够不够、什么时候提交答案**。

落地 **Todo-driven investigation** 模式——Agent 收到问题后，先规划调查清单，再逐项检索，最后综合回答。

## 和 Day1 的本质区别

| 维度 | Day1 传统 RAG | Day4 Agentic RAG |
|------|--------------|------------------|
| 谁决定检索 | 代码 pipeline（固定） | **Agent 自主决策** |
| 检索时机 | 每次必检索 | Agent 判断是否需要检索 |
| 检索几次 | 固定 1 次 | Agent 决定（0 到 N+1 次） |
| 检索结果去哪 | 直接塞 LLM context | Agent 逐轮消化，判断够不够 |
| 终止条件 | 检索完就生成 | Agent 判断"够了"才调用 submit_final_answer |
| Agent 角色 | 无（纯流水线） | **编排器**：规划→检索→判断→提交 |

一句话：Day1 是"检索增强的 LLM"，Day4 是"自主检索的 Agent"。

## 依赖

无需新依赖。复用 Day1 的 `chromadb` + week1 的 `openai` + `httpx`。

```bash
# 已有则跳过
pip install chromadb openai httpx python-dotenv
```

## 跑起来

```bash
cd projects/agent-training
python scripts/week2/day4_agentic_rag.py
```

Day1 的向量库已建好（`scripts/week2/data/chroma_db/`），Day4 直接复用，秒级启动。

## 架构：Todo-driven Agentic RAG

```
用户问题
    │
    ▼
┌─────────────────────────────────┐
│         Agent（编排器）          │
│                                 │
│  ① plan_investigation          │
│     拆问题 → 待查事项列表        │
│                                 │
│  ② search_knowledge_base × N   │
│     逐项检索知识库               │
│     每项最多重试 1 次            │
│                                 │
│  ③ submit_final_answer         │
│     综合所有结果 → 最终答案      │
│                                 │
└──────────┬──────────────────────┘
           │ 检索
           ▼
    ┌──────────────┐
    │  Chroma 向量库 │  ← 复用 Day1
    │  合同 + 延期记录│
    └──────────────┘
```

**Agent 循环**（与 week1 day2 的 ReAct 循环同构）：

```
Turn 1: LLM 返回 plan_investigation("拆成 3 个事项")
Turn 2: LLM 返回 search_knowledge_base("事项1") + search_knowledge_base("事项2") + ...
Turn 3: LLM 返回 submit_final_answer("综合回答")
```

## 三个工具

| 工具 | 作用 | 谁调用 |
|------|------|--------|
| `plan_investigation` | 把用户问题拆成 2-4 个待查事项，每项是一个自然语言搜索查询 | Agent（第 1 步） |
| `search_knowledge_base` | 搜索向量库，返回 top-k 相关片段及来源 | Agent（逐项调用） |
| `submit_final_answer` | 提交综合答案，列出引用来源 | Agent（最后一步） |

对比 Day1：Day1 只有一个隐式的"检索"动作，没有规划、没有多次检索、没有显式提交。Day4 把检索拆成了三个可组合的工具，Agent 自己编排。

## 为什么是 Todo-driven

LangChain Deep Agents 定义了 4 种 Agentic RAG 模式。本周落地 Todo-driven，理由：

1. **和 week1 的 Function Calling 自然衔接**——Agent 循环逻辑完全一致，只是工具从"查订单"变成了"规划+检索"
2. **概念清晰**——规划→执行→提交，三步走，和人类的调查流程一致
3. **适合小规模知识库**——我们的合同+延期记录只有几十 KB，不需要 Filesystem backend（模式④的场景）

另外 3 种模式（Skills-guided、Rubric-checked、Retrieve-offload）已在 day3 阅读中了解，week3/4 做多 Agent 时再深入。

## 代码结构

`day4_agentic_rag.py` 四层：

```
1. 复用层：from day1_rag_basics import PROVIDERS, get_or_build_vectorstore, retrieve
2. 工具定义层：TOOLS 列表（3 个 Function Calling 工具定义）+ execute_tool() 执行器
3. Agent 循环层：run_agentic_rag() —— 逐轮调 LLM → 执行工具 → 回传结果 → 直到 submit
4. 演示层：demo() —— 3 个场景（深圳赔付、航天质检、加急风险）
```

## 三个演示场景

| 场景 | 问题 | 验证点 |
|------|------|--------|
| 1 | 深圳精密五金的订单延期了，要赔多少钱？ | Agent 能否：规划→查合同→查案例→综合 |
| 2 | 广州航天精工有什么特殊要求？质检不合格怎么办？ | Agent 能否：规划→查特殊条款→查质检案例→综合 |
| 3 | 加急订单有什么风险？有加急没逾期的案例吗？ | Agent 能否：规划→查加急规定→查历史→总结风险 |

预期每个场景 3 轮完成：规划(1) + 检索(1) + 提交(1)。

## 预期输出（关键节点）

```
🚀 第二周 Day 4：Agentic RAG 进阶层（Todo-driven 模式）

场景 1：深圳精密五金的订单延期了，要赔多少钱？

🔄 Turn 1（已执行 0 次检索）...
  🔧 调用工具: plan_investigation(question='...', items=3项)
      1. 深圳精密五金合同的延期赔付条款和违约金规定
      2. 深圳精密五金历史延期案例和实际赔付金额
      3. 深圳精密五金订单的交付时间和金额基数

🔄 Turn 2（已执行 0 次检索）...
  🔧 调用工具: search_knowledge_base(query='深圳精密五金合同延期赔付条款...')
  🔧 调用工具: search_knowledge_base(query='深圳精密五金历史延期案例...')
  🔧 调用工具: search_knowledge_base(query='深圳精密五金订单交付时间...')

🔄 Turn 3（已执行 3 次检索）...
  🔧 调用工具: submit_final_answer(answer='...')

📊 执行摘要
  Provider: 火山豆包(coding)
  规划事项: 3 项
  检索次数: 3
  总轮数: 3
  来源: 深圳精密五金_合同特殊条款.txt, 历史延期记录.txt

💬 最终答案：
## 深圳精密五金延期赔付说明
### 一、合同规定（合同编号：SZ-JM-2025-014，第三条）
日赔付比例：0.5%/日，累计超 5 个工作日客户可解约...
```

## 踩坑与修复

### 坑1：Agent 无限检索（18 次还不停）

**现象**：第一版跑场景1，Agent 规划了 3 项，但检索了 18 次——从"延期赔付"查到"表面处理阳极氧化"，越查越远，直到 MAX_TURNS 耗尽。

**根因**：知识库只有 10 条向量，每次检索返回的基本是同一批 chunk。Agent 发现"没看到完整的合同条款"，不断换查询词尝试，但向量检索的结果始终相似。

**修复**：System Prompt 加强约束——"规划 N 项，最多检索 N+1 次，之后必须提交答案。信息不够就在答案中诚实说明。" 让 Agent 知道"够了"是硬约束，不是建议。

### 坑2：最终答案 JSON 被截断

**现象**：`json.loads(tc.function.arguments)` 抛出 `Unterminated string`，答案是长文本，`max_tokens=800` 不够。

**修复**：`max_tokens` 提到 2000，给最终答案留足空间。同时加了 `json.JSONDecodeError` 的容错捕获——截断时回传错误让模型重试。

### 坑3：检索结果只给预览，模型看不到全文

**现象**：第一版 `execute_tool` 的 `search_knowledge_base` 返回 120 字预览（`preview = h["text"][:120]`），模型在"盲搜"——它不知道 chunk 里到底有什么，只能猜。

**修复**：返回完整文本。模型有了完整上下文，规划更准、回答更具体（能引用条款原文和金额）。

### 坑4：OpenAI SDK `arguments` 属性名

**现象**：`AttributeError: 'Function' object has no attribute 'argument'`

**修复**：`tc.function.arguments`（有 s），不是 `tc.function.argument`。

## Day1 vs Day4 对比实验（建议做）

在 Day1 和 Day4 上问同一个问题，对比行为：

```
问题：深圳精密五金的订单延期了，要赔多少钱？

Day1 行为（pipeline）：
  固定：query → retrieve(3条) → LLM 回答
  不管检索到什么，都基于那 3 条回答

Day4 行为（Agent）：
  Turn 1: plan → 拆成 3 个待查事项
  Turn 2: search × 3 → 逐项检索
  Turn 3: submit → 综合回答
  Agent 自己判断检索结果够不够，不够会重试
```

## 练习（巩固）

1. **改规划粒度**：把 System Prompt 里的"拆成 2-4 项"改成"拆成 2 项"或"拆成 5 项"，观察 Agent 的检索行为变化
2. **加一个不相关问题**：问"今天天气怎么样？"——Agent 应该在 plan 阶段就拒绝（输出边界），不调检索
3. **对比 Day1 无 RAG**：把 `execute_tool` 的 `search_knowledge_base` 改成返回空结果，看 Agent 是否会诚实说明"知识库未覆盖"
4. **模拟 Skills-guided 模式**：在 System Prompt 里加一段"skill 描述"（如"查询航天件时须同时检索保密条款和质检条款"），观察 Agent 是否按 skill 指引调整检索策略

## 下一步

**Day 5（周五 7/17）**：Week2 Demo 串联。把 week1 的 Function Calling Agent（查订单、改交期） + Day4 的 Agentic RAG（查合同、查延期史）拼成一个完整的调度助手。Agent 收到"客户 A 订单情况"后，既能查订单数据，又能自主检索合同条款和历史案例。

产出：`scripts/week2/week2_rag_agent.py`