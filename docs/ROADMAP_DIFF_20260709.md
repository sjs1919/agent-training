# 培训路线图 vs 权威文档 · 偏差报告（2026-07-09）

> **对齐范围**：知识块 ① ② ③ ④ ⑤ ⑦（P0 + Prompt 工程）
> **数据来源**：本地抓取 6 份权威英文源（OpenAI/Anthropic/MCP/LangChain 官方页），经 clash 3450 代理，2026-07-09 抓取
> **原文文件**：`C:\Users\wenext\AppData\Local\Temp\roadmap_sources\*.txt`（每份 3-5KB，含标题大纲 + 正文前 3000 字）
> **目的**：审阅偏差 → 你确认方向 → 我修 `docs/培训路线图分析.md` 对应字段

---

## ① 大模型 API（Function Calling）

**权威源**：`platform.openai.com/docs/guides/function-calling` — 当前版本目录：
- How it works / Function tool example / Defining functions / **Defining namespaces** / **Tool search** / Handling function calls / Additional configurations（tool_choice / parallel / strict） / Streaming / **Custom tools（CFG 约束）** / Docs agent

**培训路线图当前"必须章节"**：Chat Completions 请求响应 / Function Calling 参数（name/description/parameters） / tool_choice 四取值 / Structured Outputs / Streaming / 错误重试

**偏差**：
- ✅ **对上的**：Structured Outputs / Streaming / tool_choice / Function Calling 基本概念 / strict mode
- ⚠️ **遗漏（权威新增）**：
  - **Defining namespaces**：工具按 namespace 分组管理（多 MCP Server 时刚需）
  - **Tool search**：工具发现机制（工具多时靠 search 找）
- ℹ️ **表述不准**：培训路线图说 "Assistants API 已于 2026 年 8 月关闭" — 权威页导航里 Assistants API 仍在（Legacy APIs 分类），标注"迁移到 Responses API"更准
- 📌 **周边扩展**：权威页把 Responses API / MCP / Skills / Computer use / Web search tool / Code interpreter 都归到"Using tools"下 — 说明 Function Calling 只是"用工具"的一种（多了）

**建议改动**：
1. "必须章节"增加 "**Defining namespaces**" + "**Tool search**" 两项
2. "跳过"里 "Assistants API 已于 2026-08 关闭" 改为 "Assistants API 已被 Responses API 取代（原 API 进入 Legacy 分类）"

---

## ② Agent 核心机制

**权威源**：`anthropic.com/research/building-effective-agents`（发布 2024-12-19，目前仍是 Anthropic 权威 Agent 分类文档）— 目录：
- What are agents / When (and when not) to use agents / **When and how to use frameworks** / Building blocks（The augmented LLM） / **五种 Workflow 模式**：Prompt chaining / Routing / Parallelization / Orchestrator-workers / Evaluator-optimizer / **Agents** / Combining patterns / Appendix 1: Agents in practice（Customer support / Coding agents） / **Appendix 2: Prompt engineering your tools**

**培训路线图当前"必须章节"**：ReAct 模式 / Plan-and-Execute / 记忆三层 / 上下文窗口管理 / 工具调用循环 / Agent 评估

**偏差（最严重的一块）**：
- ❌ **术语系统性错误**：培训路线图用的是**学术论文分类**（ReAct 2022 / Plan-and-Execute 2023），但**Anthropic 权威文档从不使用这两个词**。Anthropic 的 canonical taxonomy 是 **workflows（5 种模式）vs agents**。这两套体系并行，但 Anthropic 视角明确更简洁。
- ⚠️ **遗漏（关键的 5 种 workflow 模式）**：
  - **Prompt chaining**（顺序链式调用）
  - **Routing**（意图分类路由到不同 prompt/model）
  - **Parallelization**（voting / sectioning，并发调用后聚合）
  - **Orchestrator-workers**（中心 orchestrator 动态拆解任务分给 workers）
  - **Evaluator-optimizer**（generator + evaluator 循环，直到过关）
