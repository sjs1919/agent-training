# Week 5 收尾复盘

> 2026-08-07 | 知识块 ⑩⑪ | 可观测性 + 业务匹配
> **一句话结论**：工程化深度超额完成（观测/缓存/持久化/容器化/成本追踪），R1-R8 缺陷修复（沙箱/护栏/校验/压缩/MCP/评估/筛选/多租户）已于 2026-08-07 全部合入 demo。剩余缺口：Docker 验收、强制鉴权 FORCE_AUTH、SLA 定义。
> ⚠️ **2026-08-08 同步**：本复盘原文写于 R1-R8 修复前，各节缺口清单已更新为修复后状态（详见下文「三、缺口清单」）。

## 一、产出清单

### 观测层（3 文件）

| 文件 | 行数 | 状态 |
|------|------|------|
| `observability/tracer.py` | 139 | Span 全链路追踪 + 延迟批量导出 |
| `observability/exporter.py` | 142 | 可插拔 backend：none/console/otel/OTLP |
| `observability/cost.py` | 172 | CostTracker + 定价计费 + 预算熔断 + 预警 |

### 缓存层（2 文件）

| 文件 | 行数 | 状态 |
|------|------|------|
| `cache/llm_cache.py` | ~80 | L1 精确缓存（SQLite，<1ms 命中） |
| `cache/semantic_cache.py` | ~120 | L2 语义缓存（Chroma cosine，~50ms 命中） |

### 持久化层（3 文件改动）

| 文件 | 改动 | 状态 |
|------|------|------|
| `graph/checkpointer.py` | 新建 | SqliteSaver / MemorySaver / None |
| `auth/token_exchange.py` | 重写 | TokenStore 抽象 + SqliteTokenStore |
| `auth/audit_logger.py` | 重写 | JSONL 即时追加 + AUDIT_LOG=none |

### 部署层（4 文件）

| 文件 | 状态 |
|------|------|
| `api.py` | FastAPI 网关（/ask + /health + /threads） |
| `Dockerfile` | python:3.11-slim + CPU torch |
| `docker-compose.yml` | 模型缓存挂载 + runtime 卷 |
| `requirements-demo.txt` | demo 专用精简依赖 |

### 文档（2 文件）

| 文件 | 说明 |
|------|------|
| `docs/courses/Agent评测漫谈-由浅入深讲解Agent评测.md` | 美团图灵 Agent 评测课程笔记 |
| `docs/courses/demo-缺陷漏洞与知识盲区分析.md` | 对照课程三梯队的 demo 缺陷排查 |

## 二、10 维差距表进度

> ⚠️ **2026-08-08 同步**：下表「Week 5 状态」为 R1-R8 修复后状态。变化列新增 R1-R8 归属。

| # | 维度 | Week 4 状态 | Week 5 状态 | 变化 |
|---|------|------------|------------|------|
| 1 | 编排层 | 🔶 | ✅ | + SqliteSaver 检查点 + 多轮 + 重启恢复 + R3 步骤校验 + R4 上下文压缩 |
| 2 | 权限层 | 🔶 | 🔶 | + Token 持久化 + R8 多租户隔离；缺 JWT 签名 + ABAC + FORCE_AUTH |
| 3 | 观测层 | ⬜ | ✅ | + Tracer + 可插拔导出 + OTel 同构 |
| 4 | 工具层 | ⬜ | 🔶 | + R1 沙箱（超时/重试）+ R5 MCP 子进程；默认仍走 local fast path |
| 5 | RAG | 🔶 | 🔶 | + R7 结构化筛选；缺增量索引 + 多租户 RAG |
| 6 | LLM 调用 | 🔶 | ✅ | + 两级缓存 + 成本追踪 + 熔断 |
| 7 | 状态管理 | ⬜ | ✅ | + SqliteSaver + 多轮 + thread_id |
| 8 | 数据层 | ⬜ | ⬜ | 本地 CSV 只读 + R8 租户过滤 |
| 9 | 审计 | 🔶 | ✅ | + JSONL 持久化 + trace_id 贯穿 |
| 10 | 部署 | ⬜ | 🔶 | + 代码完成，Docker 环境待验收 |

