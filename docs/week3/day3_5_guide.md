# 第三周 Day3-5 - MCP Client 多 Server + LangGraph 状态图 + Demo 串连

> **本周一句话**：Day1-2 把工具装进了 MCP Server，Day3-5 让 Agent 自己决定调哪个工具、调几次、什么时候停。
>
> 对应代码：`test_mcp_client.py` · `langgraph_agent.py` · `order_server.py` · `resource_server.py`
> 理论清单：[`day1_2_理论知识清单.md`](./day1_2_理论知识清单.md) 第 12-17 节（LangGraph / Agent 核心机制 / 状态管理 / 多 Server 拆分）

---

## 先看清全貌：week3 的两条路径

Day3-5 最容易卡住的地方，是代码里其实存在**两套调用路径**，不看破就会觉得"明明说好的 MCP stdio，怎么 langgraph_agent 里是直接 import？"

```
路径 A（真 MCP，Day2-3 验证协议）
  test_mcp_client.py  ──stdio──>  week3_mcp_server.py（单 Server · 7 工具）
  目的：证明 initialize -> list_tools -> call_tool 协议链路畅通
  这是 MCP 的 "Hello World"，不是给业务用的

路径 B（Demo，Day4-5 端到端调度）
  langgraph_agent.py  ──直接 import──>  order_server.py + resource_server.py（双 Server · 6 工具）
  目的：让 LangGraph Agent 稳定跑通端到端调度场景
  代码注释（langgraph_agent.py:44-48）明确写了这个取舍
```

**为什么 Demo 不走 stdio？** LangGraph 的节点在事件循环里同步执行，stdio MCP 是异步子进程通信，两者嵌套在培训 Demo 里容易踩坑（进程启动、管道关闭、async/sync 边界）。直接 import 函数**架构分层不变**（数据层 → 工具层 → 编排层），但执行稳定。生产环境把 `TOOLS[name]["fn"]` 换成 stdio `call_tool` 即可，上层节点代码一行不改--这才是分层架构的价值。

> 一句话：**路径 A 证明"协议通"，路径 B 证明"业务通"**。两者共用同一套工具函数和数据层，区别只在调用方式（stdio vs 函数调用）。

---

## Day 3：MCP Client + 多 Server

### 1. 从单 Server 到多 Server：为什么拆？

Day2 的 `week3_mcp_server.py` 把 7 个工具堆在一个 Server 里，跑 `test_mcp_client.py` 验证协议没问题。但工具数增长到 6+ 后，单 Server 出现三个问题：

| 问题 | 单 Server 的表现 | 拆分后 |
|------|-----------------|--------|
| **职责混杂** | 订单查询和库存查询挤在一个文件 | order_server 管订单域，resource_server 管资源域 |
| **独立演进** | 改库存工具要重启整个 Server | 只重启 resource_server，订单域无感 |
| **可扩展** | 新增财务域要动现有代码 | 加一个 finance_server，现有代码零改动 |

拆分原则（`resource_server.py:9-13` 注释）：

```
order_server（订单域）              resource_server（资源域）
├── query_orders                   ├── query_inventory
├── get_order_detail               ├── query_machine_load
└── get_production_status          └── query_customer
        │                                  │
        └──────── 共享 shared_data.py ──────┘
                  （数据层，互不调用）
```

- **高内聚**：同一业务域的工具放一起
- **低耦合**：两个 Server 共享数据层但**互不调用**对方工具
- **独立部署**：各自 `mcp.run(transport="stdio")`，独立进程

> 关键认知：两个 Server 之间**没有依赖关系**。它们只是恰好读同一批 CSV，谁都不调谁。新增"财务域"就是加一个 `finance_server.py`，不动现有代码。

### 2. test_mcp_client.py：MCP 协议的 Hello World

这个脚本（133 行）是路径 A，目的是验证 stdio 通信链路。它连的是 **Day2 的单 Server**（`week3_mcp_server.py`），不是拆分后的双 Server--因为 Day3 的重点是"验证协议通"，不是"验证业务通"。

通信四步（对照 `test_mcp_client.py` 行号）：