- ⚠️ **遗漏**：**When and how to use frameworks**（Anthropic 明确建议：不要过早用框架，简单 pattern 优先）
- ⚠️ **遗漏**：**Appendix 2: Prompt engineering your tools**（工具描述本身就是 Prompt 工程的一部分——这个观点对 week1 有直接价值）
- ✅ 记忆三层 / 上下文管理 / 工具调用循环 概念上没错，但不是 Anthropic 的 canonical 分类

**建议改动**：
1. "必须章节"**重写**：以 Anthropic taxonomy（workflows 5 种 + agents）为主轴，把 ReAct/Plan-Execute 作为"学术论文视角"补充在"重要章节摘要"里
2. "重要章节摘要"加一段：**"workflows 5 种模式速查"**（每种一句话 + 何时用）
3. 补一条：**"工具描述本身是 Prompt 工程"**（week1 已实践的原则得到权威背书）

---

## ③ Tools & Skills 体系

**权威源**：`docs.anthropic.com/.../tool-use/overview` — 目录：
- How tool use works / When Claude uses tools / **Choose a tool**（**Your own tools** / **Anthropic-schema client tools** / **Server tools**） / Pricing
- 侧边导航还列了：Define tools / Handle tool calls / **Parallel tool use** / **Tool Runner (SDK)** / **Strict tool use** / **Server tools**（Web search / Web fetch / Code execution / Advisor / Tool search / Memory / Bash / Text editor / Computer use） / Troubleshooting / **Tool infrastructure**（**Manage tool context** / Tool combinations / **Tool use with prompt caching** / Mid-conversation system messages / Build an orchestration mode / **Programmatic tool calling** / **Fine-grained tool streaming**）

**培训路线图当前"必须章节"**：工具 Schema（name/description/parameters/returns） / 工具注册与发现 / 错误处理与降级 / 权限边界 / 调用链追踪

**偏差**：
- ⚠️ **遗漏关键分类**：Anthropic 现在把工具明确分**三类**：
  1. **Your own tools**（你自己实现）
  2. **Anthropic-schema client tools**（Anthropic 提供 schema，你实现）— 新分类
  3. **Server tools**（Anthropic 服务端执行，如 web_search / code_execution / memory 等）— 新增了 **Memory tool / Advisor tool**
- ⚠️ **遗漏进阶特性**：
  - **Parallel tool use**（并行调用多个工具，week1 Day2 已用但没系统学）
  - **Strict tool use**（strict:true 保证 schema 严格匹配）
  - **Tool use with prompt caching**（长 tool schema 缓存降本）
  - **Programmatic tool calling**（程序化控制工具调用循环）
  - **Fine-grained tool streaming**（流式解析工具参数）
  - **Manage tool context**（长会话时工具历史压缩）
- ✅ Schema 设计原则 / 权限边界 / 错误处理 — 抽象层面对上了

**建议改动**：
1. "必须章节"增加 "**工具三类分类**（your own / anthropic-schema / server）"
2. "必须章节"增加 "**Parallel tool use + Strict mode + Prompt caching for tools**"
3. "重要章节摘要"补充：Server tools 已经是 Anthropic 的重要能力（Memory / Web search / Code execution 都不需要自己实现）

---

## ④ MCP（Model Context Protocol）

**权威源**：`modelcontextprotocol.io/introduction` + `modelcontextprotocol.io/specification/2025-03-26`
- 版本：**2025-03-26**（培训路线图写的版本号对了 ✓）
- 架构三角色：**Hosts / Clients / Servers**（培训路线图对上了 ✓）
- Server features：**Resources / Prompts / Tools**（培训路线图漏了 Prompts）
- Client features：**Sampling**（培训路线图完全没提）
- Additional utilities：Configuration / Progress tracking / Cancellation / Error reporting / Logging

**培训路线图当前"必须章节"**：架构概览 / Server 端（工具注册/资源暴露/Prompt 模板） / Client 端 / 传输层（Stdio vs SSE/HTTP） / MCP 鉴权（OAuth） / 多 Server 编排

