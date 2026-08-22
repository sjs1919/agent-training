# agent-training-demo 项目规范（薄入口 · 基于模板 v1.2）

## 项目定位

制造业排程排产多 Agent 助手（第二阶段重构）。文档仓：docs/demo/（spec / plan / todo 全部写入该目录编号子目录）。

## Top 红线

- 🚫 禁止自动 git：commit / push / pull 必须用户发起
- 🚫 禁止自主部署：编译测试通过后必须经用户批准（门禁4）
- 🚫 未测试禁止部署：python run_all_tests.py 全过 + 构建成功才可提请部署
- 🚫 敏感信息不入库：密码/密钥只留占位符，真实值在 docs/demo/credentials.local.md

## 附加红线（本项目特有）

1. **豁免区**：`job-portfolio/`、`docs/`（demo 子目录除外）为轻量文档区，不走四门禁流程；仅守 commit 格式与敏感信息两条红线。
2. **冲突消歧**：与 workspace 根 CLAUDE.md 冲突时（如并行 Agent 上限、命令速查），以本仓 `rules/rules-index.md` 及其加载文件为准。

## 编码红线（Karpathy 原则）

1. **先思考** - 明假设、曝困惑、呈权衡；不默选、敢反对
2. **简单优先** - 最少代码解决问题；不预设扩展；200 行能 50 行就重写
3. **外科手术** - 只改要求的；不动相邻代码/格式；保持现有风格；清理无用 import
4. **目标驱动** - 先定义可验证标准；多步任务列「步骤->验证」清单

## 命令速查

测试 `python run_all_tests.py` · 构建 `docker compose build`（WSL 下）· 静态检查 `python -m compileall demo`

## 规则总索引

全部规则见 `rules/rules-index.md`（按触发场景加载）。本文件不承载规则条款。
