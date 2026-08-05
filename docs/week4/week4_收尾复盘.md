# Week 4 收尾复盘

> 2026-07-30 | 知识块 ⑧⑨ | 多 Agent 集群 + 鉴权
> **一句话结论**：脚手架完整、鉴权审计可跑；LLM 智能层已于 2026-07-30 补齐（三 Agent + Supervisor 综合均接 LLM），剩余缺口为 Token/审计持久化等工程化项。

## 一、产出清单

### 核心 6 文件（README 计划）

| 文件 | 行数 | 状态 |
|------|------|------|
| `supervisor_agent.py` | 234 | 编排骨架完整，未接 LLM |
| `agents/agent_router.py` | 61 | 关键词路由（docstring 误标 LLM） |
| `agents/review_agent.py` | 98 | 桩函数，返回 pending_review |
| `agents/production_agent.py` | 50 | 透传工具数据，无评估 |
| `auth/token_exchange.py` | 121 | RBAC + Token Exchange 完整，内存存储 |
| `auth/audit_logger.py` | 63 | Trace ID 串联 OK，未落盘 |

### 扩展 9 文件（计划外增量）

| 文件 | 行数 | 主题 |
|------|------|------|
| `adk_coordinator_autoflow.py` | 197 | Google ADK 协调器 |
| `adk_code_executor_calculator.py` | 128 | ADK 代码执行器 |
| `adk_vsearch_agent.py` | 99 | ADK 向量搜索 Agent |
| `coordinator_router_branch.py` | 154 | 协调器路由分支 |
| `ragas_eval.py` | 403 | RAGAS 4 指标评估 |
| `rubric_checked_rag.py` | 260 | Rubric 检查 RAG |
| `tool_calling_agent_executor.py` | 130 | 工具调用执行器 |
| `lcel_extract_json_chain.py` | 91 | LCEL JSON 提取链 |
| `openai_deep_research.py` | 118 | Deep Research |

## 二、缺口清单（按严重度）

| # | 严重度 | 位置 | 缺口 |
|---|--------|------|------|
| 1 | 严重 | `review_agent.py:91-99` | `review_order()` 返回 `pending_review`，未调 LLM，核心风险评级未实现 |
| 2 | 严重 | `production_agent.py:41-51` | 仅聚合原始数据，无 LLM 可行性判定/交期估算 |
| 3 | 严重 | `supervisor_agent.py:35,47-73` | `call_llm` 已导入、`SUPERVISOR_PROMPT` 已定义，但从未调用；"综合输出"只打印原始数据 |
| 4 | 高 | `agent_router.py:5 vs 33-53` | docstring 声称 LLM 意图分类，实现是关键词匹配 |
| 5 | 高 | `token_exchange.py:63` | Token 内存字典存储，重启丢失，无持久化 |
| 6 | 高 | `audit_logger.py:23` | `log_path` 参数接受但未写入，审计仅内存 |
| 7 | 中 | `supervisor_agent.py:106-129` | Token 签发/交换了，但工具调用前未校验权限，子 Agent 不传 Token |
| 8 | 中 | `supervisor_agent.py:163-164` | 路由目标仅 print，无实际分发 |

## 三、核心问题：LLM 智能层缺失

Week 4 的目标是"多 Agent 协作"，但三个 Agent（Supervisor / 审核 / 生产）无一调用 LLM：

- 路由靠关键词分类
- 审核 / 生产只采集工具数据，返回原始 JSON 或 `pending_review`
- Supervisor 不做综合分析，只拼接打印

结果是：跑起来能看到数据流和鉴权审计日志，但没有"Agent 推理决策"。这相当于把 Week 3 的工具调用拆成多 Agent 骨架，但没注入智能。

**根因推测**：时间分配偏了--扩展文件（ADK / RAGAS / Rubric，9 个）占了不少精力，核心多 Agent 的 LLM 接入反而没收尾。

## 四、完成度评估

