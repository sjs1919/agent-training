"""
第二周 · Day 5（周五）- Week2 Demo 串联
==========================================
目标：把 week1 的 Function Calling Agent（查订单）+ Day4 的 Agentic RAG（查合同/案例）
      合成一个完整的生产调度助手。Agent 既能查结构化数据（订单/客户），又能检索
      非结构化知识库（合同条款 + 历史延期记录）。

核心认知：真实 Agent = 多种工具协同。结构化查询（CSV）+ 语义检索（RAG）+ 规划编排，
        Agent 按 plan 逐项调用，综合回答。这是 week1-2 的总集成。

工具栈（5 个）：
  - plan_investigation      ：规划调查步骤（Todo-driven）
  - query_orders            ：查订单 CSV（复用 week1 day2）
  - query_customer          ：查客户等级/信用/延期率（customers.csv）
  - search_knowledge_base   ：混合检索合同 + 案例（复用 day2 retrieve_hybrid）
  - submit_final_answer     ：提交综合答案

复用：
  - week1 day2 的 query_orders（订单查询）
  - day1 的 Provider 主备 + Chroma 向量库
  - day2 的混合检索（BM25 + RRF + Cross-Encoder）
  - day4 的 plan/submit Agent 循环骨架

业务域：3D 打印/CNC 调度（订单 + 客户 + 合同 + 历史延期记录）

[AI:Claude] 架构设计：week1 Agent + day4 Agentic RAG + day2 混合检索 三合一
"""

import csv
import json
import sys
from pathlib import Path

# ---- 复用 day1（Provider + 向量库）+ day2（混合检索）----
sys.path.insert(0, str(Path(__file__).parent))
from day1_rag_basics import (  # noqa: E402
    PROVIDERS,
    call_with_fallback,
    _is_real_key,
    get_or_build_vectorstore,
    retrieve,
)
from day2_hybrid_rerank import (  # noqa: E402
    retrieve_hybrid,
    build_bm25_index,
    load_reranker,
)

# ---- 复用 week1 day2 的 query_orders ----
sys.path.insert(0, str(Path(__file__).parent.parent / "week1"))
from day2_function_calling import query_orders  # noqa: E402

# Windows stdout UTF-8（开箱即跑）
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


# ============================================================
# day2 混合检索层（同 day4，模块级初始化）
# ============================================================

_BM25 = None
_CHUNKS = None
_METAS = None
_RERANKER = None


def init_retrieval(collection):
    """建 BM25 索引 + 加载 reranker，存到模块级全局。"""
    global _BM25, _CHUNKS, _METAS, _RERANKER
    _BM25, _CHUNKS, _METAS = build_bm25_index(collection)
    _RERANKER = load_reranker()


# ============================================================
# 工具实现：query_customer（查客户等级/信用/延期率）
# ============================================================

CUSTOMERS_CACHE = None


def _load_customers():
    global CUSTOMERS_CACHE
    if CUSTOMERS_CACHE is None:
        csv_path = Path(__file__).parent / "data" / "customers.csv"
        with open(csv_path, encoding="utf-8") as f:
            CUSTOMERS_CACHE = list(csv.DictReader(f))
    return CUSTOMERS_CACHE


def query_customer(customer=None, customer_id=None):
    """
    查询客户档案：等级、信用分、历史延期率。
    可按客户名模糊匹配或 id 精确查询。返回匹配的客户列表。
    """
    customers = _load_customers()
    result = []
    for c in customers:
        if customer_id and c["id"] != customer_id:
            continue
        if customer and customer not in c["客户名"]:
            continue
        result.append(c)
    return {"total": len(result), "customers": result}


