# Week 5 — 7 周路线 vs Demo 差距全景图

> 基于 7 周训练路线，逐一对照 demo 当前代码，标注完成度、差距、严重度和修复建议。
> 分析时间：2026-08-07 | demo commit: ab1b620

---

## 一、Week 1 — API + Prompt 工程化（对照 demo）

### 1.1 路线要求

| 日期 | 要求 | 产出 |
|------|------|------|
| Day 1 | 大模型谱系 + API 入门，跑通第一个 API 调用 | `day1_api_basics.py` |
| Day 2 | Function Calling / Tool Use 闭环 | `day2_function_calling.py` |
| Day 3 | System Prompt 三层架构 + JSON Schema | `day3_system_prompt.py` |
| Day 4 | Token/Context/Temperature 原理 | 笔记消化 |

### 1.2 对照 demo

| 路线要求 | demo 现状 | 完成度 | 备注 |
|---------|----------|--------|------|
| API 调用 | `core/llm_client.py` — 统一 `call_llm(messages, tools)` 签名 | ✅ 完成并升级 | 从词条 call 升级到主备 fallback + 连接池 |
| 主备 fallback | 遍历 PROVIDERS，第一个成功返回，失败降级 | ✅ | 有 fallback，无熔断/重试（路线未要求） |
| Function Calling 闭环 | `graph/single_agent_graph.py:39-83` — select_and_execute 决策→执行→注入 | ✅ | 从手写 while 升级到 LangGraph 状态图 |
| 三层 Prompt | `prompts/system_prompts.py` 集中管理各 Agent Prompt | ✅ | 从 Jinja2 模板升级到模块化 Prompt 文件 |
| JSON Schema 约束 | `tools/registry.py` — ToolSchema 定义 name/description/parameters | ✅ | 但 Prompt 级非 strict mode（路线遗留） |
| A/B 分流 | 无 | ⬜ 缺失 | 仅 week1 脚本有 MD5 分桶，demo 未集成 |

### 1.3 剩余差距

| # | 差距 | 严重度 | 修复建议 |
|---|------|--------|---------|
| W1.1 | Prompt 版本管理 — `system_prompts.py` 硬编码，无 A/B 测试基础 | 🟡 | 按版本组织 `prompts/v1/`、`prompts/v2/`，配置化加载 |
| W1.2 | JSON Schema 约束为 Prompt 级，非 `response_format` strict mode | 🟡 | LLM 输出结构用 strict mode 强约束 |

---

## 二、Week 2 — RAG + Agent 概念（对照 demo）

### 2.1 路线要求

| 日期 | 要求 | 产出 |
|------|------|------|
| Day 1 | RAG 基础 + Embedding + 分块 + 向量库 | `day1_rag_basics.py` |
| Day 2 | 混合检索 + BM25 + 重排序 | `day2_hybrid_rerank.py` |
| Day 3 | Agent 概念：ReAct、工具调用循环、记忆三层 | 笔记 |
| Day 4 | Anthropic Building Effective Agents | 读后感 |
| Day 5 | Week 1-2 串联 Demo | `week2_agentic_rag_agent.py` |

### 2.2 对照 demo

| 路线要求 | demo 现状 | 完成度 | 备注 |
|---------|----------|--------|------|
| RAG 基础 | `rag/knowledge_base.py` — 文档加载/分块/Chroma 向量库 | ✅ | 与路线一致 |
| 混合检索 | `rag/retriever.py` — BM25(jieba)+向量+RRF+Cross-Encoder 重排 | ✅ | 四步混合检索完整 |
| Agent 概念 | `graph/single_agent_graph.py` — ReAct 循环（分析→执行→评估→生成） | ✅ | 从手写 while 升级到 LangGraph |
| Agentic RAG | `agents/single_agent.py` — Agent 通过 search_knowledge_base 工具自主检索 | ✅ | Todo-driven 升级为 tool-driven |
| 重排器离线防坑 | `rag/retriever.py` — patch HF constants | ✅ | 生产细节到位 |

### 2.3 剩余差距

