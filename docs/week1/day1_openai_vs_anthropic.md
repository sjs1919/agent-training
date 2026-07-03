# OpenAI vs Anthropic 协议对比笔记

> 基于 Day 1 完成的文档阅读，整理对写 Agent 代码有实际影响的差异。
> 阅读参考：OpenAI Function Calling 指南 + Anthropic Tool Use 文档

---

## 一、API 协议核心差异

### 请求格式

```
OpenAI / DeepSeek：                     Anthropic：
POST /chat/completions                  POST /v1/messages
{                                       {
  "model": "deepseek-v4-flash",           "model": "claude-sonnet-4-6",
  "messages": [                           "system": "你是调度助手",     ← 独立字段
    {"role": "system", "content": "..."},  "messages": [
    {"role": "user", "content": "..."}       {"role": "user", "content": "..."}
  ],                                       ],
  "temperature": 0.3,                      "max_tokens": 1024,          ← 必填
  "max_tokens": 1024                       "temperature": 0.3
}                                         }
```

**关键差异**：
- Anthropic 的 system prompt 是顶层 `system` 字段，不在 messages 数组里
- Anthropic 的 `max_tokens` **必填**，OpenAI 可选
- 端点不同：`/chat/completions` vs `/v1/messages`

### 响应格式

```
OpenAI：                               Anthropic：
{                                       {
  "choices": [{                           "id": "msg_xxx",
    "message": {                           "content": [
      "role": "assistant",                   {"type": "text", "text": "..."}
      "content": "你好"                      ],
    },                                       "stop_reason": "end_turn",
    "finish_reason": "stop"                  "usage": {...}
  }],                                     }
  "usage": {...}
}
```

**关键差异**：
- Anthropic 的 content 是**数组** `[{type, text}]`，不是纯字符串
- 停止原因字段：`finish_reason` vs `stop_reason`
- Anthropic 没有 `choices` 外层包装

---

## 二、Tool Use / Function Calling 定义格式（写 Agent 的核心差异）

### 工具定义

**OpenAI / DeepSeek：**
```json
{
  "type": "function",
  "function": {
    "name": "query_orders",
    "description": "查询订单列表",
    "parameters": {
      "type": "object",
      "properties": {
        "status": { "type": "string", "description": "订单状态" }
      },
      "required": []
    }
  }
}
```

**Anthropic：**
```json
{
  "name": "query_orders",
  "description": "查询订单列表",
  "input_schema": {
    "type": "object",
    "properties": {
      "status": { "type": "string", "description": "订单状态" }
    },
    "required": []
  }
}
```

**差异**：
- OpenAI 有 `{"type": "function", "function": {...}}` 外层包装，参数叫 `parameters`
- Anthropic 没有外层包装，参数叫 `input_schema`
- 结构本质相同（JSON Schema），只是包装层不同

### 模型返回的 tool call

**OpenAI：**
```json
{
  "role": "assistant",
  "content": null,
  "tool_calls": [{
    "id": "call_abc123",
    "type": "function",
    "function": {
      "name": "query_orders",
      "arguments": "{\"status\": \"生产中\"}"
    }
  }]
}
```

**Anthropic：**
```json
{
  "role": "assistant",
  "content": [{
    "type": "tool_use",
    "id": "toolu_abc123",
    "name": "query_orders",
    "input": { "status": "生产中" }
  }]
}
```

**差异**：
- OpenAI：`tool_calls` 数组，arguments 是 JSON 字符串，需要 `json.loads()`
- Anthropic：content 数组里的 `tool_use` 块，input 已经是解析好的 dict

### 工具结果回传

**OpenAI：**
```python
messages.append({
    "role": "tool",
    "tool_call_id": "call_abc123",
    "content": json.dumps(tool_result)
})
```

**Anthropic：**
```python
messages.append({
    "role": "user",
    "content": [{
        "type": "tool_result",
        "tool_use_id": "toolu_abc123",
        "content": json.dumps(tool_result)
    }]
})
```

**差异**：
- OpenAI 用 `role: "tool"` + `tool_call_id`
- Anthropic 用 `role: "user"` + content 块 `type: "tool_result"` + `tool_use_id`

---

## 三、服务端工具 vs 客户端工具

```
┌──────────────────────────────────────────────────────┐
│  客户端工具（所有模型通用，你要写实现）                  │
│                                                      │
│  你定义 Schema  →  模型决定调用  →  你的代码执行       │
│  例：query_orders() —— 你写 Python 读 CSV            │
│                                                      │
│  ✅ DeepSeek 有  ✅ 豆包有  ✅ Anthropic 有           │
├──────────────────────────────────────────────────────┤
│  服务端工具（只有 Anthropic 有，你不用写实现）          │
│                                                      │
│  你声明可用  →  模型决定调用  →  Anthropic 服务器执行   │
│  例：web_search —— Anthropic 帮你搜网页               │
│                                                      │
│  ❌ DeepSeek 无  ❌ 豆包无  ✅ Anthropic 有           │
└──────────────────────────────────────────────────────┘
```

