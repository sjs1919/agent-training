"""
第二周 · Day 4 - Agentic RAG 进阶层（Todo-driven 模式）
========================================================
目标：从"pipeline 固定检索"跃迁到"Agent 自主决定检索"。
      落地 Todo-driven investigation 模式——Agent 先规划要查什么，
      再逐项检索，最后综合回答。

核心认知：传统 RAG（day1）= 每次必检索，路径写死。
         Agentic RAG（day4）= Agent 决定何时检索、检索什么、检索几次、够不够。

今日模式：Todo-driven investigation
  Agent 收到问题 → plan_investigation 拆成待查事项 →
  逐项 search_knowledge_base → 全部查完 → submit_final_answer 综合回答

知识块：② Agent 核心机制 + ⑤ RAG 检索增强
复用：day1 的 Provider 主备架构 + Chroma 向量库
业务域：3D 打印/CNC 调度（合同条款 + 历史延期记录）

[AI:Claude] 架构设计：Todo-driven Agentic RAG，复用 day1 向量库 + Provider
"""

import json
import os
import sys
from pathlib import Path

# ---- 复用 day1 的 Provider + 向量库 ----
sys.path.insert(0, str(Path(__file__).parent))
from day1_rag_basics import (  # noqa: E402
    PROVIDERS,
    call_llm,
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

# ---- day2 混合检索层（BM25 + RRF + Cross-Encoder 重排）----
# 模块级初始化：demo 启动时调 init_retrieval 建好索引 + 加载 reranker，
# 之后 execute_tool 的 search_knowledge_base 优先用混合检索；未初始化则回退 day1 纯向量。
_BM25 = None
_CHUNKS = None
_METAS = None
_RERANKER = None


def init_retrieval(collection):
    """建 BM25 索引 + 加载 reranker，存到模块级全局。day2 混合检索前置。"""
    global _BM25, _CHUNKS, _METAS, _RERANKER
    _BM25, _CHUNKS, _METAS = build_bm25_index(collection)
    _RERANKER = load_reranker()

# Windows stdout UTF-8（开箱即跑）
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ============================================================
# Agentic RAG 的 System Prompt（Todo-driven 模式）
# ============================================================
# 对比 day1 的 RAG_SYSTEM_PROMPT（"只根据检索片段回答"），
# day4 的 prompt 多了"工作流程"——Agent 自己决定检索策略，不是被动等 context。

AGENTIC_RAG_SYSTEM_PROMPT = """你是 3D 打印/CNC 加工生产调度助手，具备自主检索知识库的能力。

## 工作流程（Todo-driven investigation）

收到用户问题后，按以下步骤执行：

1. **规划**：调用 plan_investigation 工具，把问题拆成 2-4 个具体的待查事项。
   每个事项写成一个独立的搜索查询（自然语言，越具体越好）。
   例如：用户问"客户A的订单延期了怎么赔？"
   → 事项：["客户A的合同赔付条款", "客户A的历史延期记录"]

2. **逐项检索**：按规划的顺序，逐项调用 search_knowledge_base。
   每次只查一个事项。如果某项检索结果不够，最多重试 1 次（用不同查询词）。
   **重要**：规划了 N 项，最多检索 N+1 次，之后必须提交答案。

3. **综合回答**：所有事项查完后，调用 submit_final_answer 提交最终答案。
   答案必须引用检索到的具体内容（条款、案例号、金额等），
   并在 sources 中列出所有引用的来源文件。

## 规则

- 必须先 plan 再 search，不要跳过规划直接搜索
- 检索片段是唯一的信息来源，不要凭空编造
- 如果某次检索没找到相关信息，在最终答案中诚实说明"知识库未覆盖"
- 规划 N 项 → 最多检索 N+1 次 → 必须调用 submit_final_answer
- 不要无限搜索，信息不够就在答案中诚实说明
- 回答简洁专业，用中文

## 输出边界

- 只处理调度、合同、延期、质检、赔付相关的问题
- 超出范围的问题礼貌拒绝
"""

# ============================================================
# 工具定义（OpenAI Function Calling 格式，与 week1 day2 一致）
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "plan_investigation",
            "description": (
                "规划调查步骤。把用户问题拆成 2-5 个具体的待查事项，"
                "每个事项写成一个独立的自然语言搜索查询。"
                "例如：用户问'深圳客户的合同有什么特殊要求？'"
                "→ ['深圳客户合同特殊条款', '深圳客户历史延期记录', '加急订单通用规定']"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "用户的原始问题（原文）",
                    },
                    "todo_items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "待查事项列表，每项是一个具体的搜索查询（2-5 项）",
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
            "name": "search_knowledge_base",
            "description": (
                "搜索知识库（合同特殊条款 + 历史延期记录）。"
                "传入自然语言查询，返回最相关的文档片段及其来源。"
                "如果第一次检索结果不够，可以用不同的查询词再搜。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询，用自然语言描述要查什么，越具体越好",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回片段数，默认 3",
                        "default": 3,
                    },
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
                "答案必须综合所有检索结果，引用具体内容（条款、案例号、金额等），"
                "并列出所有引用的来源文件。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "综合所有检索结果的最终回答，引用具体条款/案例/数据",
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "引用的来源文件列表",
                    },
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
            f"待查事项（共 {len(items)} 项）：\n"
            f"{plan_text}\n"
            f"请逐项调用 search_knowledge_base 检索。"
        )

    elif tool_name == "search_knowledge_base":
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 3)
        # 优先用 day2 混合检索+重排；reranker 未初始化则回退 day1 纯向量
        if _RERANKER is not None:
            hits = retrieve_hybrid(collection, _BM25, _CHUNKS, _METAS, _RERANKER, query, top_k=top_k)
            score_label = "rerank分"
            score_key = "rerank_score"
        else:
            hits = retrieve(collection, query, top_k=top_k)
            score_label = "距离"
            score_key = "distance"
        if not hits:
            return f"检索 '{query}'：未找到相关结果。请尝试用不同的查询词重新搜索。"
        lines = [f"检索 '{query}' 命中 {len(hits)} 条："]
        for i, h in enumerate(hits, 1):
            lines.append(
                f"  [{i}] 来源: {h['source']}  {score_label}: {h.get(score_key, 0):.4f}\n"
                f"      内容: {h['text']}"
            )
        return "\n".join(lines)

    elif tool_name == "submit_final_answer":
        # 最终答案：直接返回，Agent 循环检测到后终止
        return "__FINAL_ANSWER__"

    else:
        return f"未知工具: {tool_name}"


