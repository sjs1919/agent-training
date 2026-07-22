"""
Week 3 · Day 3-4 — LangGraph 调度 Agent（MCP 架构版）
======================================================
这是 Week 3 的核心文件——把所有概念串在一起的可运行 Agent 系统。

核心架构（自上而下三层）：
  ┌─────────────────────────────────────────┐
  │  LangGraph 编排层（本节）                  │
  │  状态图：analyze → select → evaluate →   │
  │          generate → END                   │
  ├─────────────────────────────────────────┤
  │  MCP 工具层（order_server / resource_server）│
  │  6 个工具，按业务域分组                     │
  ├─────────────────────────────────────────┤
  │  LLM 调用层（OpenAI 兼容 API）              │
  │  火山豆包 ark-code-latest                 │
  └─────────────────────────────────────────┘

LangGraph 状态图流程：
  analyze_intent → select_and_execute → evaluate_results
      ↑                                       │
      └──────────── needs_more_data ──────────┘
                                              │
                                         generate_answer → END

MCP Server 文件可独立运行（stdio 传输）：
  python order_server.py
  python resource_server.py

知识块：④ MCP · ⑥ LangGraph · ② Agent 核心机制
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, TypedDict

import httpx
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from openai import OpenAI

# ---- 工具导入（MCP 架构：两个 Server 的工具函数） ----
# 在实际 MCP 部署中，这些工具通过 stdio 管道调用
# 这里为了 Demo 稳定性，直接 import 函数，但架构分层不变
from order_server import query_orders, get_order_detail, get_production_status
from resource_server import query_inventory, query_machine_load, query_customer

# 加载 .env 中的 API Key 和 Base URL
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# ---- LLM Provider 配置 ----
# trust_env=False 禁用系统代理检测（避免 Clash 代理干扰国内 API）
_client = OpenAI(
    api_key=os.getenv("VOLC_API_KEY"),
    base_url=os.getenv("VOLC_BASE_URL"),
    http_client=httpx.Client(trust_env=False),
)
MODEL = os.getenv("VOLC_MODEL", "ark-code-latest")


# ============================================================
# 工具注册表 — Agent 的"能力清单"
# ============================================================
# 这是整个 Agent 系统的核心数据结构。每个工具包含三部分：
#   fn     — Python 函数对象，实际执行的代码
#   server — 所属 MCP Server 名称，用于日志和调试
#   schema — OpenAI Function Calling 格式的 JSON Schema
#
# Schema 中的 description 至关重要——LLM 靠它理解工具用途。
# 写得越清晰，LLM 调用越准确。给正负示例比单纯描述更有效。
#
# 类比：前端的组件注册表，或 Java 的 Service 注册中心
# ============================================================

TOOLS = {
    # ========================
    # order_server 工具（3 个）
    # ========================

    "query_orders": {
        "fn": query_orders,           # ← 实际调用的 Python 函数
        "server": "order_server",     # ← 所属 Server，用于分组和日志
        "schema": {
            "type": "function",
            "function": {
                "name": "query_orders",
                "description": "查询订单列表，可按状态和客户名筛选。状态：生产中/紧急/待排产/排期中/即将完成",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "订单状态筛选，空=全部"},
                        "customer_name": {"type": "string", "description": "客户名模糊匹配，空=全部"},
                    },
                },
            },
        },
    },

    "get_order_detail": {
        "fn": get_order_detail,
        "server": "order_server",
        "schema": {
            "type": "function",
            "function": {
                "name": "get_order_detail",
                "description": "获取单个订单的完整信息",
                "parameters": {
                    "type": "object",
                    "properties": {"order_id": {"type": "string", "description": "订单编号，如 ORD001"}},
                    "required": ["order_id"],  # ← 必填参数
                },
            },
        },
    },

    "get_production_status": {
        "fn": get_production_status,
        "server": "order_server",
        "schema": {
            "type": "function",
            "function": {
                "name": "get_production_status",
                "description": "获取订单的当前生产环节和状态",
                "parameters": {
                    "type": "object",
                    "properties": {"order_id": {"type": "string", "description": "订单编号，如 ORD001"}},
                    "required": ["order_id"],
                },
            },
        },
    },

    # ========================
    # resource_server 工具（3 个）
    # ========================

    "query_inventory": {
        "fn": query_inventory,
        "server": "resource_server",
        "schema": {
            "type": "function",
            "function": {
                "name": "query_inventory",
                "description": "查询材料库存，可按材料名模糊搜索",
                "parameters": {
                    "type": "object",
                    "properties": {"material_name": {"type": "string", "description": "材料名关键词，如'钛合金''铝合金'，空=全部"}},
                },
            },
        },
    },

    "query_machine_load": {
        "fn": query_machine_load,
        "server": "resource_server",
        "schema": {
            "type": "function",
            "function": {
                "name": "query_machine_load",
                "description": "查询所有设备负载状态——哪些在运行、哪些空闲、预计何时释放",
                "parameters": {"type": "object", "properties": {}},  # ← 无参数工具
            },
        },
    },

    "query_customer": {
        "fn": query_customer,
        "server": "resource_server",
        "schema": {
            "type": "function",
            "function": {
                "name": "query_customer",
                "description": "查询客户信息——等级、信用分、历史延期率、行业",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string", "description": "客户编号，如 C001"},
                        "customer_name": {"type": "string", "description": "客户名模糊匹配，如'深圳'"},
                    },
                },
            },
        },
    },
}


# ============================================================
# System Prompt — Agent 的"岗位说明书"
# ============================================================
# 这是 Prompt 工程化中"系统级"的部分。
# 包含四个要素：
#   1. 角色设定（你是谁）
#   2. 能力清单（你有什么工具）
#   3. 工作流程（怎么做）
#   4. 业务规则（判断标准）
#
# 每次 LLM 调用都会带上这段 Prompt，作为 messages[0]
# ============================================================

SYSTEM_PROMPT = """你是 3D 打印/CNC 加工生产调度专家。你拥有两套工具系统：