**完成度**：10 项中 5 项 ✅、3 项 🔶、2 项 ⬜。R1-R8 后新增：工具层沙箱 ✅、编排层步骤校验 ✅、上下文压缩 ✅、评估 ✅、多租户 ✅。

## 三、缺口清单（按严重度）

> ⚠️ **2026-08-08 同步**：R1-R8 缺陷修复已在 2026-08-07 完成并合入 demo，下方缺口 #1-#4 已修复，状态更新如下。详见 `8大缺陷-可执行代码改造方案.md` 和 `demo/README.md` 验收清单。

| # | 严重度 | 位置 | 缺口 | 状态（2026-08-08） |
|---|--------|------|------|-------------------|
| 1 | 🔴 | `tools/registry.py` | 工具执行无重试逻辑，API 超时直接抛异常 | ✅ **已修复（R1）**：`tools/sandbox.py` 超时 + 指数退避重试 |
| 2 | 🔴 | `graph/single_agent_graph.py` | `evaluate_results` 是 noop，模型可能 hallucinate 工具结果 | ✅ **已修复（R3）**：`evaluate_results` 真校验（needs_retry/needs_more/ready_for_answer） |
| 3 | 🔴 | 全局 | 无输出护栏（guardrails）：无 JSON 格式校验、越权指令过滤、有害内容过滤 | ✅ **已修复（R2）**：`guardrails/` 越权/敏感检测 + block/warn/off |
| 4 | 🔴 | `core/llm_client.py` | 无上下文压缩，messages 无限增长 | ✅ **已修复（R4）**：`graph/context_compressor.py` summarization buffer |
| 5 | 🟡 | `agents/single_agent.py` | 单 Agent 模式 `token=None` 绕过鉴权，无强制鉴权开关 | ❌ **仍缺口**：R8 只补了 FORCE_TENANT，**FORCE_AUTH 未做** |
| 6 | 🟡 | `observability/` | 缺自动告警（成本超阈值通知）和采样（高 QPS 全量导出性能差） | ❌ 仍缺口 |
| 7 | 🟡 | `observability/cost.py` | 按会话计费而非按用户/租户，无成本看板 | ❌ 仍缺口 |
| 8 | 🟡 | `prompts/system_prompts.py` | Prompt 无版本管理，无 A/B 测试基础 | ❌ 仍缺口 |
| 9 | 🟡 | 全局 | 无业务数据包概念（未按"问答/筛选/推荐/流程"四类场景组织） | ❌ 仍缺口 |
| 10 | 🟡 | 全局 | 无 SLA 定义（如"排产建议 < 3s""准确率 > 95%"） | ❌ 仍缺口 |
| 11 | 🟢 | Docker | Docker Desktop 引擎未启动，容器化待验收 | ❌ 仍缺口 |
| 12 | 🟢 | `observability/` | Langfuse 集成未做（路线 week5 原定要求） | ❌ 仍缺口（自研 Tracer 替代） |
| 13 | 🟢 | `tools/registry.py` | MCP 真进程隔离 | ✅ **已修复（R5）**：`tools/mcp_client.py` stdio 子进程，默认 `MCP_MODE=local` |
| 14 | 🟢 | 全局 | 无 Agent 评估脚本 | ✅ **已修复（R6）**：`eval/` 10 组 ground truth + 指标 + runner |
| 15 | 🟢 | `tools/order_tools.py` | RAG 无结构化筛选 | ✅ **已修复（R7）**：query_orders 多字段 AND + 排序 + limit |
| 16 | 🟢 | `auth/` + `tools/` | 无多租户隔离 | ✅ **已修复（R8）**：token + tenant_id + FORCE_TENANT |

## 四、Week 5 路线 vs 实际