# ============================================================
# Agent 循环（Todo-driven）
# ============================================================


def run_agentic_rag(collection, user_question, verbose=True):
    """
    Todo-driven Agentic RAG 主循环。

    与 day1 传统 RAG 的本质区别：
    - day1: query → retrieve（固定）→ generate（固定）
    - day4: question → plan（Agent 决定）→ search（Agent 决定查几次）→ answer（Agent 决定够了）

    循环逻辑（与 week1 day2 的 ReAct 循环同构）：
    1. 发送 messages + 工具定义给 LLM
    2. LLM 返回 tool_calls 或文本回复
    3. 执行工具 → 结果回传 → 回到步骤 1
    4. 直到 LLM 调用 submit_final_answer 或达到 max_turns
    """
    messages = [
        {"role": "system", "content": AGENTIC_RAG_SYSTEM_PROMPT},
        {"role": "user", "content": user_question},
    ]

    search_count = 0
    plan_items = []
    final_answer = None
    final_sources = []
    turn_log = []
    used = None

    MAX_TURNS = 8  # plan(1) + searches(≤5) + submit(1) + 容错(1)

    for turn in range(1, MAX_TURNS + 1):
        if verbose:
            print(f"\n🔄 Turn {turn}（已执行 {search_count} 次检索）...")

        resp, used, fb_log = _chat_with_tools(messages, verbose=verbose)

        if verbose:
            for line in fb_log:
                print(f"  {line}")

        choice = resp.choices[0]
        msg = choice.message

        # 情况 1：模型返回 tool_calls → 执行工具
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError as e:
                    if verbose:
                        print(f"  ⚠️ JSON 解析失败: {e}")
                        print(f"     原始: {tc.function.arguments[:200]}...")
                    # 回传错误让模型重试
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
                    turn_log.append(f"📋 规划: {' → '.join(plan_items)}")

                elif tool_name == "search_knowledge_base":
                    search_count += 1
                    turn_log.append(f"🔍 检索 #{search_count}: {args.get('query', '?')[:60]}")

                elif tool_name == "submit_final_answer":
                    final_answer = args.get("answer", "")
                    final_sources = args.get("sources", [])
                    turn_log.append("✅ 提交最终答案")
                    # 追加 assistant 消息后终止循环
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                        ],
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": "最终答案已提交。",
                    })
                    break

                # 追加 assistant(tool_call) + tool(result) 到 messages
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                    ],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            if final_answer is not None:
                break

        # 情况 2：模型直接返回文本（没调工具）→ 提示它按流程走
        else:
            text = msg.content or ""
            if verbose:
                print(f"  💬 模型文本回复: {text[:120]}...")
            # 提示模型按流程走
            messages.append({"role": "assistant", "content": text})
            messages.append({
                "role": "user",
                "content": (
                    "请按工作流程执行：先调用 plan_investigation 规划调查步骤，"
                    "再逐项调用 search_knowledge_base 检索知识库，"
                    "最后调用 submit_final_answer 提交答案。"
                ),
            })
            turn_log.append(f"⚠️ 未调工具，提示按流程走")

    if final_answer is None:
        final_answer = "（Agent 未在最大轮数内提交最终答案）"
        final_sources = []

    return {
        "answer": final_answer,
        "sources": final_sources,
        "plan_items": plan_items,
        "search_count": search_count,
        "turns": turn,
        "turn_log": turn_log,
        "provider": used["name"],
    }