```python
# ① 启动 Server 子进程，建立 stdio 管道（test_mcp_client.py:41-48）
server_params = StdioServerParameters(command="python", args=[str(_SERVER_PATH)])
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:

        # ② 握手：交换协议版本和能力（:51）
        await session.initialize()

        # ③ 发现工具：Client 不需要事先知道 Server 有什么工具（:55）
        tools_result = await session.list_tools()

        # ④ 调用工具：传 name + arguments，拿回 content（:74-116）
        result = await session.call_tool("tool_query_orders", {"customer": "深圳"})
```

**这四步对应 MCP 规范的生命周期**（理论清单第 9 节）：

```
Client                              Server
  │──── initialize ──────────────────►│  ① 握手
  │◄─── {serverInfo, capabilities} ───│
  │──── tools/list ──────────────────►│  ② 发现
  │◄─── [{name, description,          │
  │       inputSchema}] ──────────────│
  │──── tools/call ──────────────────►│  ③ 调用
  │◄─── {content: [{type:"text", ...}]}│  ④ 返回
```

脚本里连续调了 4 个工具（query_orders / query_inventory / query_machine_load / query_customer），每个都走一遍 `call_tool`。注意调用名带 `tool_` 前缀（如 `tool_query_orders`），这是 `week3_mcp_server.py` 里 `@mcp.tool()` 装饰的函数名--**MCP 的工具名就是函数名**，FastMCP 自动从函数签名生成 `inputSchema`。

> **关键认知**：Client 连上后**自动发现**工具有什么、参数是什么。这就是 MCP 相比 week2 硬编码 TOOLS 列表的核心优势--工具定义和 Agent 代码彻底解耦。

### 3. 多 Server 调度：Agent 如何跨 Server？

路径 B 里，`langgraph_agent.py` 同时用两个 Server 的工具。它是怎么跨 Server 调度的？

答案在 `TOOLS` 注册表（`langgraph_agent.py:110-219`）--**所有工具平铺在一个字典里，不按 Server 分组**：

```python
TOOLS = {
    "query_orders":      {"fn": query_orders,      "server": "order_server",    "schema": {...}},
    "get_order_detail":  {"fn": get_order_detail,  "server": "order_server",    "schema": {...}},
    ...
    "query_inventory":   {"fn": query_inventory,   "server": "resource_server", "schema": {...}},
    "query_machine_load":{"fn": query_machine_load,"server": "resource_server", "schema": {...}},
    "query_customer":    {"fn": query_customer,    "server": "resource_server", "schema": {...}},
}
```

三个字段各自的用途：

| 字段 | 用途 | 谁用它 |
|------|------|--------|
| `fn` | Python 函数对象，实际执行 | `select_and_execute` 节点（:387） |
| `server` | 所属 Server 名 | **仅用于日志分组**（:384 打印 `[{server}]`） |
| `schema` | OpenAI Function Calling 格式 | 发给 LLM 做决策（:364） |

**LLM 决策时根本不知道有"两个 Server"**--它看到的是 6 个平铺的工具 schema，根据 description 选一个调用。`server` 字段只在打印日志时显示来源，方便人看：

```
 -> [order_server] query_orders({'status': '生产中'})
 -> [resource_server] query_machine_load({})
```

> 这是多 Server 架构的精髓：**对 LLM 透明**。Server 拆分是工程层面的解耦决策，不该泄漏到 LLM 的决策上下文里--否则 LLM 还得学会"先选 Server 再选工具"，徒增错误率。

### 4. Demo 路径的架构取舍（必懂）

把路径 A 和路径 B 放一起对比，看清"保留了什么、牺牲了什么"：

| 维度 | 路径 A（test_mcp_client） | 路径 B（langgraph_agent） |
|------|--------------------------|--------------------------|
| **调用方式** | stdio 子进程 + JSON-RPC | Python 函数直接 import |
| **连的 Server** | week3_mcp_server（单·7工具） | order_server + resource_server（双·6工具） |
| **协议开销** | 有（序列化/管道/async） | 无 |
| **稳定性** | 受进程/async 边界影响 | 高（纯函数调用） |
| **架构分层** | 完整三层 | 完整三层（分层不变，只换调用方式） |
| **用途** | 验证 MCP 协议 | 跑端到端业务 Demo |

