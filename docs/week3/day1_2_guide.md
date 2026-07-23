# 第三周 Day1+2 — 工具体系设计 + MCP Server

> **本周一句话**：这一周开始，Demo 从"脚本"变成有架构的 Agent 系统。

---

## Day 1：工具体系设计

### 1. 为什么需要工具注册中心？

回顾 week2 的工具管理方式（`week2_agentic_rag_agent.py`）：

```python
# week2 方式：内联字典 + if/elif 分支
TOOLS = [
    {"type": "function", "function": {"name": "query_orders", ...}},
    {"type": "function", "function": {"name": "query_customer", ...}},
    {"type": "function", "function": {"name": "search_knowledge_base", ...}},
]

def execute_tool(tool_name, arguments, collection):
    if tool_name == "plan_investigation":    ...
    elif tool_name == "query_orders":        ...
    elif tool_name == "query_customer":      ...
    elif tool_name == "search_knowledge_base": ...
    elif tool_name == "submit_final_answer": ...
    else: return f"未知工具: {tool_name}"
```

**问题**：
- 工具定义（Schema）和执行逻辑（Handler）**分离**在代码的不同位置，新增工具要改两个地方
- 没有统一的**工具发现**机制——要知道有哪些工具只能翻 TOOLS 列表
- 新增工具 = 在 TOOLS 列表加一个 dict + 在 execute_tool 加一个 elif，容易遗漏
- 工具多了以后（10+），if/elif 链变得不可维护
- 无法**按类别分组**（订单类、客户类、知识库类）——所有工具平铺在一个列表里

### 2. 解决方案：ToolRegistry（工具注册中心）

核心思路：**一个类管理所有工具的生命周期**。

```
         register(name, desc, params, handler, category)
                     │
                     ▼
┌─────────────────────────────────────────┐
│            ToolRegistry                  │
│                                          │
│  _tools:   {name → ToolSchema}          │  ← Schema 存储
│  _handlers:{name → Callable}            │  ← 执行函数存储
│                                          │
│  ┌─ register()      注册一个工具         │
│  ├─ get_tool_defs() 获取 OpenAI 格式列表  │
│  ├─ execute()       执行工具            │
│  ├─ list_by_category() 按类别列出       │
│  └─ get_schema()    获取单个工具 Schema  │
└─────────────────────────────────────────┘
```

**关键概念**：

| 概念 | 说明 | 示例 |
|------|------|------|
| **ToolSchema** | 工具的"身份证"：name、description、parameters（JSON Schema）、category | `ToolSchema(name="query_orders", category="order", ...)` |
| **Handler** | 工具的执行函数，接收 arguments dict，返回结果字符串 | `def query_orders(customer=None, status=None): ...` |
| **Category** | 工具分类标签，用于分组发现 | `"order"`, `"customer"`, `"knowledge"`, `"system"` |

### 3. 工具 Schema 规范化

每个工具 Schema 必须包含三个要素（**这是 MCP 协议和 OpenAI Function Calling 的共同要求**）：

```json
{
  "name": "query_orders",           // ① 唯一标识：字母+下划线，见名知意
  "description": "查询订单列表...",   // ② 自然语言描述：LLM 据此决定何时调用
  "parameters": {                    // ③ JSON Schema：类型约束，LLM 据此填参数
    "type": "object",
    "properties": {
      "customer": {"type": "string", "description": "按客户名模糊筛选"},
      "status":   {"type": "string", "enum": ["生产中", "待排产", ...]}
    },
    "required": []
  }
}
```

> **为什么 description 很重要？** LLM 是根据 description（不是 name）来决定调用哪个工具的。description 越清晰，工具选择越准确。

### 4. 工具粒度原则

> "一个工具只做**一件事**，通过**组合**而非**膨胀**来扩展能力。"

| 原则 | 说明 | 好的例子 | 坏的例子 |
|------|------|---------|---------|
| **单一职责** | 一个工具只做一种查询/操作 | `query_orders` 只查订单 | `query_everything` 查所有表 |
| **参数正交** | 参数之间不隐含依赖 | `customer` 和 `status` 独立筛选 | `mode=1` 时 `customer` 才生效 |
| **可组合** | 多个小工具组合完成复杂任务 | agent 依次调 query_orders → query_customer → search_kb | 一个大工具包办一切 |
| **可测试** | 每个工具可独立输入输出验证 | 给定 customer="深圳"，返回 8 条 | 需要先调 A 再调 B 才能验证 C |

