# Week 5 收尾复盘

> 2026-08-07 | 知识块 ⑩⑪ | 可观测性 + 业务匹配
> **一句话结论**：工程化深度超额完成（观测/缓存/持久化/容器化/成本追踪），Agent 评估与业务匹配有理论框架但缺实操脚本，Docker 环境待验收。

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

| # | 维度 | Week 4 状态 | Week 5 状态 | 变化 |
|---|------|------------|------------|------|
| 1 | 编排层 | 🔶 | ✅ | + SqliteSaver 检查点 + 多轮 + 重启恢复 |
| 2 | 权限层 | 🔶 | 🔶 | + Token 持久化；缺 JWT + ABAC |
| 3 | 观测层 | ⬜ | ✅ | + Tracer + 可插拔导出 + OTel 同构 |
| 4 | 工具层 | ⬜ | ⬜ | MCP 仅展示，未真隔离 |
| 5 | RAG | 🔶 | 🔶 | 无变化；缺增量索引 + 多租户 |
| 6 | LLM 调用 | 🔶 | ✅ | + 两级缓存 + 成本追踪 + 熔断 |
| 7 | 状态管理 | ⬜ | ✅ | + SqliteSaver + 多轮 + thread_id |
| 8 | 数据层 | ⬜ | ⬜ | 本地 CSV 只读 |
| 9 | 审计 | 🔶 | ✅ | + JSONL 持久化 + trace_id 贯穿 |
| 10 | 部署 | ⬜ | 🔶 | + 代码完成，Docker 环境待验收 |

**完成度**：10 项中 5 项 ✅、3 项 🔶、2 项 ⬜。Week 4 时 0 项 ✅。

## 三、缺口清单（按严重度）

| # | 严重度 | 位置 | 缺口 |
|---|--------|------|------|
| 1 | 🔴 | `tools/registry.py` | 工具执行无重试逻辑，API 超时直接抛异常 |
| 2 | 🔴 | `graph/single_agent_graph.py` | `evaluate_results` 是 noop，模型可能 hallucinate 工具结果 |
| 3 | 🔴 | 全局 | 无输出护栏（guardrails）：无 JSON 格式校验、越权指令过滤、有害内容过滤 |
| 4 | 🔴 | `core/llm_client.py` | 无上下文压缩，messages 无限增长 |
| 5 | 🟡 | `agents/single_agent.py` | 单 Agent 模式 `token=None` 绕过鉴权，无强制鉴权开关 |
| 6 | 🟡 | `observability/` | 缺自动告警（成本超阈值通知）和采样（高 QPS 全量导出性能差） |
| 7 | 🟡 | `observability/cost.py` | 按会话计费而非按用户/租户，无成本看板 |
| 8 | 🟡 | `prompts/system_prompts.py` | Prompt 无版本管理，无 A/B 测试基础 |
| 9 | 🟡 | 全局 | 无业务数据包概念（未按"问答/筛选/推荐/流程"四类场景组织） |
| 10 | 🟡 | 全局 | 无 SLA 定义（如"排产建议 < 3s""准确率 > 95%"） |
| 11 | 🟢 | Docker | Docker Desktop 引擎未启动，容器化待验收 |
| 12 | 🟢 | `observability/` | Langfuse 集成未做（路线 week5 原定要求） |

## 四、Week 5 路线 vs 实际

| 路线原定 | 实际完成 | 差距 |
|---------|---------|------|
| Langfuse 追踪 | 自研 Tracer + OTel 导出 | 功能等价，缺 Langfuse UI 看板 |
| 成本监控仪表盘 | CostTracker + format_text | 有数据无 UI 看板 |
| Agent 评估脚本 | 课程笔记 + 缺陷分析文档 | 缺可运行评估脚本（如 RAGAS） |
| 业务匹配度判断 | 框架理解 + 场景分析 | 缺 SLA 定义和 ROI 框架 |
| 15min Demo 演示 | 未做 | 可用 `--demo` 替代 |

**根因**：Week 5 实际重心偏移到工程化补齐（缓存/持久化/容器化/成本追踪），这些是路线未显式列出但 demo 10 维差距表中的高优项。评估和 SLA 属于"理论框架已有，实操脚本未写"。

## 五、完成度评估

| 维度 | 完成度 | 说明 |
|------|--------|------|
| 全链路追踪 | 高 | Span + 可插拔导出 + OTel 同构 |
| 成本监控 | 高 | 定价计费 + 预算熔断 + 预警 |
| 缓存 | 高 | L1 精确 + L2 语义两级 |
| 状态持久化 | 高 | SqliteSaver + 多轮 + 重启恢复 |
| Token/审计持久化 | 高 | SQLite + JSONL 落盘 |
| 容器化 | 中 | 代码完成，Docker 环境待验收 |
| Agent 评估 | 中 | 理论框架完成，缺评估脚本 |
| 业务匹配 | 中 | 框架理解完成，缺 SLA |
| **整体** | **中高** | 工程化深度超额，评估/SLA 有缺口 |

## 六、下一步建议

### Week 6（8/10-14）微调 + 推理优化

**路线原定**：LoRA/QLoRA 实战 + DPO + vLLM + AWQ

**建议优先级调整**：

1. **先验收 Docker**（#11，0.5 天）— 启动 Docker Desktop → build → up → 验收 /ask /health /threads
2. **补评估脚本**（#3 评估缺口，1 天）— RAGAS 4 指标跑通，至少有量化基线
3. **按路线推进 Week 6**（3.5 天）— 微调决策框架 + QLoRA 实战 + DPO + 推理优化

**可选**（时间允许）：
- 工具执行重试（#1，0.5 天）— `registry.execute` 加指数退避
- 输出护栏（#3，1 天）— JSON Schema 校验 + 越权指令过滤
- Langfuse 集成（#12，0.5 天）— 替换自研 Tracer 的 console 导出

### 缺陷修复优先级

| 优先级 | 缺陷 | 建议归属 |
|--------|------|---------|
| P0 | Docker 验收 | Week 5 收尾 |
| P1 | 评估脚本 | Week 6 Day 1 |
| P1 | 工具执行重试 | Week 6 或后续 |
| P2 | 输出护栏 | Week 7 或后续 |
| P2 | 上下文压缩 | Week 7 或后续 |
| P3 | Langfuse 集成 | 按需 |