`langgraph_agent.py:44-48` 的注释把这件事说得很清楚：

```python
# ---- 工具导入（MCP 架构：两个 Server 的工具函数） ----
# 在实际 MCP 部署中，这些工具通过 stdio 管道调用
# 这里为了 Demo 稳定性，直接 import 函数，但架构分层不变
from order_server import query_orders, get_order_detail, get_production_status
from resource_server import query_inventory, query_machine_load, query_customer
```

**保留了什么**：三层架构（shared_data → order/resource_server → langgraph_agent）、TOOLS 注册表的 `server` 分组、工具的独立定义。**牺牲了什么**：真正的进程隔离和协议通信。**怎么补回**：把 `TOOLS[name]["fn"](**args)`（:389）换成 `await session.call_tool(name, args)`，上层 `select_and_execute` 节点逻辑不变。

> 设计意图：培训 Demo 优先保证"能跑通、能看清逻辑"，而不是"架构最纯粹"。真实生产里 stdio/HTTP 才是多 Server 的正确打开方式。

---

## Day 4：LangGraph 状态图

### 1. 为什么用 StateGraph 而不是 while 循环？

week2 的 `week2_agentic_rag_agent.py` 用手写 while 循环跑 Agent，week3 换成 LangGraph。对比：

```
week2（手写 while）                     week3（LangGraph StateGraph）
───────────────────────                ─────────────────────────────
state 是局部变量，散落在函数里          State 是 TypedDict，全图共享
路由靠 if/else 嵌在循环体里             路由靠条件边显式声明
循环终止靠手动 break                    循环终止靠条件边返回值 + END
调试靠 print                            自带执行追踪，可可视化
```

LangGraph 把 Agent 建模为**节点（Node）+ 边（Edge）的有向图**，支持条件分支和循环--这正是多轮工具调用需要的。

### 2. AgentState：贯穿全图的状态

`langgraph_agent.py:277-281` 定义了四个字段：

```python
class AgentState(TypedDict):
    messages: list[dict[str, Any]]      # 完整对话历史（system+user+assistant+tool）
    tool_results: list[dict[str, Any]]  # 工具调用结果汇总，用于统计和兜底
    iteration: int                       # 当前迭代次数，安全阀（≥5 强制结束）
    final_answer: str                    # 最终输出
```

| 字段 | 类型 | 作用 | 谁读它 | 谁写它 |
|------|------|------|--------|--------|
| `messages` | list[dict] | LLM 的上下文 | 所有节点 | select_and_execute / generate_answer |
| `tool_results` | list[dict] | 结果汇总，统计+兜底 | generate_answer（兜底） | select_and_execute |
| `iteration` | int | 防死循环计数 | should_continue | select_and_execute |
| `final_answer` | str | 最终输出 | run_agent（打印） | generate_answer |

> **为什么用 TypedDict 而不是 Pydantic？** 零依赖、轻量，适合 Agent 状态（不需要复杂校验）。LangGraph 原生支持，生产环境可无痛升级为 Pydantic BaseModel（理论清单第 16 节）。

`messages` 遵循 OpenAI 标准四种 role（理论清单第 16 节有完整格式）：

```
system    -> {"role": "system", "content": "你是调度专家..."}        ← SYSTEM_PROMPT
user      -> {"role": "user", "content": "今天先做哪些订单？"}
assistant -> {"role": "assistant", "content": null, "tool_calls":[...]} ← LLM 决策
tool      -> {"role": "tool", "tool_call_id": "xxx", "content": "..."}  ← 工具结果
```

### 3. 四个节点

#### 节点 1：analyze_intent（:328-335）--意图分析（当前占位）

```python
def analyze_intent(state: AgentState) -> AgentState:
    user_msg = next((m["content"] for m in reversed(state["messages"]) if m["role"] == "user"), "")
    print(f" 用户提问：{user_msg}")
    return state
```