def _chat_with_tools(messages, verbose=True):
    """用主备 fallback 调 LLM，带工具定义。按 PROVIDERS 顺序逐个试，第一个成功即返回。"""
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
    """工具参数的简短摘要，用于日志输出。"""
    if "question" in args:
        return f"question='{args['question'][:40]}...', items={len(args.get('todo_items', []))}项"
    if "query" in args:
        return f"query='{args['query'][:50]}...'"
    if "answer" in args:
        return f"answer='{args['answer'][:50]}...'"
    return str(args)[:60]


# ============================================================
# 演示
# ============================================================


def demo():
    print("=" * 60)
    print("第一部分：加载向量库（复用 Day1）+ 混合检索层（Day2）")
    print("=" * 60)
    collection = get_or_build_vectorstore()
    print(f"  向量库: {collection.count()} 条向量")
    init_retrieval(collection)

    scenarios = [
        (
            "深圳精密五金的订单延期了，要赔多少钱？合同怎么规定的？",
            "测试 Agent 能否：规划→查合同条款→查历史案例→综合回答",
        ),
        (
            "广州航天精工有什么特殊要求？质检不合格怎么办？",
            "测试 Agent 能否：规划→查合同特殊条款→查历史质检案例→综合回答",
        ),
        (
            "加急订单有什么风险？以前有加急但没逾期的案例吗？",
            "测试 Agent 能否：规划→查加急规定→查历史加急案例→总结风险",
        ),
    ]

    print(f"\n{'=' * 60}")
    print("第二部分：Agentic RAG 自主检索（Todo-driven 模式）")
    print("=" * 60)
    print("  对比 Day1：Day1 是 pipeline 固定检索，Day4 是 Agent 自主决定")
    print("  Agent 会：规划 → 逐项检索 → 判断够了 → 综合回答")

    for i, (question, description) in enumerate(scenarios, 1):
        print(f"\n{'─' * 60}")
        print(f"场景 {i}：{question}")
        print(f"  （{description}）")
        print(f"{'─' * 60}")

        result = run_agentic_rag(collection, question, verbose=True)

        print(f"\n{'─' * 60}")
        print(f"📊 执行摘要")
        print(f"  Provider: {result['provider']}")
        print(f"  规划事项: {len(result['plan_items'])} 项")
        for item in result["plan_items"]:
            print(f"    - {item}")
        print(f"  检索次数: {result['search_count']}")
        print(f"  总轮数: {result['turns']}")
        print(f"  来源: {', '.join(result['sources']) if result['sources'] else '无'}")
        print(f"\n💬 最终答案：")
        print(result["answer"])

    print(f"\n{'=' * 60}")
    print("✅ Day 4 完成！")
    print("   Agentic RAG（Todo-driven）跑通：Agent 自主规划 → 逐项检索 → 综合回答")
    print("   对比 Day1：pipeline 每次必检索，Agent 不参与决策")
    print("   Day4：Agent 决定何时检索、检索什么、检索几次、何时够了")
    print("   下一步 -> Day 5（周五）：Week2 Demo 串联，week1 Agent + Agentic RAG")


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    print("🚀 第二周 Day 4：Agentic RAG 进阶层（Todo-driven 模式）\n")

    available = [p for p in PROVIDERS if p.get("enabled") and _is_real_key(p["api_key"])]
    if not available:
        print("❌ 没有可用的 provider！请检查 .env 配置")
        sys.exit(1)
    print(f"可用 provider: {', '.join(p['name'] for p in available)}")
    print(f"模式: Todo-driven investigation（Agent 自主规划检索策略）")
    print(f"复用: Day1 的 Chroma 向量库 + Provider 主备架构\n")

    try:
        demo()
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)