**粒度判断方法**：如果一个工具的描述里出现了"或者"、"也可以"、"此外还支持"，就该拆成两个。

### 5. week2 → week3 演进对比

```
week2（硬编码）                          week3 day1（ToolRegistry）
─────────────────────────              ─────────────────────────
TOOLS = [{...}, {...}]  列表           registry.register() 逐个注册
execute_tool() if/elif 链             registry.execute() 字典分发
工具名散落在代码各处                   registry.list_by_category() 集中发现
新增工具 = 改 2 处代码                 新增工具 = 1 次 register() 调用
无法独立测试单个工具                   handler 是独立函数，可直接单测
```

---

## Day 2：MCP Server

### 1. MCP 是什么？

**MCP（Model Context Protocol）** 是 Anthropic 提出的**开放协议**，定义了 LLM 应用与外部工具/数据源之间的标准化通信方式。

**一句话理解**：MCP 是工具调用的"USB 协议"——任何实现了 MCP 的工具 Server，都可以被任何支持 MCP 的 Client（Claude、Cursor、自建 Agent）即插即用。

### 2. MCP 的核心架构

```
┌──────────────┐     MCP 协议（JSON-RPC）     ┌──────────────┐
│  MCP Client  │ ◄──────────────────────────► │  MCP Server   │
│  (你的 Agent) │     Transport: stdio/SSE     │  (工具提供方)  │
└──────────────┘                              └──────────────┘
                                                     │
                                          ┌──────────┼──────────┐
                                          ▼          ▼          ▼
                                       Tools     Resources   Prompts
                                       (工具)    (资源)      (提示模板)
```

**MCP Server 提供三种能力**：

| 能力 | 说明 | 我们的场景 |
|------|------|-----------|
| **Tools** | 可执行的函数，LLM 通过 Client 调用 | `query_orders`、`query_inventory` 等 |
| **Resources** | 暴露给 Client 的数据（文件、数据库记录等） | 合同条款文件、订单 CSV |
| **Prompts** | 预定义的 Prompt 模板 | "你是 3D 打印调度专家..." |

> week3 只聚焦 **Tools**，Resources 和 Prompts 后续需要时再加。

### 3. MCP vs 直接 Function Calling

| 维度 | 直接 Function Calling（week2） | MCP（week3） |
|------|-------------------------------|-------------|
| **工具定义** | 内联在 Agent 代码里 | 在 MCP Server 里独立定义 |
| **工具发现** | 硬编码的 TOOLS 列表 | Client 连接后自动 `list_tools()` |
| **工具复用** | 复制粘贴到其他项目 | 启动 MCP Server，任何 Client 可连 |
| **进程模型** | 工具和 Agent 同进程 | 工具在独立进程，通过 stdio/SSE 通信 |
| **热更新** | 需要重启 Agent | 重启 MCP Server 即可，Agent 无感 |
| **多语言** | 只能用 Agent 的语言写工具 | Server 可用任何语言（Python/Node/Go） |

### 4. MCP 传输层：stdio vs SSE

| 传输方式 | 工作原理 | 适用场景 |
|---------|---------|---------|
| **stdio** | Client 启动 Server 子进程，通过标准输入/输出通信 | 本地开发、单机部署 |
| **SSE** | Server 作为 HTTP 服务运行，Client 通过 HTTP 连接 | 远程工具、多 Client 共享 |

> week3 先用 **stdio**——最简单、零配置，Client 启动 Server 进程即可通信。

### 5. MCP 通信流程（一次工具调用）

```
Client                              Server
  │                                    │
  │──── initialize ──────────────────►│  ① 握手：交换协议版本和能力
  │                                    │
  │◄─── {serverInfo, capabilities} ───│
  │                                    │
  │──── tools/list ──────────────────►│  ② 发现：获取所有可用工具
  │                                    │
  │◄─── [{name:"query_orders", ...}] ──│
  │                                    │
  │──── tools/call ──────────────────►│  ③ 调用：执行具体工具
  │     {name:"query_orders",          │
  │      arguments:{customer:"深圳"}}   │
  │                                    │
  │◄─── {content: [{type:"text",       │  ④ 返回结果
  │        text:"查到 8 条订单..."}]}   │
```

> **关键**：MCP 把"有哪些工具"（发现）和"怎么调用工具"（执行）标准化了。Client 不需要事先知道 Server 有什么工具，连上后自动发现。

### 6. FastMCP：Python SDK 最快上手方式