| # | 差距 | 严重度 | 修复建议 |
|---|------|--------|---------|
| W2.1 | 固定字符分块切在词中间（500 字硬切） | 🟡 | 按段落/语义分块 + 重叠窗口 |
| W2.2 | RAG 无法处理结构化筛选（"交期<7/30 AND 等级=A AND 工艺=3D打印"） | 🔴 | 引入 NL2SQL 或结构化查询工具 |
| W2.3 | 向量库本地 Chroma，单租户，无增量索引 | 🟡 | 独立向量库服务 + 增量入库 pipeline |
| W2.4 | MiniLM 中文判别力一般 | 🟡 | 换 bge-large-zh 或通过 reranker 弥补 |
| W2.5 | 无 RAG 评估脚本集成 | 🔴 | 虽 week4 scripts 有 RAGAS，但 demo 未接入 |

---

## 三、Week 3 — MCP + LangGraph 单 Agent（对照 demo）

### 3.1 路线要求

| 日期 | 要求 | 产出 |
|------|------|------|
| Day 1 | 工具体系设计：注册发现、Schema 规范、粒度原则 | `week3_mcp_agent/` |
| Day 2 | MCP Server 开发（Python SDK） | order_server + resource_server |
| Day 3 | MCP Client + 多 Server 连接管理 | test_mcp_client.py |
| Day 4 | LangGraph StateGraph 重构 Agent 循环 | langgraph_agent.py |
| Day 5 | 串联 + 回顾 | 完整 Demo |

### 3.2 对照 demo

| 路线要求 | demo 现状 | 完成度 | 备注 |
|---------|----------|--------|------|
| 工具注册中心 | `tools/registry.py` — ToolRegistry O(1) 查找 + 参数白名单 | ✅ 完成并升级 | 从 if/elif 进化到注册中心 + RBAC 集成 |
| MCP Server | `tools/mcp_servers.py` — FastMCP server 构建 | 🔶 展示级 | 仅展示 MCP 协议概念，运行时未真隔离 |
| MCP 多 Server | 无真 stdio/SSE 通信 | ⬜ 未真实现 | demo 走函数调用非协议调用 |
| LangGraph 状态图 | `graph/single_agent_graph.py` — StateGraph + 条件边 | ✅ | 4 节点 + 条件边 + 5 轮安全阀 |
| 双 MCP Server 按域拆分 | ToolRegistry 中 server 字段区分 order_server / resource_server / rag_server | ✅ 概念有 | 概念到位但非真进程隔离 |

### 3.3 剩余差距

| # | 差距 | 严重度 | 修复建议 |
|---|------|--------|---------|
| W3.1 | **MCP 真进程隔离未落地** — 工具与 Agent 同进程，故障耦合 | 🔴 | 工具拆 MCP 子进程（stdio/SSE），Agent 通过协议调用 |
| W3.2 | `analyze_intent` 节点是空占位（仅 print） | 🟡 | 实现意图分类器路由（单 Agent 内按问题类型分流） |
| W3.3 | `evaluate_results` 节点是 noop（直接 pass） | 🔴 | 实现 todo 列表 + 每步校验（工具结果非空、格式正确） |
| W3.4 | 无 Reducer，手动 mutate state（裸 `messages: list`） | 🟡 | 并行节点有风险，加 add_messages reducer |
| W3.5 | StateGraph 编译未用 interrupt_before（无 human-in-the-loop） | 🟡 | 长任务加 interrupt_before 等人工确认 |

---

## 四、Week 4 — 多 Agent 集群 + 鉴权（对照 demo）

### 4.1 路线要求

| 日期 | 要求 | 产出 |
|------|------|------|
| Day 1 | 多 Agent 协作模式：Supervisor/Manager-Worker | supervisor_agent.py |
| Day 2 | 子 Agent 设计 + 路由 + 汇总 | review_agent + production_agent + router |
| Day 3 | Token Exchange（RFC 8693）+ RBAC + 洋葱型防御 | auth/token_exchange.py |
| Day 4 | 审计日志 + 联调 | auth/audit_logger.py |
| Day 5 | 多租户隔离 + 完整联调 | 全部串联 |

### 4.2 对照 demo