当前只打印用户提问，**不做真正的意图分类**。注释（:325-326）写明了扩展方向：生产环境可改成意图分类器 → 路由到不同处理策略。这是 LangGraph 的典型用法--节点是"插槽"，先占位再填实现。

#### 节点 2：select_and_execute（:359-418）--核心：决策 + 执行 + 注入

这是整个 Agent 最关键的节点，做三件事：

```
┌─────────────────────────────────────────────────────┐
│  select_and_execute（一次迭代）                        │
│                                                      │
│  步骤 1 · 决策（:364-371）                            │
│    tools_schema = [t["schema"] for t in TOOLS]       │
│    response = call_llm(messages, tools_schema)       │
│    ↓ LLM 返回两种可能：                                │
│      a) tool_calls -> "我要调工具"                    │
│      b) content    -> "信息够了，直接答"               │
│                                                      │
│  步骤 2 · 执行（:374-398）                            │
│    for tc in msg.tool_calls:                         │
│        args = json.loads(tc.function.arguments)      │
│        result = TOOLS[tool_name]["fn"](**args)       │
│        state["tool_results"].append({...})           │
│                                                      │
│  步骤 3 · 注入（:402-415）                            │
│    追加 assistant 消息（含 tool_calls 元数据）         │
│    逐个追加 tool 消息（含 tool_call_id + 结果）        │
│    iteration += 1                                    │
└─────────────────────────────────────────────────────┘
```

**三个关键细节**：

1. **并行调用**（:374）：LLM 可以一次返回多个 `tool_calls`，for 循环逐个执行。这是 OpenAI Parallel Tool Calling 的体现（理论清单资源 J）。
2. **参数解析容错**（:378-381）：`json.loads` 失败就用空参数 `{}`，不让一个坏参数搞崩整轮。
3. **消息格式严格遵循 OpenAI 标准**（:402-415）：assistant 消息带 `tool_calls`，每条 tool 消息带 `tool_call_id` 配对。格式错了 LLM 会报错。

> 步骤 3 的消息注入是 Agent 多轮对话的核心：**工具结果以 tool role 消息回到 messages 里，下一轮 LLM 就能看到这些结果继续推理**。这就是 ReAct 模式的"观察"环节（理论清单第 13 节）。

#### 节点 3：evaluate_results（:428-430）--评估（当前占位）

```python
def evaluate_results(state: AgentState) -> AgentState:
    return state  # 直接返回，不做判断
```

和 analyze_intent 一样是**占位节点**。当前路由判断完全由条件边 `should_continue` 做，这个节点留作扩展：未来可在这里检查数据完整性、置信度，把"够不够"的判断从消息角色推断升级为显式评估。

#### 节点 4：generate_answer（:479-513）--综合生成

两条路径进入此节点：

```
路径 1：LLM 在 select_and_execute 里直接回了文本（没调工具）
        → last_msg 是 assistant + content + 无 tool_calls
        → 直接复用为 final_answer（:484-486）

路径 2：迭代到 5 轮强制结束（安全阀触发）
        → last_msg 是 tool 结果
        → 追加 summary_prompt，让 LLM 做最终综合（:489-504）
        → LLM 调用失败时，兜底返回原始 tool_results（:505-509）
```

兜底逻辑（:505-509）值得注意：LLM 万一挂了，Agent 不会崩，而是把已收集的工具数据吐出来--这是企业级 Agent 的容错意识。

### 4. 条件边 should_continue：路由的心脏

`should_continue`（:446-463）是条件边函数，读 state 返回下一个节点名。三种情况：

```python
def should_continue(state: AgentState) -> str:
    # ① 安全阀：最多 5 轮，防死循环
    if state["iteration"] >= 5:
        return "generate_answer"

    last_msg = state["messages"][-1] if state["messages"] else {}

    # ② 工具结果刚返回 -> 继续让 LLM 决策
    if last_msg.get("role") == "tool":
        return "select_and_execute"

    # ③ assistant 发出了 tool_calls -> 继续执行（防御性分支）
    if last_msg.get("role") == "assistant" and last_msg.get("tool_calls"):
        return "select_and_execute"

    # ④ assistant 直接回复了文本 -> 生成最终答案
    return "generate_answer"
```