**偏差**：
- ✅ **对上得最好的一块**：架构三角色 / 传输层 / 鉴权 / 多 Server 都覆盖
- ⚠️ **遗漏**：**Sampling**（客户端 → 服务端的反向能力：Server 可以让 Client 触发 LLM 调用，用于递归 agentic 场景）
- ✅ Prompts 是 Server features 之一，培训路线图里其实写了"Prompt 模板"，只是没和 Resources/Tools 并列成"三大 Server features"

**建议改动**：
1. "必须章节"里 **明确列出**：Server features = **Resources / Prompts / Tools**（三个并列）
2. "必须章节"增加 "**Client features: Sampling**"
3. "重要章节摘要"加一句：Sampling 让 MCP Server 能反过来"请求 Host 调用 LLM"，是递归 agentic 场景的基础

---

## ⑤ RAG + 向量数据库

**权威源**：`python.langchain.com/docs/tutorials/rag/` — **重大发现**：
- 标题不再是传统 "RAG Tutorial"，而是 "**RAG with Deep Agents**"
- 目录：**RAG patterns**（4 种）/ Why retrieval matters / Setup / Index docs / Load / Split / Embeddings / VectorStore / **Build the agent** / Run the agent / Security / Full code
- 4 种 RAG patterns：
  1. **Skills-guided retrieval**（agent 加载 skill 描述如何搜索）
  2. **Rubric-checked grounding**（grader sub-agent 检查答案是否有根据）
  3. **Todo-driven investigation**（planning tool 生成 todo 逐项检索）
  4. **Retrieve, offload, and delegate**（检索结果写文件，subagents 并行读）

**培训路线图当前"必须章节"**：RAG 三大范式（Naive/Advanced/Modular） / Embedding 选型 / 分块策略 / 混合检索（BM25+向量） / 重排序 / 向量数据库选型 / RAG 评估

**偏差（RAG 领域整体升级）**：
- ❌ **过时的分类**：培训路线图讲的 "Naive → Advanced → Modular" 是 Gao et al. 2023 论文分类。当前主流工具链（LangChain）已经进入 **Agentic RAG** 时代。
- ⚠️ **遗漏关键概念**：
  - **Agentic RAG 4 种模式**（Skills-guided / Rubric-checked / Todo-driven / Retrieve-offload-delegate）
  - **Filesystem backend**（大文档 offload 到文件系统，orchestrator context 保持干净）
  - **Subagents 委派检索**（多个 subagent 并行读文件、总结）
- ✅ **仍然重要的基础**：Embedding 选型 / 分块 / 混合检索 / 重排序 / 向量库 — 这些是 Agentic RAG 的底座，不能删
- ⚠️ **具体数据可能过时**：培训路线图写 "bge-large-zh-v1.5 Recall@3=92%" — 2026 年可能有新模型（bge-m3、qwen3-embedding 等），需查最新

**建议改动**：
1. "必须章节"里**保留**基础部分（Embedding/分块/混合/重排/向量库/评估），**新增**：
   - **Agentic RAG 4 种模式**（LangChain 官方 2026 taxonomy）
   - **RAG + Deep Agents 组合**（filesystem backend + subagents）
2. "重要章节摘要"加：从 Naive RAG → Advanced/Modular RAG → **Agentic RAG** 是演进路径
3. Embedding 选型的具体数据加"截至 2026-07，需持续关注 bge-m3 / qwen3-embedding 等新选择"

---

## ⑦ 提示词工程（系统化）

**权威源**：`platform.openai.com/docs/guides/prompt-engineering` — 目录：
- Choosing a model / **Message roles and instruction following**（system/developer/user 三层） / **Version prompts in code** / **Message formatting with Markdown and XML** / **Save on cost and latency with prompt caching** / **Few-shot learning** / Include relevant context / Planning for the context window / **Prompting current GPT-5 series models** / **Prompting reasoning models**

