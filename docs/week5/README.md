# Week 5 — 可观测性 + 业务匹配 + Agent 评估

> **2026-08-03 ~ 08-07** | 知识块 ⑩ ⑪
> 本周一句话：一个能上线的 Agent 系统，必须有监控、有评估、有业务判断依据。

## 文档索引

| 文件 | 内容 |
|------|------|
| `README.md`（本文） | 总览：产出/架构/运行/对比/每日要点/模块职责/代码脉络/核心认知/环境变量/差距表/缺陷/参考资料 |
| `day1_2_guide.md` | Day 1-2：全链路追踪（Span/Tracer/延迟批量导出/OTel）+ 成本监控（定价/熔断/预警） |
| `day3_5_guide.md` | Day 3-5：两级缓存 + 状态持久化 + Token/审计持久化 + 容器化 + Agent 评估 + 业务匹配 + 缺陷分析 |
| `week5_收尾复盘.md` | 收尾复盘：产出清单/10维差距进度/缺口清单/路线vs实际/完成度/下一步建议 |
| **`7周路线-vs-demo-差距全景图.md`** | 🔥 7 周路线逐条对照 demo 代码的差距矩阵：15 个知识块 × 完成度 × 严重度 × 修复建议 |
| **`面试技术深度与应对策略.md`** | 🔥 9 个技术深挖问答预演 + 7 个现网故障场景预案 + VP/同事/HR 三角色策略 + 弱点应对 + 对比题 |

## 产出

```
demo/observability/          # 观测层（Harness 观测层）
├── tracer.py                # Span 全链路追踪（OTel 同构，延迟批量导出）
├── exporter.py              # 可插拔导出 backend：none/console/otel/OTLP
└── cost.py                  # CostTracker：按 provider 定价 + 预算熔断 + 预警

demo/cache/                  # 缓存层（减少 LLM API 调用 = 减成本 + 减延迟）
├── llm_cache.py             # L1 精确缓存（SQLite，相同 prompt 命中 <1ms）
└── semantic_cache.py        # L2 语义缓存（Chroma cosine，近义改写命中 ~50ms）

demo/graph/checkpointer.py   # 状态持久化：sqlite/memory/none，多轮对话 + 重启恢复

demo/core/llm_client.py      # LLM 连接池 + L1 缓存集成 + 成本追踪自动记录

demo/auth/
├── token_exchange.py        # Token 持久化（SqliteTokenStore / MemoryTokenStore）
└── audit_logger.py          # 审计 JSONL 持久化（AUDIT_LOG=none 可禁用）

demo/api.py                  # FastAPI 网关（POST /ask + GET /health + GET /threads/{id}/history）
Dockerfile                    # python:3.11-slim + CPU torch + 精简依赖
docker-compose.yml            # 模型缓存挂载 + demo-runtime 卷
requirements-demo.txt         # demo 专用依赖（不含 akshare/pandas/adk/litellm）

docs/courses/
├── Agent评测漫谈-由浅入深讲解Agent评测.md    # 美团图灵 Agent 评测课程笔记
└── demo-缺陷漏洞与知识盲区分析.md            # 对照课程三梯队的 demo 缺陷排查
```

## 架构

```
Week 4 架构                              Week 5 架构
─────────────                            ─────────────
Supervisor + 子 Agent                    Supervisor + 子 Agent（不变）
       │                                       │
       ├── 鉴权层                               ├── 鉴权层（+ 持久化）
       │   auth/token_exchange.py               │   auth/token_exchange.py（SqliteTokenStore）
       │   auth/audit_logger.py                 │   auth/audit_logger.py（JSONL 落盘）
       │                                       │
       │                                       ├── 观测层（新增 ⭐）
       │                                       │   observability/tracer.py（Span 全链路）
       │                                       │   observability/exporter.py（可插拔 backend）
       │                                       │   observability/cost.py（成本追踪 + 熔断）
       │                                       │
       │                                       ├── 缓存层（新增 ⭐）
       │                                       │   cache/llm_cache.py（L1 精确）
       │                                       │   cache/semantic_cache.py（L2 语义）
       │                                       │
       │                                       ├── 持久化层（新增 ⭐）
       │                                       │   graph/checkpointer.py（SQLite 检查点）
       │                                       │
       ▼                                       ▼
MCP 工具层                               MCP 工具层（不变）
```