```python
from mcp.server.fastmcp import FastMCP

# ① 创建 Server
mcp = FastMCP("我的工具服务器")

# ② 注册工具（装饰器方式）
@mcp.tool()
def query_orders(customer: str = None, status: str = None) -> str:
    """查询订单列表。按客户名、状态筛选。"""
    # ... 查询逻辑 ...
    return result

# ③ 启动 Server（stdio 传输）
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**FastMCP 帮我们做了什么**：
- 自动从函数签名 + docstring 生成 JSON Schema
- 自动处理 MCP 协议的 JSON-RPC 消息
- 自动注册 `tools/list` 和 `tools/call` 处理器

### 7. 我们的 week3 day2 架构

```
┌──────────────────────────────────────────┐
│         week3_mcp_server.py               │
│                                           │
│  ToolRegistry (day1)                      │
│  ├─ query_orders                          │
│  ├─ query_customer                        │
│  ├─ search_knowledge_base                 │
│  ├─ query_inventory          ← 新增       │
│  ├─ query_machine_load       ← 新增       │
│  ├─ plan_investigation                    │
│  └─ submit_final_answer                   │
│                                           │
│  FastMCP("调度助手工具服务器")              │
│  └─ 把 ToolRegistry 中的工具逐个注册       │
│                                           │
│  Transport: stdio     ← 标准输入/输出      │
└──────────────────────────────────────────┘
         ▲
         │ MCP 协议（stdio）
         │
┌────────┴─────────────────────────────────┐
│  Client（你的 Agent / Claude Desktop）     │
│  - 连接后自动发现 7 个工具                  │
│  - 调用 tools/call 执行                   │
└──────────────────────────────────────────┘
```

---

## Week 3 代码理解脉络

> 学完 Day1-2 的理论后，先看一眼这张图，建立全局认知再深入代码。

### 一句话

Week 3 的代码是一栋 **三层小楼**：底层管数据，中层管工具，上层管调度。

### 全景图

```
┌──────────────────────────────────────────────────────────────────┐
│                    第 3 层 · Agent 编排                           │
│                   langgraph_agent.py（~500 行）                    │
│                                                                  │
│  用户提问  ──→  analyze_intent  ──→  select_and_execute           │
│                   ↑                      │  LLM 决策 + 工具执行    │
│                   │                      ▼                        │
│                   │               evaluate_results               │
│                   │                      │                        │
│                   └── needs_more_data ───┘                        │
│                                          │                        │
│                                    generate_answer ──→ 调度建议   │
│                                                                  │
│  核心机制：                                                       │
│  · TOOLS 注册表 — Agent 的"能力清单"（6 个工具）                   │
│  · AgentState  — 贯穿所有节点的共享状态                            │
│  · 条件边      — 数据不够→继续查, 够了→生成答案, 超过5轮→强制结束    │
│  · 主备降级    — 火山豆包失败→自动切 DeepSeek                      │
├──────────────────────────────────────────────────────────────────┤
│                    第 2 层 · MCP 工具                              │
│          order_server.py           resource_server.py             │
│          (3 个工具)                (3 个工具)                      │
│                                                                  │
│  · query_orders                  · query_inventory               │
│  · get_order_detail              · query_machine_load            │
│  · get_production_status         · query_customer                │
│                                                                  │
│  核心机制：                                                       │
│  · FastMCP — @mcp.tool() 装饰器注册工具                           │
│  · 自动生成 JSON Schema（函数签名 → parameters）                   │
│  · stdio 传输层（标准输入/输出通信）                                │
├──────────────────────────────────────────────────────────────────┤
│                    第 1 层 · 数据                                 │
│                 shared_data.py（~110 行）                          │
│                                                                  │
│  data/orders.csv   data/inventory.csv                            │
│  data/machines.csv data/customers.csv                             │
│                                                                  │
│  核心机制：                                                       │
│  · _read_csv() — 通用加载，返回 list[dict]                        │
│  · format_table() — 转 Markdown 表格（省 token + LLM 友好）       │
│  · filter_by()   — 多条件 AND 过滤                                │
└──────────────────────────────────────────────────────────────────┘
```

### 阅读顺序（自底向上）

```
第 1 步（10min）→ shared_data.py
   理解数据从哪来、怎么加载、怎么格式化
   关键问题：为什么返回 Markdown 表格而不是 JSON？

第 2 步（15min）→ order_server.py（只读这一个 Server 即可）
   理解 @mcp.tool() 的三件事：注册 → 生成 Schema → 路由
   关键问题：如果不用 FastMCP，手写需要多少代码？