| 情况 | 触发条件 | 路由到 | 含义 |
|------|---------|--------|------|
| ① 安全阀 | iteration ≥ 5 | generate_answer | 防死循环，强制总结 |
| ② 工具结果 | last msg role == tool | select_and_execute | LLM 看结果继续决策 |
| ③ 有 tool_calls | last msg 是 assistant+tool_calls | select_and_execute | 防御性，正常不会触发 |
| ④ 直接回答 | last msg 是 assistant+content | generate_answer | 信息够了，收尾 |

> **情况 ③ 为什么是防御性？** 正常流程里 select_and_execute 执行完 tool_calls 后，最后一条消息一定是 tool 结果（情况 ②）。③ 是兜底，防止某轮 LLM 只返回 tool_calls 但工具执行异常没追加 tool 消息时卡死。条件边写多个分支比单 else 安全。

类比：`should_continue` 就是前端的路由守卫 `router.beforeEach()`--根据当前状态决定下一步去哪。

### 5. build_graph：组装状态图（:530-558）

LangGraph 的核心 API 六步：

```python
def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)                    # ① 创建状态图，指定 State 类型

    graph.add_node("analyze_intent", analyze_intent)  # ② 添加节点
    graph.add_node("select_and_execute", select_and_execute)
    graph.add_node("evaluate_results", evaluate_results)
    graph.add_node("generate_answer", generate_answer)

    graph.set_entry_point("analyze_intent")           # ③ 设置入口

    graph.add_edge("analyze_intent", "select_and_execute")      # ④ 普通边（固定流向）
    graph.add_edge("select_and_execute", "evaluate_results")

    graph.add_conditional_edges("evaluate_results", should_continue, {  # ⑤ 条件边
        "select_and_execute": "select_and_execute",
        "generate_answer": "generate_answer",
    })

    graph.add_edge("generate_answer", END)            # ⑥ 终止边

    return graph.compile()                            # 编译成可执行对象
```

**普通边 vs 条件边**：

| 边类型 | API | 流向 | 何时用 |
|--------|-----|------|--------|
| 普通边 | `add_edge(from, to)` | 固定 | 上一步完了一定去下一步 |
| 条件边 | `add_conditional_edges(from, router, mapping)` | 动态 | 需要根据 state 决定去哪 |

条件边的 `mapping`（:549-552）把 `should_continue` 的返回值映射到节点名。这里 key 和 value 相同是因为返回值直接就是节点名。

编译后返回的 `app` 可调用 `app.invoke(state)`（同步，:596）或 `app.stream(state)`（流式，生产常用）。

### 6. 一次完整循环的轨迹

以"今天先做哪些订单？"为例，追踪 messages 和 iteration 变化：

```
初始 state（run_agent 初始化，:582-590）
  messages = [system, user]  iteration = 0

── analyze_intent ──> 打印提问，state 不变

── select_and_execute（第 1 轮）──>
  LLM 看到 [system, user] + 6 工具，决定先查订单
  执行 query_orders(status="生产中")
  messages = [system, user, assistant(tool_calls), tool(结果)]
  iteration = 1

── evaluate_results ──> pass-through

── should_continue ──> last msg 是 tool → 返回 select_and_execute

── select_and_execute（第 2 轮）──>
  LLM 看到订单结果，决定查库存 + 设备 + 客户（并行 3 工具）
  iteration = 2

  ... 重复，直到 LLM 觉得数据够了 ...

── select_and_execute（第 N 轮）──>
  LLM 不再调工具，直接返回 content（调度建议文本）
  messages 末尾 = assistant(content, 无 tool_calls)

── should_continue ──> last msg 是 assistant+content → 返回 generate_answer

── generate_answer ──> 复用 assistant 内容为 final_answer → END
```