**培训路线图当前"必须章节"**：System Prompt 架构（角色+边界+约束+安全） / **三层 Prompt 架构（系统级/场景级/用户级）** / Few-shot / CoT / JSON Schema / 版本管理 A/B / Prompt Injection 防护

**偏差**：
- ⚠️ **术语混淆**：培训路线图的"三层 Prompt 架构"是 **Jimmy Song 提出的分层法**（系统级/场景级/用户级），不是权威分层。**权威分层**是 OpenAI 的 **Message roles: system / developer / user**（instruction hierarchy，system > developer > user 优先级链）—— 这是 GPT-5 时代的官方消息角色三级。两者可以共存，但要区分清楚。
- ⚠️ **遗漏（权威强调的）**：
  - **Prompt caching**（system prompt / few-shot examples 缓存降本 90%+ 延迟，week1 Demo 完全可以用）
  - **Prompting reasoning models**（o3/GPT-5 等 reasoning 模型的 prompt 方式**反常识**：不要给太详细的步骤指导，让模型自己推理）
  - **Instruction hierarchy**（system > developer > user 的优先级链，用于防 Injection）
- ✅ Few-shot / JSON Schema / 版本管理 / A/B 测试 / Prompt Injection — 大方向对
- ⚠️ **CoT 的定位可能要调整**：OpenAI 权威页专门开了 "**Prompting reasoning models**" 一节说 reasoning 模型不需要传统 CoT（自己会），CoT 主要用于**非 reasoning 模型**。培训路线图讲 "CoT 数学题准确率 +41%" 是老数据（GPT-4 时代）。

**建议改动**：
1. "必须章节"把 "**三层架构**" 明确区分两种解读：
   - **OpenAI 官方**：system / developer / user message roles（instruction hierarchy）
   - **Jimmy Song 分层**：系统级 / 场景级 / 用户级（这是**Prompt 内容分层**，可与 message roles 组合）
2. "必须章节"增加：
   - **Prompt caching**（重要成本优化）
   - **Prompting reasoning models**（推理模型的特殊方式：少指导、多留白）
3. "重要章节摘要"补：CoT 主要针对非 reasoning 模型；reasoning 模型（o3/GPT-5）不需要外挂 CoT

---

## 总结：6 个知识块的整体健康度

| 知识块 | 健康度 | 主要问题 |
|-------|-------|---------|
| ① API/Function Calling | 🟢 良好 | 遗漏 namespaces + Tool search |
| ② Agent 核心机制 | 🔴 **严重** | 术语系统错位（用学术论文 vs Anthropic 权威） |
| ③ Tools & Skills | 🟡 中等 | 遗漏工具三分类 + 进阶特性 |
| ④ MCP | 🟢 良好 | 遗漏 Sampling + Server features 未三并列 |
| ⑤ RAG | 🟡 中等 | 停留在旧分类，未跟上 Agentic RAG |
| ⑦ Prompt 工程 | 🟡 中等 | 三层架构混淆 + 遗漏 caching/reasoning |

**优先修**：② 严重（今天下午必修）→ ⑤ + ⑦ 中等（有 Agent/RAG/Prompt 工程学习计划背书）→ ① + ③ + ④ 小修补即可

---

## 修改前请确认

1. **② Agent 核心机制的术语大调**：是否同意用 Anthropic canonical taxonomy（workflows 5 种 + agents）作为主轴，把 ReAct/Plan-Execute 降为"补充视角"？
2. **⑤ RAG 加 Agentic RAG 4 种模式**：是否同意保留传统基础（Embedding/分块/混合/重排）+ 加 Agentic RAG 一节？
3. **⑦ 三层架构区分两种解读**：是否同意在文档里明确说明"OpenAI message roles" vs "Jimmy Song 内容分层"是两个正交概念？
4. **暂不改的**：培训路线图后半部分 P1（LangChain/LangGraph/⑧⑨⑩⑪）和 P2（微调/数据/推理/多模态）本次不动，等你确认修 P0+⑦ 后再决定要不要继续

我等你审阅这份报告，OK 就动手改 `docs/培训路线图分析.md`。
