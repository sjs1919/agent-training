# LangChain + LangGraph 理论与结合点

> **为什么单独拎出来讲**：week3 的 `langgraph_agent.py` 用了 LangGraph（`from langgraph.graph import StateGraph`），但 LLM 调用的是**原生 OpenAI SDK**（`from openai import OpenAI`），没碰 LangChain 的任何抽象。所以走读完代码，"LangGraph 会用了，但 LangChain 到底是啥、两者什么关系"还是没底。本文档补这个理论地基。
>
> 配合阅读：[`day1_2_理论知识清单.md`](./day1_2_理论知识清单.md) 第 12 节（LangGraph 状态图简版）· 本文档是它的深化 + LangChain 部分

---

## 0. 先看全景：三者是什么关系

```
┌──────────────────────────────────────────────────────────┐
│                   langchain-core（地基）                   │
│                                                          │
│   Runnable 接口 · BaseMessage 消息类型 · Tool 定义 ·       │
│   PromptTemplate · 输出解析基类                            │
└──────────────────────────────────────────────────────────┘
            ▲                              ▲
            │ 依赖                          │ 依赖
            │                              │
┌───────────┴──────────────┐   ┌───────────┴──────────────────┐
│      LangChain            │   │         LangGraph             │
│  （组件层 / 做什么）        │   │   （编排层 / 怎么串）           │
│                           │   │                              │
│  · ChatModel（调 LLM）     │   │  · StateGraph（状态图）        │
│  · PromptTemplate          │   │  · Node / Edge / 条件边       │
│  · OutputParser            │   │  · State + Reducer           │
│  · Retriever（RAG 检索）    │   │  · Checkpointer（持久化）     │
│  · Memory / Tools          │   │  · 多 Agent 编排              │
│  · LCEL（管道组合）         │   │                              │
└───────────────────────────┘   └──────────────────────────────┘
        ▲                                        ▲
        │          节点里可调用 LangChain 组件       │
        └──────────────────┬──────────────────────┘
                           │
                  ┌────────┴────────┐
                  │   你的 Agent 应用  │
                  └─────────────────┘
```

**三句话**：
1. `langchain-core` 是**地基**，定义Runnable 接口和消息/工具类型--LangChain 和 LangGraph 都依赖它。
2. LangChain 是**组件层**：怎么调模型、怎么写 prompt、怎么检索、怎么解析输出。
3. LangGraph 是**编排层**：怎么把这些组件串成有状态、能循环、能分支的工作流。

> 关键认知：**LangGraph 不是 LangChain 的替代品，是它的编排补全**。你可以只用 LangGraph（像 week3 那样），也可以在 LangGraph 节点里调用 LangChain 组件--后者才是"全家桶"用法。

---

## 1. LangChain 是什么

### 1.1 定位

LangChain 是 LangChain Inc.（Harrison Chase 创立）开源的 **LLM 应用开发框架**。它解决的核心问题：**裸 LLM 调用是"无状态、单次请求"，但真实应用需要 prompt 管理、记忆、检索、工具调用、输出解析**。

```
裸 OpenAI 调用：        client.chat.completions.create(messages=[...])
                       ↑ 每次 自己拼 messages、自己解析输出、自己管记忆

LangChain：             model.invoke(prompt)  ← prompt 模板化、输出结构化、记忆自动化
```

### 1.2 核心抽象：Runnable + LCEL

LangChain 最重要的一件事是把所有组件统一成 **Runnable** 接口，然后用 **LCEL**（LangChain Expression Language）把它们像管道一样串起来。

**Runnable 接口**（统一四个方法）：

| 方法 | 同步/异步 | 用途 |
|------|----------|------|
| `invoke` | 同步 | 单次输入 -> 单次输出 |
| `stream` | 同步 | 流式输出（逐 token） |
| `batch` | 同步 | 批量输入并行处理 |
| `ainvoke / astream / abatch` | 异步 | 异步版本 |

> 为什么统一接口？因为这样**任何组件都能用同一种方式组合和调用**。prompt、model、parser、retriever 都是 Runnable，所以能用 `|` 串起来。