> 这就是 ReAct 模式的完整闭环：**感知（读 messages）→ 决策（LLM 选工具）→ 执行（调 TOOLS）→ 观察（tool 结果回灌）→ 再决策**。条件边让这个循环可以自动终止，不用手写 break。

---

## Day 5：Demo 串连

### 1. 端到端场景

Day5 把 Day1-4 的所有零件串起来跑一个真实调度场景。`DEMO_SCENARIOS`（:571-577）第一个是典型：

> "今天先做哪些订单？帮我综合考虑交期紧迫度、客户等级、材料库存和设备负载情况，给出优先级排序。"

Agent 自主决策的典型轨迹（README 记录约 8 次工具调用，横跨两个 Server）：

```
用户提问
  ↓
[order_server] query_orders(状态=生产中)        → 拿到在产订单清单
  ↓
[resource_server] query_machine_load()          → 看哪些设备有空
  ↓
[order_server] get_order_detail(ORD00x)         → 深挖关键订单详情
  ↓
[resource_server] query_inventory(材料名)        → 查关键材料库存
  ↓
[resource_server] query_customer(客户名)         → 查客户等级/信用
  ↓
... LLM 综合交期/客户/库存/设备，按优先级排序 ...
  ↓
generate_answer → "今日优先排产 ORD00x，理由：交期最紧+客户A级+材料充足+设备空闲"
```

> 注意：Agent **不是按固定顺序调工具**，而是 LLM 每轮根据已得结果决定下一步。换个问题（如"PEEK 材料库存够吗"），调用顺序会完全不同。这是 Agent 模式 vs 固定 Workflow 的本质区别（理论清单资源 H）。

### 2. 三种运行模式（:607-659）

`main()` 支持三种入口：

| 模式 | 命令 | 用途 |
|------|------|------|
| 命令行传参 | `python langgraph_agent.py "ORD001 能按时交付吗？"` | 跑单个问题 |
| 预设场景 | `python langgraph_agent.py --demo` | 选 1-5 场景或全部演示 |
| 交互模式 | `python langgraph_agent.py` | 循环提问，输 quit 退出 |

`--demo` 模式会列出 5 个场景让用户选编号（:621-639），回车则全部跑一遍--适合分享演示。

### 3. DEMO_SCENARIOS 五个场景（:571-577）

| # | 场景 | 考察点 |
|---|------|--------|
| 1 | "今天先做哪些订单？综合交期/客户/库存/设备" | 端到端多工具综合排序 |
| 2 | "ORD001 能按时交付吗？" | 单订单深挖（detail + 物料 + 设备） |
| 3 | "有哪些紧急订单？哪些设备和材料是瓶颈？" | 瓶颈识别 |
| 4 | "东莞模具厂的订单总体情况？信用如何？" | 按客户聚合 + 客户档案 |
| 5 | "PEEK 材料库存够吗？不够会影响哪些订单？" | 反向排查（材料→订单） |

这 5 个场景覆盖了调度业务的典型问法，从不同角度验证 Agent 的工具选择能力。

### 4. run_agent 执行流（:580-604）

```python
def run_agent(app, query: str):
    # ① 构造初始 state
    initial_state: AgentState = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},   ← 岗位说明书
            {"role": "user", "content": query},
        ],
        "tool_results": [],
        "iteration": 0,
        "final_answer": "",
    }
    # ② 编译后的图执行（同步）
    result = app.invoke(initial_state)
    # ③ 打印最终建议 + 工具调用统计
    print(result["final_answer"])
    print(f"工具调用统计：{len(result['tool_results'])} 次")
    for tr in result["tool_results"]:
        print(f"  [{TOOLS[tr['tool']]['server']}] {tr['tool']}({tr['arguments']})")
```

最后的统计打印（:602-604）会把每次工具调用按 Server 分组列出，方便复盘 Agent 的决策路径。这也是 `TOOLS[name]["server"]` 字段的唯一用途--日志可观测。

---

## Week3 代码阅读顺序（Day3-5）

> Day1-2 的阅读顺序见 `day1_2_guide.md` 末尾。Day3-5 自底向上接着读：

