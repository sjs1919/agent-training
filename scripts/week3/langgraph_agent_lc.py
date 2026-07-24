"""
Week 3 · LangChain 升级版调度 Agent（langgraph_agent_lc.py）
============================================================
[AI:Claude] 在 langgraph_agent.py 基础上引入 LangChain 组件重写。
原文件保留不动，本文件与之对照阅读，看"引入 LangChain 后每处怎么变"。

落地 docs/week3/理论补充_走读后.md 的 P0 三件套：
  ① add_messages reducer       -> AgentState.messages 自动累积
  ② ToolNode + tools_condition -> 替代手写 select_and_execute / should_continue
  ③ MemorySaver checkpointer   -> compile() 加记忆，跨调用保持上下文

旧 -> 新 对照（详见各段注释）：
  call_llm 裸 SDK + 手写 fallback  ->  ChatOpenAI.with_fallbacks(...)
  TOOLS 字典 + 手写 JSON Schema    ->  StructuredTool.from_function(fn) 自动 schema
  messages: list 手动拼接          ->  Annotated[list, add_messages] reducer
  select_and_execute 手写执行      ->  ToolNode(tools) 预置
  should_continue 手写条件边       ->  tools_condition 预置 + iteration 安全阀
  compile() 无记忆                 ->  compile(checkpointer=MemorySaver())

文末附录：create_react_agent 一行版（--react 模式可跑），对照"手写图 vs 预置 Agent"。

知识块：④ MCP · ⑥ LangGraph · ② Agent · LangChain 生态
依赖：pip install langchain-openai（其余 langchain-core / langgraph 已就绪）
"""

import sys
from pathlib import Path
from typing import Annotated, TypedDict

import logging
import httpx
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, create_react_agent, tools_condition

# ---- 复用 week3 原工具函数 ----
# @mcp.tool() 装饰器返回原函数（signature/docstring 完整），
# 可被 StructuredTool.from_function 直接内省，无需重写工具逻辑。
from order_server import get_order_detail, get_production_status, query_orders
from resource_server import query_customer, query_inventory, query_machine_load

# ---- Windows GBK 编码兼容 ----
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# 压掉 httpx/openai 的 INFO 请求日志（原版裸 SDK 不打这些，保持输出干净）
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

load_dotenv(Path(__file__).parent.parent.parent / ".env")


# ============================================================
# Provider -> ChatOpenAI（替代原 call_llm 的裸 OpenAI SDK）
# ============================================================
# 原 _build_client 返回 openai.OpenAI；这里返回 langchain 的 ChatOpenAI。
# trust_env=False 通过 http_client 字段传入，绕过系统代理（与原版一致）。
# 主备 fallback 用 LangChain 的 .with_fallbacks()，替代原手写 for 循环。
import os

PROVIDERS = [
    {
        "name": "火山豆包(coding)",
        "enabled": True,
        "api_key": os.getenv("VOLC_API_KEY", ""),
        "base_url": os.getenv("VOLC_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding/v3"),
        "model": os.getenv("VOLC_MODEL", "ark-code-latest"),
    },
    {
        "name": "DeepSeek",
        "enabled": True,
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    },
]


def _is_real_key(key: str) -> bool:
    if not key:
        return False
    return "your-" not in key.lower()


def _build_chat(provider: dict) -> ChatOpenAI:
    """单个 Provider -> ChatOpenAI（OpenAI 兼容协议，trust_env=False 直连）"""
    return ChatOpenAI(
        model=provider["model"],
        api_key=provider["api_key"],
        base_url=provider["base_url"],
        temperature=0.3,
        http_client=httpx.Client(trust_env=False),
    )


def _enabled_chats() -> list[ChatOpenAI]:
    chats = [
        _build_chat(p)
        for p in PROVIDERS
        if p.get("enabled") and _is_real_key(p["api_key"])
    ]
    if not chats:
        raise RuntimeError("无可用 Provider（检查 .env 的 VOLC_API_KEY / DEEPSEEK_API_KEY）")
    return chats


def build_llm_with_tools(tools: list) -> object:
    """带工具绑定的 LLM + 主备 fallback。
    注意顺序：先 bind_tools 再 with_fallbacks（fallback wrapper 不暴露 bind_tools）。
    """
    bound = [c.bind_tools(tools) for c in _enabled_chats()]
    return bound[0] if len(bound) == 1 else bound[0].with_fallbacks(bound[1:])