**LCEL（管道组合）**：

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# 三个 Runnable 用 | 串成一条链
chain = (
    ChatPromptTemplate.from_template("用一句话解释 {topic}")   # Runnable 1: prompt 模板
    | ChatOpenAI(model="gpt-4o-mini")                          # Runnable 2: 调模型
    | StrOutputParser()                                         # Runnable 3: 解析输出
)

# 整条链也是 Runnable，统一调用
result = chain.invoke({"topic": "LangGraph"})
```

`|` 运算符的语义：上一个 Runnable 的输出，作为下一个 Runnable 的输入。等价于 `parser.invoke(model.invoke(prompt.invoke(input)))`，但可读性高得多。

> **这是 LangChain 的灵魂**：一切皆 Runnable，用 `|` 组合。类比 Unix 管道 `cat | grep | sort`，每个命令读 stdin 写 stdout，组合出复杂流程。

### 1.3 组件清单

| 组件 | 作用 | week3 代码里的对应 |
|------|------|-------------------|
| **ChatModel / LLM** | 调用大模型 | 用原生 `OpenAI` 替代了（:89） |
| **PromptTemplate** | 模板化 prompt | 用 f-string 手拼 `SYSTEM_PROMPT`（:235） |
| **OutputParser** | 把 LLM 文本解析成结构化数据 | 手写 `json.loads`（:379） |
| **Retriever** | RAG 检索接口 | week2 day2 的混合检索，未包成 Retriever |
| **Memory** | 对话记忆管理 | 用 `state["messages"]` 手动管理（:278） |
| **Tools** | 工具定义 + 调用 | `TOOLS` 注册表（:110） |
| **Chains（LCEL）** | 组件管道组合 | 无，week3 直接在节点里写逻辑 |

> 看这张表就懂 week3 的位置了：**它把 LangChain 的每个组件都手写了一遍**（手拼 prompt、手 parse JSON、手管 messages），目的是让你看清底层机制。生产环境这些都应该用 LangChain 的现成组件。

### 1.4 包结构（重要，别装错）

LangChain 拆成了多个包，初学者常装错：

| 包 | 内容 | 是否需要 |
|----|------|---------|
| `langchain-core` | 核心抽象（Runnable / Message / Tool 基类） | LangGraph 自动依赖，通常不用单独装 |
| `langchain` | 通用链、agent 基础 | 用 LangChain 组件时装 |
| `langchain-community` | 第三方集成（各种向量库、文档加载器） | 按需 |
| `langchain-openai` / `langchain-anthropic` 等 | 各模型厂商的 partner 包 | 用哪家模型装哪家 |
| `langgraph` | 图编排框架 | week3 已装 |

> week3 的 `requirements.txt` 装了 `langgraph` 和 `langchain-core`，没装 `langchain` / `langchain-openai`--印证了"只用 LangGraph，没用 LangChain 组件"。

---

## 2. LangGraph 是什么

### 2.1 定位

LangGraph 是 LangChain 团队推出的**有状态、有环图的 Agent 编排框架**。它把 Agent 的决策过程建模为**节点 + 边的有向图**，显式支持循环和条件分支--这是多轮工具调用、反思、人机协作必需的。

### 2.2 为什么诞生？（关键背景）

LangChain 早期用 **AgentExecutor** 跑 Agent--本质是个**固定的 while 循环**：`LLM 决策 -> 调工具 -> 观察结果 -> 再决策`。但它有三个硬伤：

| AgentExecutor 的问题 | LangGraph 怎么解决 |
|---------------------|-------------------|
| 循环逻辑写死在框架里，无法定制 | 把循环显式建模为**条件边**，你想怎么绕就怎么绕 |
| 难做 human-in-the-loop（中途暂停等人确认） | **Checkpointer** 持久化状态，可随时暂停/恢复 |
| 状态管理混乱（藏在框架内部） | **State** 显式定义，全图共享，可观测 |
| 难做多 Agent 协作 | 图天然支持多节点 = 多 Agent |

> **演进关系**：LangGraph 不是凭空发明的，是把 AgentExecutor 那个黑盒 while 循环**拆开变成白盒图**。现在 LangChain 官方**推荐用 LangGraph 构建 Agent**，AgentExecutor 已退居 legacy。week3 直接学 LangGraph 是对的，跳过了过时的 AgentExecutor。

### 2.3 核心概念

| 概念 | 说明 | week3 代码对应 |
|------|------|---------------|
| **StateGraph** | 状态图，所有节点共享同一个 State | `StateGraph(AgentState)`（:532） |
| **Node** | 节点函数，接收 State 返回 State | `analyze_intent` / `select_and_execute` / `evaluate_results` / `generate_answer` |
| **Edge** | 普通边，固定流向 | `add_edge("analyze_intent", "select_and_execute")`（:544） |
| **Conditional Edge** | 条件边，根据 State 动态路由 | `add_conditional_edges("evaluate_results", should_continue, {...})`（:549） |
| **State** | 共享状态，TypedDict 或 Pydantic | `AgentState`（:277） |
| **Reducer** | 定义 State 字段如何合并更新 | **week3 没用**（见 2.4） |
| **Checkpointer** | 状态持久化（记忆/时间旅行/人机协作） | **week3 没用**（见 2.5） |
| **Compile** | 编译成可执行 Runnable | `graph.compile()`（:558） |
| **START / END** | 图的入口和终止 | `set_entry_point`（:541）/ `END`（:555） |

### 2.4 Reducer：week3 没用但该懂的细节

LangGraph 的 State 更新有个**坑**：节点返回的 State 字段**默认是覆盖**，不是追加。比如 `messages` 字段，如果节点返回 `{"messages": [新消息]}`，默认会**替换**整个 messages 列表，而不是追加。

**Reducer 就是为了解决这个问题**--声明某个字段用"追加"而非"覆盖"：

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # add_messages 是个 reducer 函数：返回的新消息会 append 到原列表
    messages: Annotated[list, add_messages]
    iteration: int
    final_answer: str
```

