# Week 6 — 微调 + 推理优化 + 剩余缺口收口

> **计划 2026-08-10 ~ 08-14** | 知识块 ⑫ ⑬ ⑭
> 本周一句话：在推进微调/推理的同时，收口 Week 5 R1-R8 之后仍未解决的缺口。
> 维护：2026-08-08

## 一、本周路线（沿用 00_总纲）

| 原定 | 优先级调整（2026-08-08） |
|------|--------------------------|
| LoRA/QLoRA 实战 + DPO + vLLM + AWQ | 1. 先收口 demo 缺口（见下）→ 2. 微调决策框架 + QLoRA 实战 + DPO → 3. 推理优化（vLLM/AWQ） |
| 产出：微调实验 Notebook + vLLM 部署配置 + 技术选型决策文档 | 额外产出：demo 缺口收口记录 |

## 二、剩余缺口待办（R1-R8 之后，按优先级）

> 来源：`week5_收尾复盘.md` 缺口清单（2026-08-08 同步后）中「仍缺口」项 + `面试话术-项目2` 十一节 F 表。

### P0（本周必须收）

| # | 缺口 | 位置 | 验收标准 |
|---|------|------|---------|
| 1 | **Docker 环境验收** | `demo/Dockerfile` + compose | `docker compose up` 后 `/health` `/ask` `/threads/{id}/history` 全部通；模型缓存挂载生效 |
| 2 | **强制鉴权 FORCE_AUTH** | `auth/guard.py` | 单 Agent 模式也强制鉴权（当前 token=None 放行），补 `FORCE_AUTH=true` 开关 |

### P1（本周尽量收）

| # | 缺口 | 位置 | 验收标准 |
|---|------|------|---------|
| 3 | **eval 接 CI 持续评估** | `demo/eval/runner.py` | 10 组 ground truth 纳入 CI，回归基线 7/10 自动化 |
| 4 | **逐工具结果质量规则** | `graph/single_agent_graph.py` R3 深化 | 按工具定制规则（如"query_orders 必须 ≥1 条""search_knowledge_base rerank > 0.5"），不达标自动重试/降级 |
| 5 | **检索质量阈值** | `rag/retriever.py` | rerank 分全 < 0.5 标记"低质量检索"，不喂 LLM |

### P2（时间允许）

| # | 缺口 | 位置 | 验收标准 |
|---|------|------|---------|
| 6 | 按用户/租户计费 | `observability/cost.py` | CostTracker 加 user_id 维度 |
| 7 | 熔断后自动恢复 | `observability/cost.py` | 冷却时间（如 5 分钟）后自动重置 |
| 8 | 告警 + 采样 | `observability/` | provider 失败率阈值告警；高 QPS 采样导出 |
| 9 | Prompt 版本管理 / A/B | `prompts/system_prompts.py` | 版本化 + 分流基础 |
| 10 | Langfuse 看板 | 替换自研 Tracer console 导出 | 接 Langfuse 观察 Agent 轨迹 |
| 11 | SLA 定义 | 全局 | "排产建议 < 3s""准确率 > 95%"等可量化指标 |

## 三、R1-R8 已关闭记录（2026-08-07 完成）

> 已全部合入 demo，见 `demo/README.md` 验收清单，无需在 week6 重复做。

| # | 缺陷 | 归属文件 |
|---|------|---------|
| R1 | 工具沙箱（超时 + 指数退避重试） | `tools/sandbox.py` |
| R2 | 输出护栏（越权/敏感检测 + block/warn/off） | `guardrails/` |
| R3 | evaluate 步骤校验（不再 noop） | `graph/single_agent_graph.py` |
| R4 | 上下文压缩（summarization buffer） | `graph/context_compressor.py` |
| R5 | MCP 子进程隔离（stdio） | `tools/mcp_client.py` |
| R6 | Agent 评估（10 组 ground truth + 指标 + runner） | `eval/` |
| R7 | 结构化筛选（多字段 AND + 排序 + limit） | `tools/order_tools.py` |
| R8 | 多租户隔离（FORCE_TENANT） | `auth/` + `tools/registry.py` |

## 四、本周注意

- 微调/推理是全新知识块（⑫⑬⑭），与 demo 工程化互补，不是替换
- 缺口收口以「面试能讲清 + 代码可追溯」为准，不必追求规模
- 每个缺口完成后回核 `面试话术-项目2` 十一节 F 表，标注状态