def build_llm_plain() -> object:
    """不带工具的 LLM（generate_answer 汇总用）+ 主备 fallback"""
    chats = _enabled_chats()
    return chats[0] if len(chats) == 1 else chats[0].with_fallbacks(chats[1:])


# ============================================================
# 工具：StructuredTool.from_function（替代原 TOOLS 字典 + 手写 JSON Schema）
# ============================================================
# 原版手写每个工具的 JSON Schema（name/description/parameters）；
# LangChain 从函数签名 + docstring 自动生成 schema，零手写。
# server 字段保留用于日志分组（原版 TOOLS[name]["server"] 的等价物）。

_TOOLS_SRC = [
    (query_orders, "order_server"),
    (get_order_detail, "order_server"),
    (get_production_status, "order_server"),
    (query_inventory, "resource_server"),
    (query_machine_load, "resource_server"),
    (query_customer, "resource_server"),
]

# 工具名 -> 所属 Server，用于日志（对应原 TOOLS[name]["server"]）
SERVER_MAP = {fn.__name__: server for fn, server in _TOOLS_SRC}


def build_tools() -> list:
    """把 6 个函数包成 LangChain StructuredTool（自动 schema）"""
    return [StructuredTool.from_function(fn) for fn, _ in _TOOLS_SRC]


# ============================================================
# System Prompt（沿用原版，自包含不跨文件导入）
# ============================================================
SYSTEM_PROMPT = """你是 3D 打印/CNC 加工生产调度专家。你拥有两套工具系统：

**订单工具（order_server）**：
- query_orders - 查订单列表（按状态/客户筛选）
- get_order_detail - 查单个订单详情
- get_production_status - 查订单当前生产环节

**资源工具（resource_server）**：
- query_inventory - 查材料库存
- query_machine_load - 查设备负载
- query_customer - 查客户等级/信用/延期率

## 工作流程
收到用户问题后：
1. 分析意图--用户想知道什么？
2. 按需调用工具，先查订单再查资源
3. 如果数据不够，继续调用更多工具
4. 综合所有数据给出调度建议

## 调度规则
- 优先级：交期紧 > 客户等级高(S>A>B>C) > 信用分高 > 延期率低
- 库存不足的材料不能排产
- 空闲设备优先分配
- 综合输出：哪些订单今天优先做，哪些可以延后，以及原因"""


# ============================================================
# AgentState（替代原裸 messages: list）
# ============================================================
# 关键升级：messages 用 Annotated[list, add_messages] reducer。
# 节点只需返回 {"messages": [new_msg]}，LangGraph 自动 append--
# 不再像原版那样手动 state["messages"].append(...) 再 return state。
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # ← reducer 自动累积
    iteration: int                            # 安全阀（对应原版 iteration>=5）
    final_answer: str