**Week 5 的核心增量 = 观测层 + 缓存层 + 持久化层**——它们插入在编排层和工具层之间/周围，做四件事：

1. **全链路追踪**：每次 LLM/工具调用记 Span，可导出到 console/OTel/Jaeger
2. **成本监控**：按 provider 定价计费，超预算自动熔断
3. **缓存降本**：L1 精确 + L2 语义两级缓存，相似问题跳过 LLM
4. **状态持久化**：检查点落盘，多轮对话可恢复

## 运行

```bash
cd projects/agent-training

# 地基自检
python -m demo.main --check

# 单 Agent + 观测导出（默认 console）
python -m demo.main "今天先做哪些订单？"

# OTel 格式导出
OTEL_EXPORTER=otel python -m demo.main "ORD001 能按时交付吗？"

# 多轮对话（状态持久化）
python -m demo.main --chat

# 多 Agent + 鉴权 + 审计
python -m demo.main "广州航天合同有什么特殊条款？" --mode multi

# 预算熔断演示（设低预算触发）
LLM_BUDGET_LIMIT=0.01 python -m demo.main "今天先做哪些订单？"
```

## 对比 Week 4

| 维度 | Week 4（多 Agent + 鉴权） | Week 5（可观测 + 缓存 + 持久化） |
|------|--------------------------|--------------------------------|
| 观测 | print 友好摘要 | Span 全链路 + 可插拔导出（console/otel/OTLP） |
| 成本 | 无 | CostTracker + 预算熔断 + 预警 |
| 缓存 | 无 | L1 精确（SQLite）+ L2 语义（Chroma） |
| 状态持久化 | 无 | SqliteSaver 检查点 + 多轮 + 重启恢复 |
| Token 存储 | 内存字典 | SQLite 持久化（可切回内存） |
| 审计日志 | 内存列表 | JSONL 文件落盘 |
| 部署 | 本地 python -m | FastAPI 网关 + Dockerfile + compose |

## 每日要点

### Day 1 — 可观测性：全链路追踪
- Span/Tracer 设计（OTel 同构最小实现）
- 延迟批量导出：业务代码在 span 退出后写 token 属性不丢
- 可插拔 backend：none / console / otel / OTLP(Jaeger)
- **配套代码**：`observability/tracer.py` + `observability/exporter.py`

### Day 2 — 成本监控 + 告警
- 按 provider 定价计费（¥/百万 token，输入输出分开）
- 预算熔断（BudgetExceededError）：累计超限拒绝新请求
- 预警阈值（80% 开始警告）
- 与 tracer 集成：每轮 flush 输出费用摘要
- **配套代码**：`observability/cost.py`

### Day 3 — 缓存 + 状态持久化
- L1 精确缓存：SQLite，相同 prompt 命中 <1ms，0 token
- L2 语义缓存：Chroma cosine，近义改写命中 ~50ms
- 检查点持久化：SqliteSaver / MemorySaver / None
- 多轮对话 + 跨进程恢复（thread_id 续接）
- **配套代码**：`cache/llm_cache.py` + `cache/semantic_cache.py` + `graph/checkpointer.py`

### Day 4 — 持久化补齐 + 容器化
- Token 持久化：SqliteTokenStore（默认）/ MemoryTokenStore
- 审计持久化：JSONL 即时追加（AUDIT_LOG=none 可禁用）
- FastAPI 网关：POST /ask + GET /health + GET /threads/{id}/history
- Dockerfile + docker-compose + requirements-demo.txt
- **配套代码**：`auth/token_exchange.py` + `auth/audit_logger.py` + `api.py`

### Day 5 — Agent 评估 + 业务匹配 + 缺陷分析
- Agent 评估体系：Trajectory Evaluation vs Response Evaluation
- 观测是评测的基石：观测 + 评测 = 持续迭代
- 业务匹配度：Prompt/Workflow/Agent 边界判断
- demo 缺陷排查：对照课程三梯队框架逐项分析
- **配套文档**：`docs/courses/Agent评测漫谈*.md` + `demo-缺陷漏洞与知识盲区分析.md`

## 模块职责

### observability/tracer.py — 全链路追踪

**职责**：进程内 Span 收集器，记录每次 LLM/工具调用的耗时和 token 用量。

