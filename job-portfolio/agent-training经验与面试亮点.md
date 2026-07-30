# Agent Training 训练成果与面试素材

> 基于 agent-training 计划前 4 周真实训练提炼（2026-07-03 ~ 07-31）
> demo 载体锁定制造业排程排产（3D 打印 / CNC 订单、库存、设备、客户），能力可迁移但载体不跨行业
> 整理日期：2026-07-30
> 配套文档：`vibe-coding经验与面试亮点.md`（Vibe Coding 三项目素材版）
> 本文档定位：把原"面试禁区"中的 **Agent 开发 / LangChain-LangGraph / MCP 协议** 三项，从"未接触"补成"有 4 周实战、可讲可追源码"的面试卖点

---

## 一、四周训练总览

| 周 | 日期 | 主题 | 核心技术 | 关键产出 | 状态 |
|----|------|------|----------|----------|------|
| **Week 1** | 07-03~10 | API + Prompt 工程化 | OpenAI 兼容协议、主备 fallback、Function Calling、ReAct 循环、Jinja2 三层 Prompt、MD5 分桶 A/B | 4 脚本 + Prompt 模板 + 30 条订单数据 | 完成 |
| **Week 2** | 07-13~17 | RAG + Agent 概念 | Chroma 向量库、BM25+RRF+Cross-Encoder 混合检索、Agentic RAG、Todo-driven Agent | 4 脚本 + 合同/历史延期知识库 | 完成 |
| **Week 3** | 07-20~24 | MCP + LangGraph 单 Agent ⭐ | MCP stdio/FastMCP、StateGraph 条件边路由、ToolRegistry、双 MCP Server | 8 脚本 + 15 订单/10 材料/8 设备数据 | 完成 |
| **Week 4** | 07-27~31 | 多 Agent 集群 + 鉴权 🎤 | Supervisor 模式、Token Exchange(RFC 8693)、RBAC、Trace ID 审计、RAGAS、Rubric-checked RAG、ADK | Supervisor + 3 子 Agent + 鉴权审计 + 9 额外脚本 | 完成 |

四周的递进关系：Week 1（手写 Agent 原语 + 容灾底座）-> Week 2（检索增强 + Agent 自主决策）-> Week 3（协议化工具暴露 + 状态图编排）-> Week 4（多 Agent 协作 + 安全纵深 + 评估闭环）。一条线从"调通 API"走到"企业级 Agent 系统的架构与治理"。

---

## 二、训练经验（跨周提炼）

### 1. Agent 循环三段式：从手写原语到框架编排

四周贯穿同一条主线：**调 LLM(带 tools) -> 判断返回类型 -> 执行工具回传**。

- Week 1 `day2_function_calling.py:251-333` 手写 `run_agent` while 循环，`:319-323` 严格按 `tool_call_id` 配对回传
- Week 3 `langgraph_agent.py:359-418` 用 LangGraph StateGraph 替代手写循环，条件边 `should_continue` 三分支路由
- Week 4 `supervisor_agent.py:131-189` 在 Agent 之上再叠一层 Supervisor 编排多个子 Agent

**可迁移经验**：所有 Agent 框架（LangChain、MCP、ADK）都建在三段式原语之上。先手写一遍底座再换框架，能看清框架替你做了什么、藏了什么。Week 3 同时保留手写版 `langgraph_agent.py` 和 LangChain 版 `langgraph_agent_lc.py` 对照，就是这个思路。

### 2. 主备 fallback：企业级容灾最小实现

- Week 1 `day1_api_basics.py:115-144` 链式 `call_with_fallback`，`:99` `trust_env=False` 绕过系统死代理，`:206-209` 演示故意改坏主 key 自动切 DeepSeek
- Week 3 `langgraph_agent.py:62-77,294-318` Provider 列表遍历 + `_is_real_key` 过滤占位符

**可迁移经验**：OpenAI 兼容协议让所有 provider 代码层只差 `base_url` + `api_key`，一段 try/except 链就是企业级容灾的最小实现。但要诚实：这套方案只有切换、没有熔断和重试，生产要补。

### 3. Prompt 工程化：从一句话到 PromptOps

- Week 1 `day3_system_prompt.py` 把硬编码 Prompt 重构为 Jinja2 三层模板（system / scenario / user），`:46-55` 用 XML 标签隔离防注入
- `prompts/__init__.py:27` `AB_V2_RATIO=20`，`:44-52` 用 MD5 稳定分桶做 A/B 分流（防 Python `hash()` 随机化漂移）
- Week 4 拆子 Agent 后，每个 Agent Prompt 只做一件事（审核只管风控、生产只管产能），Prompt 复杂度从"一个大 Prompt 覆盖所有"降到"每个 2-3 个工具"