# ============================================================
# 工具定义（OpenAI Function Calling 格式，5 个工具）
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "plan_investigation",
            "description": (
                "规划调查步骤。把用户问题拆成 2-5 个具体的待查事项，"
                "每个事项说明查什么、用哪个工具。可调查方向：查订单（query_orders）、"
                "查客户档案（query_customer）、查合同/案例知识库（search_knowledge_base）。"
                "例如：用户问'深圳精密五金订单情况，有什么特殊要求？'"
                "-> ['用 query_orders 查深圳精密五金的订单', "
                "'用 query_customer 查深圳精密五金的客户等级和延期率', "
                "'用 search_knowledge_base 查深圳精密五金合同特殊条款']"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "用户的原始问题（原文）"},
                    "todo_items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "待查事项列表，每项说明查什么、用哪个工具（2-5 项）",
                        "minItems": 1,
                        "maxItems": 6,
                    },
                },
                "required": ["question", "todo_items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_orders",
            "description": (
                "查询 3D 打印/CNC 加工订单列表。可按客户名、状态、加工环节、交期范围筛选，支持排序。"
                "返回订单的 id、客户名、产品、数量、交期、当前环节、状态。"
                "用于回答'有哪些订单/某客户的订单/快超期的订单'等。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer": {"type": "string", "description": "按客户名模糊筛选，如'深圳精密五金'"},
                    "status": {
                        "type": "string",
                        "enum": ["生产中", "待排产", "即将超期", "已完成"],
                        "description": "按订单状态精确筛选",
                    },
                    "stage": {"type": "string", "description": "按当前加工环节筛选，如'CNC加工'、'质检'、'备料'、'热处理'"},
                    "due_before": {"type": "string", "description": "交期在此日期之前（含当天），格式 YYYY-MM-DD"},
                    "due_after": {"type": "string", "description": "交期在此日期之后（含当天），格式 YYYY-MM-DD"},
                    "sort_by": {"type": "string", "enum": ["交期", "数量", "id"], "description": "排序字段"},
                    "sort_order": {"type": "string", "enum": ["asc", "desc"], "description": "升序(asc)或降序(desc)，默认升序"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_customer",
            "description": (
                "查询客户档案：客户等级（A/B/C）、信用分、历史延期率。"
                "可按客户名模糊匹配或客户 id 精确查询。"
                "用于评估客户重要度、延期风险。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer": {"type": "string", "description": "按客户名模糊筛选，如'深圳精密五金'"},
                    "customer_id": {"type": "string", "description": "按客户 id 精确查询，如'C001'"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "搜索知识库（合同特殊条款 + 历史延期记录），混合检索 + 重排序。"
                "传入自然语言查询，返回最相关的文档片段及其来源。"
                "用于查合同条款（赔付/质检/加急规定）和历史延期案例。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询，自然语言描述要查什么，越具体越好"},
                    "top_k": {"type": "integer", "description": "返回片段数，默认 3", "default": 3},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_final_answer",
            "description": (
                "提交最终答案。所有调查步骤完成后调用。"
                "答案必须综合所有工具结果（订单数据 + 客户档案 + 合同条款 + 历史案例），"
                "引用具体内容（订单号、条款、案例号、金额等），并列出引用来源。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "description": "综合所有调查结果的最终回答，引用具体数据/条款/案例"},
                    "sources": {"type": "array", "items": {"type": "string"}, "description": "引用的来源列表（订单号/客户/合同文件/案例号）"},
                },
                "required": ["answer", "sources"],
            },
        },
    },
]


# ============================================================
# 工具执行器
# ============================================================