**Anthropic 的服务端工具清单**：

| 工具 | 类型标识 | 做什么 |
|------|---------|--------|
| Web Search | `web_search_20250305` | 搜索网页，返回摘要 + 引用 |
| Web Fetch | `web_fetch_20250910` | 抓取指定 URL 完整内容 |
| Code Execution | `code_execution_20250825` | 沙箱跑 Python/Bash（算数学、画图） |
| MCP Connector | `mcp_toolset` | 连接外部的 MCP Server |

**对你的意义**：用 DeepSeek 做主模型时，所有工具都必须自己写客户端实现。只有切换到 Anthropic API 时才能白嫖服务端工具。Day 2-4 继续在 DeepSeek 上做客户端工具就够了。

---

## 四、Tool Search —— 工具的"搜索引擎"

**问题**：工具太多（比如 200+ 个），每次请求都发全部工具定义 → 浪费 Token

**解决方案**：

```
关闭 Tool Search：                      开启 Tool Search：
                                        defer_loading: true 的工具
请求 ──> 发送全部 200 个工具定义              不在初始上下文里
         ↓                                   ↓
        模型从 200 个里选              请求 ──> 只发 5 个常用工具
        浪费大量 token                       ↓
                                       模型发现不够用
                                           ↓
                                       调用 tool_search 搜
                                       "有没有查询订单的工具？"
                                           ↓
                                       系统返回匹配的 3 个
                                           ↓
                                       模型从中选择
```

**效果**：Token 减少约 85%（77K → 8.7K）

**什么时候需要**：工具 ≥ 10 个。Day 2 只有 1 个工具，**完全不需要**。

---

## 五、Thinking 模式

```
正常模式：  Prompt ──────────────────────> 回答（脱口而出）
Thinking： Prompt → [内部推理...自我校验] → 回答（先打草稿再誊写）
```

### 两种方式

| | Adaptive（推荐） | Extended（旧，逐步废弃） |
|---|---|---|
| 配置 | `thinking: {type: "adaptive"}` | `thinking: {type: "enabled", budget_tokens: 10000}` |
| 谁决定想多久 | 模型自己判断 | 你指定 token 上限 |
| effort 等级 | low / medium / high / xhigh / max | 无 |
| 适用模型 | Opus 4.6+ / Sonnet 4.6+ | 老模型 |
| 计费 | thinking token 按输出价计费 | 同左 |

### 什么时候用

| 不用（关掉） | 用（开启） |
|-------------|----------|
| 简单问答、闲聊 | 复杂数学、算法 |
| 单步操作、简单代码 | 多步推理、大范围重构 |
| 追求低延迟 | Agent 长工具链 |

### Think 工具 ≠ Extended Thinking

| | Extended/Adaptive Thinking | Think 工具 |
|---|---|---|
| 时机 | 生成回答**之前**深度推理 | Agent 调用链**中途**暂停思考 |
| 触发 | 你设参数，自动 | 模型自己决定调用 |
| 用途 | 深度推理整个问题 | 长链中回溯、验证策略 |

### 对你的意义

- DeepSeek **不支持** Extended Thinking
- 只在调 Anthropic API 时能用
- Day 2-3 阶段知道概念即可，第三四周切 Claude API 时会用到

---

## 六、对你的训练项目的实际影响

| 问题 | 答案 |
|------|------|
| Day 2 用谁做主力？ | DeepSeek，OpenAI 兼容协议 |
| 工具调用用谁的格式？ | OpenAI Function Calling 格式（DeepSeek 兼容） |
| 需要适配 Anthropic 协议吗？ | 暂时不需要，第 3-4 周加 Anthropic provider 时再适配 |
| 服务端工具能用吗？ | 不能，DeepSeek 没有。工具全部客户端实现 |
| Thinking 模式能用吗？ | 不能，DeepSeek 不支持 |
| Tool Search 需要吗？ | 不需要，Day 2 只有 1 个工具 |

---

## 七、现在能回答的三个面试题

**Q：OpenAI Function Calling 和 Anthropic Tool Use 有什么区别？**

本质相同（JSON Schema 定义工具 + 模型返回调用意图 + 你的代码执行）。差异在格式层：
OpenAI 有 `{type:"function", function:{...}}` 包装，参数叫 `parameters`，返回的 arguments 是 JSON 字符串；
Anthropic 无包装，参数叫 `input_schema`，返回的 input 已解析为 dict。

**Q：服务端工具和客户端工具有什么区别？**

客户端工具：你写代码执行（所有模型通用）。服务端工具：Anthropic 服务器执行（只有调 Anthropic API 时有）。比如 web_search——你声明模型可以用，Anthropic 帮你搜，你不用写爬虫代码。

**Q：什么时候用 Extended Thinking？**

需要对复杂问题进行深度推理时（数学证明、算法设计、多步规划）。简单问答和 CRUD 不需要。核心判断：这个问题你是不是需要"想一想"才能答对——如果是，就值得开。