**可迁移经验**：Prompt 是工程化资产，不是一句话。分层 + 模板 + 版本 + A/B 分流，让模型行为可预测、可维护、可灰度。Week 1 修的"年份 bug"（`:58-71` 系统级注入当前日期根治"模型把 7 月 5 号填成 2025"）是典型:模型不是错，是缺上下文。

### 4. 检索质量分层补短：纯向量 -> 混合 -> 重排 -> Agentic -> 评估

这是一条完整的 RAG 进化链，横跨 Week 2 和 Week 4：

- Week 2 `day1_rag_basics.py` 纯向量检索 -- MiniLM 对"广州航天精工合同" top1 常召回"历史延期记录"
- Week 2 `day2_hybrid_rerank.py:247-259` 加 jieba+BM25 + `:104-134` RRF(k=60) 融合 + BGE Cross-Encoder 重排，把目标合同顶到 top1
- Week 2 `day4_agentic_rag.py` Todo-driven Agent 自主规划检索
- Week 4 `rubric_checked_rag.py:51-68,153-205` 生成后按 4 条 Rubric 逐条检查、不达标反馈修订、最多 3 轮
- Week 4 `ragas_eval.py:118-307` RAGAS 4 指标手写实现（faithfulness / answer_relevancy / context_precision / context_recall）

**可迁移经验**：
- **RRF 用排名而非分数融合** -- 向量 distance 和 BM25 score 尺度不同无法线性加权，RRF 只看排名位置统一尺度且免调参。
- **双塔召回 + Cross-Encoder 精排** 是速度/精度权衡的标准答案，能讲清为什么不能只用一步。
- **Rubric 后验拦截是幻觉 Mitigation 最硬的一道** -- 合同条款涉及钱和解约权，漏一条出事，把"不能漏"变成可检查规则比指望模型自觉可靠得多。

### 5. 工具治理演进：if/elif -> Registry -> MCP 多 Server -> 子 Agent 隔离

- Week 2 `day4_agentic_rag.py` 工具调度还是 if/elif 判断
- Week 3 `tool_registry.py` 抽出 ToolSchema + ToolRegistry，`:156-162` 执行前按 Schema 过滤多余参数防 LLM 乱传
- Week 3 `order_server.py` + `resource_server.py` 按 business 域拆成双 MCP Server，对 LLM 透明（`langgraph_agent.py:110-219` 平铺 6 工具，`server` 字段仅用于日志）
- Week 4 每个子 Agent 只持有 2-3 个工具，权限按角色隔离

**可迁移经验**：工具层治理和微服务演进同构 -- 按域拆分、注册中心、参数校验、权限隔离。新增能力从"改大 Prompt"变成"加 Server / 加子 Agent"，不动现有代码。

### 6. Agent 安全纵深：Token Exchange + RBAC + 审计

这是原"面试禁区"里完全空白、现在补上的一块：

- `token_exchange.py:74-99` Token Exchange（RFC 8693）：父 Token 换子 Token，`:86-88` 逐条校验子角色权限不超父角色，子 Token 5 分钟短时效
- `token_exchange.py:26-33` RBAC 5 角色矩阵（admin/scheduler/reviewer/operator/viewer），`:51-56` `can_access` 先查过期再查权限，`:112-121` 一键吊销
- `audit_logger.py:24,34-47` 一个请求一个 Trace ID，每条日志携带，`:50-64` `get_report` 按时间线还原调用链

**可迁移经验**：Agent 是"黑箱中的黑箱"，审计是唯一的事后追溯手段。Token Exchange 把最小权限原则落到 Agent 调用链 -- 审核 Agent 只能看客户信息不能改订单状态，生产 Agent 只能查库存设备不能看客户信用。洋葱型防御（网关 JWT -> 运行时 RBAC -> 工具二次验证）是 Agent 系统区别于普通后端的安全新课题。

### 7. 评估闭环：从肉眼判断到 RAGAS 量化

- Week 2 `day2_hybrid_rerank.py:330-334` "top1 改进"靠 demo 打印肉眼判断，注释反复提 RAGAS/Recall 但未实现
- Week 4 `ragas_eval.py` 手写 RAGAS 4 指标（不依赖 ragas 库，因库版本/依赖常出问题），用 5 个合同 Q&A 作 ground truth