| 路线要求 | demo 现状 | 完成度 | 备注 |
|---------|----------|--------|------|
| Supervisor 模式 | `agents/supervisor.py` — 五步编排（路由→鉴权→分发→汇总→审计） | ✅ | 结构完整 |
| 子 Agent 设计 | `agents/review_agent.py` + `agents/production_agent.py` | ✅ | 各持令牌 + LLM 驱动 |
| 意图路由 | `agents/router.py` — 关键词路由 | 🔶 | 关键词匹配非 LLM 路由 |
| Token Exchange | `auth/token_exchange.py` — RFC 8693 + 权限收缩 + 短时效 | ✅ | 逻辑完整 + SQLite 持久化 |
| RBAC 权限矩阵 | `auth/token_exchange.py` — 5 角色 + `auth/guard.py` 工具层校验 | ✅ | 洋葱三层 |
| 审计日志 | `auth/audit_logger.py` — trace_id 贯穿 + JSONL 持久化 | ✅ | 完整 |
| 多租户隔离 | 无 | ⬜ 缺失 | 仅有 RBAC 角色隔离，无租户维度 |

### 4.3 剩余差距

| # | 差距 | 严重度 | 修复建议 |
|---|------|--------|---------|
| W4.1 | **AgentRouter 仅关键词匹配** — 不支持模糊意图 | 🟡 | 加 LLM 路由（用小模型做意图分类） |
| W4.2 | **Supervisor 硬编码 sample_orders** — `["ORD001","ORD003","ORD005"]` | 🟡 | 改为从订单查询动态获取 |
| W4.3 | Supervisor 编排是硬编码 if/else（非声明式 YAML/DSL） | 🟡 | 声明式工作流定义 |
| W4.4 | 子 Agent 角色未和真实制造业岗位对齐 | 🟡 | 对齐"排产计划员""车间调度""质检员" |
| W4.5 | 无多租户隔离 — RBAC 有角色但无租户维度 | 🔴 | 加 tenant_id 维度，Token 携租户信息 |
| W4.6 | 单 Agent 模式 `token=None` 完全绕过鉴权 | 🟡 | 加 `FORCE_AUTH=True` 环境变量 |

---

## 五、Week 5 — 可观测 + 业务匹配（对照 demo）

### 5.1 路线要求

| 日期 | 要求 | 产出 |
|------|------|------|
| Day 1 | 全链路追踪（Langfuse + OTel）、五大指标、Span 三层 | week5_production/ |
| Day 2 | 成本监控 + Token 用量追踪 + 三级告警 | 成本仪表盘 |
| Day 3 | 业务匹配度判断 + Agent 评估体系 | 评估脚本 |
| Day 4 | 综合实战：给 week4 Demo 接可观测 + 评估 | 完整系统 |
| Day 5 | 15min Demo 演示 | — |

### 5.2 对照 demo

| 路线要求 | demo 现状 | 完成度 | 备注 |
|---------|----------|--------|------|
| 全链路追踪 | `observability/tracer.py` + `exporter.py` — OTel 同构 + 可插拔 backend | ✅ 完成 | 自研实现，非 Langfuse（功能等价，缺看板 UI） |
| Span 三层设计 | Span(name/duration/attrs) + tracer.span + tracer.record | ✅ | 结构设计完整 |
| 成本监控 | `observability/cost.py` — CostTracker + 定价表 + 预算熔断 | ✅ | 三级告警（预警→熔断）实现 |
| 业务匹配度 | 框架理解完成，文档有分析 | 🔶 理论 | 有框架（Prompt/Workflow/Agent 边界），缺 ROI 计算工具 |
| Agent 评估体系 | `docs/courses/Agent评测漫谈*.md` 课程笔记 + 缺陷分析文档 | 🔶 理论 | 缺可运行评估脚本（RAGAS 未接入 demo） |
| Langfuse 集成 | 无 | ⬜ 缺失 | 路线指定 Langfuse，实际走了自研 Tracer |
| 成本监控仪表盘 | `cost_tracker.format_text()` 文本摘要 | 🔶 CLI级 | 无 UI 看板 |
| 15min Demo 演示 | `--demo` 预设场景可跑 | 🔶 | 未录演示，可用 `--demo` 替代 |

### 5.3 剩余差距