第 3 步（10min）→ resource_server.py
   对比 order_server，找共性和差异
   关键问题：两个 Server 之间有没有依赖关系？

第 4 步（30min）→ langgraph_agent.py（重点）
   按 5 个模块阅读：TOOLS → Prompt → State → 节点 → 图
   关键问题：LLM 怎么知道该调哪个工具？调完怎么知道该继续还是结束？

第 5 步（5min） → 跑一遍 python langgraph_agent.py
   看日志输出，理解每一步发生了什么
```

### 三个"为什么"（理解设计意图）

| 设计决策 | 为什么这样？ |
|---------|-------------|
| 为什么数据层要独立一个文件？ | 换数据源（CSV→DB）时，上层代码一行不改 |
| 为什么拆成两个 MCP Server？ | 订单域和资源域独立演进，互不影响；新增"财务域"加一个 Server 即可 |
| 为什么用 LangGraph 而不是 while 循环？ | 状态集中管理、路由显式声明、条件边自动处理循环终止 |

---


## 今天的学习路径

```
上午 · 理论消化（本文档）
  ├─ 第 1 节：工具体系 → 理解 ToolRegistry 为什么取代硬编码
  ├─ 第 2-4 节：MCP 协议 → 理解 Client/Server/Transport
  ├─ 第 5 节：通信流程 → 理解一次工具调用经过哪些步骤
  └─ 第 6-7 节：FastMCP → 理解代码怎么写

下午 · 编码（参考本文档和代码注释）
  ├─ tool_registry.py    → 把理论第 1 节的 ToolRegistry 写成代码
  ├─ week3_mcp_server.py → 把理论第 6 节的 FastMCP 写成代码
  └─ test_mcp_client.py  → 验证 MCP 通信跑通
```

---

## 核心认知（今天最重要的 3 句话）

1. **工具注册中心 = 从"散落各处的 if/elif"到"集中管理的 register/execute"** —— 这是 Agent 架构化的第一步
2. **MCP = 工具调用的 USB 协议** —— Server 和 Client 解耦，工具可以独立开发、独立部署、跨语言复用
3. **description 是 Agent 选工具的唯一依据** —— Schema 里的 description 写得好不好，直接决定 Agent 能不能选对工具

---

## 参考资料

### Day 1-2：工具体系 + MCP

| 知识块 | 资料 |
|--------|------|
| ③ Tools/Skills | [Anthropic Tool Use Overview](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview) · [Function Calling 全平台实战](https://blog.csdn.net/weixin_42260382/article/details/162133638) |
| ④ MCP | [MCP 官方规范](https://modelcontextprotocol.io/specification/2025-03-26) ⭐ · [MCP 中文站](https://mcpcn.com/) ⭐ · [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) |

### Day 3-5：LangGraph + Agent 编排

| 知识块 | 资料 |
|--------|------|
| ⑥ LangGraph | [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/) ⭐ · [LangGraph 中文文档](https://langchain.com.cn/docs/langgraph/) · [GitHub](https://github.com/langchain-ai/langgraph) |
| ② Agent 核心机制 | [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) ⭐ · [吴恩达 Agentic Design Patterns](https://www.deeplearning.ai/short-courses/ai-agentic-design-patterns-with-autogen/) · [智能体设计模式](https://jimmysong.io/zh/book/agentic-design-patterns/) ⭐ |
| System Prompt 工程 | [Prompt Engineering Guide 中文版](https://www.promptingguide.ai/zh) ⭐ · [Anthropic Prompt Engineering](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering) |
| 主备降级 | [OpenAI 兼容协议](https://platform.openai.com/docs/api-reference/chat/create) · [DeepSeek API](https://platform.deepseek.com/api-docs/) · [火山引擎豆包](https://www.volcengine.com/docs/82379/1928261) |
| 多 Server 拆分 | [MCP 多 Server 架构](https://modelcontextprotocol.io/specification/2025-03-26/basic/) · [OpenAI Defining Namespaces](https://platform.openai.com/docs/guides/function-calling#defining-namespaces) |
| 状态管理 | [LangGraph State 文档](https://langchain-ai.github.io/langgraph/concepts/low_level/#state) · [OpenAI Tool Calling 消息格式](https://platform.openai.com/docs/guides/function-calling#tool-calls-and-tool-results) |

> 完整逐篇提炼（含阅读优先级、章节导航、预估阅读时间）见：[`day1_2_理论知识清单.md`](./day1_2_理论知识清单.md)
