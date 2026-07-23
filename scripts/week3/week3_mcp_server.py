"""
第三周 · Day 2 - MCP Server 开发
==================================
目标：用 MCP Python SDK (FastMCP) 把 week2 的工具 + week3 新增工具全部注册到
      一个 MCP Server，实现工具的标准化暴露。

核心认知：
  MCP = 工具调用的 USB 协议——Server 独立部署，Client 自动发现工具
  对比 week2：工具和 Agent 同进程 → tools 直调函数
         week3：工具在独立 MCP Server 进程 → Client 通过 stdio 协议调用

架构演进：
  week2:  Agent ──直接调用──→ query_orders()
  week3:  Agent ──MCP协议──→ MCP Server ──内部──→ query_orders()

知识块：④ MCP (Model Context Protocol)
对比：见 docs/week3/day1_2_guide.md → Day2 → 第3节 MCP vs Function Calling

启动方式：
  python scripts/week3/week3_mcp_server.py
  （stdio 传输，由 MCP Client 进程启动，不直接对外暴露端口）

[AI:Claude] 架构设计：FastMCP 单 Server 模式（day3 拆为 order_server + resource_server）
"""

import csv
import sys
from pathlib import Path

# ---- 路径设置：week1/week2 无 __init__.py，用 sys.path 做 flat import ----
_WEEK_DIR = Path(__file__).parent
sys.path.insert(0, str(_WEEK_DIR.parent / "week1"))  # scripts/week1/ → from day2_function_calling import ...
sys.path.insert(0, str(_WEEK_DIR.parent / "week2"))  # scripts/week2/ → from day1_rag_basics import ...

# ---- 复用 week1 day2 的 query_orders ----
from day2_function_calling import query_orders  # noqa: E402

# ---- MCP SDK ----
from mcp.server.fastmcp import FastMCP  # noqa: E402

# Windows stdout UTF-8
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ============================================================
# FastMCP Server 创建
# ============================================================

mcp = FastMCP("3D打印生产调度工具服务器")


# ============================================================
# 工具注册区
# ============================================================
# FastMCP 通过 @mcp.tool() 装饰器自动完成：
#   ① 从函数签名 + docstring 生成 JSON Schema
#   ② 注册 tools/list 处理器（Client 连上后自动发现）
#   ③ 注册 tools/call 处理器（Client 调用时自动执行）
#
# 对比 week2 的 TOOLS 内联字典：
#   week2: 手写 JSON Schema dict + 手写 if/elif 路由
#   week3: 写普通 Python 函数 + @mcp.tool() → FastMCP 自动生成 Schema


# ============================================================
# 工具 1：query_orders（复用 week1 day2）
# 导航：知识块 ③ Tools → week2 工具定义 → query_orders
# ============================================================

@mcp.tool()
def tool_query_orders(
    customer: str | None = None,
    status: str | None = None,
    stage: str | None = None,
    due_before: str | None = None,
    due_after: str | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
) -> str:
    """
    查询 3D 打印/CNC 加工订单列表。可按客户名、状态、加工环节、交期范围筛选，支持排序。
    返回订单的 id、客户名、产品、数量、交期、当前环节、状态。
    用于回答"有哪些订单/某客户的订单/快超期的订单"等。
    """
    # 【原子操作】参数白名单：只传 query_orders 接受的参数
    valid_keys = {"customer", "status", "stage", "due_before", "due_after", "sort_by", "sort_order"}
    args = {k: v for k, v in locals().items() if k != "valid_keys" and v is not None}
    args = {k: v for k, v in args.items() if k in valid_keys}

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


# ============================================================
# 工具 2：query_customer（查客户档案）
# 导航：知识块 ③ Tools → week2 扩展 → 数据源为 customers.csv
# ============================================================

_CUSTOMERS_CACHE: list[dict] | None = None


def _load_customers() -> list[dict]:
    global _CUSTOMERS_CACHE
    if _CUSTOMERS_CACHE is None:
        csv_path = _WEEK_DIR.parent / "week2" / "data" / "customers.csv"
        with open(csv_path, encoding="utf-8") as f:
            _CUSTOMERS_CACHE = list(csv.DictReader(f))
    return _CUSTOMERS_CACHE


