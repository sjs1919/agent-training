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
| Week 1 | Jul 3-10 | API + Prompt 工程化 | [day1_guide](docs/week1/day1_guide.md) · [API 对比](docs/week1/day1_openai_vs_anthropic.md) · [fallback 架构](docs/week1/day1_主备fallback架构.md) · [day2_guide](docs/week1/day2_guide.md) · [day3 扩展](docs/week1/day3_extension.md) · [day4 原理](docs/week1/day4_guide.md) | [day1](scripts/week1/day1_api_basics.py) · [day2](scripts/week1/day2_function_calling.py) · [day3](scripts/week1/day3_system_prompt.py) · [day4](scripts/week1/day4_principles.py) · [data](scripts/week1/data/orders.csv) |
| Week 2 | Jul 13-17 | RAG + Agent 概念 | — | — |
| Week 3 | Jul 20-24 | MCP + LangGraph 单 Agent ⭐ | — | — |
| Week 4 | Jul 27-31 | 多 Agent 集群 + 鉴权 🎤 | — | — |
| Week 5 | Aug 3-7 | 可观测 + 业务匹配 | — | — |
| Week 6 | Aug 10-14 | 微调 + 推理优化 | — | — |
| Week 7 | Aug 17-21 | 多模态 Agent | — | — |

## 启动

```bash
# 1. 配置 API Key（主用 火山豆包）
#    编辑 .env，填入 VOLC_API_KEY=...

# 2. 安装依赖
pip install openai anthropic python-dotenv jinja2 tiktoken

# 3. 开始
cd scripts/week1 && python day1_api_basics.py
```

## 开发服务器

| 服务器 | IP | 备注 |
|--------|-----|------|
| `token_hub`    | 120.76.242.17 | 阿里云 ECS |
| `token_hub_47`  | 47.106.114.104 | 阿里云 ECS |
| `token_hub_172` | 172.26.68.61 | 经 `token_hub_47` 跳板 |

## 参考

- 路线图：[企业级 Agent 开发加速路线](docs/企业级Agent开发加速路线.md)
- 资料索引：[培训路线图分析](docs/培训路线图分析.md)
- Claude Code 学习仓库：[learn-claude-code](../../learn-claude-code)