**可迁移经验**：检索质量必须量化评测，不能靠看输出。Week 2 的"无评估"是真实教训，Week 4 补上 RAGAS 是闭环。手写而非依赖库，是为了理解原理能定制 -- 这条"先理解再选用"的思路和 Week 3 手写 LangGraph 再用 ToolNode 一致。

### 8. 载体锁定：制造业排程排产

四周 demo 载体始终是制造业排程排产，不跨行业：
- 数据层：3D 打印/CNC 订单（交期/当前环节/状态）、材料库存（安全库存/采购周期）、设备（类型/负载/预计空闲）、客户（等级/信用分/延期率）
- 业务规则：System Prompt 内嵌排产优先级（交期紧 > 客户等级 > 信用分 > 延期率）、合同延期赔付（0.5%/日）、航天件全检+报废、加急绿色通道
- 端到端场景：Week 3 Agent 自主跨 Server 调用 8 次工具完成"今日优先排产"综合排序；Week 4 Supervisor 编排审核+生产双 Agent 评估订单风险与产能可行性

能力（混合检索 / Agent 编排 / 主备容灾 / 鉴权审计）可迁移到任何私有知识库场景，但 demo 载体锁定制造业 -- 这是有意为之，避免"样样都讲样样不深"。

---

## 三、面试亮点

### Week 1（API + Prompt 工程化）

1. **主备 fallback 链 + 故意改坏 key 验证切换**（`day1_api_basics.py:115-144` 链式 fallback，`:99` trust_env=False 绕死代理，`:206-209` 演示改坏主 key 自动切 DeepSeek）-- 企业级 Agent 容灾最小实现，能讲清五种容灾模式与自身缺熔断/重试
2. **手写 ReAct Agent 循环跑通订单查询闭环**（`day2_function_calling.py:251-333`，`:319-323` tool_call_id 回传协议）-- 3 个演示 query 平均 2-3 轮完成，证明理解 Agent 原语而非调库
3. **三层 Prompt + Jinja2 + MD5 稳定 A/B 分流**（`day3_system_prompt.py:46-55` XML 隔离防注入，`prompts/__init__.py:27,44-52` MD5 分桶防 hash 漂移）-- PromptOps 落地，v2_cot 含 `<thinking>` 引导
4. **修复 Day2 年份 bug 的工程化思路**（`day3_system_prompt.py:58-71` 系统级注入当前日期）-- 从"模型把 7 月 5 号填成 2025"定位到"缺日期上下文"，用 system.jinja 根治

### Week 2（RAG + Agent）

1. **混合检索四步管线 + 实测对比**（`day2_hybrid_rerank.py:247-259` retrieve_hybrid，`:104-134` RRF k=60，`:292-334` demo 对比 top1 改进）-- 向量+BM25+RRF+Cross-Encoder 全链路手写，能讲清双塔 vs Cross-Encoder 速度/精度权衡
2. **Reranker 离线加载策略**（`day2_hybrid_rerank.py:151-198`，`:162-171` patch HF_HUB_OFFLINE constants）-- huggingface_hub import 时固化常量，运行时设 env 无效，必须直接 patch，真实踩坑后的 production 细节
3. **Todo-driven Agentic RAG 从 pipeline 到 Agent 的跃迁**（`day4_agentic_rag.py:74-106` System Prompt，`:281` MAX_TURNS=8，`:301-312` JSONDecodeError 容错回传重试）-- Agent 自主规划 2-4 项 -> 逐项检索 -> submit
4. **5 工具三合一 + 参数白名单防御**（`week2_agentic_rag_agent.py:258-259` valid_keys 过滤防模型传多余字段，`:430` MAX_TURNS=10）-- Week 1 订单查询 + Day 2 混合检索 + Day 4 Agent 骨架总集成

### Week 3（MCP + LangGraph 单 Agent）