| # | 差距 | 严重度 | 修复建议 |
|---|------|--------|---------|
| W5.1 | **无 Langfuse 集成**（路线指定） | 🟡 | 路线原定，当前自研替代功能等价但缺 UI |
| W5.2 | **成本按会话计费非按用户/租户** | 🟡 | CostTracker 加 user_id 维度 |
| W5.3 | **无 Agent 评估脚本**（RAGAS/自定义指标） | 🔴 | 接入评测脚本，至少 RAGAS 4 指标 |
| W5.4 | 缺自动告警（成本超阈值/错误率飙升不通知） | 🟡 | webhook/邮件告警 |
| W5.5 | 无采样（高 QPS 全量导出性能差） | 🟡 | 按 trace_id 采样 |
| W5.6 | LangGraph 未用 `config.callbacks` 自动埋点 | 🟡 | 免去手动 with tracer.span() |
| W5.7 | 无 SLA 定义（"排产 < 3s""准确率 > 95%"） | 🟡 | 定义 SLI/SLO/SLA |
| W5.8 | 无异步导出 | 🟢 | 控制台同步 flush 足够 demo |

---

## 六、Week 6 — 微调 + 推理优化（未开始）

### 6.1 路线要求

| 日期 | 要求 | 覆盖知识块 |
|------|------|-----------|
| Day 1 | 微调决策框架：Prompt vs RAG vs Fine-tuning 边界 | ⑫ |
| Day 2 | LoRA/QLoRA 实战（PEFT + Qwen2.5-7B） | ⑫ |
| Day 3 | DPO 偏好对齐（DPO vs RLHF 选型） | ⑫ |
| Day 4 | 数据工程（IFD/LESS 筛选）+ 推理优化（vLLM + AWQ） | ⑬⑭ |
| Day 5 | 消化 + 补代码 | — |

### 6.2 demo 当前状态（Week 6 前置差距）

| 知识块 | demo 现状 | 说明 |
|--------|----------|------|
| ⑫ 微调 | 无 | 路线定位"应用层开发者视角"，demo 不需要微调能力 |
| ⑬ 数据工程 | 无 | CSV 静态数据，无数据筛选/增强/评估 |
| ⑭ 推理优化 | 无 | 用 API 调外部 models，不涉及本地推理部署 |

### 6.3 对 demo 的影响

Week 6 知识对 demo 的实际影响较小（因为 demo 是应用层 Agent，走 API 调模型）。**但对面试的影响大** — 需要能讲清"什么场景该微调"的决策框架。

| 面试点 | 需要掌握的程度 |
|--------|--------------|
| Prompt vs RAG vs Fine-tuning 边界线 | 能画决策树，能举 demo 中的例子 |
| LoRA/QLoRA 能跑通 | 至少有一个 Notebook 产出 |
| vLLM + AWQ 概念 | 知道什么时候用，不要求部署 |
| IFD/LESS 数据筛选 | 知道"数据质量 > 数量"原则 |

---

## 七、Week 7 — 多模态 Agent（未开始）

### 7.1 路线要求

| 日期 | 要求 |
|------|------|
| Day 1 | 视觉 Agent（GPT-4o/Claude Vision、截图理解、PDF 解析） |
| Day 2 | 语音 Agent（Whisper ASR + TTS，P99 < 2s） |
| Day 3 | 视频理解 + 统一多模态路由器 |
| Day 4 | 接入现有 Demo（保持架构整洁） |
| Day 5 | 7 周回顾 + 30min 技术分享 |

### 7.2 demo 当前状态（Week 7 前置差距）

| 能力 | demo 现状 | 说明 |
|------|----------|------|
| 视觉 Agent | 无 | demo 无图像/PDF/扫描件处理 |
| 语音 Agent | 无 | demo 无 ASR/TTS |
| 多模态路由器 | 无 | demo 只有文本路由器 |

**潜在应用场景**（如果能做）：
- 上传工单截图/扫码件 → OCR 识别 → Agent 录入订单
- 语音"今天先做哪些订单？" → ASR → Agent 回答
- PDF 合同上传 → 视觉理解 → RAG 入库

---

## 八、综合差距矩阵（按知识块 × 维度）

按路线 15 个知识块，一一标注 demo 的实现状态：