**订单工具（order_server）**：
- query_orders — 查订单列表（按状态/客户筛选）
- get_order_detail — 查单个订单详情
- get_production_status — 查订单当前生产环节

**资源工具（resource_server）**：
- query_inventory — 查材料库存
- query_machine_load — 查设备负载
- query_customer — 查客户等级/信用/延期率

## 工作流程
收到用户问题后：
1. 分析意图——用户想知道什么？
2. 按需调用工具，先查订单再查资源
3. 如果数据不够，继续调用更多工具
4. 综合所有数据给出调度建议

## 调度规则
- 优先级：交期紧 > 客户等级高(S>A>B>C) > 信用分高 > 延期率低
- 库存不足的材料不能排产
- 空闲设备优先分配
- 综合输出：哪些订单今天优先做，哪些可以延后，以及原因"""


# ============================================================
# AgentState — LangGraph 的状态定义
# ============================================================
# 状态是贯穿所有节点的共享数据。
# 每个节点接收 state，返回 state（或修改 state 后返回）。
#
# 类比：Vuex Store 的 state / Redux 的 store / Pinia 的 state
# 区别：LangGraph 的 state 是 TypedDict，不是响应式的
#
# 四个字段：
#   messages     — 对话历史（system + user + assistant + tool）
#   tool_results — 工具调用结果的汇总列表
#   iteration    — 当前迭代次数，用于防止死循环
#   final_answer — 最终输出
# ============================================================

class AgentState(TypedDict):
    messages: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    iteration: int
    final_answer: str


# ============================================================
# LLM 调用封装
# ============================================================
# 把 OpenAI 调用包装成统一接口。
# tools 参数是可选的——传了 tools 就是 Function Calling 模式，
# 不传就是普通对话模式。
#
# temperature=0.3 用于调度场景（偏确定性，不要创意）
# ============================================================

def call_llm(messages: list[dict], tools: list[dict] | None = None) -> Any:
    """调用 LLM，支持 Function Calling 模式。"""
    kwargs: dict[str, Any] = {"model": MODEL, "messages": messages, "temperature": 0.3}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"  # ← LLM 自主决定是否调用工具
    return _client.chat.completions.create(**kwargs)


# ============================================================
# 节点 1：analyze_intent — 分析用户意图
# ============================================================
# 当前实现：简单打印用户提问，不做真正的意图分类。
# 生产环境可以扩展为：意图分类器 → 路由到不同处理策略
# ============================================================

def analyze_intent(state: AgentState) -> AgentState:
    """分析用户意图，打印日志。"""
    # 从 messages 中取出最后一条 user 消息
    user_msg = next((m["content"] for m in reversed(state["messages"]) if m["role"] == "user"), "")
    print(f"\n{'='*60}")
    print(f" 用户提问：{user_msg}")
    print(f"{'='*60}")
    return state


# ============================================================
# 节点 2：select_and_execute — Agent 的核心决策+执行
# ============================================================
# 这是整个 Agent 最关键的节点，做了三件事：
#
# 1. 决策：把当前对话 + 工具列表发给 LLM
#    LLM 返回两种可能：
#      a) tool_calls — "我需要调用这些工具"
#      b) content — "我已经有足够信息，直接回答"
#
# 2. 执行：遍历 LLM 返回的 tool_calls，逐个执行
#    从 TOOLS 注册表中找到对应的 Python 函数，传入参数
#
# 3. 注入：把工具调用结果追加到 messages 中
#    格式遵循 OpenAI 的 tool calling 消息格式：
#      assistant 消息（含 tool_calls）
#      tool 消息（含 tool_call_id + 结果）
#
# LLM 可以一次返回多个 tool_calls（并行调用）
# ============================================================

def select_and_execute(state: AgentState) -> AgentState:
    """LLM 决策 + 工具执行。"""

    # --- 步骤 1：决策 ---
    # 从 TOOLS 注册表提取所有 schema，发给 LLM
    tools_schema = [t["schema"] for t in TOOLS.values()]
    response = call_llm(state["messages"], tools_schema)
    msg = response.choices[0].message

    # 如果 LLM 没有调用工具，直接返回文本
    if not msg.tool_calls:
        state["messages"].append({"role": "assistant", "content": msg.content or ""})
        return state

    # --- 步骤 2：执行 ---
    for tc in msg.tool_calls:
        tool_name = tc.function.name

        # 解析 LLM 返回的 JSON 参数
        try:
            args = json.loads(tc.function.arguments)
        except json.JSONDecodeError:
            args = {}  # 解析失败就用空参数

        # 打印调用日志（培训演示用）
        print(f" → [{TOOLS[tool_name]['server']}] {tool_name}({args})")

        # 从注册表取出函数并执行
        tool_fn = TOOLS[tool_name]["fn"]
        try:
            result = tool_fn(**args)  # ← **args 将 dict 展开为关键字参数
        except Exception as e:
            result = f"工具调用错误：{e}"

        # 打印结果预览
        preview = result[:120].replace("\n", " ")
        print(f"   结果：{preview}...")

        # 记录到 tool_results
        state["tool_results"].append({"tool": tool_name, "arguments": args, "result": result})

    # --- 步骤 3：注入 ---
    # 3a. 追加 assistant 消息（含 tool_calls 元数据）
    state["messages"].append({
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ],
    })

    # 3b. 逐个追加 tool 消息（含工具执行结果）
    for tc in msg.tool_calls:
        matching = [r for r in state["tool_results"] if r["tool"] == tc.function.name]
        result_text = matching[-1]["result"] if matching else ""
        state["messages"].append({"role": "tool", "tool_call_id": tc.id, "content": result_text})

    state["iteration"] += 1
    return state


# ============================================================
# 节点 3：evaluate_results — 评估数据是否足够
# ============================================================
# 当前实现：不做判断，由 should_continue 条件边决定
# 生产环境可扩展：检查数据完整性、置信度等
# ============================================================

def evaluate_results(state: AgentState) -> AgentState:
    """评估当前数据是否足够回答用户问题。"""
    return state


# ============================================================
# 条件边：should_continue — 决定下一步
# ============================================================
# 这是 LangGraph 条件边的核心——根据 state 动态路由。
#
# 三种情况：
#   1. iteration >= 5 → 强制结束（防死循环）
#   2. 最后一条消息是 tool 结果 → 继续让 LLM 决策
#   3. 最后一条消息是 assistant 回复（无 tool_calls）→ 生成最终答案
#
# 类比：前端的路由守卫 router.beforeEach()
# ============================================================

def should_continue(state: AgentState) -> str:
    """条件边：判断是否继续调用工具。"""
    # 安全阀：最多 5 轮迭代，防止死循环
    if state["iteration"] >= 5:
        return "generate_answer"

    last_msg = state["messages"][-1] if state["messages"] else {}

    # 工具结果刚返回 → 继续让 LLM 决策
    if last_msg.get("role") == "tool":
        return "select_and_execute"

    # assistant 发出了 tool_calls → 继续执行
    if last_msg.get("role") == "assistant" and last_msg.get("tool_calls"):
        return "select_and_execute"

    # assistant 直接回复了文本 → 不需要更多工具
    return "generate_answer"


# ============================================================
# 节点 4：generate_answer — 生成最终调度建议
# ============================================================
# 两种路径进入此节点：
#   1. LLM 直接回复（不需要工具）
#   2. 多轮工具调用后，数据足够，LLM 综合生成
#
# 策略：
#   - 如果上一条 assistant 消息已有内容，直接复用
#   - 否则追加 summary_prompt 让 LLM 做最终综合
#   - 如果 LLM 调用失败，兜底返回原始工具数据
# ============================================================

def generate_answer(state: AgentState) -> AgentState:
    """综合所有数据生成最终调度建议。"""

    # 检查上一条消息是否已经是最终回复
    last_msg = state["messages"][-1] if state["messages"] else {}
    if last_msg.get("role") == "assistant" and last_msg.get("content") and not last_msg.get("tool_calls"):
        state["final_answer"] = last_msg["content"]
        return state

    # 追加综合指令，要求 LLM 做最终汇总
    summary_prompt = {
        "role": "system",
        "content": (
            "请基于以上所有工具查询结果，给出综合调度建议。\n"
            "必须包含：\n"
            "1. 关键发现（交期/客户/库存/设备）\n"
            "2. 今日优先排产订单（按优先级排序，列出订单号和原因）\n"
            "3. 可以延后的订单及原因\n"
            "用中文回答，格式清晰。"
        ),
    }
    messages = state["messages"] + [summary_prompt]

    try:
        response = call_llm(messages)
        answer = response.choices[0].message.content or ""
    except Exception as e:
        # 兜底：LLM 调用失败时，返回原始工具数据
        answer = f"调度建议生成失败：{e}\n\n已收集的工具数据：\n"
        for tr in state["tool_results"]:
            answer += f"\n--- {tr['tool']} ---\n{tr['result'][:300]}"

    state["final_answer"] = answer
    state["messages"].append({"role": "assistant", "content": answer})
    return state


# ============================================================
# 构建 Graph — 把节点和边组装成状态图
# ============================================================
# 这是 LangGraph 的核心 API：
#   1. StateGraph(AgentState) — 创建状态图，指定 State 类型
#   2. add_node(name, func) — 添加节点
#   3. add_edge(from, to) — 添加普通边（固定流向）
#   4. add_conditional_edges(from, router, mapping) — 添加条件边（动态路由）
#   5. set_entry_point(name) — 设置入口节点
#   6. compile() — 编译成可执行对象
#
# 编译后返回的 app 可以调用 app.invoke(state) 或 app.stream(state)
# ============================================================

def build_graph() -> StateGraph:
    """构建 LangGraph 状态图。"""
    graph = StateGraph(AgentState)

    # 注册四个节点
    graph.add_node("analyze_intent", analyze_intent)
    graph.add_node("select_and_execute", select_and_execute)
    graph.add_node("evaluate_results", evaluate_results)
    graph.add_node("generate_answer", generate_answer)

    # 设置入口
    graph.set_entry_point("analyze_intent")

    # 普通边（固定流向）
    graph.add_edge("analyze_intent", "select_and_execute")
    graph.add_edge("select_and_execute", "evaluate_results")

    # 条件边（动态路由）
    # evaluate_results 后根据 should_continue 的返回值决定下一步
    graph.add_conditional_edges("evaluate_results", should_continue, {
        "select_and_execute": "select_and_execute",  # 继续查
        "generate_answer": "generate_answer",         # 生成答案
    })

    # 最终答案后结束
    graph.add_edge("generate_answer", END)

    # compile() 编译并返回可执行对象
    return graph.compile()


# ============================================================
# 主入口 — 运行 Agent
# ============================================================
# 1. 构建 Graph
# 2. 构建初始状态（system prompt + 用户提问）
# 3. app.invoke(initial_state) 一行代码启动整个 Agent 循环
# 4. 打印结果
# ============================================================

def main():
    print("Week 3 — MCP + LangGraph 调度 Agent")
    print(f"工具总数：{len(TOOLS)}（order_server: 3 / resource_server: 3）")
    print(f"模型：{MODEL}")

    # 构建可执行的状态图
    app = build_graph()

    # 场景：调度员问"今天先做哪些订单？"
    query = "今天先做哪些订单？帮我综合考虑交期紧迫度、客户等级、材料库存和设备负载情况，给出优先级排序。"

    # 初始状态
    initial_state: AgentState = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        "tool_results": [],
        "iteration": 0,
        "final_answer": "",
    }

    # 一行代码启动 Agent 循环
    # LangGraph 自动处理：节点调度 → 条件路由 → 状态管理 → 循环终止
    result = app.invoke(initial_state)

    # 打印结果
    print(f"\n{'='*60}")
    print(" 最终调度建议")
    print(f"{'='*60}")
    print(result["final_answer"])
    print(f"\n工具调用统计：{len(result['tool_results'])} 次")
    for tr in result["tool_results"]:
        print(f"  [{TOOLS[tr['tool']]['server']}] {tr['tool']}({tr['arguments']})")


if __name__ == "__main__":
    main()