**week3 的做法**：不用 Reducer，而是在节点里**手动 mutate state 字典**（`state["messages"].append(...)`，:402），然后 `return state` 返回同一个对象。因为是在原对象上追加，覆盖不覆盖无所谓。这能跑，但**不是 LangGraph 的惯用风格**。

| 方式 | week3（手动 mutate） | 标准用法（Reducer） |
|------|---------------------|---------------------|
| 写法 | `state["messages"].append(msg); return state` | `return {"messages": [msg]}` |
| 状态更新 | 原地修改 | 框架按 reducer 合并 |
| 函数纯净性 | 不纯（有副作用） | 纯函数（易测试） |
| 并行节点 | 有风险（共享可变状态） | 安全（reducer 处理合并） |

> 生产环境推荐 Reducer 方式：节点是纯函数，返回"我想更新的字段"，框架负责合并。并行节点安全，测试也容易。

### 2.5 Checkpointer：week3 也没用但该懂

Checkpointer 是 LangGraph 的**状态持久化机制**，在每个节点执行后自动存档状态。三个用途：

| 用途 | 说明 | 没有 Checkpointer 时 |
|------|------|---------------------|
| **记忆** | 跨会话记住对话 | week3 每次重启 state 清零 |
| **时间旅行** | 回到某个历史节点重跑 | 无法回溯 |
| **人机协作** | 暂停等人确认，再恢复 | 无法暂停 |

```python
from langgraph.checkpoint.memory import MemorySaver

graph = build_graph()
app = graph.compile(checkpointer=MemorySawer())  # 传入 checkpointer

# 用 thread_id 区分会话
config = {"configurable": {"thread_id": "user-001"}}
app.invoke(initial_state, config)  # 自动存档每步状态
```

> week3 没用 Checkpointer，所以是"无记忆单次 Agent"。week4+ 做多 Agent / 鉴权时大概率要引入。

---

## 3. 结合点（本文档核心）

### 3.1 共享地基：langchain-core

LangChain 和 LangGraph **不是两个独立框架**，它们是建在同一个地基 `langchain-core` 上的兄弟：