**对外接口**：
| 方法/属性 | 说明 |
|----------|------|
| `tracer.span(name, **attrs)` | contextmanager，记录一段工作单元 |
| `tracer.record(name, duration_ms, **attrs)` | 手动记录已完成 span |
| `tracer.reset()` | 每轮查询前清空 |
| `tracer.flush()` | 整轮结束后导出到 backend |
| `tracer.trace_id` | 本轮 trace 唯一 ID |
| `tracer.format_text()` | 友好文本摘要 |
| `tracer.get_summary()` | 结构化摘要 dict |

### observability/exporter.py — 可插拔导出

**职责**：把完成的 trace 序列化到外部 sink。

**对外接口**：
| 类 | 说明 |
|----|------|
| `NoneExporter` | 空导出（等价 week4） |
| `ConsoleExporter` | 控制台 JSON 行（默认，零基建） |
| `OTelSpanExporter` | 真 OTel SDK → ConsoleSpanExporter 或 OTLP(Jaeger) |
| `build_exporter()` | 按 `OTEL_EXPORTER` 环境变量构造 |

### observability/cost.py — 成本追踪

**职责**：Token 用量计费 + 预算熔断。

**对外接口**：
| 类/方法 | 说明 |
|--------|------|
| `CostTracker.record(provider, prompt_tokens, completion_tokens)` | 记录一次调用费用，超限抛 BudgetExceededError |
| `CostTracker.total_cost` | 累计费用（¥） |
| `CostTracker.by_provider()` | 按 provider 分组统计 |
| `CostTracker.format_text()` | 文本版费用摘要（含预算进度条） |
| `CostTracker.reset()` | 每轮清零 |
| `BudgetExceededError` | 预算熔断异常 |

### cache/llm_cache.py — L1 精确缓存

**职责**：SQLite 存储，相同 prompt 命中返回缓存结果，0 token 消耗。

**对外接口**：
| 方法 | 说明 |
|------|------|
| `LLMCache.get(cache_key)` | 查缓存，命中返回 (response, True) |
| `LLMCache.put(cache_key, response)` | 写缓存 |

### cache/semantic_cache.py — L2 语义缓存

**职责**：Chroma cosine 空间，近义改写命中跳过整图执行。

**对外接口**：
| 方法 | 说明 |
|------|------|
| `SemanticCache.lookup(query, threshold)` | 语义查找，命中返回 (answer, distance) |
| `SemanticCache.put(query, answer)` | 写入缓存 |

**环境变量**：`SEMANTIC_CACHE=on[默认]/off`、`CACHE_THRESHOLD=0.20[默认]`

### graph/checkpointer.py — 状态持久化

**职责**：LangGraph 检查点，支持多轮对话和重启恢复。

**对外接口**：
| 方法 | 说明 |
|------|------|
| `build_checkpointer()` | 按 `CHECKPOINTER` 环境变量构造（sqlite/memory/none） |

**环境变量**：`CHECKPOINTER=sqlite[默认]/memory/none`

## 代码理解脉络

### 全景图

```
┌──────────────────────────────────────────────────────────────────┐
│                    第 4 层 · 观测 + 成本                          │
│            observability/tracer.py   observability/cost.py        │
│            observability/exporter.py                              │
│                                                                  │
│  追踪：                          成本：                           │
│  · Span(name/duration/attrs)      · CostTracker 单例             │
│  · 延迟批量导出                    · 按 provider 定价计费          │
│  · OTel 同构接口                   · 预算熔断 + 预警              │
│  · console/otel/OTLP              · by_provider 分组统计          │
├──────────────────────────────────────────────────────────────────┤
│                    第 3 层 · 缓存 + 持久化                        │
│            cache/llm_cache.py   cache/semantic_cache.py           │
│            graph/checkpointer.py                                 │
│                                                                  │
│  L1 精确缓存：                   L2 语义缓存：                   │
│  · SQLite 存储                    · Chroma cosine 空间            │
│  · 相同 prompt <1ms              · 近义改写 ~50ms                │
│  · 0 token 消耗                   · 跳过整图执行                  │
│                                                                  │
│  检查点：                                                         │
│  · SqliteSaver 落盘               · 多轮 + 重启恢复              │
│  · thread_id 续接                 · --chat REPL                  │
├──────────────────────────────────────────────────────────────────┤
│                    第 2 层 · 鉴权（Week 4 + 持久化）              │
│            auth/token_exchange.py   auth/audit_logger.py          │
│                                                                  │
│  Token 持久化：                  审计持久化：                     │
│  · SqliteTokenStore（默认）        · JSONL 即时追加               │
│  · MemoryTokenStore（可切）        · AUDIT_LOG=none 禁用          │
├──────────────────────────────────────────────────────────────────┤
│                    第 1 层 · 部署                                 │
│            api.py   Dockerfile   docker-compose.yml              │
│                                                                  │
│  FastAPI 网关：                  容器化：                         │
│  · POST /ask                     · python:3.11-slim              │
│  · GET /health                   · CPU torch + 精简依赖          │
│  · GET /threads/{id}/history     · 模型缓存挂载 + runtime 卷     │
└──────────────────────────────────────────────────────────────────┘
```