| 知识块 | Week | 覆盖度 | 实现方式 | 关键缺口 |
|--------|------|--------|---------|---------|
| ① 大模型 API | 1 | 高 | `core/llm_client.py` — 统一 call_llm + 主备 fallback + 连接池 | 无熔断/重试/速率限制 |
| ② Agent 核心机制 | 2 | 高 | `graph/` + `agents/` — ReAct → LangGraph → Supervisor 三级演进 | 评估节点 noop |
| ③ Tools/Skills | 3 | 高 | `tools/registry.py` — O(1) 注册中心 + 参数白名单 + RBAC | 无工具执行超时/重试/沙箱 |
| ④ MCP 协议 | 3 | 中 | `tools/mcp_servers.py` — FastMCP 展示 | 未真进程隔离，仅概念 |
| ⑤ RAG + 向量库 | 2 | 高 | `rag/retriever.py` — 混合检索四步管道 | 无结构化筛选/NL2SQL、无增量索引 |
| ⑥ LangChain/LangGraph | 3 | 高 | `graph/single_agent_graph.py` — StateGraph + 条件边 + checkpointer | interrupt_before 未用 |
| ⑦ 提示词工程 | 1 | 高 | `prompts/system_prompts.py` | 无版本管理/A/B 测试 |
| ⑧ Agent 集群 | 4 | 高 | `agents/supervisor.py` + 双子 Agent | 硬编码路由/编排、无动态分解 |
| ⑨ 鉴权体系 | 4 | 高 | `auth/` — STS+RBAC+审计完整 | 无 OAuth2/JWT、无多租户 |
| ⑩ 可观测性 | 5 | 高 | `observability/` — tracer + exporter + cost | 无 Langfuse/告警/采样/异步导出 |
| ⑪ 业务匹配 | 5 | 中 | 文档分析 + 框架理解 | 无评估脚本/ROI/SLA |
| ⑫ 模型微调 | 6 | ⬜ | 未开始 | 需一个 QLoRA Notebook |
| ⑬ 数据工程 | 6 | ⬜ | CSV 静态数据 | 无数据筛选/增强 |
| ⑭ 推理优化 | 6 | ⬜ | 走 API，不涉及 | 概念级 |
| ⑮ 多模态 Agent | 7 | ⬜ | 未开始 | 视觉/语音全缺 |

---

## 九、按严重度排序的修复清单

### 🔴 红色（生产级阻断，面试被深挖高风险）

| # | 缺陷 | 知识块 | 所属 Week | 面试风险 |
|---|------|--------|----------|---------|
| R1 | **工具执行无沙箱与重试** — `registry.execute` 无超时/重试/隔离 | ③ Tools | Week 6 应补 | 高 — 面试官问"工具挂了怎么办？" |
| R2 | **输出护栏（guardrails）缺失** — 无 JSON 校验/越权过滤/有害内容过滤 | ② Agent ⑦ Prompt | 跨 Week | 最高 — Agent 系统最大的安全隐患 |
| R3 | **步骤校验为 noop** — `evaluate_results` 节点不校验，模型可能 hallucinate 工具结果 | ② Agent ⑥ LangGraph | Week 3 | 高 — "Agent 怎么做质量保障？" |
| R4 | **上下文无限增长** — messages 列表无限增长，长轮无截断/压缩 | ② Agent | Week 5 | 高 — "长对话成本怎么控制？" |
| R5 | **MCP 真进程隔离未落地** — 工具同进程，故障耦合 | ④ MCP | Week 6 应补 | 中 — "工具怎么隔离的？" |
| R6 | **无 Agent 评估脚本** — RAGAS 有代码但未接入 demo | ⑪ 业务匹配 | Week 5 | 高 — "怎么评估 Agent 好不好？" |
| R7 | **RAG 无结构化筛选** — "交期<7/30 AND 等级=A AND 工艺=3D打印"无法直接回答 | ⑤ RAG | Week 6 应补 | 中 — 实际业务场景中最常见的问题类型 |
| R8 | **无多租户隔离** — RBAC 有角色无租户维度 | ⑨ 鉴权 | Week 4 | 中 — "多租户怎么做？" |

### 🟡 黄色（重要优化，面试被追问可能暴露）

