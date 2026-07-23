# Week3 Day1+2 理论知识清单（含权威链接）

> 日期：2026-07-21 · 知识块：③ Tools/Skills 体系 + ④ MCP 协议
> 产出：`scripts/week3/tool_registry.py` + `scripts/week3/week3_mcp_server.py`

---

## Day 1：工具体系设计（知识块 ③）

### 1. 工具 Schema 规范化 —— 工具的"身份证"

每个工具必须包含三个字段，这是 **OpenAI Function Calling** 和 **MCP 协议** 的共同要求：

| 字段 | 作用 | 谁用它 |
|------|------|--------|
| `name` | 唯一标识（字母+下划线） | 代码路由 |
| `description` | 自然语言描述 → **LLM 据此选工具** | LLM |
| `parameters` | JSON Schema 类型约束 → **LLM 据此填参数** | LLM |

> **为什么 description 最重要？** LLM 是根据 description（不是 name）来决定调用哪个工具的。description 模糊 → 工具选错 → Agent 行为异常。

🏛️ **权威资料**：
- [OpenAI Function Calling 官方文档](https://platform.openai.com/docs/guides/function-calling) — 参数定义规范（name/description/parameters）、tool_choice 四种取值
- [Anthropic Tool Use Overview](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview) — Anthropic 工具三分类（your own / anthropic-schema / server）+ Parallel/Strict/Caching
- [JSON Schema 规范](https://json-schema.org/) — parameters 字段遵循的标准

### 2. 工具注册中心（ToolRegistry）—— 集中管理工具生命周期

**解决的问题**：week2 的工具定义（`TOOLS = [{...}]` 列表）和执行逻辑（`execute_tool()` if/elif 链）分散在代码不同位置，新增工具要改两处，容易遗漏。

**核心 API**：

| 方法 | 功能 | 对应 week2 的等价操作 |
|------|------|---------------------|
| `register()` | 注册工具（Schema + Handler 一起） | 在 TOOLS 列表加 dict + 在 execute_tool 加 elif |
| `get_tool_defs()` | 获取 OpenAI 兼容的工具列表 | `TOOLS` 列表变量 |
| `execute()` | 按名称分派执行 | `execute_tool()` if/elif |
| `list_by_category()` | 按类别（订单/客户/库存/系统）分组发现 | **week2 没有此能力** |

**week2 → week3 对比**：
```
week2: TOOLS = [{...}] 列表 + execute_tool() if/elif 链 → 散落，O(n) 查找
week3: registry.register() 一步注册 + registry.execute() 字典分派 → 集中，O(1) 查找
```

🏛️ **权威资料**：
- [OpenAI Defining Namespaces](https://platform.openai.com/docs/guides/function-calling) — 工具按 namespace 分组的官方实践，Registry 的 `category` 字段即对应此概念
- [Anthropic Tool Search](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview#tool-search) — 工具多时的发现机制，`list_by_category()` 为后续 Tool Search 做准备

### 3. 工具粒度四原则

| 原则 | 说明 | 判断方法 |
|------|------|---------|
| **单一职责** | 一个工具只做一种查询/操作 | description 里出现"或者/也可以/此外"就该拆 |
| **参数正交** | 参数之间不隐含依赖关系 | 去掉一个参数，工具还能独立工作吗？ |
| **可组合** | 多个小工具组合完成复杂任务 | Agent 能否通过多次调用来完成任务？ |
| **可测试** | 每个工具可独立输入输出验证 | 给定固定输入，输出是否确定可验证？ |

🏛️ **权威资料**：
- [Anthropic Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) ⭐ — canonical taxonomy：5 种 workflow 模式 + agent 模式，定义了"什么时候用工具链 vs 什么时候让 Agent 自主决策"
- [Anthropic Agents and Tools 概览](https://docs.anthropic.com/en/docs/agents-and-tools) — Agent 设计哲学，工具粒度的官方建议

### 4. 从硬编码到标准化工具生态的演进路径

```
阶段 1（week2）: 内联 TOOLS 字典 + if/elif 分派
     ↓  问题：工具定义和执行分离，5+ 工具后不可维护
阶段 2（week3 day1）: ToolRegistry 集中管理
     ↓  问题：工具和 Agent 同进程，无法跨项目复用
阶段 3（week3 day2）: MCP Server 标准化暴露
     ↓  问题：单 Server，工具多了需要拆分
阶段 4（week3 day3）: 多 MCP Server 按业务域拆分
```

🏛️ **权威资料**：
- [Function Calling 全平台实战 — CSDN](https://blog.csdn.net/weixin_42260382/article/details/162133638) ⭐ — 从 OpenAI 到 MCP 的工具定义演进全流程
- [OpenAI Function Calling 完整指南 — 博客园](https://www.cnblogs.com/qiniushanghai/p/19937290) ⭐ — 2026 中文版，含 Defining namespaces + Tool search

---

## Day 2：MCP Server（知识块 ④）

### 5. MCP 是什么？

**MCP（Model Context Protocol）** 是 Anthropic 于 2024 年底发布的**开放协议**，定义了 LLM 应用与外部工具/数据源之间的标准化通信方式。

**一句话**：MCP 是工具调用的"**USB 协议**"——任何实现了 MCP 的 Server，可以被任何支持 MCP 的 Client（Claude Desktop、Cursor、自建 Agent）**即插即用**。

**补充纠正**：MCP 的版权并不属于 Anthropic（如相关公告所示）。它现在是社区驱动的开放标准，由多家公司和开发者共同维护。

🏛️ **权威资料**：
- [MCP 官方规范 v2025-03-26](https://modelcontextprotocol.io/specification/2025-03-26) ⭐ — 协议完整规范，必读
- [MCP 官方入门](https://modelcontextprotocol.io/introduction) — 5 分钟理解 MCP 是什么
- [MCP Python SDK (GitHub)](https://github.com/modelcontextprotocol/python-sdk) — 官方 Python 实现，FastMCP 的源码

### 6. MCP 核心架构

```
┌──────────────┐     MCP 协议（JSON-RPC）     ┌──────────────┐
│  MCP Client  │ ◄──────────────────────────► │  MCP Server   │
│  (你的 Agent) │     Transport: stdio/SSE     │  (工具提供方)  │
└──────────────┘                              └──────────────┘
                                                     │
                                          ┌──────────┼──────────┐
                                          ▼          ▼          ▼
                                       Tools     Resources   Prompts
```

**Server 提供三种能力**：

| 能力 | 说明 | 类比 |
|------|------|------|
| **Tools** | 可执行的函数（模型可控） | REST API 的 POST 端点 |
| **Resources** | 暴露数据（应用可控） | REST API 的 GET 端点 |
| **Prompts** | 预定义模板（用户可控） | 快捷键/快捷回复 |

🏛️ **权威资料**：
- [MCP 规范 - Server Features](https://modelcontextprotocol.io/specification/2025-03-26/server/) — Tools/Resources/Prompts 三并列的官方定义
- [MCP 规范 - Client Features](https://modelcontextprotocol.io/specification/2025-03-26/client/) — Client 端能力（Sampling、Roots 等）

### 7. 传输层：stdio vs SSE

| 传输方式 | 工作原理 | 延迟 | 适用场景 |
|---------|---------|------|---------|
| **stdio** | Client 启动 Server 子进程，通过标准输入/输出通信 | 极低（进程内管道） | 本地开发、单机部署、Claude Desktop 插件 |
| **Streamable HTTP** | Server 作为独立服务运行，Client 通过 HTTP 连接 | 较低（localhost 网络） | 远程工具、多 Client 共享、生产部署 |

> week3 day2 用 **stdio**——零配置，Client 启动 Server 进程即可通信。
> 注：MCP 起初支持 SSE（Server-Sent Events）作为传输方式之一，但在规范迭代中已被 Streamable HTTP 取代。stdio 仍是本地开发的首选。

🏛️ **权威资料**：
- [MCP 规范 - Transport 层](https://modelcontextprotocol.io/specification/2025-03-26/basic/) — 传输层官方定义
- [MCP Python SDK - stdio_client](https://github.com/modelcontextprotocol/python-sdk) — stdio 传输的 Python 实现

### 8. MCP vs 直接 Function Calling

| 维度 | 直接 Function Calling（week2） | MCP（week3） |
|------|-------------------------------|-------------|
| **工具定义位置** | 内联在 Agent 代码里 | 在独立 MCP Server 里 |
| **工具发现** | 硬编码的 TOOLS 列表 | Client 连接后自动 `tools/list` |
| **工具复用** | 复制粘贴到其他项目 | 启动 MCP Server，任何 Client 可连 |
| **进程模型** | 工具和 Agent 同进程 | 工具在独立进程，通过 stdio/HTTP 通信 |
| **热更新** | 需要重启 Agent | 重启 MCP Server，Agent 无感 |
| **跨语言** | 只能用 Agent 的语言 | Server 可用 Python/Node/Go/任何语言 |

🏛️ **权威资料**：
- [Model Context Protocol 官方 FAQ](https://modelcontextprotocol.io/introduction) — 为什么用 MCP 而不是直接调用 API
- [Anthropic Tool Use 文档](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview) — 直接 Tool Use 的官方说明，与 MCP 形成对比

### 9. MCP 通信流程（一次工具调用）

```
Client                              Server
  │                                    │
  │──── initialize ──────────────────►│  ① 握手：交换协议版本和能力
  │◄─── {serverInfo, capabilities} ───│
  │                                    │
  │──── tools/list ──────────────────►│  ② 发现：获取所有可用工具
  │◄─── [{name, description,          │
  │       inputSchema}] ──────────────│
  │                                    │
  │──── tools/call ──────────────────►│  ③ 调用：执行具体工具
  │     {name:"query_orders",          │
  │      arguments:{customer:"深圳"}}   │
  │◄─── {content: [{type:"text",      │  ④ 返回：结构化结果
  │        text:"查到 8 条..."}]}      │
```

> **关键认知**：MCP 把"有哪些工具"（发现）和"怎么调用"（执行）标准化了。Client 不需要事先知道 Server 有什么工具——连上后自动发现。这就是 `@mcp.tool()` 装饰器自动处理的 `tools/list` 和 `tools/call` 两个处理器。

🏛️ **权威资料**：
- [MCP 规范 - Lifecycle](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle/) — initialize → list → call 的生命周期
- [MCP 规范 - Tool 定义](https://modelcontextprotocol.io/specification/2025-03-26/server/tools/) — Tool 的 JSON Schema 格式

### 10. FastMCP：Python SDK 最快上手方式

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("我的工具服务器")

@mcp.tool()
def my_tool(param: str) -> str:
    """工具描述 → 自动生成 JSON Schema"""
    return f"结果: {param}"

mcp.run(transport="stdio")  # 启动 stdio 传输
```

**FastMCP 自动完成的 3 件事**：
1. 从函数签名 + docstring **自动生成 JSON Schema**（不用手写 parameters dict）
2. 自动注册 `tools/list` 处理器（Client 连上后自动发现）
3. 自动注册 `tools/call` 处理器（Client 调用时自动执行函数）

🏛️ **权威资料**：
- [MCP Python SDK - FastMCP 文档](https://github.com/modelcontextprotocol/python-sdk) — FastMCP 完整 API
- [MCP Python SDK 示例](https://github.com/modelcontextprotocol/python-sdk/tree/main/examples) — 官方 examples 目录

### 11. MCP Client 使用

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["path/to/server.py"],
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()                    # 握手
        tools = await session.list_tools()            # 发现工具
        result = await session.call_tool("name", {})  # 调用工具
```

🏛️ **权威资料**：
- [MCP Python SDK - Client 文档](https://github.com/modelcontextprotocol/python-sdk) — ClientSession + stdio_client 用法
- [MCP 规范 - Client](https://modelcontextprotocol.io/specification/2025-03-26/client/) — Client 端协议要求

---

## 中文学习资源

| 主题 | 资源 |
|------|------|
| **MCP 完整文档翻译** | [MCP 中文站](https://mcpcn.com/) ⭐ — MCP 规范的完整中文翻译 |
| **MCP 规范中译** | [MCP 规范完整中译稿 — 腾讯云](https://cloud.tencent.cn/developer/article/2541726) |
| **MCP 完全指南** | [掘金 - MCP 完全指南](https://juejin.cn/post/7576838552472076331) |
| **MCP 案例实战** | [工良出品 MCP 案例实战 — 腾讯云](https://cloud.tencent.cn/developer/article/2528910) |
| **Function Calling 全平台** | [CSDN - Function Calling 全平台实战](https://blog.csdn.net/weixin_42260382/article/details/162133638) ⭐ |
| **Agent 设计模式** | [Jimmy Song - 智能体设计模式](https://jimmysong.io/zh/book/agentic-design-patterns/) ⭐ |

---

## 今天的 4 条核心认知

1. **ToolRegistry = 从 if/elif 散落到 register/execute 集中管理** → Agent 架构化的第一步
2. **MCP = 工具调用的 USB 协议** → Server 和 Client 解耦，跨语言、跨进程、热更新
3. **@mcp.tool() 装饰器 = 自动 Schema 生成 + 自动路由注册** → 不用再手写 JSON Schema 和 if/elif
4. **description 是 Agent 选工具的唯一依据** → Schema 的 description 写得好不好，直接决定 Agent 能不能选对工具

---

## 中文资源 · 重要章节逐篇提炼

> 标注说明：⭐ = 今天必须读（与 Day1 工具体系 + Day2 MCP Server 直接相关）
>           📖 = 建议本周读完（为 Day3-4 LangGraph 做准备）
>           ⏭️ = 当前可跳过（week4+ 才用到）

---

### 资源 A：Function Calling 全平台实战（CSDN）⭐

> 链接：https://blog.csdn.net/weixin_42260382/article/details/162133638
> 定位：**今天最重要的中文资料**，覆盖从 FC→MCP→Skills 的完整演进

| 章节 | 重要度 | 与今天的关系 |
|------|--------|-------------|
| **第1章** 为什么 AI 工具调用是 2026 必备核心能力 | 📖 | 建立全局认知，理解"为什么学这个" |
| **第2.1-2.3 节** Function Calling 原理：契约定义→大脑决策→闭环执行 | ⭐ | **今天 Day1 的核心**：理解 Schema(name/description/parameters) 的设计原因 |
| **第2.4 节** OpenAI 标准协议详解（tools 字段、JSON Schema、多轮调用流程） | ⭐ | **ToolRegistry.get_tool_defs() 的理论基础**：输出的正是这个格式 |
| **第2.5 节** Function Calling 的局限（重复造轮子、紧耦合、上下文消耗） | ⭐ | **为什么需要 ToolRegistry → MCP**：这段就是 week2→week3 的演进动机 |
| **第3章** Anthropic Tool Use（input_schema vs parameters、混合内容块） | 📖 | 对比理解，知道 OpenAI 和 Anthropic 的 Schema 差异 |
| **第6章** MCP 是什么：AI 世界的"USB-C 接口" | ⭐ | **今天 Day2 的入口**：理解 MCP 的定位 |
| **第7章** MCP 三层架构：Host → Client → Server | ⭐ | **理解 MCP 通信模型**：Client 不是独立进程，是 Host 内部的协议转换层 |
| **第8.1 节** 两种传输方式：stdio vs HTTP | ⭐ | **我们选的 stdio 的原因**：本地开发零配置 |
| **第9章** MCP 完整工作流实战（Initialize→List Tools→Call Tool） | ⭐ | **test_mcp_client.py 的协议层原理**：每一步发生了什么 |
| **第10章** 开发 MCP Server（含完整代码、list_tools/call_tool 接口） | ⭐ | **week3_mcp_server.py 的参考实现**：对照理解 FastMCP 帮我们做了什么 |
| **第11章** MCP vs Function Calling 深度对比 | 📖 | 理解"互补而非替代"——为什么两套都要学 |
| **第12章** 选型决策：什么时候用纯 FC，什么时候上 MCP | 📖 | 生产选型参考 |
| 第13-18章 Skills 相关 | ⏭️ | week5+ 内容 |

> **今天必读章节（约 40 分钟）**：2.1→2.4→2.5→6→7→8.1→9→10

---

### 资源 B：MCP 中文站（mcpcn.com）⭐

> 链接：https://mcpcn.com/
> 定位：**MCP 规范的完整中文翻译**，当字典查

| 章节 | 重要度 | 与今天的关系 |
|------|--------|-------------|
| **快速入门 → MCP 是什么？** | ⭐ | 5 分钟建立概念 |
| **核心概念 → 工具（Tools）** | ⭐ | **今天最核心的一节**：MCP 层面如何定义 Tool 的 name/description/inputSchema |
| **核心概念 → 传输（Transport）** | ⭐ | stdio 的协议层原理 |
| **核心概念 → 架构（Architecture）** | ⭐ | Host/Client/Server 三层的职责边界 |
| **规范 → 服务器功能 → Tools** | ⭐ | Tool 定义的 JSON Schema 格式，对照我们代码里的 @mcp.tool() |
| **规范 → 生命周期管理** | 📖 | initialize 握手的具体协议字段 |
| **规范 → 客户端功能 → Sampling** | 📖 | Client 端的高级能力（week3 day3 用到） |
| 核心概念 → 资源（Resources）/ 提示词（Prompts） | ⏭️ | 当前聚焦 Tools，后续再加 |

> **今天必读（约 20 分钟）**：「MCP 是什么」→「工具」→「传输」→「架构」

---

### 资源 C：MCP 完全指南 - 掘金 ⭐

> 链接：https://juejin.cn/post/7576838552472076331
> 定位：**从零到一的完整教程**，自带代码示例

| 章节 | 重要度 | 与今天的关系 |
|------|--------|-------------|
| **1.1** MCP 的定义与背景 | ⭐ | 快速复习（5 分钟） |
| **1.2** 为什么需要 MCP？（痛点与价值） | ⭐ | **week2 硬编码 → week3 MCP 的演进动机** |
| **1.3** MCP vs Function Calling / LangChain / ReAct 对比 | ⭐ | **今天的核心认知**：MCP 解决的是"标准化"问题，不是替代 FC |
| **2.1** 三大核心组件（Host → Client → Server） | ⭐ | 配合 MCP 中文站「架构」章节加深理解 |
| **2.2** 三大原语（Tools / Resources / Prompts） | ⭐ | 理解为什么 @mcp.tool() 只注册了 Tools，Resources/Prompts 是什么 |
| **2.3** 工作原理：从请求到响应（基于 JSON-RPC 2.0） | ⭐ | **test_mcp_client.py 的底层协议**：每个 `call_tool` 背后是 JSON-RPC 消息 |
| **3.1-3.2** 环境准备 + 构建第一个 MCP Server | ⭐ | **对照 week3_mcp_server.py**：这个教程是手写版，我们的代码用 FastMCP 简化了 |
| **4.1** 高级功能（流式、多 Server 聚合、跨语言） | 📖 | week3 day3 多 Server 的前置知识 |
| **4.3** 常见 Pitfalls 与解决方案 | 📖 | 避坑参考 |
| 第5章 生态与未来 | ⏭️ | 扩展视野，可快速浏览 |

> **今天必读（约 30 分钟）**：1.1→1.2→1.3→2.1→2.2→2.3→3.1→3.2

---

### 资源 D：工良 MCP 案例实战 - 腾讯云 📖

> 链接：https://cloud.tencent.cn/developer/article/2528910
> 定位：**Python 手把手实战**，附带完整 GitHub 仓库

| 章节 | 重要度 | 与今天的关系 |
|------|--------|-------------|
| **一、MCP 协议** — Hosts/Clients/Servers 定义 | ⭐ | 架构概念的另一种讲解角度，配合资源 A/B 加深理解 |
| **二、核心概念** — stdio / SSE / Streamable / Transport | ⭐ | transport 层的实战解释 |
| **三、MCP Tool 说明** — Tool 定义 + 依赖注入 + 提交到 AI 对话 | ⭐ | **Tool 如何被 AI 使用的完整流程** |
| **五、实现 MCP Server** — 最佳实践 + Resources + Prompts + Sampling | 📖 | week3 day3+ 拆多 Server 时的参考 |
| **五、安全考虑** | ⏭️ | week4 鉴权时再读 |
| **四、高德地图 MCP 实战** | ⏭️ | 具体业务场景，可跳过 |

> **今天必读（约 20 分钟）**：一 + 二 + 三（MCP Tool 说明部分）

---

### 资源 E：智能体设计模式 - Jimmy Song 📖

> 链接：https://jimmysong.io/zh/book/agentic-design-patterns/
> 定位：**Agent 架构设计的"百科全书"**，21 种设计模式

| 章节 | 重要度 | 与今天/本周的关系 |
|------|--------|-----------------|
| **第5章 工具使用（函数调用）** | ⭐ | **今天 Day1 的理论基础**：工具注册/Schema 定义/错误处理的模式化总结 |
| **第10章 模型上下文协议（MCP）** | ⭐ | **今天 Day2 的理论基础**：MCP 作为一种"设计模式"来理解 |
| **第2章 路由（Routing）** | 📖 | **Day3 拆分多 Server 的前置知识**：意图识别→路由到不同 Server |
| **第4章 反思（Reflection）** | 📖 | LangGraph 条件边的前置理论（Agent 自己判断"还需要更多数据吗"） |
| **第6章 规划（Planning）** | 📖 | Todo-driven 模式的理论化（week2 的 plan_investigation 的理论依据） |
| **第1章 提示链（Prompt Chaining）** | 📖 | Agent 编排的基本单元 |
| 第7-21章 多 Agent/记忆/安全/评估等 | ⏭️ | week4+ 内容 |

> **今天必读（约 25 分钟）**：第5章 + 第10章

---

### 资源 F：MCP 规范完整中译稿 - 腾讯云

> 链接：https://cloud.tencent.cn/developer/article/2541726
> 定位：MCP 规范的中文翻译版，与 MCP 中文站互为补充
> 注意：搜索未获取到详细目录，建议作为 MCP 中文站（资源 B）的补充阅读，遇到协议细节时查阅

---

## 今天阅读路线（按优先级排序，总计约 2 小时）

```
第一步（40min）→ 资源 A 第2.1-2.5节 + 第6-10章
   建立 FC→MCP 的完整演进认知，理解"为什么"

第二步（20min）→ 资源 B「MCP是什么」+「工具」+「传输」+「架构」
   对照 MCP 中文站的协议层定义，理解"是什么"

第三步（30min）→ 资源 C 第1章全章 + 第2章全章 + 第3.1-3.2节
   跟着掘金教程走一遍手写 MCP Server，理解"怎么写"

第四步（25min）→ 资源 E 第5章 + 第10章
   从设计模式的高度理解 Tool Use 和 MCP

第五步（20min）→ 资源 D 一+二+三节
   案例实战视角，加深理解

如果时间不够：至少完成 第一步 + 第二步，其余明天补
```

---

## Day 3-5：LangGraph 调度 Agent + 端到端 Demo（知识块 ② ⑥）

> 以下为 Week3 Day3-5 新增知识点的权威中文教材链接。
> 对应代码：`scripts/week3/langgraph_agent.py`

---

### 12. LangGraph 状态图（知识块 ⑥）— Agent 的"交通指挥系统"

**LangGraph** 是 LangChain 团队推出的**有状态、有环图的 Agent 编排框架**。它把 Agent 的决策过程建模为**节点（Node）+ 边（Edge）** 的有向图，支持条件分支和循环——这正是 Agent 多轮工具调用所需要的。

**核心概念**：

| 概念 | 说明 | 我们代码中的对应 |
|------|------|-----------------|
| **StateGraph** | 状态图，所有节点共享同一个 State | `StateGraph(AgentState)` |
| **Node** | 图中的节点，接收 State，返回 State | `analyze_intent` / `select_and_execute` / `evaluate_results` / `generate_answer` |
| **Edge** | 普通边，固定流向 | `add_edge("analyze_intent", "select_and_execute")` |
| **Conditional Edge** | 条件边，根据 State 动态路由 | `add_conditional_edges("evaluate_results", should_continue, {...})` |
| **Compile** | 编译为可执行对象 | `graph.compile()` |

**为什么用 LangGraph 而不是手写 while 循环？**
- 手写 while 循环：状态管理混乱、路由逻辑散落、难以调试和可视化
- LangGraph：状态集中管理、路由逻辑显式声明、自带执行追踪、支持流式输出

🏛️ **权威资料**：

| 资源 | 链接 | 说明 |
|------|------|------|
| **LangGraph 官方文档** ⭐ | https://langchain-ai.github.io/langgraph/ | 权威参考，How-to Guides + API Reference |
| **LangGraph 中文文档** ⭐ | https://langchain.com.cn/docs/langgraph/ | LangChain 中文网翻译，建议对照英文原文阅读 |
| **LangGraph GitHub** | https://github.com/langchain-ai/langgraph | 源码 + 示例 Notebooks |
| **LangGraph 概念总览** | https://langchain-ai.github.io/langgraph/concepts/ | StateGraph / Nodes / Edges / Conditional Edges 的官方定义 |
| **LangGraph 快速入门** | https://langchain-ai.github.io/langgraph/tutorials/introduction/ | 官方教程，从零构建第一个 StateGraph |
| **LangChain 中文网 - LangGraph 教程** | https://langchain.com.cn/docs/langgraph/tutorials/ | 中文版快速入门教程 |

---

### 13. Agent 核心机制（知识块 ②）— 决策循环与工具编排

Agent 的核心是**"感知 → 决策 → 执行 → 评估"的循环**。这不同于传统的"请求→响应"模式，Agent 需要自主判断：
- 当前信息是否足够回答用户问题？
- 如果不够，应该调用哪个工具？
- 工具返回后，是否需要继续调用更多工具？

**我们的代码中实现的循环**：

```
analyze_intent → select_and_execute → evaluate_results
    ↑                                       │
    └────────── needs_more_data ────────────┘
                                            │
                                       generate_answer → END
```

**关键概念**：

| 概念 | 说明 | 对应代码 |
|------|------|---------|
| **ReAct 模式** | Reasoning + Acting，交替进行推理和行动 | LLM 先思考 → 决定调工具 → 观察结果 → 再思考 |
| **Tool Choice** | LLM 自主决定是否调用工具 | `tool_choice="auto"` |
| **安全阀** | 防止无限循环 | `iteration >= 5` 强制结束 |
| **多轮对话** | 工具结果注入 messages，LLM 继续推理 | tool role 消息追加到对话历史 |

🏛️ **权威资料**：

| 资源 | 链接 | 说明 |
|------|------|------|
| **Anthropic Building Effective Agents** ⭐ | https://www.anthropic.com/research/building-effective-agents | **Agent 设计圣经**：5 种 workflow 模式（Prompt Chaining / Routing / Parallelization / Orchestrator-Workers / Evaluator-Optimizer）+ Agent 模式的定义和适用场景 |
| **吴恩达 AI Agentic Design Patterns** | https://www.deeplearning.ai/short-courses/ai-agentic-design-patterns-with-autogen/ | DeepLearning.AI 短课程，4 种 Agent 设计模式（Reflection / Tool Use / Planning / Multi-agent） |
| **Jimmy Song 智能体设计模式** ⭐ | https://jimmysong.io/zh/book/agentic-design-patterns/ | 中文版 Agent 设计模式全书，21 种模式，含代码示例（已在资源 E 中引用） |
| **OpenAI Function Calling 指南** | https://platform.openai.com/docs/guides/function-calling | tool_choice 四种取值（auto/none/required/指定工具）、多轮调用流程、Parallel Tool Calling |
| **Anthropic Tool Use 文档** | https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview | Tool Use 三分类（your own / anthropic-schema / server）、Parallel / Strict / Caching 模式 |
| **ReAct 论文** | https://arxiv.org/abs/2210.03629 | ReAct 模式原始论文（Reasoning + Acting） |

---

### 14. System Prompt 工程化 — Agent 的"岗位说明书"

System Prompt 是 Agent 行为的**第一决定因素**。一个合格的 System Prompt 必须包含四个要素：

| 要素 | 说明 | 我们的代码 |
|------|------|-----------|
| **角色设定** | 你是谁？专长是什么？ | "你是 3D 打印/CNC 加工生产调度专家" |
| **能力清单** | 你有什么工具？各自能做什么？ | 列出 6 个工具，按 Server 分组 |
| **工作流程** | 怎么做？先做什么后做什么？ | "先查订单再查资源，数据不够继续调用" |
| **业务规则** | 判断标准是什么？ | "优先级：交期紧 > 客户等级高 > 信用分高 > 延期率低" |

**为什么 System Prompt 在 Agent 中比在普通对话中更重要？**
- 普通对话：LLM 只需"回答"，Prompt 偏风格设定
- Agent 场景：LLM 需要"决策"——选哪个工具、调几次、什么时候停——Prompt 中的规则直接决定 Agent 行为质量

🏛️ **权威资料**：

| 资源 | 链接 | 说明 |
|------|------|------|
| **Prompt Engineering Guide 中文版** ⭐ | https://www.promptingguide.ai/zh | 提示工程完整指南中文版，含 System Prompt 设计原则、Few-Shot、Chain-of-Thought 等 |
| **Anthropic Prompt Engineering** | https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering | Anthropic 官方 Prompt 工程指南，含 System Prompt 最佳实践 |
| **OpenAI Prompt Engineering** | https://platform.openai.com/docs/guides/prompt-engineering | OpenAI 官方 Prompt 工程指南，六种策略 |
| **Anthropic System Prompts 元提示** | https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/system-prompts | System Prompt 的官方设计建议 |
| **提示工程指南 - 角色扮演** | https://www.promptingguide.ai/zh/techniques/prompt_chaining | 中文 Prompt Chaining 技术 |

---

### 15. 主备 Provider 降级架构 — 企业级 Agent 的容灾机制

**为什么单 Provider 不够？**
- 限流：火山豆包 5 小时配额用完 → 429 RateLimitError
- 故障：API 服务宕机、网络断开
- 成本：不同 Provider 价格差异大（DeepSeek ¥1/百万Token vs 豆包 coding plan）

**我们的链式 fallback 方案**：

```
PROVIDERS = [火山豆包, DeepSeek, Kimi]  # 按优先级排序

def call_llm(messages, tools):
    for p in PROVIDERS:
        try:
            return p.client.chat.completions.create(...)  # 第一个成功即返回
        except Exception:
            continue  # 失败自动切下一个
    raise RuntimeError("所有 provider 均失败")
```

**设计要点**：
- 按优先级排序：主用在前，备用在后
- 同协议切换：OpenAI 兼容协议，换 Provider 只改 base_url + api_key
- 失败透明：调用方不需要知道哪个 Provider 在服务
- 日志可观测：每次切换打印日志，方便排查

🏛️ **权威资料**：

| 资源 | 链接 | 说明 |
|------|------|------|
| **OpenAI 兼容协议规范** | https://platform.openai.com/docs/api-reference/chat/create | Chat Completions API 完整规范，所有 Provider 的共同协议基础 |
| **DeepSeek API 文档** ⭐ | https://platform.deepseek.com/api-docs/ | DeepSeek OpenAI 兼容接口文档，`base_url` 和 `model` 配置 |
| **火山引擎豆包 API 文档** ⭐ | https://www.volcengine.com/docs/82379/1928261 | 豆包 coding plan 的 API 文档，端点 `/api/coding/v3` |
| **企业级 API 容灾设计** | https://learn.microsoft.com/zh-cn/azure/architecture/patterns/retry | 微软 Azure 重试模式中文文档，与我们的 fallback 逻辑同源 |
| **Circuit Breaker 模式** | https://learn.microsoft.com/zh-cn/azure/architecture/patterns/circuit-breaker | 熔断器模式中文文档，Provider 故障时的进阶处理 |

---

### 16. Agent 状态管理 — 消息历史与工具结果累积

在 LangGraph 中，**State 是所有节点共享的数据**。我们的 `AgentState` 包含四个字段：

| 字段 | 类型 | 作用 |
|------|------|------|
| `messages` | `list[dict]` | 完整对话历史（system + user + assistant + tool），LLM 的上下文 |
| `tool_results` | `list[dict]` | 工具调用结果汇总，用于最终统计和调试 |
| `iteration` | `int` | 当前迭代次数，安全阀（≥5 强制结束） |
| `final_answer` | `str` | 最终输出，从 generate_answer 节点写入 |

**为什么用 TypedDict 而不是 Pydantic Model？**
- LangGraph 原生支持 TypedDict，零依赖
- 更轻量，适合 Agent 状态（不需要复杂校验）
- 生产环境可升级为 Pydantic BaseModel（LangGraph 兼容）

**消息格式遵循 OpenAI 标准**：
```
system    → {"role": "system", "content": "你是调度专家..."}
user      → {"role": "user", "content": "今天先做哪些订单？"}
assistant → {"role": "assistant", "content": null, "tool_calls": [...]}
tool      → {"role": "tool", "tool_call_id": "xxx", "content": "查到 15 条..."}
```

🏛️ **权威资料**：

| 资源 | 链接 | 说明 |
|------|------|------|
| **LangGraph State 管理文档** ⭐ | https://langchain-ai.github.io/langgraph/concepts/low_level/#state | State 的官方定义：TypedDict / Pydantic / Reducer 函数 |
| **OpenAI Chat Completions - Messages** | https://platform.openai.com/docs/api-reference/chat/create#chat-create-messages | messages 字段的官方格式（system/user/assistant/tool 四种 role） |
| **LangGraph AgentState 示例** | https://langchain-ai.github.io/langgraph/tutorials/introduction/#part-1-build-a-basic-chatbot | 官方教程中的 State 定义示例 |
| **OpenAI Tool Calling 消息格式** | https://platform.openai.com/docs/guides/function-calling#tool-calls-and-tool-results | tool_calls + tool role 消息的标准格式 |

---

### 17. 多 MCP Server 拆分 — 按业务域分组管理

当工具数量增长到 6+ 时，单 Server 把所有工具堆在一起变得不可维护。我们的方案是**按业务域拆分为两个 Server**：

```
order_server（订单域）          resource_server（资源域）
├── query_orders               ├── query_inventory
├── get_order_detail           ├── query_machine_load
└── get_production_status      └── query_customer
```

**拆分原则**：
- **高内聚**：同一业务域的工具放在一起（订单相关 → order_server）
- **低耦合**：两个 Server 共享数据层但互不调用
- **独立部署**：每个 Server 可以独立重启，互不影响
- **可扩展**：新增"财务域"只需加一个 finance_server，不动现有代码

**Agent 如何跨 Server 调用**？
- Agent 不关心工具来自哪个 Server——它只看 `TOOLS` 注册表
- `TOOLS` 注册表中每个工具的 `server` 字段仅用于日志分组
- LLM 决策时，所有工具平铺在 `tools` 参数中，不分 Server

🏛️ **权威资料**：

| 资源 | 链接 | 说明 |
|------|------|------|
| **MCP 规范 - 多 Server 架构** | https://modelcontextprotocol.io/specification/2025-03-26/basic/ | MCP 协议本身支持多 Server 同时连接 |
| **OpenAI Defining Namespaces** | https://platform.openai.com/docs/guides/function-calling#defining-namespaces | 工具按 namespace 分组的官方实践，我们 `TOOLS[name]["server"]` 即对应此概念 |
| **微服务拆分原则** | https://learn.microsoft.com/zh-cn/azure/architecture/microservices/ | 微软 Azure 微服务中文指南，高内聚低耦合的拆分方法 |
| **MCP 中文站 - 架构** | https://mcpcn.com/ | MCP 架构中 Host/Client/Server 的职责边界 |

---

## 中文资源 · Day3-5 逐篇提炼

> 标注说明：⭐ = 今天必须读（与 Day3-4 LangGraph Agent 直接相关）
>           📖 = 建议本周读完（为 Week4 做准备）
>           ⏭️ = 当前可跳过

---

### 资源 G：LangGraph 官方文档 ⭐

> 链接：https://langchain-ai.github.io/langgraph/
> 中文版：https://langchain.com.cn/docs/langgraph/
> 定位：**Day3-4 最重要的参考资料**，理解 StateGraph 的权威来源

| 章节 | 重要度 | 与今天的关系 |
|------|--------|-------------|
| **Concepts → StateGraph** | ⭐ | **今天 Day3 的核心**：理解 StateGraph 是什么、State 怎么定义 |
| **Concepts → Nodes** | ⭐ | `add_node()` 的官方定义，节点函数签名 |
| **Concepts → Edges** | ⭐ | 普通边 vs 条件边的区别，`add_conditional_edges()` 的用法 |
| **Concepts → Compile** | ⭐ | `compile()` 做了什么，编译后的 `app.invoke()` 和 `app.stream()` |
| **Tutorials → Introduction** | ⭐ | 手把手构建第一个 StateGraph，对照我们的 `build_graph()` |
| **How-to → State Management** | ⭐ | TypedDict vs Pydantic，Reducer 函数 |
| **How-to → Conditional Edges** | ⭐ | 条件边的路由函数写法，返回值映射 |
| **How-to → Tool Calling** | 📖 | LangGraph 内置的 ToolNode，与我们的手写 `select_and_execute` 对比 |
| **How-to → Streaming** | 📖 | `app.stream()` 流式输出，生产环境常用 |

> **今天必读（约 45 分钟）**：Concepts 四大章节 + Tutorials Introduction

---

### 资源 H：Anthropic Building Effective Agents ⭐

> 链接：https://www.anthropic.com/research/building-effective-agents
> 定位：**Agent 设计的"第一性原理"**，理解"什么时候该用 Agent，什么时候不该用"

| 章节 | 重要度 | 与今天的关系 |
|------|--------|-------------|
| **What are agents?** | ⭐ | 区分 Agent vs Workflow vs 普通 LLM 调用 |
| **When to use agents** | ⭐ | **今天最重要的认知**：Agent 不是银弹，"简单任务用 Workflow，复杂任务用 Agent" |
| **5 种 Workflow 模式** | ⭐ | Prompt Chaining / Routing / Parallelization / Orchestrator-Workers / Evaluator-Optimizer |
| **Agent 模式** | ⭐ | 我们的 `langgraph_agent.py` 就是 Agent 模式：LLM 自主决定调哪些工具、调几次 |
| **Orchestrator-Workers** | 📖 | 与我们的双 Server 架构对比：Agent 是 Orchestrator，两个 Server 是 Workers |
| **总结与建议** | ⭐ | "Start simple, add complexity only when needed" |

> **今天必读（约 30 分钟）**：What are agents → When to use agents → 5 Workflows → Agent 模式

---

### 资源 I：Prompt Engineering Guide 中文版 📖

> 链接：https://www.promptingguide.ai/zh
> 定位：**System Prompt 设计的系统化参考**，从基础到进阶

| 章节 | 重要度 | 与今天的关系 |
|------|--------|-------------|
| **提示工程简介** | 📖 | 建立全局认知 |
| **System Prompt 设计** | ⭐ | **今天 Day3 的核心**：理解 System Prompt 的四要素（角色/能力/流程/规则） |
| **Few-Shot Prompting** | 📖 | 在 Prompt 中给示例，提高 LLM 工具选择准确率 |
| **Chain-of-Thought** | 📖 | 让 LLM 在调用工具前先"思考"，提高决策质量 |
| **ReAct** | ⭐ | Reasoning + Acting 的 Prompt 模板，正是我们 Agent 的运作方式 |

> **今天必读（约 20 分钟）**：System Prompt 设计 + ReAct

---

### 资源 J：OpenAI Function Calling 多轮调用 📖

> 链接：https://platform.openai.com/docs/guides/function-calling
> 定位：**理解 tool_calls 消息格式和 tool_choice 的权威来源**

| 章节 | 重要度 | 与今天的关系 |
|------|--------|-------------|
| **Function Calling 概述** | ⭐ | 单轮 vs 多轮调用的区别 |
| **tool_choice 参数** | ⭐ | auto / none / required / 指定工具 — 控制 LLM 的工具调用行为 |
| **Parallel Tool Calling** | ⭐ | LLM 一次返回多个 tool_calls，我们的 Agent 支持并行执行 |
| **Tool Call Results** | ⭐ | tool role 消息的标准格式，对应我们的 `select_and_execute` 步骤 3 |
| **Defining Namespaces** | 📖 | 工具按 namespace 分组，对应 `TOOLS[name]["server"]` |

> **今天必读（约 20 分钟）**：Function Calling 概述 + tool_choice + Parallel Tool Calling + Tool Call Results

---

## Day 3-5 阅读路线（总计约 2 小时）

```
第一步（45min）→ 资源 G Concepts 四大章节 + Tutorials Introduction
   理解 StateGraph / Node / Edge / Conditional Edge / Compile

第二步（30min）→ 资源 H Building Effective Agents
   建立 Agent 设计的全局认知，理解"什么时候用 Agent"

第三步（20min）→ 资源 I System Prompt 设计 + ReAct
   理解 Prompt 如何影响 Agent 的决策质量

第四步（20min）→ 资源 J Function Calling 核心章节
   理解 tool_choice、Parallel Tool Calling、消息格式

第五步（15min）→ 回到代码：langgraph_agent.py 逐行对照
   把理论映射到代码，每个概念找到对应的代码行

如果时间不够：至少完成 第一步 + 第二步，其余明天补
```