def execute_tool(tool_name, arguments, collection):
    """执行工具调用，返回结果字符串。"""
    if tool_name == "plan_investigation":
        question = arguments.get("question", "")
        items = arguments.get("todo_items", [])
        plan_text = "\n".join(f"  {i}. {item}" for i, item in enumerate(items, 1))
        return (
            f"调查计划已生成（问题：{question}）\n"
            f"待查事项（共 {len(items)} 项）：\n{plan_text}\n"
            f"请逐项调用相应工具执行。"
        )

    elif tool_name == "query_orders":
        # 过滤只传 query_orders 接受的参数，防模型传多余字段
        valid_keys = {"customer", "status", "stage", "due_before", "due_after", "sort_by", "sort_order"}
        args = {k: v for k, v in arguments.items() if k in valid_keys}
        result = query_orders(**args)
        total = result["total"]
        if total == 0:
            return "未查到符合条件的订单。请调整筛选条件。"
        lines = [f"查到 {total} 条订单："]
        for o in result["orders"]:
            lines.append(
                f"  - {o['id']} | {o['客户名']} | {o['产品']} | 数量{o['数量']} | "
                f"交期{o['交期']} | {o['当前环节']} | {o['状态']}"
            )
        return "\n".join(lines)

    elif tool_name == "query_customer":
        valid_keys = {"customer", "customer_id"}
        args = {k: v for k, v in arguments.items() if k in valid_keys}
        result = query_customer(**args)
        total = result["total"]
        if total == 0:
            return "未查到符合条件的客户。请检查客户名或 id。"
        lines = [f"查到 {total} 个客户："]
        for c in result["customers"]:
            lines.append(
                f"  - {c['id']} | {c['客户名']} | 等级{c['等级']} | "
                f"信用分{c['信用分']} | 历史延期率{c['历史延期率']}"
            )
        return "\n".join(lines)

    elif tool_name == "search_knowledge_base":
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 3)
        # 优先 day2 混合检索；reranker 未初始化则回退 day1 纯向量
        if _RERANKER is not None:
            hits = retrieve_hybrid(collection, _BM25, _CHUNKS, _METAS, _RERANKER, query, top_k=top_k)
            score_label = "rerank分"
            score_key = "rerank_score"
        else:
            hits = retrieve(collection, query, top_k=top_k)
            score_label = "距离"
            score_key = "distance"
        if not hits:
            return f"检索 '{query}'：未找到相关结果。请尝试用不同的查询词。"
        lines = [f"检索 '{query}' 命中 {len(hits)} 条："]
        for i, h in enumerate(hits, 1):
            lines.append(
                f"  [{i}] 来源: {h['source']}  {score_label}: {h.get(score_key, 0):.4f}\n"
                f"      内容: {h['text']}"
            )
        return "\n".join(lines)

    elif tool_name == "submit_final_answer":
        return "__FINAL_ANSWER__"

    else:
        return f"未知工具: {tool_name}"


# ============================================================
# Agent 循环（Todo-driven，复用 day4 骨架，支持 5 工具）
# ============================================================

AGENT_SYSTEM_PROMPT = """你是 3D 打印/CNC 加工生产调度助手，具备查订单、查客户档案、检索知识库三种能力。

## 工作流程（Todo-driven investigation）

收到用户问题后：
1. **规划**：调用 plan_investigation，把问题拆成 2-5 个待查事项，每项说明用哪个工具查什么。
2. **逐项执行**：按规划逐项调用工具（query_orders / query_customer / search_knowledge_base）。
   每个事项用一个工具。规划 N 项 -> 最多执行 N+1 次工具调用。
3. **综合回答**：所有事项查完后，调用 submit_final_answer 提交。答案综合订单数据、客户档案、合同条款、历史案例，引用具体内容（订单号、条款号、案例号、金额等）。

## 工具选用指引
- 问"有哪些订单/某客户订单/快超期订单"-> query_orders
- 问"客户等级/信用/延期率"-> query_customer
- 问"合同条款/赔付规定/质检要求/加急规定/历史案例"-> search_knowledge_base
- 复合问题（如"某客户订单情况+特殊要求"）-> 拆成多项，分别用 query_orders + query_customer + search_knowledge_base

## 规则
- 必须先 plan 再执行，不要跳过规划
- 工具结果是唯一信息来源，不要凭空编造
- 信息不够就在答案中诚实说明
- 规划 N 项 -> 最多执行 N+1 次 -> 必须调用 submit_final_answer
- 回答简洁专业，用中文

## 输出边界
- 只处理调度、订单、客户、合同、延期、质检、赔付相关
- 超出范围礼貌拒绝
"""