# ============================================================
# 节点 1：analyze_intent（保留，入口日志，对应原版）
# ============================================================
def analyze_intent(state: AgentState) -> dict:
    user_msg = next(
        (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        "",
    )
    print(f"\n{'='*60}")
    print(f" 用户提问：{user_msg}")
    print(f"{'='*60}")
    return {}  # 无状态变更（reducer 模式下空 dict 即可）


# ============================================================
# 节点 2：agent（替代原 select_and_execute 的"决策"部分）
# ============================================================
# 原版在 select_and_execute 里把 messages+tools_schema 发给 LLM；
# 这里用 ChatOpenAI.bind_tools(tools).invoke(messages)，工具 schema 自动绑定。
# 返回的 AIMessage 由 add_messages reducer 自动追加，无需手动 append。
def make_agent_node(llm_with_tools):
    def agent_node(state: AgentState) -> dict:
        response = llm_with_tools.invoke(state["messages"])  # AIMessage（含 tool_calls 或 content）
        return {"messages": [response], "iteration": state["iteration"] + 1}

    return agent_node


# ============================================================
# 条件边：route_from_agent（替代原 should_continue）
# ============================================================
# 复用预置 tools_condition（返回 "tools" 或 END），叠加 iteration 安全阀。
# 原版 should_continue 手写三种判断；这里 tools_condition 包揽工具相关分支。
def route_from_agent(state: AgentState) -> str:
    if state["iteration"] >= 5:          # 安全阀（对应原版）
        return "generate_answer"
    # tools_condition：最后一条 AIMessage 有 tool_calls -> "tools"，否则 -> END
    return "tools" if tools_condition(state) == "tools" else "generate_answer"


# ============================================================
# 节点 3：tools = ToolNode(tools)（替代原 select_and_execute 的"执行"部分）
# ============================================================
# 原版手写：遍历 tool_calls -> json.loads 参数 -> TOOLS[name]["fn"](**args) -> 拼 tool 消息。
# ToolNode 一行搞定：读最后一条 AIMessage 的 tool_calls，执行对应工具，返回 ToolMessage 列表。
# （在 build_graph 里用 ToolNode(tools) 直接注册，无需写函数）


# ============================================================
# 节点 4：generate_answer（保留，综合汇总，对应原版）
# ============================================================
# 与原版一致：追加 summary_prompt 让 LLM 做最终综合；失败兜底返回原始数据。
# 用不带工具的 llm_plain（汇总阶段不需要再调工具）。
def make_generate_answer(llm_plain):
    def generate_answer(state: AgentState) -> dict:
        last = state["messages"][-1] if state["messages"] else None
        # 若 agent 已直接给出文本回答，可直接复用；这里仍走汇总以对齐原版行为
        summary_prompt = SystemMessage(content=(
            "请基于以上所有工具查询结果，给出综合调度建议。\n"
            "必须包含：\n"
            "1. 关键发现（交期/客户/库存/设备）\n"
            "2. 今日优先排产订单（按优先级排序，列出订单号和原因）\n"
            "3. 可以延后的订单及原因\n"
            "用中文回答，格式清晰。"
        ))
        try:
            resp = llm_plain.invoke(state["messages"] + [summary_prompt])
            answer = resp.content if isinstance(resp, AIMessage) else str(resp)
        except Exception as e:
            answer = f"调度建议生成失败：{e}\n\n已收集的工具数据：\n"
            for m in state["messages"]:
                if isinstance(m, ToolMessage):
                    answer += f"\n--- {m.name} ---\n{str(m.content)[:300]}"
        return {"messages": [AIMessage(content=answer)], "final_answer": answer}

    return generate_answer


# ============================================================
# 构建 Graph（替代原 build_graph）
# ============================================================
def build_graph() -> object:
    tools = build_tools()
    llm_with_tools = build_llm_with_tools(tools)
    llm_plain = build_llm_plain()

    g = StateGraph(AgentState)
    g.add_node("analyze_intent", analyze_intent)
    g.add_node("agent", make_agent_node(llm_with_tools))
    g.add_node("tools", ToolNode(tools))                       # ← 预置，替代手写执行
    g.add_node("generate_answer", make_generate_answer(llm_plain))

    g.set_entry_point("analyze_intent")
    g.add_edge("analyze_intent", "agent")
    g.add_conditional_edges(
        "agent", route_from_agent,
        {"tools": "tools", "generate_answer": "generate_answer"},
    )
    g.add_edge("tools", "agent")           # 工具结果回 agent 再决策（ReAct 循环）
    g.add_edge("generate_answer", END)

    # ← checkpointer：跨调用记忆（原版 compile() 无此参数）
    return g.compile(checkpointer=MemorySaver())


# ============================================================
# 附录 B：create_react_agent 一行版（对照"手写图 vs 预置 Agent"）
# ============================================================
# 上面 build_graph() 几十行手写 4 节点图；预置 create_react_agent 一行等价：
#   - agent 节点 = 内置 ReAct 循环（bind_tools + invoke）
#   - tools 节点 = 内置 ToolNode
#   - 条件边 = 内置 tools_condition
#   - state_modifier = 把 SYSTEM_PROMPT 注入每轮
# 代价：失去 analyze_intent / generate_answer 等自定义节点（教学脚手架）。
# 用 --react 模式跑这个版本，与默认模式对比输出。
def build_react_agent() -> object:
    tools = build_tools()
    llm = build_llm_with_tools(tools)  # create_react_agent 内部自己管 tool 循环
    return create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,  # 注：langgraph 1.x 用 prompt（旧版叫 state_modifier，已废）
        checkpointer=MemorySaver(),
    )


# ============================================================
# 运行入口
# ============================================================
DEMO_SCENARIOS = [
    "今天先做哪些订单？帮我综合考虑交期紧迫度、客户等级、材料库存和设备负载情况，给出优先级排序。",
    "ORD001 能按时交付吗？帮我查一下这个订单的当前状态、所需材料和设备情况。",
    "现在有哪些紧急订单？哪些设备和材料是瓶颈？",
    "东莞模具厂的订单总体情况怎么样？信用如何？建议优先处理还是延后？",
    "帮我查一下 PEEK 材料的库存，如果不够，会影响哪些订单？",
]


