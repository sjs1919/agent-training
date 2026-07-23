"""
第三周 · Day 1 - 工具体系设计：ToolRegistry
=============================================
目标：从 week2 的"硬编码 TOOLS 列表 + if/elif 分支"演进到标准化的工具注册中心。
     这是 Agent 架构从"脚本"到"系统"的第一步。

核心认知：
  工具注册中心 = 集中管理工具的注册(Schema) + 发现(list) + 执行(handler)
  替代 week2 的：TOOLS 列表(散落) + execute_tool() if/elif(脆弱)

知识块：③ Tools/Skills 体系
对比：见 docs/week3/day1_2_guide.md → Day1 → 第5节 week2→week3 演进对比

[AI:Claude] 架构设计：ToolSchema + ToolRegistry，为 day2 MCP Server 提供工具管理基础
"""

from dataclasses import dataclass
from typing import Any, Callable


# ============================================================
# ToolSchema：工具的"身份证"
# ============================================================

@dataclass
class ToolSchema:
    """
    工具的标准化定义，包含 LLM 选择工具所需的全部信息。

    三个必须字段（OpenAI Function Calling + MCP 协议的共同要求）：
      name        — 唯一标识，字母+下划线，见名知意
      description — 自然语言描述，LLM **据此**决定何时调用该工具（最重要！）
      parameters  — JSON Schema，定义参数类型/枚举/必填，LLM 据此填参数

    一个辅助字段：
      category — 工具分类标签，用于分组发现（order/customer/inventory/system）
    """
    name: str
    description: str
    parameters: dict  # JSON Schema (type: object, properties: {...}, required: [...])
    category: str = "general"


# ============================================================
# ToolRegistry：工具注册中心
# ============================================================

class ToolRegistry:
    """
    工具注册中心——管理所有工具的生命周期。

    核心方法：
      register()        — 注册一个工具（Schema + Handler 一起注册）
      get_tool_defs()   — 获取 OpenAI Function Calling 格式的工具列表
      execute()         — 按名称执行工具，返回结果字符串
      list_by_category()— 按类别分组列出所有工具
      list_all()        — 列出所有工具名

    使用示例：
      >>> registry = ToolRegistry()
      >>> registry.register("query_orders", "查询订单列表", {...}, handler_fn, "order")
      >>> tools = registry.get_tool_defs()  # 传给 LLM
      >>> result = registry.execute("query_orders", {"customer": "深圳"})
    """

    def __init__(self):
        self._tools: dict[str, ToolSchema] = {}
        self._handlers: dict[str, Callable] = {}

    # ---- 注册 ----

    def register(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable[..., Any],
        category: str = "general",
    ) -> None:
        """
        注册一个工具。一个 register() 调用同时完成 Schema 定义和 Handler 绑定。

        与 week2 的对比：
          week2：1. 在 TOOLS 列表加 dict  2. 在 execute_tool() 加 elif  → 两步，分散
          week3：1. registry.register(...)  → 一步，集中
        """
        if name in self._tools:
            raise ValueError(f"工具 '{name}' 已注册，不能重复注册")

        self._tools[name] = ToolSchema(
            name=name,
            description=description,
            parameters=parameters,
            category=category,
        )
        self._handlers[name] = handler

    # ---- 发现 ----

    def get_tool_defs(self) -> list[dict]:
        """
        返回 OpenAI Function Calling 格式的工具列表。
        可直接传给 Chat Completions API 的 tools 参数。

        返回格式：
          [{"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}, ...]
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": schema.name,
                    "description": schema.description,
                    "parameters": schema.parameters,
                },
            }
            for schema in self._tools.values()
        ]

    def list_all(self) -> list[str]:
        """列出所有已注册的工具名称。"""
        return list(self._tools.keys())

    def list_by_category(self) -> dict[str, list[str]]:
        """
        按类别分组列出工具。用于了解各业务域有哪些工具可用。

        返回格式：
          {"order": ["query_orders"], "customer": ["query_customer"], ...}
        """
        result: dict[str, list[str]] = {}
        for name, schema in self._tools.items():
            result.setdefault(schema.category, []).append(name)
        return result

    def get_schema(self, name: str) -> ToolSchema | None:
        """获取单个工具的 Schema，不存在返回 None。"""
        return self._tools.get(name)

    # ---- 执行 ----

    def execute(self, name: str, arguments: dict) -> str:
        """
        执行指定工具，返回结果字符串。

        与 week2 的 execute_tool() if/elif 链不同：
          week2: if tool_name == "query_orders": ... elif ...  → O(n) 线性查找
          week3: self._handlers[name](arguments)               → O(1) 字典查找
        """
        if name not in self._handlers:
            available = ", ".join(self.list_all())
            return f"❌ 未知工具: '{name}'。可用工具: {available}"

        try:
            handler = self._handlers[name]
            # 【原子操作】参数白名单过滤：只传 Schema 中定义的参数，防 LLM 传多余字段
            schema = self._tools[name]
            valid_keys = set(schema.parameters.get("properties", {}).keys())
            if valid_keys:
                filtered_args = {k: v for k, v in arguments.items() if k in valid_keys}
            else:
                filtered_args = arguments  # 无参数约束时全部透传

            return handler(**filtered_args)
        except Exception as e:
            return f"❌ 工具 '{name}' 执行失败: {type(e).__name__}: {e}"

    # ---- 统计 ----

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        cats = self.list_by_category()
        parts = [f"{cat}: {len(names)}个工具" for cat, names in cats.items()]
        return f"ToolRegistry({len(self)}工具 | {', '.join(parts)})"
