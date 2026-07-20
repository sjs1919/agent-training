# 规则总索引

> **规则优先级（冲突裁决顺序）**：项目 CLAUDE.md 附加红线 > `stack-*/` > `common/`。

## 触发场景 → 加载文件

| 触发场景 | 加载文件 |
|---------|---------|
| TDD / 单测 / 集成测试 / E2E（流程与分层） | → `common/testing.md` |
| Go 测试执行 / WSL / Mock / 字段对齐 | → `stack-go/testing.md` |
| 前端测试执行 / Vitest / Playwright | → `stack-vue3/frontend-core.md` |
| 任务拆分 / 四门禁 / 执行模式（自动挡） | → `common/workflow.md` |
| 提问 / 需求澄清 / Bug 修复节奏 | → `common/conversation.md` |
| 需求澄清 / UI 原型设计（Superpowers Brainstorming） | → `common/skill-integration.md` |
| 需求变更影响分析 / 知识图谱（CodeGraph + Understand-Anything） | → `common/skill-integration.md` |
| 分支 / 提交 / 代码更新 | → `common/git.md` |
| 文档流转 / 归档 / 待办登记 | → `common/docs-flow.md` |
| 前后端接口对接 / API 文档同步 | → `common/api-contract.md` |
| 部署 / 发布 / 镜像构建 / 回滚 | → `common/deployment.md` |
| 服务器操作（读/写边界） | → `common/server-approval.md` |
| handler / service / repository 分层 | → `stack-go/arch.md` |
| 错误处理 / 错误码 | → `stack-go/error.md` |
| 日志 / SSE 流 | → `stack-go/logging.md` |
| 数据库 / 迁移脚本 | → `stack-go/database.md` |
| Redis / 缓存 | → `stack-go/redis.md` |
| API 设计（URL/分页/响应） | → `stack-go/api.md` |
| 测试 | → `stack-go/testing.md` |
| 运维 / 优雅关闭 | → `stack-go/ops.md` |
| 构建 / 服务重启 / 版本约束 | → `stack-go/build.md` |
| 前端组件 / 页面 / 状态管理 | → `stack-vue3/frontend-core.md` |

## 新栈追加协议（三步）

1. 新建 `stack-<x>/` 目录
2. 按 stack-go 九文件骨架逐条填写：arch / error / logging / db / cache / api / testing / ops / build
3. 在上表追加对应触发行

**`common/` 永不因换栈修改** —— 通用层与语言无关，新技术栈只做追加，不动已有文件。