def _chat_with_tools(messages, verbose=True):
    """主备 fallback 调 LLM，带工具定义。"""
    from openai import OpenAI
    import httpx
    last_err = None
    for p in PROVIDERS:
        if not p.get("enabled"):
            continue
        if not _is_real_key(p["api_key"]):
            continue
        try:
            client = OpenAI(
                api_key=p["api_key"],
                base_url=p["base_url"],
                http_client=httpx.Client(trust_env=False),
            )
            resp = client.chat.completions.create(
                model=p["model"],
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=2000,
                temperature=0.3,
            )
            return resp, p, [f"  ✅ {p['name']:18s} 成功"]
        except Exception as e:
            last_err = e
            if verbose:
                print(f"  ❌ {p['name']:18s} 失败: {type(e).__name__}: {str(e)[:80]}")
            continue
    raise RuntimeError(f"所有 provider 均失败。最后错误: {last_err}")


def _brief_args(args):
    """工具参数简短摘要，用于日志。"""
    if "question" in args:
        return f"question='{args['question'][:40]}...', items={len(args.get('todo_items', []))}项"
    if "customer" in args or "customer_id" in args:
        return f"customer='{args.get('customer', args.get('customer_id', '?'))}'"
    if "query" in args:
        return f"query='{args['query'][:50]}...'"
    if "answer" in args:
        return f"answer='{args['answer'][:50]}...'"
    return str(args)[:60]


def run_agent(collection, user_question, verbose=True):
    """
    [AI:Claude] Todo-driven Agent 主循环（复用 day4 骨架，支持 5 工具）：
    1. 发 messages + TOOLS 给 LLM
    2. 有 tool_calls -> 执行工具 -> 结果回传 -> 回到 1
    3. 调 submit_final_answer 或达 MAX_TURNS 终止
    """
    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_question},
    ]
    tool_count = 0
    plan_items = []
    final_answer = None
    final_sources = []
    turn_log = []
    used = None
    MAX_TURNS = 10  # plan(1) + 工具(≤6) + submit(1) + 容错(2)

    for turn in range(1, MAX_TURNS + 1):
        if verbose:
            print(f"\n🔄 Turn {turn}（已执行 {tool_count} 次工具）...")

        resp, used, fb_log = _chat_with_tools(messages, verbose=verbose)
        if verbose:
            for line in fb_log:
                print(line)

        msg = resp.choices[0].message

        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError as e:
                    if verbose:
                        print(f"  ⚠️ JSON 解析失败: {e}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": f"JSON 解析错误: {e}。请重新调用，确保 arguments 是合法 JSON。",
                    })
                    continue
                if verbose:
                    print(f"  🔧 调用工具: {tool_name}({_brief_args(args)})")

                result = execute_tool(tool_name, args, collection)

                if verbose:
                    for line in result.split("\n")[:5]:
                        print(f"      {line}")
                    if len(result.split("\n")) > 5:
                        print(f"      ...（共 {len(result.split(chr(10)))} 行）")

                if tool_name == "plan_investigation":
                    plan_items = args.get("todo_items", [])
                    turn_log.append(f"📋 规划: {' -> '.join(plan_items)}")
                elif tool_name == "submit_final_answer":
                    final_answer = args.get("answer", "")
                    final_sources = args.get("sources", [])
                    turn_log.append("✅ 提交最终答案")
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{"id": tc.id, "type": "function",
                                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}}],
                    })
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": "最终答案已提交。"})
                    break
                else:
                    tool_count += 1
                    turn_log.append(f"🔧 {tool_name}: {_brief_args(args)}")

                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{"id": tc.id, "type": "function",
                                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}}],
                })
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

            if final_answer is not None:
                break
        else:
            text = msg.content or ""
            if verbose:
                print(f"  💬 模型文本回复: {text[:120]}...")
            messages.append({"role": "assistant", "content": text})
            messages.append({
                "role": "user",
                "content": "请按工作流程执行：先 plan_investigation 规划，再逐项调工具，最后 submit_final_answer。",
            })
            turn_log.append("⚠️ 未调工具，提示按流程走")

    if final_answer is None:
        final_answer = "（Agent 未在最大轮数内提交最终答案）"
        final_sources = []

    return {
        "answer": final_answer,
        "sources": final_sources,
        "plan_items": plan_items,
        "tool_count": tool_count,
        "turns": turn,
        "turn_log": turn_log,
        "provider": used["name"] if used else "无",
    }