| 维度 | 完成度 | 说明 |
|------|--------|------|
| 多 Agent 骨架 | 高 | Supervisor + 2 子 Agent 结构清晰 |
| 鉴权体系 | 中高 | RBAC + Token Exchange 逻辑完整，缺持久化 |
| 审计日志 | 中 | Trace ID 串联 OK，缺落盘 |
| LLM 智能层 | 高 | 三 Agent + Supervisor 综合均接 LLM（2026-07-30 补齐） |
| **整体** | **中** | 智能层闭环，剩余持久化/权限校验等工程化项 |

## 五、下一步建议（已选 A 并完成，见第六节）

**选项 A：补齐 LLM 层再进 Week 5（推荐）**
- 优先级 1：supervisor 的 `call_llm` 综合分析接上（PROMPT 已写好，只差调用）
- 优先级 2：`review_order` / `assess_production_feasibility` 接 LLM
- 优先级 3：`agent_router` 升级为 LLM 路由（或修正 docstring）
- 工作量：约 0.5-1 天
- 收益：Week 4 真正闭环，面试讲得通"多 Agent LLM 协作"

**选项 B：标记为"骨架完成"，先进 Week 5，后续补**
- 风险：Week 5 依赖 Week 4 的 Agent 做可观测接入，骨架不接 LLM 会让 Week 5 的追踪/评估失去意义
- 适用：时间紧，且 Week 5 能独立跑

**选项 C：补关键一项（supervisor 综合），其余标记**
- 最小投入让"综合输出"有 LLM 推理，其余留到 Week 5 后

## 六、补齐记录（2026-07-30）

已选方案 A，补齐 LLM 智能层：

| 缺口 | 文件 | 补齐内容 |
|------|------|---------|
| #1 review 未接 LLM | `agents/review_agent.py` | `review_order` 调 `call_llm`，按 SYSTEM_PROMPT 输出风险评级 JSON |
| #2 production 未接 LLM | `agents/production_agent.py` | 新增 SYSTEM_PROMPT，`assess_production_feasibility` 调 `call_llm` 输出可行性 JSON |
| #3 supervisor 未综合 | `supervisor_agent.py` | 步骤 5 调 `call_llm` 综合 review+production 结果，输出排产建议 |
| #4 router docstring 误导 | `agents/agent_router.py` | docstring 改为"基于关键词（后续可升级 LLM 路由）" |

**测试**：`python supervisor_agent.py "今天先做哪些订单？综合风险评估和产能情况给出排产建议"` 跑通，5 次 LLM 调用（3 审核 + 1 产能 + 1 综合），输出按优先级排序的排产建议（ORD003 → ORD001 → ORD005，每单含风险+产能+操作+理由）。

**剩余缺口（2026-08-05 全部修复）**：
- ~~#5 Token 内存存储（无持久化，重启丢失）~~ ✅ 已修复：`TokenStore` 抽象 + `SqliteTokenStore` 实现，默认 `tokens.db`
- ~~#6 audit `log_path` 未落盘（仅内存）~~ ✅ 已修复：`_persist()` 即时追加 JSONL 到 `{RUNTIME_DIR}/audit.jsonl`
- ~~#7 工具调用前未校验 Token 权限（子 Agent 不传 Token）~~ ✅ 代码排查确认不成立：`review_agent.py:35` 和 `production_agent.py:28` 均传 `token` 给 `registry.execute()`
- ~~#8 `query` 路由目标仅 print，无实际分发~~ ✅ 代码排查确认不成立：`review_agent.py:42` 和 `production_agent.py:29` 在 Agent 中调 `registry.execute()`，非仅 print

## 七、2026-08-05 企业级缺口补齐

| 缺口 | 修复 | 文件 |
|------|------|------|
| **成本监控**（week5 #1） | `CostTracker` 单例 + 按 provider 定价 + 预算熔断 + `LLM_BUDGET_LIMIT` | 新建 `observability/cost.py`，集成 `core/llm_client.py` |
| **Token 持久化**（week4 #5） | `TokenStore` 抽象 → `SqliteTokenStore` 默认落地，`TOKEN_STORE=memory` 切回内存 | `auth/token_exchange.py` 重写 |
| **审计持久化**（week4 #6） | `_persist()` 即时追加 JSONL，`AUDIT_LOG=none` 禁用 | `auth/audit_logger.py` 重写 |