1. **LangGraph StateGraph 四节点 + 条件边路由**（`langgraph_agent.py:530-558` build_graph 六步 API，条件边 `should_continue` 三分支：安全阀/工具结果/直接回答）
2. **select_and_execute 实现 ReAct 闭环**（`langgraph_agent.py:359-418` 决策->执行->注入，支持 Parallel Tool Calling，参数解析容错，消息严格遵循 OpenAI 标准 assistant+tool 成对、tool_call_id 配对）
3. **双 MCP Server 按域拆分 + 对 LLM 透明**（`langgraph_agent.py:110-219` TOOLS 平铺 6 工具，`server` 字段仅日志分组）-- 微服务思维迁移到 Agent 工具层
4. **Provider 链式 fallback**（`langgraph_agent.py:62-77,294-318` 遍历 PROVIDERS，`_is_real_key` 过滤占位符，`trust_env=False`）
5. **generate_answer 兜底容错**（`langgraph_agent.py:505-509` LLM 失败返回原始 tool_results，Agent 不崩）
6. **LangChain 升级版对照实现**（`langgraph_agent_lc.py:186-189` add_messages reducer 替代手动 append，`:281` ToolNode 替代手写执行，`:294` MemorySaver checkpointer 跨调用记忆，`:307-315` create_react_agent 一行版对照）-- 手写版 vs 标准版并列，证明知其然且知其所以然
7. **ToolRegistry 参数白名单过滤**（`tool_registry.py:156-162` 执行前按 Schema properties 过滤多余参数）
8. **MCP stdio 协议验证**（`test_mcp_client.py:41-116` 完整四步：启动子进程 -> initialize -> list_tools -> call_tool×4）

### Week 4（多 Agent + 鉴权）

1. **Supervisor 五步编排**（`supervisor_agent.py:131-189` route -> setup_auth -> dispatch_review+dispatch_production -> aggregate -> audit_report，鉴权与调度交织）
2. **Token Exchange 权限收缩**（`token_exchange.py:74-99` 三步检查：父 Token 有效 -> 子权限 ≤ 父权限 -> 签发短时效子 Token，`:86-88` 逐条校验）
3. **RBAC 5 角色权限矩阵**（`token_exchange.py:26-33` 五角色各持不同工具集，`:51-56` can_access 先查过期再查权限）
4. **STS 紧急响应**（`token_exchange.py:112-121` revoke 单个 + revoke_all 一键吊销，对应 Token 泄漏/Agent 异常/用户降权）
5. **AuditLogger Trace ID 全链路**（`audit_logger.py:24,34-47` trace_id 贯穿，`:50-64` get_report 按时间线还原调用链）
6. **Rubric-checked RAG 生成-评分-修订循环**（`rubric_checked_rag.py:51-68` 4 条 Rubric，`:153-205` 最多 3 轮，grader 用第二个 LLM 逐条检查）-- 后验拦截幻觉
7. **RAGAS 4 指标手写实现**（`ragas_eval.py:118-162` faithfulness 拆原子陈述逐条核查，`:170-212` answer_relevancy 反推问题语义匹配，`:221-261` context_precision Average Precision，`:268-307` context_recall 标准答案拆陈述检索覆盖）
8. **ADK sub_agents 自动委托**（`adk_coordinator_autoflow.py:119-130` `Agent(sub_agents=[...])` 声明父子，ADK 自动注入 transfer_to_agent 工具，模型按 instruction 自行委托）-- 对照 LangGraph Supervisor，理解不同框架的多 Agent 范式

---

## 四、缺点与教训

### Week 1

1. **无任何测试** -- Week 1/2 全目录无 test 文件，`query_orders` 筛选/排序全靠 demo 跑通验证。**教训**：训练代码重演示轻回归，生产必须补单测。
2. **交期用字符串比较**（`day2_function_calling.py:165-168` `o["交期"] > due_before`）-- 依赖 YYYY-MM-DD 恰好可字典序排序，换格式即崩。**教训**：日期就该转 date 比，别侥幸。
3. **PROVIDERS 在三个文件各 copy 一份**（day1_api_basics / day2_function_calling / day1_rag_basics 重复定义）-- 改配置要改三处。**教训**：训练代码"开箱即跑"优先导致复用差。
4. **JSON Schema 约束是 Prompt 级非 strict mode**（`day3_system_prompt.py:154-176,206` 注释自认"非 100% 可靠"）-- **教训**：生产用 `response_format={type:"json_object"}` 强约束，Prompt 级只能 demo。

### Week 2

1. **固定字符分块切在词中间**（`day1_rag_basics.py:141-166` 中文 500 字硬切）-- Recall 注释自承 0.67 -> 0.91 升级空间。**教训**：分块是 RAG 第一道坎，教学版和生产版差距大。
2. **reranker 代理地址硬编码且不一致**（`day2_hybrid_rerank.py:148` 写 7890，注释却说 3450）-- 环境耦合死。**教训**：代理应走 env 配置，别写死。
3. **模块级全局状态非线程安全**（`day4_agentic_rag.py:46-49`、`week2_agentic_rag_agent.py:62-65` `_BM25/_RERANKER` 全局）-- 并发会崩。**教训**：demo 可，生产要封装。
4. **无 RAG 评估**（`day2_hybrid_rerank.py:330-334` 靠肉眼判断）-- **教训**：检索质量必须量化评测，这条教训直接驱动了 Week 4 补 RAGAS。