# ============================================================
# 演示
# ============================================================

def demo():
    print("=" * 60)
    print("第一部分：加载向量库 + 混合检索层")
    print("=" * 60)
    collection = get_or_build_vectorstore()
    print(f"  向量库: {collection.count()} 条向量")
    init_retrieval(collection)
    print(f"  工具: plan_investigation / query_orders / query_customer / search_knowledge_base / submit_final_answer")

    scenarios = [
        (
            "深圳精密五金现在有哪些订单？客户等级和延期风险怎么样？合同对延期赔付怎么规定？",
            "测试 Agent 同时用 query_orders（查订单）+ query_customer（查客户档案）+ search_knowledge_base（查合同赔付条款）",
        ),
        (
            "广州航天精工有什么特殊要求？如果质检不合格会怎样？这个客户重要吗？",
            "测试 Agent 用 query_customer（查客户等级）+ search_knowledge_base（查合同全检/报废条款）",
        ),
        (
            "哪些订单快超期了？按交期排一下。其中东莞模具厂的订单有什么合同风险？",
            "测试 Agent 用 query_orders（查即将超期）+ search_knowledge_base（查东莞合同热处理排队条款）",
        ),
    ]

    print(f"\n{'=' * 60}")
    print("第二部分：调度助手 Agent（订单 + 客户 + 合同 三合一）")
    print("=" * 60)

    for i, (question, description) in enumerate(scenarios, 1):
        print(f"\n{'─' * 60}")
        print(f"场景 {i}：{question}")
        print(f"  （{description}）")
        print(f"{'─' * 60}")

        result = run_agent(collection, question, verbose=True)

        print(f"\n{'─' * 60}")
        print(f"📊 执行摘要")
        print(f"  Provider: {result['provider']}")
        print(f"  规划事项: {len(result['plan_items'])} 项")
        for item in result["plan_items"]:
            print(f"    - {item}")
        print(f"  工具调用: {result['tool_count']} 次")
        print(f"  总轮数: {result['turns']}")
        print(f"  来源: {', '.join(result['sources']) if result['sources'] else '无'}")
        print(f"\n💬 最终答案：")
        print(result["answer"])

    print(f"\n{'=' * 60}")
    print("✅ Week2 Demo 串联完成！")
    print("   调度助手 Agent 跑通：plan -> 查订单/查客户/查合同 -> submit 综合")
    print("   集成：week1 query_orders + day2 混合检索 + day4 plan/submit Agent 循环")
    print("   week1-2 成果汇总：API+主备 -> Function Calling -> Prompt 工程化 -> RAG -> 混合检索 -> Agentic RAG -> 多工具 Agent")


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    print("🚀 第二周 Day 5（周五）：Week2 Demo 串联（订单 + 客户 + 合同 三合一 Agent）\n")

    available = [p for p in PROVIDERS if p.get("enabled") and _is_real_key(p["api_key"])]
    if not available:
        print("❌ 没有可用的 provider！请检查 .env 配置")
        sys.exit(1)
    print(f"可用 provider: {', '.join(p['name'] for p in available)}")
    print(f"工具: query_orders（week1）+ query_customer（新）+ search_knowledge_base（day2 混合检索）")
    print(f"模式: Todo-driven investigation（Agent 自主规划多工具协同）\n")

    try:
        demo()
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