### 阅读顺序（自底向上）

```
第 1 步（10min）→ observability/tracer.py
   理解 Span 数据结构和 Tracer 的 contextmanager 用法
   关键问题：为什么导出是延迟批量而不是每个 span 立即导出？

第 2 步（10min）→ observability/exporter.py
   理解三种导出 backend 的区别
   关键问题：OTel 档下怎么把多个 span 挂到同一个 trace_id？

第 3 步（10min）→ observability/cost.py
   理解定价表、预算熔断、预警阈值
   关键问题：BudgetExceededError 在哪里被捕获？熔断后怎么恢复？

第 4 步（10min）→ cache/llm_cache.py + cache/semantic_cache.py
   对比两级缓存的命中条件和适用场景
   关键问题：语义缓存为什么只对 thread_id=None 的独立问题生效？

第 5 步（10min）→ graph/checkpointer.py
   理解检查点怎么实现多轮对话和重启恢复
   关键问题：多轮时从 checkpoint 取历史 messages 的策略是什么？

第 6 步（10min）→ auth/token_exchange.py（重点看持久化部分）
   对比 Week 4 内存版，理解 SqliteTokenStore 的改动
   关键问题：TOKEN_STORE=memory 怎么切回内存？

第 7 步（10min）→ auth/audit_logger.py（重点看持久化部分）
   理解 JSONL 追加写入和 AUDIT_LOG=none 切换
   关键问题：审计日志的不可否认性在文件存储下如何保证？

第 8 步（15min）→ api.py + Dockerfile + docker-compose.yml
   理解 FastAPI 网关和容器化部署
   关键问题：docker-compose 的 volume 挂载解决了什么问题？
```

### 三个"为什么"

| 设计决策 | 为什么这样？ |
|---------|-------------|
| 为什么导出是延迟批量而非逐 span？ | 业务代码（llm_client.py）在 `with tracer.span()` 退出后还会往 span.attributes 写 token 用量，立即导出会丢这些属性 |
| 为什么语义缓存只对独立问题生效？ | 多轮对话依赖前文上下文，首轮缓存的结果不包含后续上下文，复用会导致回答不连贯 |
| 为什么成本按会话计费而非按用户？ | demo 是单用户场景；生产级需按用户/租户计费，加 user_id 维度即可扩展 |

## 核心认知

1. **观测是评测的基石** — 没有观测就没有数据，没有数据就无法评估，无法评估就无法迭代。公式：观测 + 评测 = 持续迭代
2. **Span 全链路 = Agent 的黑箱透视镜** — 每次调用记 Span，trace_id 串联，出问题时按 trace 还原完整链路
3. **成本熔断 = 安全阀** — Agent 自主调用 LLM 可能失控（循环/重试），预算上限是最后一道防线
4. **两级缓存 = 降本 + 降延迟** — L1 精确缓存 0 token，L2 语义缓存跳过整图执行，命中时用户无感
5. **持久化 = 从 Demo 到产品** — 内存状态重启即失，SQLite 持久化让 Agent 真正"记住"上下文
6. **Agent 评估 ≠ 只看结果** — Trajectory Evaluation（过程）+ Response Evaluation（结果）并行，过程对不对比结果好不好更重要