```
第 1 步（10min）-> test_mcp_client.py
   理解 MCP 协议四步通信
   关键问题：Client 怎么知道 Server 有哪些工具？

第 2 步（10min）-> order_server.py + resource_server.py
   对比两个 Server，找共性和差异
   关键问题：两个 Server 之间有没有依赖？为什么拆？

第 3 步（40min）-> langgraph_agent.py（重点）
   按 5 个模块读：TOOLS(:110) -> SYSTEM_PROMPT(:235) -> AgentState(:277)
                 -> 四节点(:328/:359/:428/:479) -> build_graph(:530)
   关键问题：LLM 怎么知道调哪个工具？调完怎么知道该继续还是结束？

第 4 步（5min）-> 跑 python langgraph_agent.py --demo
   选场景 1，看日志里的 [server] 工具调用轨迹
   关键问题：8 次调用分别是什么？为什么是这个顺序？

第 5 步（5min）-> 跑 python test_mcp_client.py
   看真 MCP 协议通信的握手/发现/调用输出
   关键问题：和路径 B 的直接函数调用有什么不同？
```

---

## 今天的学习路径

```
上午 · 理论消化（配合 day1_2_理论知识清单.md 第 12-17 节）
  ├─ 第 12 节：LangGraph 状态图 -> StateGraph / Node / Edge / 条件边
  ├─ 第 13 节：Agent 核心机制 -> ReAct 循环 / Tool Choice / 安全阀
  ├─ 第 16 节：Agent 状态管理 -> AgentState 四字段 / 消息格式
  └─ 第 17 节：多 Server 拆分 -> 高内聚低耦合 / 跨 Server 调度

下午 · 代码走读（参考本文档）
  ├─ test_mcp_client.py      -> 验证 MCP 协议链路（路径 A）
  ├─ order/resource_server.py -> 理解双 Server 拆分
  └─ langgraph_agent.py       -> 逐节点读 StateGraph（路径 B）
     重点：select_and_execute 的决策+执行+注入三步，should_continue 的三种路由
```

---

## 核心认知（Day3-5 最重要的 5 句话）

1. **两条路径并存** -- 路径 A（test_mcp_client + stdio）证明协议通，路径 B（langgraph_agent + 直接 import）证明业务通。Demo 为稳定性选了直接 import，但三层架构分层不变，换 stdio 只改调用方式。
2. **多 Server 对 LLM 透明** -- TOOLS 注册表平铺所有工具，`server` 字段仅用于日志。LLM 只看 description 选工具，不需要知道 Server 拆分。
3. **StateGraph = State + Node + 条件边** -- State 全图共享，Node 是插槽（可占位），条件边 `should_continue` 是路由心脏。手写 while 循环的 if/else 路由被显式声明取代。
4. **select_and_execute 是 ReAct 闭环** -- 决策（LLM 选工具）→ 执行（TOOLS 调函数）→ 注入（tool 结果回灌 messages），下一轮 LLM 就能看到结果继续推理。
5. **安全阀 + 兜底 = 企业级容错** -- iteration ≥ 5 防死循环，generate_answer 的 LLM 失败兜底返回原始数据，Agent 不会崩。

---

## 参考资料

理论部分已写在 [`day1_2_理论知识清单.md`](./day1_2_理论知识清单.md) 第 12-17 节（含权威链接），此处不重复。重点对应关系：

| Day | 理论清单章节 | 代码文件 |
|-----|------------|---------|
| Day 3 | 第 9 节（MCP 通信流程）· 第 17 节（多 Server 拆分） | test_mcp_client.py · order_server.py · resource_server.py |
| Day 4 | 第 12 节（LangGraph 状态图）· 第 13 节（Agent 核心机制）· 第 16 节（状态管理） | langgraph_agent.py |
| Day 5 | 第 13 节（ReAct 模式）· 第 14 节（System Prompt 工程化） | langgraph_agent.py（DEMO_SCENARIOS + run_agent） |

阅读路线（理论清单末尾）：资源 G（LangGraph 官方文档）+ 资源 H（Building Effective Agents）是 Day3-5 必读。
