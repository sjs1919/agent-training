# Week 3 — MCP + LangGraph 单 Agent

> **2026-07-20 ~ 07-24** | 知识块 ③ ④ ⑥
> 本周一句话：Demo 从"脚本"变成有架构的 Agent 系统。

## 产出

```
scripts/week3/
├── shared_data.py          # 共享数据层（CSV 加载 + 格式化）
├── order_server.py         # MCP Server: 订单服务（3 工具）
├── resource_server.py      # MCP Server: 资源服务（3 工具）
├── langgraph_agent.py      # LangGraph 调度 Agent（主入口）
└── data/
    ├── orders.csv          # 15 条订单
    ├── inventory.csv       # 10 种材料
    ├── machines.csv        # 8 台设备
    └── customers.csv       # 5 个客户
```

## 架构

```
用户提问
  ↓
LangGraph Agent（langgraph_agent.py）
  ├── analyze_intent     → 分析意图
  ├── select_and_execute → LLM 决策 + 调用工具
  ├── evaluate_results   → 判断数据是否足够
  └── generate_answer    → 综合调度建议
       ↓          ↑
   ┌───┴──────────┴───┐
   │   MCP 工具层       │
   │  order_server     │  query_orders / get_order_detail / get_production_status
   │  resource_server  │  query_inventory / query_machine_load / query_customer
   └──────────────────┘
```

## 运行

```bash
cd scripts/week3

# 启动 MCP Server（独立运行）
python order_server.py      # stdio MCP Server
python resource_server.py   # stdio MCP Server

# 运行 LangGraph Agent
python langgraph_agent.py
```

## 每日要点

### Day 1 — 工具体系设计
- 工具注册/发现机制：TOOLS 字典统一管理
- Schema 规范化：name/description/parameters 标准化
- 两套 Server 的工具按来源分组

### Day 2 — MCP Server 开发
- FastMCP 框架：`@mcp.tool()` 装饰器注册工具
- 两个独立 Server：order_server（订单域）+ resource_server（资源域）
- 通过 stdio 传输层通信

### Day 3 — MCP Client + 多 Server
- 工具按 namespace 分组管理
- Agent 自主决定调用哪个 Server 的工具
- 一次 LLM 调用可并行请求多个工具

### Day 4 — LangGraph 状态图
- StateGraph 替代手写 while 循环
- 条件边实现路由：数据不够 → 继续查，够了 → 生成答案
- 状态管理：messages / tool_results / iteration / final_answer

### Day 5 — Demo 串连
- 端到端场景：调度员问"今天先做哪些订单？"
- Agent 自主决定：查订单 → 查库存 → 查设备 → 查客户 → 综合排序
- 8 次工具调用，横跨两个 MCP Server