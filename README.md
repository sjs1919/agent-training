# Agent Training — 企业级 Agent 开发加速训练

> 2026年7月 ~ 8月，7周35天，从 Vibe Coding 到 Agent Developer
> 
> **主用 API**：火山豆包 coding plan（OpenAI 兼容协议，字节编程套餐，已升级）
> 备用：DeepSeek（¥1/百万Token，性价比高）· 可随时切换 Anthropic Claude 或 OpenAI

## 目录结构

```
docs/      — 学习文档（按周组织）
scripts/   — 可运行脚本（按周组织，含 data/ 数据文件）

周计划：
  week1/  — API + Prompt 工程化（Jul 1-4）
  week2/  — RAG + Agent 概念（Jul 7-11）
  week3/  — MCP + LangGraph 单 Agent（Jul 14-18）⭐
  week4/  — 多 Agent 集群 + 鉴权（Jul 21-25）🎤 7/23
  week5/  — 可观测 + 业务匹配（Jul 28-Aug 1）
  week6/  — 微调 + 推理优化（Aug 4-8）
  week7/  — 多模态 Agent（Aug 11-15）
```

## 启动

```bash
# 1. 配置 API Key（主用 火山豆包）
#    编辑 .env，填入 VOLC_API_KEY=...

# 2. 安装依赖
pip install openai anthropic python-dotenv

# 3. 开始
cd scripts/week1 && python day1_api_basics.py
```

## 参考

- 路线图：`docs/企业级Agent开发加速路线.md`
- 资料索引：`docs/培训路线图分析.md`