```
langchain-core（地基）
  ├── Runnable 接口        ← LangChain 的链和 LangGraph 的图都实现它
  ├── BaseMessage 家族      ← HumanMessage / AIMessage / ToolMessage，两者共用
  ├── Tool 定义基类         ← LangChain 的 BaseTool 和 LangGraph 的 ToolNode 都基于它
  ├── PromptTemplate 基类   ← 两者共用
  └── OutputParser 基类     ← 两者共用
        ▲
        ├── langchain（组件实现：ChatOpenAI、各种 Retriever...）
        └── langgraph（编排实现：StateGraph、Checkpointer...）
```

**意义**：消息格式、工具定义、Runnable 接口是**通用的**。你在 LangChain 里定义的工具，能直接在 LangGraph 节点里用；反之亦然。没有"LangChain 消息"和"LangGraph 消息"两套东西。

### 3.2 Runnable 是通用胶水

这是最关键的结合点：**编译后的 LangGraph 也是一个 Runnable**。

```python
# LangChain 的 LCEL 链是 Runnable
chain = prompt | model | parser
chain.invoke({"topic": "x"})

# LangGraph 编译后的图也是 Runnable
app = graph.compile()
app.invoke(initial_state)   # ← week3 用的就是这个（:596）
app.stream(initial_state)   # 流式
```

**两者都支持 `invoke / stream / batch`**。这意味着：

1. **统一调用方式**：不管你用链还是图，对外都是 `xxx.invoke(input)`。
2. **可嵌套**：链里可以包图，图节点里可以调链。一个 LangGraph 节点完全可以是一条 LCEL 链。

```python
# 图节点里用 LangChain 链（典型的结合用法）
def analyze_intent(state):
    # 这条链就是 LangChain 组件
    chain = prompt_template | chat_model | StrOutputParser()
    intent = chain.invoke({"question": state["messages"][-1]})
    return {"intent": intent}
```

> week3 的节点里是**手写的 OpenAI 调用**（`call_llm` 函数，:294），没用 LCEL 链。如果引入 LangChain，`call_llm` 可以换成一条 `prompt | ChatOpenAI | parser` 链。

### 3.3 分工：组件 vs 编排

| 维度 | LangChain | LangGraph |
|------|-----------|-----------|
| **回答什么问题** | 怎么调模型？怎么写 prompt？怎么检索？怎么解析输出？ | 怎么把这些串成工作流？什么时候循环？什么时候分支？ |
| **抽象层级** | 组件（零件） | 编排（图纸） |
| **核心单元** | Runnable（链） | Node + Edge（图） |
| **状态** | 无状态（链是直线的，每次 invoke 独立） | 有状态（State 贯穿全图，可持久化） |
| **循环** | 不支持（链是 DAG，无环） | 原生支持（条件边绕回） |
| **适合** | 单次 RAG、简单问答、输出解析 | Agent、多轮工具调用、多 Agent、人机协作 |

**一句话**：LangChain 管"**做什么**"，LangGraph 管"**怎么串**"。

### 3.4 演进：AgentExecutor -> LangGraph

这是理解两者历史关系的关键：

```
2023  LangChain 用 AgentExecutor 跑 Agent
       （固定的 while 循环：LLM 决策 -> 调工具 -> 观察 -> 再决策）
       问题：黑盒、难定制、难暂停、难多 Agent
            │
            ▼
2024  LangGraph 诞生
       （把 while 循环拆成显式的 StateGraph，白盒可控）
       AgentExecutor 标记 legacy，官方推荐 LangGraph
            │
            ▼
2026  LangGraph 成为 LangChain 生态构建 Agent 的标准方式
       （week3 直接学 LangGraph，跳过 AgentExecutor，路线正确）
```

> week3 的 `langgraph_agent.py` 其实就是"用 LangGraph 手写了一个 AgentExecutor"。对比看：AgentExecutor 把 `LLM决策 -> 调工具 -> 观察 -> 再决策` 藏在框架里；week3 把它摊开成 `select_and_execute -> evaluate_results -> should_continue` 三个节点 + 条件边，你能看见每一步。

### 3.5 LangGraph 节点里用 LangChain 组件（标准结合用法）

week3 是"LangGraph + 原生 OpenAI"的极简组合。标准的"全家桶"用法是在 LangGraph 节点里用 LangChain 组件。对比同一件事的两种写法：