@mcp.tool()
def tool_query_customer(
    customer: str | None = None,
    customer_id: str | None = None,
) -> str:
    """
    查询客户档案：客户等级（A/B/C）、信用分、历史延期率。
    可按客户名模糊匹配或客户 id 精确查询。
    用于评估客户重要度、延期风险。
    """
    customers = _load_customers()
    result = []
    for c in customers:
        if customer_id and c["id"] != customer_id:
            continue
        if customer and customer not in c["客户名"]:
            continue
        result.append(c)

    if not result:
        return "未查到符合条件的客户。请检查客户名或 id。"

    lines = [f"查到 {len(result)} 个客户："]
    for c in result:
        lines.append(
            f"  - {c['id']} | {c['客户名']} | 等级{c['等级']} | "
            f"信用分{c['信用分']} | 历史延期率{c['历史延期率']}"
        )
    return "\n".join(lines)


# ============================================================
# 工具 3：query_inventory（新增 - 查物料库存）
# 导航：知识块 ③ → week3 新增工具 → 对照 inventory.csv
# ============================================================

_INVENTORY_CACHE: list[dict] | None = None


def _load_inventory() -> list[dict]:
    global _INVENTORY_CACHE
    if _INVENTORY_CACHE is None:
        csv_path = _WEEK_DIR / "data" / "inventory.csv"
        with open(csv_path, encoding="utf-8") as f:
            _INVENTORY_CACHE = list(csv.DictReader(f))
    return _INVENTORY_CACHE


@mcp.tool()
def tool_query_inventory(
    material: str | None = None,
    low_stock_only: bool = False,
) -> str:
    """
    查询物料库存：材料名、库存量、单位、采购周期、安全库存。
    可按材料名模糊筛选，或只看低库存（库存量低于安全库存的物料）。
    用于排产前检查物料是否充足。
    """
    items = _load_inventory()
    result = []
    for item in items:
        if material and material not in item["物料名称"]:
            continue
        stock = int(item["库存量"])
        safety = int(item["安全库存"])
        if low_stock_only and stock >= safety:
            continue
        result.append(item)

    if not result:
        return "未查到符合条件的物料。"

    lines = [f"查到 {len(result)} 条物料："]
    for item in result:
        stock = int(item["库存量"])
        safety = int(item["安全库存"])
        warn = " ⚠️低于安全库存!" if stock < safety else ""
        lines.append(
            f"  - {item['物料名称']} | 库存{stock}{item['单位']} | "
            f"安全库存{safety}{item['单位']} | 采购周期{item['采购周期(天)']}天{warn}"
        )
    return "\n".join(lines)


# ============================================================
# 工具 4：query_machine_load（新增 - 查机器负载）
# 导航：知识块 ③ → week3 新增工具 → 对照 machines.csv
# ============================================================

_MACHINES_CACHE: list[dict] | None = None


def _load_machines() -> list[dict]:
    global _MACHINES_CACHE
    if _MACHINES_CACHE is None:
        csv_path = _WEEK_DIR / "data" / "machines.csv"
        with open(csv_path, encoding="utf-8") as f:
            _MACHINES_CACHE = list(csv.DictReader(f))
    return _MACHINES_CACHE


@mcp.tool()
def tool_query_machine_load(
    machine_type: str | None = None,
    status: str | None = None,
) -> str:
    """
    查询机器负载：机器ID、型号、类型（SLM打印/CNC/SLS打印）、当前任务、预计空闲时间。
    可按机器类型筛选（如"SLM打印"、"CNC"），或按状态筛选（"运行中"/"空闲"/"准备中"）。
    用于调度时判断哪些机器可用。
    """
    machines = _load_machines()
    result = []
    for m in machines:
        if machine_type and machine_type not in m["类型"]:
            continue
        if status and m["状态"] != status:
            continue
        result.append(m)

    if not result:
        return "未查到符合条件的机器。"

    lines = [f"查到 {len(result)} 台机器："]
    for m in result:
        lines.append(
            f"  - {m['机器ID']} | {m['型号']} | {m['类型']} | "
            f"当前: {m['当前任务']} | 预计空闲: {m['预计空闲时间']} | {m['状态']}"
        )
    return "\n".join(lines)


# ============================================================
# 工具 5：search_knowledge_base（RAG 检索 - 可选，需向量库已构建）
# 导航：知识块 ⑤ RAG → week2 day2 混合检索 → 工具化封装
# ============================================================

_KB_READY = False
_COLLECTION = None
_BM25 = None
_CHUNKS = None
_METAS = None
_RERANKER = None


