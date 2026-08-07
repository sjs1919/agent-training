# 第五周 Day1+2 — 可观测性：全链路追踪 + 成本监控

> **本周一句话**：Week 4 让 Agent "能干活"，Week 5 让 Agent "干得可监控、可评估、可控制"。

---

## Day 1：全链路追踪

### 1. 为什么 Agent 系统需要可观测？

Week 4 的 Agent 跑起来后，你只能看到最终输出。但一次查询背后可能发生了：

```
用户问 "今天先做哪些订单？"
  → LLM 调用 1（意图分析）         500 tokens   1.2s
  → 工具调用 query_orders()        0 tokens     0.05s
  → LLM 调用 2（决定下一步）       800 tokens   2.1s
  → 工具调用 query_inventory()     0 tokens     0.03s
  → LLM 调用 3（综合输出）         1200 tokens  3.5s
  → 总计：2500 tokens，6.88s
```

**没有可观测，你不知道**：
- Agent 调了几次 LLM？花了多少 token？
- 哪个步骤最慢？是 LLM 还是工具？
- 工具调用是否成功？有没有重试？
- 一次查询花了多少钱？

### 2. Span：观测的最小单元

**核心概念**：一个 Span = 一次工作单元的记录。

```
Span {
  name: "llm:call"              // 做了什么
  duration_ms: 1200             // 耗时
  attributes: {                 // 附加信息
    model: "ark-code-latest",
    prompt_tokens: 500,
    completion_tokens: 200,
    provider: "火山豆包(coding)"
  }
}
```

**代码理解**（`observability/tracer.py`）：

```python
# 用法：contextmanager 自动计时
with tracer.span("llm_call", model="doubao") as s:
    response = call_llm(messages, tools)
    # with 退出后自动记录 duration
    # 业务代码可以在 with 外继续写属性
s.attributes["prompt_tokens"] = response.usage.prompt_tokens
s.attributes["completion_tokens"] = response.usage.completion_tokens
```

### 3. 延迟批量导出

**为什么不逐 span 导出？**

```
❌ 逐 span 导出（OTel 默认行为）：
  with tracer.span("llm") as s:
      response = call_llm(...)
  # ← span 结束立即导出
  s.attributes["tokens"] = ...  # ← 太晚了！已经导出了，token 属性丢了

✅ 延迟批量导出（我们的实现）：
  with tracer.span("llm") as s:
      response = call_llm(...)
  s.attributes["tokens"] = ...  # ← 在 with 外写属性
  # ← 整轮 query 结束后才 flush，所有属性都在
```

**根因**：`llm_client.py` 在 `with tracer.span()` 退出后，还需要从 response 对象提取 token 用量写入 span.attributes。如果 span 结束就导出，这些属性就丢了。

### 4. 可插拔导出 backend

| `OTEL_EXPORTER` | 输出 | 基建 | 用途 |
|---|---|---|---|
| `none` | 无导出 | 无 | 等价 week4 行为 |
| `console`（默认） | 控制台 JSON 行 | 无 | 零基建演示"导出"概念 |
| `otel` | 真 OTel SDK span | 无（ConsoleSpanExporter） | 看真 OTel 格式 |
| `otel` + `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP gRPC → collector | 本地 Jaeger（4317） | Jaeger UI 看分布式 trace |

**代码理解**（`observability/exporter.py`）：

```python
# OTel 档：把 tracer 的 trace_id 补齐成 OTel 128-bit，
# 造一个根 context，让本轮所有 span 挂到同一个 OTel trace 下
tid_hex = (trace_id + "0" * 32)[:32]
root_ctx = SpanContext(trace_id=int(tid_hex, 16), ...)
parent_ctx = otel.set_span_in_context(NonRecordingSpan(root_ctx))

for s in spans:
    otel_span = tracer.start_span(s.name, context=parent_ctx)
    for k, v in s.attributes.items():
        otel_span.set_attribute(k, v)
    otel_span.end(end_time=s.end_wall_ns)