## 环境变量速查

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OTEL_EXPORTER` | `console` | 观测导出 backend：none/console/otel |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP gRPC 端点（如 Jaeger 4317） |
| `LLM_BUDGET_LIMIT` | `5.0` | 单次会话预算上限（¥），0 禁用 |
| `LLM_BUDGET_WARN` | `0.8` | 预警阈值（0~1） |
| `SEMANTIC_CACHE` | `on` | L2 语义缓存开关 |
| `CACHE_THRESHOLD` | `0.20` | 语义缓存 cosine distance 阈值 |
| `CHECKPOINTER` | `sqlite` | 检查点 backend：sqlite/memory/none |
| `TOKEN_STORE` | `sqlite` | Token 存储：sqlite/memory |
| `AUDIT_LOG` | `jsonl` | 审计日志：jsonl/none |
| `DEMO_RUNTIME_DIR` | `demo/data` | 运行时数据目录 |

## 10 维差距表进度

| # | 维度 | 状态 | 说明 |
|---|------|------|------|
| 1 | 编排层 | ✅ | SqliteSaver 检查点 + 多轮 + 重启恢复 |
| 2 | 权限层 | 🔶 | Token 持久化已补；缺 JWT 签名 + refresh + ABAC |
| 3 | 观测层 | ✅ | Tracer + 可插拔导出 + OTel 同构 |
| 4 | 工具层 | ⬜ | MCP 仅展示，未真隔离 |
| 5 | RAG | 🔶 | 混合检索完整；缺增量索引 + 多租户 |
| 6 | LLM 调用 | ✅ | 主备 fallback + 两级缓存 + 成本追踪 |
| 7 | 状态管理 | ✅ | SqliteSaver + 多轮 + thread_id 续接 |
| 8 | 数据层 | ⬜ | 本地 CSV 只读 |
| 9 | 审计 | ✅ | JSONL 持久化 + trace_id 贯穿 |
| 10 | 部署 | 🔶 | 代码完成，Docker 环境待验收 |

## 缺陷与知识盲区（对照课程三梯队）

> 详见 `docs/courses/demo-缺陷漏洞与知识盲区分析.md`

### 核心增量盲区（🔴 严重）

| 盲区 | 说明 |
|------|------|
| 工具执行沙箱与重试 | `registry.execute` 无重试逻辑，API 超时直接抛异常 |
| 上下文压缩 | messages 无限增长，长轮对话无截断/压缩 |
| 输出护栏（guardrails） | 无输出校验（JSON 格式错误、越权指令、有害内容） |
| 步骤校验 | `evaluate_results` 是 noop，模型可能 hallucinate 工具结果 |

### 新视角补强盲区（🟡 中等）

| 盲区 | 说明 |
|------|------|
| Prompt 版本管理 | `system_prompts.py` 硬编码，无 A/B 测试基础 |
| 业务数据包 | 未按"问答/筛选比较/推荐/流程"四类场景组织 |
| SLA 定义 | 无"排产建议生成时间 < 3s"等 SLA |
| 单 Agent 绕过鉴权 | `token=None` 时完全绕过 RBAC |

## 参考资料

### Day 1-2：可观测性 + 成本监控

| 知识块 | 资料 |
|--------|------|
| ⑩ 可观测性 | [阿里云 AI Agent 全栈可观测](https://developer.aliyun.com/article/1665930) ⭐ · [Langfuse 文档](https://langfuse.com/docs) ⭐ · [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/) · [LangGraph 追踪集成](https://langchain-ai.github.io/langgraph/cloud/reference/tracing/) |

### Day 3-4：缓存 + 持久化 + 容器化

| 知识块 | 资料 |
|--------|------|
| ⑩ 可观测性（缓存） | [GPTCache 语义缓存](https://github.com/zilliztech/GPTCache) · [LangGraph 持久化](https://langchain-ai.github.io/langgraph/concepts/persistence/) ⭐ |
| 部署 | [FastAPI 部署指南](https://fastapi.tiangolo.com/deployment/docker/) · [Docker Compose](https://docs.docker.com/compose/) |

### Day 5：Agent 评估 + 业务匹配

| 知识块 | 资料 |
|--------|------|
| ⑪ 业务匹配 | [Anthropic When to use agents](https://docs.anthropic.com/en/docs/agents-and-tools) ⭐ · [Agent 评估体系 — 美团图灵](https://mp.weixin.qq.com/s/gZKWRqznB8sNBFf69fBIvw) ⭐ · [RAGAS 评估框架](https://docs.ragas.io/) · [从能回答到能办事 — 课程提炼](../courses/从能回答到能办事-重点提炼.md) |