def _init_knowledge_base():
    """初始化知识库（向量库 + BM25 + Reranker），失败则保持 _KB_READY = False。"""
    global _KB_READY, _COLLECTION, _BM25, _CHUNKS, _METAS, _RERANKER
    if _KB_READY:
        return
    try:
        from day1_rag_basics import get_or_build_vectorstore, retrieve  # noqa: F811
        from day2_hybrid_rerank import build_bm25_index, load_reranker, retrieve_hybrid  # noqa: F811

        _COLLECTION = get_or_build_vectorstore()
        _BM25, _CHUNKS, _METAS = build_bm25_index(_COLLECTION)
        _RERANKER = load_reranker()
        _KB_READY = True
    except Exception:
        pass  # 知识库不可用时 _KB_READY 保持 False


@mcp.tool()
def tool_search_knowledge_base(query: str, top_k: int = 3) -> str:
    """
    搜索知识库（合同特殊条款 + 历史延期记录），混合检索 + 重排序。
    传入自然语言查询，返回最相关的文档片段及其来源。
    用于查合同条款（赔付/质检/加急规定）和历史延期案例。
    """
    _init_knowledge_base()
    if not _KB_READY:
        return "⚠️ 知识库未就绪（向量库或 Reranker 加载失败）。请联系管理员检查 ChromaDB 和模型文件。"

    from day1_rag_basics import retrieve  # noqa: F811
    from day2_hybrid_rerank import retrieve_hybrid  # noqa: F811

    if _RERANKER is not None:
        hits = retrieve_hybrid(_COLLECTION, _BM25, _CHUNKS, _METAS, _RERANKER, query, top_k=top_k)
        score_label = "rerank分"
        score_key = "rerank_score"
    else:
        hits = retrieve(_COLLECTION, query, top_k=top_k)  # type: ignore
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


# ============================================================
# 工具 6+7：Agent 编排工具（plan + submit）
# 导航：知识块 ② Agent 核心机制 → Todo-driven 模式 → 规划+提交
# ============================================================

@mcp.tool()
def tool_plan_investigation(question: str, todo_items: list[str]) -> str:
    """
    规划调查步骤。把用户问题拆成 2-5 个具体的待查事项，每项说明查什么、用哪个工具。
    可调查方向：查订单（tool_query_orders）、查客户档案（tool_query_customer）、
    查物料库存（tool_query_inventory）、查机器负载（tool_query_machine_load）、
    查合同/案例知识库（tool_search_knowledge_base）。

    todo_items 每项格式示例：
      "用 tool_query_orders 查深圳精密五金的订单"
      "用 tool_query_inventory 查铝合金粉库存"
      "用 tool_search_knowledge_base 查深圳合同赔付条款"
    """
    plan_text = "\n".join(f"  {i}. {item}" for i, item in enumerate(todo_items, 1))
    return (
        f"调查计划已生成（问题：{question}）\n"
        f"待查事项（共 {len(todo_items)} 项）：\n{plan_text}\n"
        f"请逐项调用相应工具执行。"
    )


@mcp.tool()
def tool_submit_final_answer(answer: str, sources: list[str]) -> str:
    """
    提交最终答案。所有调查步骤完成后调用。
    答案必须综合所有工具结果（订单数据 + 客户档案 + 合同条款 + 历史案例 + 库存 + 机器），
    引用具体内容（订单号、条款、案例号、金额等），并列出引用来源。
    """
    sources_text = "\n".join(f"  - {s}" for s in sources)
    return (
        f"✅ 最终答案已提交\n"
        f"引用来源（{len(sources)} 项）：\n{sources_text}\n\n"
        f"{'=' * 40}\n{answer}\n{'=' * 40}"
    )


# ============================================================
# 主入口：启动 stdio MCP Server
# ============================================================

if __name__ == "__main__":
    print("🚀 启动 3D打印生产调度 MCP Server（stdio 传输）...", file=sys.stderr)
    print(f"   工具: tool_query_orders / tool_query_customer / tool_query_inventory / "
          f"tool_query_machine_load / tool_search_knowledge_base / "
          f"tool_plan_investigation / tool_submit_final_answer", file=sys.stderr)
    print(f"   传输: stdio（由 MCP Client 启动子进程通信）", file=sys.stderr)
    print(f"   按 Ctrl+C 停止", file=sys.stderr)
    mcp.run(transport="stdio")