### Week 3

1. **analyze_intent / evaluate_results 是空占位节点**（`langgraph_agent.py:328-335,428-430` 只打印/pass）-- **教训**：LangGraph 节点是"插槽"，先占位再填是合理教学策略，但生产必须补实现。
2. **无 Reducer，手动 mutate state**（`langgraph_agent.py:277-281` 裸 `messages: list`，节点里 append 有副作用）-- 非纯函数，并行节点有风险。**教训**：`langgraph_agent_lc.py` 已用 add_messages 修正，但原版暴露了"手写 vs 标准用法"的差距。
3. **无 Checkpointer，无记忆**（`langgraph_agent.py:558` compile() 未传 checkpointer）-- 每次 run 全新状态。**教训**：走向生产的第一道缺口。
4. **Demo 路径牺牲了真 MCP 进程隔离**（`langgraph_agent.py:44-48` 直接 import 函数而非 stdio 调用）-- **教训**：培训 Demo 优先稳定性，但要讲清"保留了什么、牺牲了什么、怎么补回"。
5. **MCP 只用了 Tools 原语**（order_server / resource_server 全是 `@mcp.tool()`，无 resource/prompt 原语）-- **教训**：只读数据用 Resources 更语义化，教学聚焦 Tools 可理解。

### Week 4

1. **review_order 未实际调 LLM 做风险评级**（`review_agent.py:91-99` 只构建上下文返回 `status:"pending_review"`）-- SYSTEM_PROMPT 定义了高/中/低危标准但未执行。**教训**：Prompt 定义了规则但代码没接上，典型"设计先行实现滞后"。
2. **production_agent 忽略 order_ids 参数**（`production_agent.py:41-51` 接收 order_ids 但只查全局库存设备，未按订单关联）-- **教训**：参数传了但没用，接口设计与实现脱节。
3. **Supervisor 硬编码 sample_orders**（`supervisor_agent.py:148` 写死 `["ORD001","ORD003","ORD005"]`）-- **教训**：Demo 用硬编码可理解，但要标注"生产应改动态查询"。
4. **AgentRouter 仅关键词匹配**（`agent_router.py:27-31` 纯关键词，不支持模糊意图）-- **教训**：简单确定零成本，但复杂场景必须升级 LLM 路由（代码注释已标明三种路由方式）。
5. **Token 存储纯内存**（`token_exchange.py:63` `_issued_tokens` 是内存 dict）-- 进程重启即丢。**教训**：生产需 Redis/DB 持久化。

---

## 五、面试讲述策略

1. **讲递进，不讲调库**：手写 ReAct（Week 1）-> LangGraph StateGraph（Week 3）-> Supervisor 多 Agent（Week 4），同一条三段式原语的三个层次。证明不是"调通了一个框架"，而是理解了 Agent 编排的本质。Week 3 手写版与 LangChain 版并列对照，是"知其然且知其所以然"的直接证据。

2. **讲填禁区，讲学习路径**：原简历诚实标注"Agent 开发未接触 / LangGraph 未实战 / MCP 未落地"。4 周训练把这三项从零补到有架构、有鉴权、有评估。面试时主动讲"我意识到这是盲区，所以用 4 周做了系统训练" -- 这比"我早就会"更有说服力，体现学习能力和工程自觉。

3. **讲制造业载体，讲能力迁移**：demo 锁定 3D 打印/CNC 排程排产（订单/库存/设备/客户），不跨行业。能力（混合检索、Agent 编排、主备容灾、鉴权审计）可迁移到任何私有知识库场景。这样讲既体现"有真实业务落地"而非玩具，又体现"懂抽象、能迁移"。

4. **讲教训，讲诚实**：空占位节点、无 checkpointer、内存 Token、硬编码 sample_orders、review_order 未接 LLM -- 训练代码的粗糙点恰恰是面试讲"教训"的素材。讲"哪些做了、哪些没做、为什么、怎么补"比"全做了"可信得多。这条策略与 `vibe-coding经验与面试亮点.md` 一致。

5. **讲安全纵深，讲新课题**：Token Exchange（RFC 8693）+ RBAC + Trace ID 审计是 Agent 系统区别于普通后端的安全新课题。Agent 是"黑箱中的黑箱"，权限收缩链 + 不可否认审计是落地企业级 Agent 必须解决的。这块多数候选人没想过，是差异化优势。