| # | 缺陷 | 所属 Week | 面试风险 |
|---|------|----------|---------|
| Y1 | Supervisor 硬编码编排（非声明式）+ 硬编码 sample_orders | Week 4 | 中 |
| Y2 | AgentRouter 仅关键词匹配（非 LLM 路由） | Week 4 | 中 |
| Y3 | 单 Agent 模式 `token=None` 绕过鉴权 | Week 5 | 中 |
| Y4 | Prompt 无版本管理/A/B 测试 | Week 1 | 低 |
| Y5 | 成本按会话计费非按用户 | Week 5 | 低 |
| Y6 | 无自动告警（成本/错误/webhook） | Week 5 | 中 |
| Y7 | 无 Langfuse 集成（走自研 Tracer） | Week 5 | 低 |
| Y8 | 无 human-in-the-loop（interrupt_before） | Week 3 | 中 |
| Y9 | MiniLM 中文向量弱 | Week 2 | 低 |
| Y10 | 固定字符分块（500 字硬切） | Week 2 | 低 |

### 🟢 绿色（优化项，面试不太会问但生产有用）

| # | 优化项 | 所属 Week |
|---|-------|----------|
| G1 | LangGraph `config.callbacks` 自动埋点替代手动 with | Week 5 |
| G2 | 异步导出（当前控制台同步 flush） | Week 5 |
| G3 | 数据库替换 CSV（MySQL 连接池、读写分离） | Week 3 |
| G4 | 独立向量库服务（Milvus/Pinecone） | Week 2 |
| G5 | 业务闭环（从"给建议"延伸到"生成工单→推送 MES"） | Week 5+ |
| G6 | Vibe Coding 开发日志记录 | 全局 |

---

## 十、可立即展示 vs 需要说明"还在做"

### 面试时可直接演示（✅ 稳固）

1. **单 Agent 模式**：`python -m demo.main "今天先做哪些订单？"` — 全链路跑通
2. **多 Agent + 鉴权**：`python -m demo.main --mode multi "..."` — Supervisor 分派 + RBAC 拒绝越权 + 审计报告
3. **RAG 混合检索**：`"广州航天合同有什么特殊条款？"` — 四步检索 + rerank 0.99+ 命中
4. **多轮对话 + 持久化**：`python -m demo.main --chat` — 跨轮上下文 + 重启恢复
5. **trace 导出**：`OTEL_EXPORTER=otel` — 真 OTel span 导出
6. **成本熔断**：`LLM_BUDGET_LIMIT=0.01` — 触发 BudgetExceededError
7. **语义缓存**：近义改写命中，跳过 LLM

### 面试被追问时诚实说"这个还在工程化中"（🔶）

1. **工具沙箱与重试** — "当前 registry 是函数直调，生产会拆 MCP 子进程 + 指数退避"
2. **输出护栏** — "guardrails 层的设计思路已经有了，代码还没写——这是下一阶段的重点工作"
3. **上下文压缩** — "当前 messages 无截断，已知问题，方案是 summarization buffer"
4. **NL2SQL 结构化筛选** — "这是 RAG 的已知盲区，用工具函数绕过了但不够优雅"
5. **Agent 评估脚本** — "RAGAS 理论框架已掌握，脚本在 week4 scripts 有但还没集成进 demo"

---

## 十一、7 周完成后的 demo 定位

如果 7 周全部学完（包括 Week 6 微调、Week 7 多模态），demo 的理想状态：

| 周次 | demo 新增能力 | 面试可讲 |
|------|-------------|---------|
| Week 5（当前） | 观测 + 缓存 + 持久化 + 容器化 | "接近生产级的 Agent 系统" |
| Week 6（补） | QLoRA 微调实验 + vLLM 推理部署 + 技术选型文档 | "知道什么时候该微调、微调决策框架" |
| Week 7（补） | 视觉（上传工单截图→OCR→Agent）或语音（Whisper 语音闭环）| "Agent 多模态扩展的架构设计" |

**最终定位**：一个有架构、有鉴权、有追踪、有缓存、有容灾的"教学级生产原型"，覆盖 Agent 工程化全链路。不是玩具（有真实业务约束），不是产品（缺沙箱/护栏/评估/多租户），而是"从 0 到接近生产级"的完整工程训练。

---

> **文档维护**：随 Week 6/7 推进更新。每修复一个 R 级缺陷，标注 ✅ + commit hash。

> 关联文档：
> - `docs/courses/demo-缺陷漏洞与知识盲区分析.md` — 按课程三梯队框架的缺陷排查
> - `docs/week5/README.md` — Week 5 总览
> - `demo/README.md` — demo 技术文档
> - [[project-agent-training-harness-course]] — 课程能力融合