| 路线原定 | 实际完成 | 差距 |
|---------|---------|------|
| Langfuse 追踪 | 自研 Tracer + OTel 导出 | 功能等价，缺 Langfuse UI 看板 |
| 成本监控仪表盘 | CostTracker + format_text | 有数据无 UI 看板 |
| Agent 评估脚本 | **R6 已补** `eval/` 模块（10 组 ground truth + 指标 + runner，基线 7/10） | ✅ 已补；未接 CI 持续评估 |
| 业务匹配度判断 | 框架理解 + 场景分析 | 缺 SLA 定义和 ROI 框架 |
| 15min Demo 演示 | 未做 | 可用 `--demo` 替代 |

**根因**：Week 5 实际重心偏移到工程化补齐（缓存/持久化/容器化/成本追踪），这些是路线未显式列出但 demo 10 维差距表中的高优项。评估和 SLA 属于"理论框架已有，实操脚本未写"——评估脚本已由 R6 补齐，SLA 定义仍未做。

## 五、完成度评估

| 维度 | 完成度 | 说明 |
|------|--------|------|
| 全链路追踪 | 高 | Span + 可插拔导出 + OTel 同构 |
| 成本监控 | 高 | 定价计费 + 预算熔断 + 预警 |
| 缓存 | 高 | L1 精确 + L2 语义两级 |
| 状态持久化 | 高 | SqliteSaver + 多轮 + 重启恢复 |
| Token/审计持久化 | 高 | SQLite + JSONL 落盘 |
| 工具安全 | 高（R1-R8 后） | R1 沙箱 + R2 护栏 + R3 校验 + R5 MCP 子进程 |
| Agent 评估 | 中高 | R6 已补评估脚本；未接 CI |
| 容器化 | 中 | 代码完成，Docker 环境待验收 |
| 业务匹配 | 中 | 框架理解完成，缺 SLA |
| **整体** | **高（R1-R8 后）** | 工程化深度超额，SLA/Docker/鉴权强制 有缺口 |

## 六、下一步建议

### Week 6（8/10-14）微调 + 推理优化

**路线原定**：LoRA/QLoRA 实战 + DPO + vLLM + AWQ

**建议优先级调整**：

1. **先验收 Docker**（#11，0.5 天）— 启动 Docker Desktop → build → up → 验收 /ask /health /threads
2. **评估脚本接 CI**（R6 已有基础，1 天）— `eval/` 模块 10 组 ground truth 接入 CI 持续评估；RAGAS 4 指标可跑通作为补充基线
3. **按路线推进 Week 6**（3.5 天）— 微调决策框架 + QLoRA 实战 + DPO + 推理优化

**可选**（时间允许）：
- 强制鉴权（FORCE_AUTH，0.5 天）— 单 Agent 模式 token=None 目前仍绕过鉴权
- 逐工具结果质量规则（0.5 天）— R3 是通用校验，可深化为按工具定制
- Langfuse 集成（#12，0.5 天）— 替换自研 Tracer 的 console 导出

> ✅ R1-R8 已于 2026-08-07 修复：工具沙箱/重试、输出护栏、evaluate 校验、上下文压缩、MCP 子进程、评估脚本、结构化筛选、多租户隔离——见「三、缺口清单」。

### 缺陷修复优先级

| 优先级 | 缺陷 | 建议归属 | 状态 |
|--------|------|---------|------|
| P0 | Docker 验收 | Week 5 收尾 | ⬜ 待验收 |
| P1 | 评估脚本 | Week 6 Day 1 | ✅ R6 已补 eval/，待接 CI |
| P1 | 工具执行重试 | Week 6 或后续 | ✅ R1 已修（sandbox） |
| P2 | 输出护栏 | Week 7 或后续 | ✅ R2 已修（guardrails） |
| P2 | 上下文压缩 | Week 7 或后续 | ✅ R4 已修（context_compressor） |
| P2 | 强制鉴权 FORCE_AUTH | Week 6 或后续 | ⬜ 未做（单 Agent token=None 仍绕过） |
| P3 | Langfuse 集成 | 按需 | ⬜ 未做（自研 Tracer 替代） |
