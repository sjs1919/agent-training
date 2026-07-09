# 第二周任务清单 - RAG + Agent 概念（自然周 7/13-7/17）

> **本周一句话**：让模型"知道"你的私有数据，理解 Agent 是怎么做决策的。
> **知识块**：⑤ RAG 检索增强 + ② Agent 核心机制
> **产出**：`scripts/week2/week2_rag_agent.py`（RAG 管线 + Agent 循环串联）
> **对齐说明**：原路线图日期-星期错位（7/1 实际周三不是周一，导致全周错位）。现按自然周（周一-周五）对齐：**本周 7/6-7/10 = week1 收尾周，week2 = 下自然周 7/13-7/17**。
> **主备 provider**：沿用 week1（豆包主 + DeepSeek 备，已修 Windows 编码+代理问题，开箱即跑）。

---

## 本周（7/6-7/10 自然周）= week1 收尾周

> 今天 **7/8 周三**。本周剩 周三/四/五，用于收尾 week1 学习资料（代码已巩固提交）。

| 日期 | 星期 | 任务 |
|------|------|------|
| 7/6 | 周一 | ✅ week1 代码巩固（主备+FC+Prompt 跑通修复提交）+ ⑦ OpenAI/Anthropic 读完 |
| 7/7 | 周二 | ✅ 同上 |
| **7/8** | **周三（今天）** | ⑦ Jimmy Song 剩半 |
| 7/9 | 周四 | ⑦ 收尾 + 可选补 CoT/版本管理进 Demo |
| 7/10 | 周五 | ⑦ 完结 + week2 预习（Milvus 环境 / RAG 基础资料） |

### 收尾知识块 ⑦（提示词工程）

**实际进度**：⑦ 的 OpenAI Prompt Engineering Guide + Anthropic Prompt Engineering 已读完，**Jimmy Song《提示词工程核心技术》（⑦ 中文主资料 ⭐）只读了一半**。

