# 企业级 Agent 开发 · 加速学习路线

## 目录 → 知识块 → 参考资料 映射

> 右侧「参考资料」列对应 `培训路线图分析.md` 第四部分的知识块编号，每个编号下有完整的中英文资料、必须章节和摘要。

| 阶段 | 天数 | 覆盖知识块 | 参考资料入口 |
|------|------|-----------|-------------|
| 第一阶段：大模型基础认知 | 5 天 | ① 大模型 API · ⑦ 提示词工程 | → `培训路线图分析.md#1-大模型-api编程化调用` · `#7-提示词工程系统化` |
| 第二阶段：RAG 检索增强 | 4 天 | ⑤ RAG + 向量数据库 | → `培训路线图分析.md#5-rag-检索增强--向量数据库` |
| 第三阶段：Agent 核心架构 | 9 天 | ② Agent 机制 · ③ Tools/Skills · ④ MCP · ⑥ LangChain/LangGraph · ⑧ Agent 集群 | → `培训路线图分析.md#2-agent-核心机制` · `#3-tools--skills-体系` · `#4-mcpmodel-context-protocol` · `#6-langchain--langgraph-编排` · `#8-agent-集群路由与跨-agent-记忆` |
| 第四阶段：企业级工程落地 | 6 天 | ⑨ 鉴权 · ⑩ 可观测性 · ⑪ 业务/项目匹配 | → `培训路线图分析.md#9-鉴权体系` · `#10-可观测性` · `#11-业务项目匹配度` |
| 第五阶段：模型微调与私有化 | 6 天 | ⑫ 模型微调 · ⑬ 数据工程 · ⑭ 推理优化 | → `培训路线图分析.md#12-模型微调sft--peft--dpo` · `#13-数据工程` · `#14-推理优化` |
| 第六阶段：多模态 Agent | 5 天 | ⑮ 多模态 Agent | → `培训路线图分析.md#15-多模态-agent` |

### 使用方式

1. **看路线** → 先读本文的周计划表，了解每周目标
2. **查资料** → 根据「参考资料入口」列，跳转到 `培训路线图分析.md` 对应知识块
3. **写代码** → 每周五产出本周的 Demo 增量，不是只看不写

---

## 设计原则

- **锚定目标**：以"能独立交付企业级多 Agent 系统"为终点，倒推所需知识
- **第三周动手**：前两周压缩前置，第三周必须开始写 Agent 代码
- **够用即走**：非 Agent 核心知识点压缩到"能看懂、能调用"即可，不深究原理
- **工程落地导向**：每一步都关联 MCP、鉴权、可观测性等企业级关注点

**目标周期**：**7 周（35 工作日）**

---

## 按周执行计划

### 第一周（Jul 1-4）　知识块 ① ⑦　　API 要能调，Prompt 要能工程化

> **本周一句话**：把模型当成一个函数来调，而不是一个聊天框。

```
Mon  Jul 1  █  大模型谱系 + API 入门      读完 ① 必须章节①②，跑通第一个 API 调用（非流式）
Tue  Jul 2  ██  Function Calling / Tool Use  搞懂 tool 定义 → 模型请求 → 解析结果 → 回传 的循环，跑通 demo
Wed  Jul 3  ██  System Prompt 工程化         三层 Prompt 架构（系统级/场景级/用户级）+ JSON Schema 约束，写到代码里
Thu  Jul 4  █  原理速览 + 本周消化           Token/Context/Temperature 含义，补充落下的代码
```

| 产出 | 说明 |
|------|------|
| `week1_api_agent.py` | 一个能循环调用 Function Calling 的脚本，Agent 闭环跑通 |

**本周 Demo 边界（严格只做这些）**：
- 1 个工具：`query_orders()` ——查订单列表
- System Prompt 角色：调度助手
- 能做：用户说"帮我看看有哪些快超期的订单，按交期排个序" → Agent 调工具 → 得到 JSON → LLM 格式化输出
- **不做**：多工具、RAG、多 Agent、优先级算法——后面周再加

**Mock 数据本周只准备**：`orders.csv` — id、客户名、产品、数量、交期、当前环节、状态（30 条）