**week3 写法（LangGraph + 原生 OpenAI）**：
```python
from openai import OpenAI

def select_and_execute(state):
    tools_schema = [t["schema"] for t in TOOLS.values()]
    client = OpenAI(api_key=..., base_url=...)
    response = client.chat.completions.create(           # ← 手写 OpenAI 调用
        model="ark-code-latest",
        messages=state["messages"],
        tools=tools_schema,
        tool_choice="auto",
    )
    msg = response.choices[0].message
    # 手动解析 tool_calls、手动执行、手动注入 messages...
```

**标准写法（LangGraph + LangChain 组件）**：
```python
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode, ToolsCondition

model = ChatOpenAI(model="gpt-4o-mini").bind_tools(tools)   # ← LangChain 模型 + 工具绑定
tool_node = ToolNode(tools)                                  # ← LangGraph 预置工具节点

def call_model(state):
    response = model.invoke(state["messages"])               # ← LangChain 调用
    return {"messages": [response]}                          # ← Reducer 自动追加

graph = StateGraph(AgentState)
graph.add_node("call_model", call_model)
graph.add_node("tools", tool_node)                           # ← 不用手写工具执行
graph.add_conditional_edges("call_model", ToolsCondition(), {...})  # ← 预置路由
```

| 对比项 | week3 写法 | 标准结合写法 |
|--------|-----------|-------------|
| LLM 调用 | 手写 `OpenAI().chat.completions.create` | `ChatOpenAI().invoke` |
| 工具执行 | 手写 for 循环 + `TOOLS[name]["fn"]` | `ToolNode` 预置节点 |
| 路由判断 | 手写 `should_continue` | `ToolsCondition` 预置 |
| 消息管理 | 手动 `append` + 手拼 dict | `add_messages` Reducer 自动处理 |
| 代码量 | 多（看清机制） | 少（封装好） |
| 学习价值 | 高（暴露 Function Calling 细节） | 中（用现成轮子） |

> **为什么 week3 选极简写法**：培训目标是**看清 Agent 的运作机制**--Function Calling 怎么传 tools、tool_calls 怎么解析、tool 消息怎么回灌。用 LangChain 的 `ToolNode` + `ToolsCondition` 会把这些细节藏起来，学不到底层。**先手写理解原理，再用框架提效**，这是正确的学习顺序。

---

## 4. 回到 week3：你的代码在全景图里的位置

```
                    langchain-core（地基）
                    ┌─────┴─────┐
              LangChain          LangGraph
            （没用 ✗）          （用了 ✓）
                                  │
                          StateGraph + 条件边
                          + 手写节点
                                  │
                          LLM 调用：原生 OpenAI SDK（✗ 没用 ChatModel）
                          Prompt：f-string 手拼（✗ 没用 PromptTemplate）
                          输出：json.loads 手 parse（✗ 没用 OutputParser）
                          记忆：state["messages"] 手管（✗ 没用 Memory/Reducer）
                          工具：TOOLS 注册表（✗ 没用 BaseTool）
```

**week3 用了 LangGraph 的什么**：StateGraph、Node、Edge、Conditional Edge、Compile、END。
**week3 没用 LangGraph 的什么**：Reducer（手 mutate）、Checkpointer（无记忆）、预置 ToolNode/ToolsCondition。
**week3 没用 LangChain 的什么**：全部组件都没用（手写替代）。

> 这就是为什么走读完代码还觉得"LangChain 没底"--**你的代码里压根没出现 LangChain**。补完本文档的理论后，下一步如果要"体验结合点"，可以把 `langgraph_agent.py` 的 `call_llm` 改写成 `ChatOpenAI + LCEL`，或把 `select_and_execute` 拆成 `call_model + ToolNode` 两个节点，亲眼看看 LangChain 组件怎么嵌进 LangGraph。

---

## 5. 学习路径建议

