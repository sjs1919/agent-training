# Agent Training — 企业级 Agent 开发加速训练

> 2026年7月 ~ 8月，7周35天，从 Vibe Coding 到 Agent Developer
>
> **主用 API**：火山豆包 coding plan（OpenAI 兼容协议，字节编程套餐，已升级）
> 备用：DeepSeek（¥1/百万Token，性价比高）· 可随时切换 Anthropic Claude 或 OpenAI

## 目录结构

```
docs/      — 学习文档（按周组织）
scripts/   — 可运行脚本（按周组织，含 data/ 数据文件）
```

## 周计划

| 周 | 日期 | 主题 | 文档 | 脚本 |
|------|------|------|------|------|
| Week 1 | Jul 1-4 | API + Prompt 工程化 | [day1_guide](docs/week1/day1_guide.md) · [API 对比](docs/week1/day1_openai_vs_anthropic.md) · [fallback 架构](docs/week1/day1_主备fallback架构.md) · [day2_guide](docs/week1/day2_guide.md) | [day1](scripts/week1/day1_api_basics.py) · [day2](scripts/week1/day2_function_calling.py) · [data](scripts/week1/data/orders.csv) |
| Week 2 | Jul 7-11 | RAG + Agent 概念 | — | — |
| Week 3 | Jul 14-18 | MCP + LangGraph 单 Agent ⭐ | — | — |
| Week 4 | Jul 21-25 | 多 Agent 集群 + 鉴权 🎤 | — | — |
| Week 5 | Jul 28-Aug 1 | 可观测 + 业务匹配 | — | — |
| Week 6 | Aug 4-8 | 微调 + 推理优化 | — | — |
| Week 7 | Aug 11-15 | 多模态 Agent | — | — |

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

- 路线图：[企业级 Agent 开发加速路线](docs/企业级Agent开发加速路线.md)
- 资料索引：[培训路线图分析](docs/培训路线图分析.md)