```

**关键设计**：in-memory Span 是事实源，flush 时才转换成 OTel span 导出。这样业务代码写属性的时机不受限。

### 5. OTel 同构但不依赖

demo 的 Tracer 是 OTel 的"最小同构实现"——接口设计对齐 OTel（Span/Tracer/Exporter），但不依赖 OTel SDK 运行。好处：

| 场景 | 行为 |
|------|------|
| 不装 opentelemetry | 默认 console 导出，零依赖 |
| 装了 opentelemetry | `OTEL_EXPORTER=otel` 切到真 OTel |
| 有 Jaeger collector | 加 `OTEL_EXPORTER_OTLP_ENDPOINT` 发 OTLP |

---

## Day 2：成本监控 + 告警

### 1. 为什么 Agent 系统需要成本监控？

Agent 自主调用 LLM，可能失控：

| 场景 | 后果 |
|------|------|
| Agent 陷入循环（反复调 LLM 不收敛） | token 消耗指数增长 |
| 工具返回异常，Agent 反复重试 | 每次重试都是 LLM 调用 |
| Prompt 注入攻击 | 恶意指令让 Agent 大量调用 |
| 多 Agent 协作，子 Agent 各自调 LLM | 成本叠加 |

**一句话**：没有成本监控，Agent 就是一个"花钱无底洞"。

### 2. CostTracker 设计

```
┌─────────────────────────────────────────────┐
│              CostTracker（单例）              │
│                                             │
│  record(provider, prompt_tokens,            │
│          completion_tokens)                 │
│      │                                      │
│      ├── 查定价表 → 算费用                   │
│      ├── 累加到 total_cost                  │
│      ├── 检查预算                            │
│      │   ├── ≥ 80% → 打印预警               │
│      │   └── ≥ 100% → 抛 BudgetExceededError│
│      └── 返回 CostEntry                     │
│                                             │
│  by_provider() → 按 provider 分组统计        │
│  format_text() → 文本摘要（含进度条）        │
│  reset()       → 每轮清零                   │
└─────────────────────────────────────────────┘
```

**定价表**（`observability/cost.py`）：

| Provider | 输入（¥/百万 token） | 输出（¥/百万 token） |
|----------|---------------------|---------------------|
| 火山豆包(coding) | 2.0 | 2.0 |
| DeepSeek | 1.0 | 1.0 |
| Kimi(coding) | 2.0 | 2.0 |
| 未知 | 2.0 | 2.0 |

### 3. 预算熔断

**三级告警**：

```
正常区间          预警区间           熔断
─────────────────┬──────────────────┬──────────
0%              80%               100%
                 │                  │
                 ▼                  ▼
            打印预警            抛 BudgetExceededError
         "剩余 ¥0.8"         "预算已耗尽"
                            拒绝新 LLM 请求
```

**代码理解**：

```python
# llm_client.py 中自动集成
def call_llm(messages, tools=None):
    # ... 调 LLM ...
    # 自动记录成本
    cost_tracker.record(
        provider=provider_name,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
    )
    # 超预算时 record 内部抛 BudgetExceededError
```

**环境变量**：
- `LLM_BUDGET_LIMIT=5.0` — 单次会话预算上限（¥），0 禁用
- `LLM_BUDGET_WARN=0.8` — 预警阈值

### 4. 费用摘要输出

```
💰 费用摘要：总计 ¥0.0034，2500 tokens，3 次调用
   预算: [▓░░░░░░░░░░░░░░░░░░░] 0%  (¥0.0034 / ¥5.00)
   火山豆包(coding): 3 次, 2500 tokens, ¥0.0034
```

### 5. 与 tracer 的集成

每轮 query 结束时，main.py 同时输出 trace 摘要和费用摘要：

```python
# main.py
print(tracer.format_text())       # 📊 Trace 摘要
print(cost_tracker.format_text()) # 💰 费用摘要
tracer.flush()                    # 导出到 backend
```

OTel 档下，费用数据随 span 导出，可以在 Jaeger/Langfuse 看到每次调用的 token 用量和费用。

---

## 代码理解脉络

```
第 1 步（10min）→ observability/tracer.py
   理解 Span 数据结构和 Tracer 的 contextmanager
   关键问题：为什么 _trace_start 在第一次 span 时才设？

第 2 步（15min）→ observability/exporter.py
   理解三种 backend 的区别，重点看 OTelSpanExporter
   关键问题：OTel 档下怎么保证多个 span 挂到同一个 trace？

第 3 步（10min）→ observability/cost.py
   理解定价表、预算熔断、预警
   关键问题：BudgetExceededError 在哪里被捕获？

第 4 步（10min）→ core/llm_client.py
   看 call_llm 怎么集成 tracer.span + cost_tracker.record
   关键问题：L1 缓存命中时，tracer 和 cost_tracker 怎么处理？
```

---

## 核心认知（今天最重要的 3 句话）

1. **观测是评测的基石** — 没有观测就没有数据，没有数据就无法评估，无法评估就无法迭代
2. **延迟批量导出 > 逐 span 导出** — 业务代码在 span 退出后写属性是刚需，立即导出会丢数据
3. **成本熔断 = 安全阀** — Agent 自主调用 LLM 可能失控，预算上限是最后一道防线

---

## 参考资料

| 知识块 | 资料 |
|--------|------|
| ⑩ 可观测性 | [阿里云 AI Agent 全栈可观测](https://developer.aliyun.com/article/1665930) ⭐ · [Langfuse 文档](https://langfuse.com/docs) ⭐ · [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/) |