6. **讲评估闭环，讲不依赖黑盒**：从 Week 2 "肉眼判断检索质量"到 Week 4 "RAGAS 手写 4 指标 + Rubric 后验拦截"，体现"不盲目依赖第三方库、理解原理才能定制"的工程观。RAGAS 手写而非调库，和 Week 3 手写 LangGraph 再用 ToolNode，是同一条方法论的两次应用。

**主动引导方向**（把面试官往这引）：
- Agent 工程化全链路（原语 -> 框架 -> 多 Agent -> 安全 -> 评估）-- 4 周实战有源码
- 制造业排程排产落地（订单/库存/设备/客户的真实 Agent 决策）-- 有业务载体
- 学习能力闭环（识别盲区 -> 系统训练 -> 诚实复盘）-- 有成长弧线

**仍要回避**（训练未覆盖，被问到坦诚说"学习中"）：
- 大模型微调/训练（应用层，不涉及）
- K8s/Service Mesh（Docker 够用）
- ADK Vertex AI Search / OpenAI Deep Research（`adk_vsearch_agent.py`、`openai_deep_research.py` 只学方法论，本机不可跑，不作卖点）

---

## 附：关键证据文件索引

### Week 1
- `projects/agent-training/scripts/week1/day1_api_basics.py` - 主备 fallback 链 + Provider 注册表
- `projects/agent-training/scripts/week1/day2_function_calling.py` - 手写 ReAct Agent 循环
- `projects/agent-training/scripts/week1/day3_system_prompt.py` - 三层 Prompt + A/B 分流
- `projects/agent-training/scripts/week1/day4_principles.py` - Token/Context/Temperature 物理量
- `projects/agent-training/scripts/week1/prompts/` - Jinja2 模板（system/scenario_v1/scenario_v2_cot）
- `projects/agent-training/scripts/week1/data/orders.csv` - 30 条 3D 打印/CNC 订单

### Week 2
- `projects/agent-training/scripts/week2/day1_rag_basics.py` - Chroma 向量库基线
- `projects/agent-training/scripts/week2/day2_hybrid_rerank.py` - 混合检索 + RRF + Cross-Encoder 重排
- `projects/agent-training/scripts/week2/day4_agentic_rag.py` - Todo-driven Agentic RAG
- `projects/agent-training/scripts/week2/week2_agentic_rag_agent.py` - 5 工具三合一总集成
- `projects/agent-training/scripts/week2/data/` - 合同/历史延期记录/客户等级

### Week 3
- `projects/agent-training/scripts/week3/langgraph_agent.py` - LangGraph StateGraph 四节点编排（手写版）
- `projects/agent-training/scripts/week3/langgraph_agent_lc.py` - LangChain 升级版对照（add_messages/ToolNode/MemorySaver）
- `projects/agent-training/scripts/week3/order_server.py` + `resource_server.py` - 双 MCP Server（订单域/资源域）
- `projects/agent-training/scripts/week3/tool_registry.py` - ToolSchema + ToolRegistry 注册中心
- `projects/agent-training/scripts/week3/test_mcp_client.py` - MCP stdio 协议验证
- `projects/agent-training/scripts/week3/shared_data.py` + `data/` - 15 订单/10 材料/8 设备/5 客户

### Week 4
- `projects/agent-training/scripts/week4/supervisor_agent.py` - Supervisor 五步编排
- `projects/agent-training/scripts/week4/agents/agent_router.py` - 意图识别路由
- `projects/agent-training/scripts/week4/agents/review_agent.py` + `production_agent.py` - 审核/生产双子 Agent
- `projects/agent-training/scripts/week4/auth/token_exchange.py` - Token Exchange(RFC 8693) + RBAC 5 角色
- `projects/agent-training/scripts/week4/auth/audit_logger.py` - Trace ID 全链路审计
- `projects/agent-training/scripts/week4/ragas_eval.py` - RAGAS 4 指标手写实现
- `projects/agent-training/scripts/week4/rubric_checked_rag.py` - Rubric 生成-评分-修订循环
- `projects/agent-training/scripts/week4/adk_coordinator_autoflow.py` - Google ADK sub_agents 自动委托
- `projects/agent-training/scripts/week4/coordinator_router_branch.py` - LCEL RunnableBranch 路由
- `projects/agent-training/scripts/week4/tool_calling_agent_executor.py` - LangChain 1.x create_agent