> 参考资料：知识块 ① [OpenAI Function Calling 完整指南](https://www.cnblogs.com/qiniushanghai/p/19937290) · 知识块 ⑦ [提示词工程核心技术](https://jimmysong.io/zh/book/ai-handbook/prompt/techniques/)

---

### 第二周（Jul 7-11）　知识块 ⑤ ②　　RAG + Agent 概念，为动手铺路

> **本周一句话**：让模型"知道"你的私有数据，理解 Agent 是怎么做决策的。

```
Mon  Jul 7  █  RAG 基础 + 向量数据库         Embedding 选型（bge-large-zh-v1.5）、分块策略、Milvus 跑起来
Tue  Jul 8  ██  混合检索 + 重排序            BM25 + 向量融合、Cross-Encoder 重排、端到端 RAG 管线
Wed  Jul 9  █  Agent 概念入门               ReAct 模式（Thought→Action→Observation）、工具调用循环、记忆三层
Thu  Jul 10 ██  Anthropic Agent 设计哲学      读"Building Effective Agents"全文，理解什么时候用 Workflow vs Agent
Fri  Jul 11 █  本周 Demo 串联                把 RAG 管线 + Agent 循环拼到一起，Agent 能检索你的文档回答问题
```

| 产出 | 说明 |
|------|------|
| `week2_rag_agent.py` | Agent + RAG 管线串联，能检索私有知识库并推理回答 |

**本周 Demo 扩展（在上周基础上叠加）**：
- 新增 1 个工具：`query_customer(id)` ——查客户等级和合同条款
- RAG 知识库：灌入「客户合同特殊条款.txt」「历史延期记录.txt」，Agent 检索后辅助判断优先级
- 能做：用户问"客户 A 的订单情况怎么样，有没有特殊要求？" → 调订单工具 + 客户工具 + RAG 召回合同条款 → 综合回答
- **不做**：多 Agent、MCP、鉴权——下周开始

**Mock 数据本周新增**：`customers.csv` — id、等级、信用分、历史延期率（15 条）；`contracts/` 目录 — 几个客户的特殊条款 txt

> 参考资料：知识块 ⑤ [All-in-RAG 开源指南](https://github.com/syp0422/prj-rag) · 知识块 ② [Anthropic Building Effective Agents](https://docs.anthropic.com/en/docs/agents-and-tools)

---

### 第三周（Jul 14-18）　知识块 ③ ④ ⑥　　开始写 Agent！

> **本周一句话**：这一周开始，你的 Demo 从一个"脚本"变成一个有架构的 Agent 系统。

```
Mon  Jul 14 ██  工具体系设计                工具注册/发现机制、Schema 规范化（name/description/parameters）、工具粒度原则
Tue  Jul 15 ██  MCP Server 开发             跑通一个 MCP Server（Python SDK），把上周的 2 个工具 + 新增工具都注册进去
Wed  Jul 16 ██  MCP Client + 多 Server       编写 Client 端连接管理，接入订单 Server + 客户 Server，工具按来源分组
Thu  Jul 17 ██  LangGraph 状态图             用 StateGraph 重构 Agent 循环（替代手写 while 循环），加条件边实现路由
Fri  Jul 18 █  本周 Demo 串连 + 回顾          MCP 标准化工具 + LangGraph 编排的单 Agent，代码结构清晰、可扩展
```

| 产出 | 说明 |
|------|------|
| `week3_mcp_agent/` | 结构化项目：MCP Server(2+) → LangGraph Agent → 工具调用闭环，有清晰的模块划分 |

**本周 Demo 扩展（真正的 Agent 架构诞生）**：
- 工具拆成两个 MCP Server：
  - `order_server`：`query_orders()` `get_order_detail()` `get_production_status()`
  - `resource_server`：`query_inventory()` `query_machine_load()` `query_customer(id)`
- LangGraph 状态图：用户提问 → 意图识别 → 选择工具 → 调用 → 结果注入 → 判断是否还需更多数据 → 最终输出
- System Prompt 升级为调度角色："你是 3D 打印生产调度专家，根据订单交期、客户等级、物料库存、机器负载来排优先级"
- 能做：用户问"今天先做哪些订单？" → Agent 自主决定依次查订单→查库存→查机器→综合给出优先级建议
- **不做**：多 Agent 集群——下周才学

**Mock 数据本周新增**：`inventory.csv` — 材料名、库存量、采购周期（10 种材料）；`machines.csv` — 机器 id、型号、当前任务、预计空闲（5 台）
- **本周开始拼完整调度逻辑**（Agent 不是简单查表，是根据多维度数据自主推理排序）

> 参考资料：知识块 ④ [MCP 中文站](https://mcpcn.com/) · 知识块 ③ [Function Calling 全平台实战](https://blog.csdn.net/weixin_42260382/article/details/162133638) · 知识块 ⑥ [LangGraph Quick Start](https://langchain-ai.github.io/langgraph/)

**为什么第三周才写 Agent？** 第一周有了 API 手感，第二周懂了 Agent 决策循环和 RAG，第三周用 MCP 标准化工具 + LangGraph 编排，写出来的 Agent 已经有了架构，不是随手写的一坨代码。

---

### 第四周（Jul 21-25）　知识块 ⑧ ⑨　　多 Agent 集群 + 鉴权 🎤 7/23 分享！

> **本周一句话**：一个 Agent 不够用，让多个 Agent 协作并管好权限。

```
Mon  Jul 21 ██  多 Agent 协作模式             Supervisor/Manager-Worker 模式实现，主 Agent 拆解任务 → 分发给子 Agent
Tue  Jul 22 ██  Agent 路由 + 准备分享           意图识别路由、结果聚合；晚上打磨 Demo，准备 7/23 分享大纲和跑通核心流程
Wed  Jul 23 🎤  分享日！                        上午过一遍 PPT + 现场跑通，下午正式分享（20min + Q&A）
Thu  Jul 24 ██  鉴权体系                      Token Exchange（RFC 8693）、API Key 管理、用户身份透传、工具级权限（RBAC+ABAC）
Fri  Jul 25 █  多租户隔离 + 本周 Demo 串连      洋葱型防御（网关→运行时→工具三层）、审计日志；多 Agent + 鉴权完整联调
```

| 产出 | 说明 |
|------|------|
| `week4_multi_agent/` | 多 Agent 系统（主 Agent + 2-3 子 Agent）+ Token Exchange 鉴权链路 + 基础审计日志 |

**本周 Demo 扩展（企业级多 Agent 协作）**：
- 角色拆成 Agent 集群：
  - `调度 Agent`（主 Agent）——拆解任务、分发、汇总
  - `审核 Agent`——审合同条款、客户信用、订单异常
  - `生产 Agent`——查物料、查机器、估交期可行性
- 协作流程：调度收到需求 → 同时分发审核和生产 → 汇总两部分结果 → 综合输出优先级清单
- 鉴权接入：客户端只持有自己的身份 Token，调度 Agent 去交换具有受限权限的子 Token，不同 Agent 只能访问对应范围的数据
- 分享时演示场景：5 个订单同时进来，Agent 自动评估和排序，演示哪些被提前哪些被推后以及原因

> 参考资料：知识块 ⑧ [《智能体设计模式》](https://jimmysong.io/zh/book/agentic-design-patterns/) · 知识块 ⑨ [Okta Securing AI Agents](https://www.okta.com/sites/default/files/2025-12/Securing%20AI%20Agents.pdf) · [企业级 Agent 信任模型](https://developer.baidu.com/article/detail.html?id=7592455)

---

### 第五周（Jul 28-Aug 1）　知识块 ⑩ ⑪　　可观测 + 业务匹配

> **本周一句话**：一个能上线的 Agent 系统，必须有监控、有评估、有业务判断依据。

```
Mon  Jul 28 ██  可观测性                      全链路追踪（Langfuse + OpenTelemetry）、五大指标、Span 三层设计
Tue  Jul 29 ██  成本监控 + 告警                Token 用量追踪、成本三级告警（100%/150%/200%）、预算熔断
Wed  Jul 30 ██  业务匹配度 + 评估              场景适用性判断（Prompt/Workflow/Agent 边界）、ROI 框架、Agent 评估体系
Thu  Jul 31 ██  综合实战                      给 week4 的 Demo 接入可观测 + 评估，补齐生产级最后一块
Fri  Aug 1  █  回顾 + 中期演示                 前 5 周成果 review，准备一个 15min 的 Demo 演示
```

| 产出 | 说明 |
|------|------|
| `week5_production/` | week4 系统 + Langfuse 追踪 + 成本监控仪表盘 + Agent 评估脚本 = **接近生产级 Agent 系统** |

> 参考资料：知识块 ⑩ [阿里云 AI Agent 全栈可观测](https://developer.aliyun.com/article/1665930) · [Langfuse 文档](https://langfuse.com/docs) · 知识块 ⑪ [Anthropic When to use agents](https://docs.anthropic.com/en/docs/agents-and-tools)

---

### 第六周（Aug 4-8）　知识块 ⑫ ⑬ ⑭　　微调 + 推理优化

> **本周一句话**：知道什么时候 Prompt/RAG 不够用、需要微调，怎么把推理成本降下来。

```
Mon  Aug 4  █  微调决策框架                  Prompt vs RAG vs Fine-tuning 边界线、成本估算、数据量评估
Tue  Aug 5  ██  LoRA/QLoRA 实战              用 PEFT 跑通一个 QLoRA 微调（Qwen2.5-7B），12GB 显存可跑
Wed  Aug 6  █  DPO 偏好对齐                  DPO vs RLHF 选型、偏好对构建、DPO 比 RLHF 简单在哪
Thu  Aug 7  ██  数据工程 + 推理优化            IFD/LESS 数据筛选、vLLM + AWQ + 前缀缓存、KV Cache 调优
Fri  Aug 8  █  本周消化 + 补代码              把微调/推理概念落实到 Demo 的配置和选型文档里
```

| 产出 | 说明 |
|------|------|
| `week6_finetune/` | QLoRA 微调实验 Notebook + vLLM 推理部署配置 + 技术选型决策文档 |

> 参考资料：知识块 ⑫ [PEFT 全解析](https://blog.csdn.net/qq_46094651/article/details/157513491) · 知识块 ⑬ [SFT 数据筛选的艺术](https://cloud.tencent.cn/developer/article/2516355) · 知识块 ⑭ [KV-Cache 调优 10 大方法](https://developer.aliyun.com/article/1684500)

---

### 第七周（Aug 11-15）　知识块 ⑮　　多模态 Agent

> **本周一句话**：拓展 Agent 的感知边界——能看图、能听语音、能读 PDF。

```
Mon  Aug 11 ██  视觉 Agent                    GPT-4o/Claude Vision API、截图理解、文档解析（PDF/表格/扫描件）
Tue  Aug 12 ██  语音 Agent                    Whisper ASR + TTS 语音闭环、延迟优化（P99 < 2s）
Wed  Aug 13 █  视频理解 + 模态路由             关键帧提取、统一多模态路由器架构
Thu  Aug 14 ██  把多模态接入现有 Demo           给 week5 系统加视觉/语音能力，保持架构整洁
Fri  Aug 15 █  7 周回顾 + 最终演示              完整路线成果验收，准备 30min 技术分享
```

| 产出 | 说明 |
|------|------|
| `week7_multimodal/` | 多模态 Agent 模块（视觉/语音）+ 最终版生产级 Agent 系统 + 技术分享 PPT 大纲 |

> 参考资料：知识块 ⑮ [从零构建多模态 Agent](https://developer.baidu.com/article/detail.html?id=7551378) · [多模态 Agent 实战营](https://cloud.tencent.com.cn/developer/article/2674972)

---

## 7 周总览

```
Week 1  ████░░░░░  API + Prompt（前铺）          产出：API 调用脚本
Week 2  ████░░░░░  RAG + Agent 概念（前铺）      产出：RAG + Agent 串联 Demo
Week 3  ████████░  开始写 Agent！MCP + LangGraph   产出：有架构的单 Agent 系统 ⭐
Week 4  █████████  多 Agent 集群 + 鉴权            产出：多 Agent 协作系统 ⭐ 🎤 7/23 分享！
Week 5  ████████░  可观测 + 业务匹配               产出：接近生产级系统 ⭐
Week 6  ██████░░░  微调 + 推理优化                 产出：微调实验 + 部署配置
Week 7  ██████░░░  多模态 Agent                    产出：最终版 + 技术分享
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
       第三周动手，第五周可上线
```

## 🎤 7/23 分享节点

**Jul 23（第四周周三）做一次技术分享**，此时已完成的内容：

| 时间 | 已完成 | 可演示 |
|------|--------|--------|
| Week 1-2 | API 工程化调用、System Prompt 三层设计、RAG 管线 | 铺垫，简单带过 |
| Week 3 | MCP 标准化单 Agent、LangGraph 状态图编排 | **重点演示：从 0 到有架构的单 Agent** |
| Week 4 前 2 天 | 多 Agent 协作（Supervisor 模式）、Agent 路由 | **分享亮点：多 Agent 架构设计思路** |

**分享提纲建议（约 20min）**：

```
1. 为什么 Agent？（3min）
    — AI 编程从聊天到自主决策的跃迁
    — Vibe Coding → Agent Developer 的转变

2. 单 Agent 架构实战（8min）⭐
    — 现场演示：Function Calling → MCP 工具标准化 → LangGraph 编排
    — 一个业务场景端到端跑通（如"帮我查业务数据并生成报告"）

3. 多 Agent 集群设计（5min）
    — Supervisor 模式：一个主 Agent 调度 N 个子 Agent
    — 代码架构对比：从手写 while 循环到 LangGraph 状态图

4. 踩坑与收获（3min）
    — 前 3.5 周最大的认知改变
    — 哪些资料真的有用，哪些浪费时间

5. 下一步（1min）
    — 鉴权、可观测、微调、多模态
```

> **建议**：分享前利用周末（7/19-20）把 Week 3 的 Demo 打磨干净，代码加 README + 架构图，确保现场能跑。Week 4 周一周二的多 Agent 部分至少做到能口头讲清楚架构思路，即使代码还没完全调通。

## 与原路线的关键差异

| 维度 | 第 6 张图（原路线） | 本加速路线 |
|------|-------------------|-----------|
| **总周期** | 53 天 | 35 天（7 周） |
| **动手写 Agent** | 第 14 天（第三阶段） | **第 11 天（第三周周一）** |
| **Agent 占比** | ~11%（6/53） | **26%（9/35）** |
| **工程落地** | 无 | **17%（6/35）**——MCP/鉴权/可观测/业务匹配 |
| **基础原理** | 16 天 | 压缩到 16 小时——够用即走 |
| **微调深度** | 21 天 | 6 天——聚焦 Agent 开发者视角 |
| **每周产出** | 无明确要求 | 每周五一个可运行 Demo |

## 学习纪律

1. **周一~周四 学+写**：上午读资料（2h），下午写代码（4h）
2. **周五 串+出 Demo**：把本周碎片拼成可演示的完整功能
3. **周末 消化+补漏**：不安排新知识，只看落下的内容
4. **第三周是关键转折点**：之前是"学"，之后是"做"。第三周写的 Agent 架构会一直演进到第七周
5. **双文件联动**：本文 = 周计划 + 产出清单，`培训路线图分析.md` 第四部分 = 每个知识块的完整参考资料

---

## 附录：前两周若想提前动手

如果你前两周就想写 Agent（完全可以），按这个顺序：

```
Day 1-2  → 跑通 Function Calling 循环（知识块 ①）
Day 3    → 加上 MCP Server（知识块 ④），工具标准化
Day 4    → 用 LangGraph 重构循环（知识块 ⑥）
Day 5    → 你就有了一个最简 Agent，然后第三周再补 Agent 理论和 RAG
```

这样第二周结束时已经有一个能跑的单 Agent，第三周直接进入多 Agent + 鉴权。
