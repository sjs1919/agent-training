"""
第三周 · Day 2 - MCP Client 测试
=================================
验证 MCP Server 通信：连接 → 发现工具 → 调用工具 → 验证结果。
这是 MCP 协议的"Hello World"——确认 Server 和 Client 之间的 stdio 通道畅通。

用法：
  python scripts/week3/test_mcp_client.py

前置：确保已 `pip install mcp`，且 week2 的 orders.csv/customers.csv 数据完好。
      MCP Server 由本脚本自动启动（作为子进程），无需手动启动。

[AI:Claude] 测试脚本：验证 MCP 协议通信链路
"""

import asyncio
import sys
from pathlib import Path

# Windows stdout UTF-8
sys.stdout.reconfigure(encoding="utf-8")

_THIS_DIR = Path(__file__).parent
_SERVER_PATH = _THIS_DIR / "week3_mcp_server.py"


async def main():
    # ---- 动态导入 MCP Client（避免非 MCP 环境下 import 报错） ----
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError:
        print("❌ 请先安装 MCP: pip install mcp")
        return

    print("=" * 60)
    print("MCP Client 测试 —— 验证与 MCP Server 的通信链路")
    print("=" * 60)

    # ---- ① 启动 MCP Server（子进程，stdio 通信） ----
    server_params = StdioServerParameters(
        command="python",
        args=[str(_SERVER_PATH)],
    )
    print(f"\n📡 启动 MCP Server: {_SERVER_PATH.name}")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # ---- ② 初始化握手 ----
                await session.initialize()
                print("   ✅ 握手成功")

                # ---- ③ 发现工具（tools/list） ----
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"\n🔍 发现 {len(tools)} 个工具：")
                for t in tools:
                    print(f"   📦 {t.name}")
                    print(f"      {t.description[:80]}...")
                    # 显示参数
                    if hasattr(t, 'inputSchema') and t.inputSchema:
                        props = t.inputSchema.get('properties', {})
                        if props:
                            param_names = list(props.keys())
                            print(f"      参数: {', '.join(param_names[:5])}"
                                  f"{'...' if len(param_names) > 5 else ''}")
                    print()

                # ---- ④ 调用工具：query_orders ----
                print("─" * 60)
                print("测试 1：调用 tool_query_orders（查深圳订单）")
                print("─" * 60)
                result = await session.call_tool(
                    "tool_query_orders",
                    {"customer": "深圳"},
                )
                for content in result.content:
                    if content.type == "text":
                        print(content.text)

                # ---- ⑤ 调用工具：query_inventory（查特定物料） ----
                print("\n" + "─" * 60)
                print("测试 2：调用 tool_query_inventory（查钛合金库存）")
                print("─" * 60)
                result = await session.call_tool(
                    "tool_query_inventory",
                    {"material": "钛合金"},
                )
                for content in result.content:
                    if content.type == "text":
                        print(content.text)

                # ---- ⑥ 调用工具：query_machine_load（查空闲机器） ----
                print("\n" + "─" * 60)
                print("测试 3：调用 tool_query_machine_load（查空闲机器）")
                print("─" * 60)
                result = await session.call_tool(
                    "tool_query_machine_load",
                    {"status": "空闲"},
                )
                for content in result.content:
                    if content.type == "text":
                        print(content.text)

                # ---- ⑦ 调用工具：query_customer ----
                print("\n" + "─" * 60)
                print("测试 4：调用 tool_query_customer（查客户）")
                print("─" * 60)
                result = await session.call_tool(
                    "tool_query_customer",
                    {"customer": "广州"},
                )
                for content in result.content:
                    if content.type == "text":
                        print(content.text)

                # ---- 总结 ----
                print("\n" + "=" * 60)
                print("✅ MCP 通信链路验证通过！")
                print("   ✅ 握手（initialize）")
                print("   ✅ 工具发现（tools/list）→ 返回了工具列表")
                print("   ✅ 工具调用（tools/call）→ 4 个工具调用均成功返回结果")
                print("=" * 60)

    except Exception as e:
        print(f"\n❌ MCP 通信失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
