# 找工作 — 简历与面试准备

> 整合自两个来源：① `workspace/shared/resume`（简历归纳、经历补充、面试口径）② 本地 `job-portfolio/`（vibe coding 项目经验、技术面试要点）

## 文件结构

```
job-portfolio/
├── README.md                              ← 本文件（整合导航）
├── summary.md                             ← 简历汇总（持续更新）
├── resume-draft-2026-05-05.md             ← 简历草稿
│
├── vibe-coding经验与面试亮点.md             ← ③ vibe coding 3项目素材库
├── 简历版与面试要点.md                      ← ④ 简历 bullet + 8领域盲点 + 答法框架
│
├── docs/                                  ← 经历补充原始文档
│   ├── 未来工场经历补充-待补充清单.md        ★ P0/P1/P2 待补充项
│   ├── 项目负责人优化-培训稿.md              ★ 面试讲故事素材
│   ├── 苏坚生个人简历-技术经理-202202.md     旧版简历
│   ├── bumenggongzuo-20260522.md           部门工作
│   ├── jixiao-20260521.md                  绩效考核
│   ├── shuangzhou-20260521.md              双周迭代
│   ├── yanfaliucheng-20260521.md           研发流程
│   ├── zhinengjiqi-20260521.md             智能机器
│   ├── 主负责人.xmind                       思维导图
│   ├── ai-training/                        AI 编程培训材料
│   │   ├── 260522-prompt-training/         提示词工程培训
│   │   └── 260526-ai-coding-practice/      AI 编程实战指南
│   └── sessions/                           找工作对话记录
│
└── sessions/                              ← 简历归纳对话记录
    ├── session-2026-05-02.md
    ├── session-2026-05-03-目标定位.md
    ├── session-2026-05-05-近期经历补充.md
    ├── session-2026-05-07-猎头画像梳理.md
    ├── session-2026-05-08-面试演练.md
    ├── session-2026-05-20-近期经历补充.md
    └── session-2026-05-21-新文档归纳.md
```

## 核心阅读路径

| 场景 | 先读 | 再读 |
|------|------|------|
| **更新简历** | `summary.md` | `resume-draft-2026-05-05.md` |
| **准备面试** | `简历版与面试要点.md` §二（8领域盲点） | `vibe-coding经验与面试亮点.md` §三（项目亮点） |
| **补充经历** | `docs/未来工场经历补充-待补充清单.md` | 按 P0→P1→P2 逐项补 |
| **讲故事素材** | `docs/项目负责人优化-培训稿.md` | `vibe-coding经验与面试亮点.md` §四（缺点与教训） |
| **AI培训参考** | `docs/ai-training/` | 培训大纲 + 实战指南 |

## 面试核心资料（已就绪）

| 资料 | 文件 | 状态 |
|------|------|------|
| 简历汇总 | `summary.md` | 2026-05-20 更新 |
| 面试口径（离职原因/薪资谈判/反向考察） | `summary.md` §面试口径 | 2026-05-07 确定 |
| 8 技术领域盲点 + Top 10 | `简历版与面试要点.md` | 2026-07-07 整理 |
| Vibe Coding 3项目亮点/教训 | `vibe-coding经验与面试亮点.md` | 2026-07-07 整理 |
| 未来工场经历 P0 补充 | `docs/未来工场经历补充-待补充清单.md` | 部分完成 |
| 项目负责人机制 | `docs/项目负责人优化-培训稿.md` | 已完成 |

## 面试禁区（来自 `简历版与面试要点.md` §四）

- Agent 开发（未接触）、LangChain/LangGraph（未实战）、MCP 协议（未落地）
- 大模型微调/训练（应用层，不涉及）
- K8s/Service Mesh（Docker Compose 够用）

## 更新记录

- 2026-07-20：从 `workspace/shared/resume` 下载并整合到 `agent-training/job-portfolio/`
- 2026-07-07：本地创建 `vibe-coding经验与面试亮点.md`、`简历版与面试要点.md`
- 2026-05-05~05-27：多轮找工作对话，积累 sessions 和 docs