**资料**：⭐ [提示词工程核心技术 - Jimmy Song](https://jimmysong.io/zh/book/ai-handbook/prompt/techniques/)（读剩下一半）· [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)（已读）· [Anthropic Prompt Engineering](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering)（已读）

**⑦ 必须章节（9 项，2026-07-09 权威对齐后，对照已读/未读）**：
1. System Prompt 设计架构（角色设定+能力边界+输出约束+安全规则）
2. **两种"分层"要区分清楚**：(a) OpenAI Message Roles / Instruction Hierarchy（system > developer > user）；(b) Jimmy Song 内容分层（系统级/场景级/用户级）—— 两者正交可组合
3. Few-shot 模板设计（3-5 对示例，准确率 +27%；示例放最后）
4. CoT 思维链引导（**主要用于非 reasoning 模型**；reasoning 模型 o3/GPT-5/Opus 4.8 extended thinking 自带内部推理，不需外挂 CoT）
5. JSON Schema 输出格式约束（Prompt 级 + API 级 strict mode）
6. Prompt 版本管理与 A/B 测试
7. Prompt Injection 防护（输入清洗、边界隔离、XML 标签）
8. **Prompt Caching**（system prompt / few-shot examples 缓存，成本降 90%+，延迟大幅优化）— 2026 新增
9. **Prompting Reasoning Models**（推理模型的特殊 prompt 方式：少指导、多留白）— 2026 新增

> week1 day3 代码已落地：① System Prompt 架构、③ Few-shot、⑤ JSON Schema、⑦ 的 XML 隔离、② 的 Jimmy Song 内容分层。读完剩余章节后，可把 ④ CoT、⑥ 版本管理、**⑧ Prompt Caching**（现在就能用，week1 SYSTEM_PROMPT 每次都发，开缓存立省 90% 输入 token）补进 Demo。

---

## 下周（7/13-7/17 自然周）= week2：Agentic RAG（2026 升级版）

> **⚠️ 2026-07-09 升级**：LangChain 官方教程已从 "RAG Tutorial" 改名 "**RAG with Deep Agents**"，新 4 种 agentic 模式成为主流。本周分**基础层**（周一-周二）+ **进阶层**（周三-周四），周五串 Demo。② Agent 概念 week1 Day2 已通过 Function Calling 学过（ReAct 循环、终止条件、记忆三层已实现），week2 聚焦 RAG 侧的 Agent 视角。

### 周一 7/13　RAG 基础层 —— Embedding + 分块 + 向量库

**任务**：搭起端到端 RAG 骨架 —— Embedding 选型、分块策略、Milvus 跑起来

**资料**：
- ⭐ [LangChain RAG with Deep Agents 教程](https://python.langchain.com/docs/tutorials/rag/) —— **2026 主教程**，先看 Prerequisites/Setup/Load/Split/Embeddings/VectorStore 前半部分
- [Milvus 官方文档](https://milvus.io/docs) —— 向量数据库
- [All-in-RAG 开源指南](https://github.com/syp0422/prj-rag) —— 传统 RAG 端到端参考
- 中文：[RAG 实战指南（百度）](https://developer.baidu.com/article/detail.html?id=3660169) · [Easy-VectorDB（Datawhale 开源）](https://datawhalechina.github.io/easy-vecdb/) · [Embedding 选型与向量库搭建（GitCode）](https://gitcode.csdn.net/69d712fd54b52172bc67e819.html)

**必须章节**：Embedding 选型（中文 bge-large-zh-v1.5 / bge-m3 / qwen3-embedding，需持续关注新模型）· 分块策略（语义切分 > 固定 token，1024 + 100 overlap，Recall 0.67→0.91）· Milvus 起 docker 单机版

**产出**：`scripts/week2/day1_rag_basics.py` —— 灌入合同/延期记录 → 向量化 → 检索 top-k 返回

---

### 周二 7/14　RAG 基础层 —— 混合检索 + 重排序

**任务**：BM25 + 向量融合（RRF）+ Cross-Encoder 重排，把 Recall/Precision 打上生产可用水平

**资料**：
- ⭐ [LangChain RAG with Deep Agents 教程](https://python.langchain.com/docs/tutorials/rag/) 继续
- [高级 RAG 优化手册（阿里云）](https://developer.aliyun.com/article/1680493)
- [三步升级检索系统（华为云）](https://bbs.huaweicloud.com/blogs/463868)

**必须章节**：混合检索（向量+BM25，RRF 融合）· 重排序（Cross-Encoder `BAAI/bge-reranker-large`）· RAG 评估（RAGAS 框架、召回率/精确率）

**产出**：`scripts/week2/day2_hybrid_rerank.py` —— 在 day1 基础上加 BM25 分支 + RRF 融合 + reranker 二次打分

---

### 周三 7/15　Agentic RAG 进阶层 —— 4 种模式认知 ⭐

**任务**：理解从"pipeline 决定检索"到"Agent 决定检索"的范式跃迁

**资料**：
- ⭐ [LangChain RAG with Deep Agents](https://python.langchain.com/docs/tutorials/rag/) —— **重点读 RAG patterns 章节 + Build the agent 章节**
- [Anthropic Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) —— 复习 workflow 5 种模式（Agentic RAG 4 种可与之类比）

**必须章节**：**Agentic RAG 4 种模式**：
1. **Skills-guided retrieval**：Agent 加载 "skill 描述"（如何搜、用哪个索引、引用格式），再调检索工具
2. **Rubric-checked grounding**：Grader sub-agent 用 RubricMiddleware 检查答案是否有源可依，不达标返工，直到过关或超上限
3. **Todo-driven investigation**：Planning tool 生成 todo 列表（要查哪些文档/查询），逐项检索后综合
4. **Retrieve, offload, and delegate**：检索结果**写文件系统**（不塞进 orchestrator context），subagents 并行读文件、总结，orchestrator context 保持干净

**要点**：
- 传统 RAG = 流水线固定：query → 检索 → 生成
- Agentic RAG = Agent 自主决定：**何时检索、检索什么、检索多少次、结果放哪、要不要复检**
- **Filesystem backend**（大文档 offload 到文件系统）是 Deep Agents 的关键创新，避免 orchestrator context 爆炸

**读完带回**：
- 4 种模式各写 1 个我们订单调度场景下的**具体用例**（比如：Rubric-checked → 检查生产建议是否引用真实订单号）
- 挑 1 种模式作为周五 Demo 主线（推荐 **Todo-driven** 或 **Retrieve-offload**）

---

### 周四 7/16　Agentic RAG 进阶层 —— 上手 Deep Agents

**任务**：跟着 LangChain 官方教程手写一个最小 Agentic RAG

**资料**：
- ⭐ [LangChain RAG with Deep Agents](https://python.langchain.com/docs/tutorials/rag/) —— **重点：Full code 章节 + Security considerations**

**必须章节**：LangChain Deep Agents 关键原语（custom retrieval tools / filesystem backend / subagents / skills / grading rubrics）· Security（Prompt Injection 通过检索内容进入 Agent，需隔离）

**产出**：`scripts/week2/day4_agentic_rag.py` —— 官方教程最小复刻，跑通 Skills-guided 或 Todo-driven 一条链路

---

### 周五 7/17　本周 Demo 串联

**任务**：把 day1-4 的 RAG 基础 + Agentic RAG 拼到 week1 Demo 上，Agent 能自主检索合同和延期记录辅助调度决策

**产出**：`scripts/week2/week2_agentic_rag_agent.py` —— **week1 的 Function Calling Agent + Agentic RAG 检索层**

---

## 本周 Demo 边界（上周基础上叠加，Agentic RAG 视角）

- **week1 底座保留**：主备 fallback、Function Calling 循环、三层 Prompt
- **新增 1 个 client tool**：`query_customer(id)` - 查客户等级和合同条款（结构化 CSV）
- **新增 1 个 retrieval tool**：`retrieve_docs(query, top_k=3)` —— 混合检索 + 重排，返回合同/延期记录片段
- **RAG 知识库**：灌入「客户合同特殊条款.txt」「历史延期记录.txt」
- **Agentic RAG 一种模式落地**（推荐 Todo-driven）：Agent 收到"客户 A 订单情况，有没有特殊要求？" → 生成 todo（查订单/查客户/查合同/查延期史）→ 逐项调工具/检索 → 综合回答
- **不做**：多 Agent、MCP、鉴权、Filesystem backend（那是 week3 的 Deep Agents 深水区）

## Mock 数据本周新增

- `customers.csv` - id、等级、信用分、历史延期率（15 条）
- `contracts/` 目录 - 几个客户的特殊条款 txt

---

## 后续周顺延（对齐自然周，周一-周五）

| 周次 | 原日期 | 对齐后日期 | 主题 |
|------|--------|-----------|------|
| week2 | 7/7-7/11 | **7/13-7/17** | RAG + Agent 概念 |
| week3 | 7/14-7/18 | **7/20-7/24** | MCP + LangGraph 单 Agent ⭐ |
| week4 | 7/21-7/25 | **7/27-7/31** | 多 Agent 集群 + 鉴权 🎤 |
| week5 | 7/28-8/1 | **8/3-8/7** | 可观测 + 业务匹配 |
| week6 | 8/4-8/8 | **8/10-8/14** | 微调 + 推理优化 |
| week7 | 8/11-8/15 | **8/17-8/21** | 多模态 Agent |

> 整体顺延约 1 周，总周期 8/15 -> 8/21 收官。

---

## 🎤 分享节点：7/24 周五（week3 结尾）

原计划 week4 周三 7/23，但 7/23 实际是周四，且 week4 顺延到 7/27-7/31 后 7/23 落在 week3 中段。**已调整为 7/24 周五（week3 结尾）**，内容聚焦 week1-3 单 Agent 成果，多 Agent 不演。

**7/24 分享内容**：
- week1：API + 主备 fallback + Function Calling + Prompt 工程化（简单带过）
- week2：RAG 管线 + Agent 概念（铺垫）
- **week3：MCP 标准化工具 + LangGraph 状态图编排 → 有架构的单 Agent** ⭐ 现场演示
- 多 Agent 架构设计思路（口头讲，不演，week4 才做）
- 踩坑与收获

**分享前打磨**：7/18-7/19 周末把 week3 Demo 打磨（README + 架构图 + 代码整洁），确保 7/24 现场能跑。