```
第一步（1h）-> LangChain 核心：Runnable + LCEL
   重点：一切皆 Runnable，用 | 组合
   动手：写一条 prompt | model | parser 链，跑通 invoke/stream
   资源：LangChain 官方 Quickstart（见下）

第二步（30min）-> langchain-core 抽象
   重点：BaseMessage 家族、Tool 定义、PromptTemplate
   理解：为什么 LangGraph 和 LangChain 能共用这些

第三步（1h）-> LangGraph 深化（你已在用，补 Reducer + Checkpointer）
   重点：Reducer（add_messages）、Checkpointer（MemorySaver）
   动手：把 week3 的 AgentState 加上 Annotated[list, add_messages]，对比手写 mutate

第四步（1h）-> 结合点实战
   动手：把 week3 的 call_llm 换成 ChatOpenAI + LCEL，或引入 ToolNode
   目标：亲眼看 LangChain 组件嵌进 LangGraph 节点
```

> **顺序建议**：你已经在用 LangGraph，所以**先补 LangChain 的 Runnable/LCEL**（这是缺口最大的地方），再回头深化 LangGraph 的 Reducer/Checkpointer（你在用但没用到的高级特性），最后做结合实战。

---

## 6. 核心认知（6 句话）

1. **langchain-core 是共同地基** -- LangChain 和 LangGraph 都依赖它，共享 Runnable 接口、消息类型、工具定义。没有"两套消息格式"。
2. **Runnable 是通用胶水** -- LCEL 链是 Runnable，编译后的 LangGraph 也是 Runnable，都支持 invoke/stream/batch，可互相嵌套。
3. **LangChain 管组件，LangGraph 管编排** -- 前者回答"怎么调模型/写 prompt/检索/解析"，后者回答"怎么串成有状态工作流"。分工非替代。
4. **LangGraph 是 AgentExecutor 的白盒化** -- 把固定 while 循环拆成显式的图，可定制循环/分支/暂停/持久化。官方推荐用 LangGraph 构建 Agent。
5. **week3 是"LangGraph + 原生 OpenAI"的极简组合** -- 刻意没用 LangChain 组件，为了暴露 Function Calling 底层机制。先手写理解，再用框架提效。
6. **结合点 = 在 LangGraph 节点里调用 LangChain 组件** -- `ToolNode`、`ChatOpenAI.bind_tools`、`ToolsCondition` 是预置的结合件，week3 都手写了，可以逐个替换体验。

---

## 7. 参考资料

### LangChain

| 资源 | 链接 | 看什么 |
|------|------|--------|
| **LangChain 官方文档** ⭐ | https://python.langchain.com/ | Quickstart + 概念 |
| **LCEL 文档** ⭐ | https://python.langchain.com/docs/concepts/lcel/ | Runnable + 管道组合 |
| **langchain-core API** | https://api.python.langchain.com/ | Runnable / Message / Tool 基类 |
| **LangChain 教程（Intro）** | https://python.langchain.com/docs/tutorials/ | 官方手把手教程 |

### LangGraph

| 资源 | 链接 | 看什么 |
|------|------|--------|
| **LangGraph 官方文档** ⭐ | https://langchain-ai.github.io/langgraph/ | 权威参考 |
| **LangGraph 概念总览** ⭐ | https://langchain-ai.github.io/langgraph/concepts/ | StateGraph/Node/Edge/Reducer 定义 |
| **LangGraph 低级 API** | https://langchain-ai.github.io/langgraph/concepts/low_level/ | State / Reducer / Checkpointer 细节 |
| **LangGraph 快速入门** | https://langchain-ai.github.io/langgraph/tutorials/introduction/ | 手把手建第一个图 |
| **LangGraph 中文文档** | https://langchain.com.cn/docs/langgraph/ | 中文翻译，对照英文 |

### 结合点 / 演进

| 资源 | 链接 | 看什么 |
|------|------|--------|
| **LangGraph 官方：为什么用图** | https://langchain-ai.github.io/langgraph/concepts/high_level/ | AgentExecutor -> LangGraph 的动机 |
| **Anthropic Building Effective Agents** ⭐ | https://www.anthropic.com/research/building-effective-agents | Agent 设计圣经（理论清单资源 H） |
| **LangChain 博客：LangGraph 介绍** | https://blog.langchain.dev/ | 官方博客讲 LangGraph 诞生背景 |

> 理论部分延伸见 [`day1_2_理论知识清单.md`](./day1_2_理论知识清单.md) 第 12-17 节（含 LangGraph 状态图、Agent 核心机制、状态管理等权威链接）。