def run_agent(app, query: str, thread_id: str = "default"):
    """运行一次 Agent。thread_id 相同则共享记忆（checkpointer）。"""
    initial: AgentState = {
        "messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=query)],
        "iteration": 0,
        "final_answer": "",
    }
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 25}

    result = app.invoke(initial, config=config)

    print(f"\n{'='*60}")
    print(" 最终调度建议")
    print(f"{'='*60}")
    print(result.get("final_answer") or _extract_last_answer(result))

    # 工具调用统计：数 ToolMessage（原版数 tool_results，这里等价）
    tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    print(f"\n工具调用统计：{len(tool_msgs)} 次")
    for m in tool_msgs:
        print(f"  [{SERVER_MAP.get(m.name, '?')}] {m.name}")


def _extract_last_answer(result: dict) -> str:
    """create_react_agent 模式没有 final_answer 字段，取最后一条 AIMessage"""
    for m in reversed(result.get("messages", [])):
        if isinstance(m, AIMessage) and m.content and not m.tool_calls:
            return m.content
    return "（无回答）"


def run_multi_turn_demo(app):
    """多轮记忆演示：同一 thread_id 连续提问，验证 checkpointer 跨调用记忆"""
    print(f"\n{'#'*60}")
    print("# 多轮记忆演示（同 thread_id，Agent 记住上文）")
    print(f"{'#'*60}")
    turns = [
        "查一下 ORD001 的状态",
        "它需要的材料库存够吗？",   # ← "它"指代 ORD001，靠上文记忆
        "那这个订单建议优先做吗？",  # ← 继续承接
    ]
    for i, q in enumerate(turns, 1):
        print(f"\n--- 第 {i} 轮 ---")
        run_agent(app, q, thread_id="multi-turn")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Week3 LangChain 升级版调度 Agent")
    parser.add_argument("query", nargs="?", help="直接提问")
    parser.add_argument("--demo", action="store_true", help="跑预设场景")
    parser.add_argument("--multi", action="store_true", help="多轮记忆演示")
    parser.add_argument("--react", action="store_true", help="用 create_react_agent 一行版（附录 B）")
    args = parser.parse_args()

    print("Week 3 - LangChain 升级版调度 Agent")
    mode = "create_react_agent（附录B）" if args.react else "手写图（4节点）"
    print(f"编排模式：{mode}")
    enabled = [p["name"] for p in PROVIDERS if p.get("enabled") and _is_real_key(p["api_key"])]
    print(f"可用 Provider：{', '.join(enabled)}（with_fallbacks 自动降级）")
    print(f"工具：{len(_TOOLS_SRC)} 个 = StructuredTool.from_function 自动 schema")

    app = build_react_agent() if args.react else build_graph()

    if args.multi:
        run_multi_turn_demo(app)
        return

    if args.query:
        run_agent(app, args.query, thread_id="cli")
        return

    if args.demo:
        print(f"\n📋 预设演示场景（共 {len(DEMO_SCENARIOS)} 个）：\n")
        for i, s in enumerate(DEMO_SCENARIOS, 1):
            print(f"  {i}. {s}")
        print()
        try:
            choice = input("选择场景编号（回车=全部演示）: ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = ""
        if choice.isdigit() and 1 <= int(choice) <= len(DEMO_SCENARIOS):
            run_agent(app, DEMO_SCENARIOS[int(choice) - 1], thread_id=f"demo-{choice}")
        else:
            for i, s in enumerate(DEMO_SCENARIOS, 1):
                print(f"\n{'#'*60}\n# 场景 {i}/{len(DEMO_SCENARIOS)}\n{'#'*60}")
                run_agent(app, s, thread_id=f"demo-{i}")
        return

    # 交互模式（默认）
    print("\n💬 交互模式 - 输入问题，Agent 回答（输入 quit 退出）\n")
    print("  示例问题：")
    for i, s in enumerate(DEMO_SCENARIOS, 1):
        print(f"  {i}. {s}")
    print()
    turn = 0
    while True:
        try:
            query = input("🔍 请输入调度问题 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 退出")
            break
        if not query:
            continue
        if query.lower() in ("quit", "exit", "q", "退出"):
            print("👋 退出")
            break
        turn += 1
        run_agent(app, query, thread_id=f"interactive-{turn}")


if __name__ == "__main__":
    main()
