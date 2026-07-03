# 第一周 · Day 2 — Function Calling / Tool Use 实战

> **今日目标**：让模型从"只会聊天"变成"能干活"——跑通 Agent 工具调用闭环。
> **对应知识块**：① 大模型 API（Function Calling / Tool Use）
> **路线图位置**：`docs/企业级Agent开发加速路线.md` 第一周 Jul 2
> **前置完成**：Day 1（API 入门 + 主备 fallback）

---

## 今日学习清单

### 1. 协议对比文档阅读（理论，~1h）

> 📖 **理论文档**：`week1/day1_openai_vs_anthropic.md`（必读）

阅读 OpenAI Function Calling 指南 + Anthropic Tool Use 文档后，整理出对写代码有实际影响的差异：

| 维度 | OpenAI / DeepSeek | Anthropic |
|------|-------------------|-----------|
| 端点 | `/chat/completions` | `/v1/messages` |
| system prompt | `messages` 数组里 `role:system` | 顶层 `system` 字段 |
| 工具定义 | `{type:"function", function:{name, parameters}}` | `{name, input_schema}` 无外层 |
| 工具结果回传 | `role:"tool"` + `tool_call_id` | `role:"user"` + `tool_result` 块 |
| 服务端工具 | ❌ 无 | ✅ web_search / web_fetch / code_execution |

**关键认知**：本质相同（JSON Schema 定义工具 + 模型返回调用意图 + 代码执行），差异只在格式包装层。

### 2. 三个延伸概念（理解即可，本阶段不用）

- **服务端工具**：Anthropic 服务器帮你执行（如 web_search），DeepSeek 没有。本阶段所有工具都自己写客户端实现。
- **Tool Search**：工具太多（≥10）时的"搜索引擎"，避免每次请求发全部工具定义浪费 Token。Day 2 只有 1 个工具，不需要。
- **Thinking 模式**：让模型"先打草稿再回答"，适合复杂推理。DeepSeek 不支持，第三四周切 Claude API 时才用。

### 3. 跑通 Function Calling Agent 闭环（实操，~2h）

运行 `day2_function_calling.py`：
```bash
cd projects/agent-training
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python week1/day2_function_calling.py
```

**Agent 循环流程**（核心，必懂）：

```
1. 发送 system + user + tools → LLM
2. LLM 返回 tool_calls? ──是──> 执行工具 → 结果追加到 messages → 回到 1
3. LLM 返回 tool_calls? ──否──> 返回纯文本 → Agent 完成
4. 超过 max_turns 轮 → 强制终止
```

代码对照：`run_agent()` 函数，正是这个循环。

### 4. 工具实现要点

**`query_orders()`** 读 `week1/data/orders.csv`（30 条 3D 打印/CNC 加工订单）：
- 支持筛选：客户名（模糊）/ 状态 / 环节 / 交期范围
- 支持排序：交期 / 数量 / id，可升降序
- 工具定义用 OpenAI Function Calling 格式（DeepSeek 兼容）

**工具调度器** `execute_tool()`：根据 tool_name 分发到具体实现。后续加新工具只需在此追加一个分支。

---

## 今日产出

- [x] 读懂 OpenAI vs Anthropic 协议差异（5 个关键点）
- [x] 理解服务端工具 / Tool Search / Thinking 模式三个延伸概念
- [x] 在 Day 1 主备架构上叠加 Function Calling（`call_with_fallback` 增加 `tools` 参数）
- [x] 实现 `query_orders()` 工具（筛选 + 排序）
- [x] 跑通 Agent 闭环（3 个演示场景）
- [x] 验证主备 fallback 仍生效（DeepSeek 主调成功）

**三个演示场景验证**：

| 场景 | 模型行为 | 轮次 | 结果 |
|------|---------|------|------|
| 快超期订单 | 先查全部 30 条 → 发现没筛选 → 再精确查"即将超期" | 3 轮 | ✅ 识别出明天到期的 ORD-006 |
| 深圳精密五金订单 | 一次调用拿到 8 条，按数量降序 | 2 轮 | ✅ 正确排序 |
| 7月5号前生产中 | 调用返回 0 条 | 2 轮 | ⚠️ 模型把年份填成 2025（应为 2026） |

---

## 发现的问题（待 Day 3 修复）

**演示 3 的 bug**：模型把"7月5号"理解成 `2025-07-05`（去年），导致查到 0 条。

**根因**：System Prompt 里没说明当前日期/年份，模型默认用了训练数据里的旧年份。

**这正好是 Day 3 的课题**——System Prompt 工程化。三层 Prompt 架构（系统级/场景级/用户级）会在系统级注入"当前日期"等上下文信息，避免这类问题。

---

## 关键代码位置

| 功能 | 位置 |
|------|------|
| 工具定义（OpenAI 格式） | `TOOLS` 列表 |
| 工具实现 | `query_orders()` |
| 工具调度器 | `execute_tool()` |
| API 调用（支持 tools） | `call_llm()` / `call_with_fallback()` |
| **Agent 循环（核心）** | `run_agent()` |
| 演示场景 | `demo()` |

---

## 面试速记卡

```
Q: Function Calling 的完整流程是什么？
A: 1) 定义工具 Schema（name/description/parameters）
   2) 把 tools 数组随请求发给模型
   3) 模型返回 tool_calls（含工具名 + 参数 JSON 字符串）
   4) 你的代码执行工具，把结果作为 role:tool 消息回传
   5) 模型基于工具结果生成最终回答

Q: OpenAI 和 Anthropic 的 Tool Use 有什么区别？
A: 本质相同。差异在格式层：
   OpenAI 有 {type:"function", function:{parameters}} 包装，arguments 是 JSON 字符串；
   Anthropic 无包装，用 input_schema，input 已解析为 dict。

Q: Agent 循环什么时候终止？
A: 两种情况——模型返回纯文本（不再调工具），或达到 max_turns 上限。
   每轮工具调用后都要把结果追加回 messages，让模型基于新信息决策。
```

---

## 下一步

Day 3 → System Prompt 工程化：
- 三层 Prompt 架构（系统级 / 场景级 / 用户级）
- 系统级注入"当前日期"等上下文，修复演示 3 的年份 bug
- JSON Schema 约束输出格式
- Prompt 模板变量注入

> Day 2 把"模型调工具"的闭环跑通了。Day 3 让这个闭环更可控——通过 Prompt 工程让模型行为可预测、输出可解析。
