# 第一周 · Day 4 — 原理速览：Token / Context / Temperature

> **今日目标**：补齐 week1 原理层，理解模型背后的三个"物理量"，为 week2 RAG 做铺垫。
> **对应知识块**：⑦ 提示词工程（延伸）+ ② Agent 核心机制（基础）
> **前置完成**：Day 3（Prompt 工程化 + Jinja2 + A/B + CoT）

---

## 学习确认清单

- [ ] 已读完 Token / 分词相关教材
- [ ] 已读完 Context Window 相关教材
- [ ] 已读完 Temperature / 采样参数相关教材
- [ ] 已对照 `day4_principles.py` 运行结果理解三个概念
- [ ] 已用自己的话把下方填空补完

---

## 1. Token — 模型的最小处理单元

### 读完教材后，确认以下要点

- [ ] 我知道 Token 是模型的最小处理单元，不是字符也不是单词
- [ ] 我知道中文 1 汉字大约 ______ token，英文平均 ______ 字符 / token
- [ ] 我知道计费按 ______ token + ______ token 分开计算
- [ ] 我亲手用过 [OpenAI Tokenizer](https://platform.openai.com/tokenizer) 或 `tiktoken` 验证过至少一段中文/英文

### 用自己的话概括

Token 就是：______

它和字符的区别是：______

### 对照脚本

`day4_principles.py` 里 Day1/2/3 的输入 token 估算结果分别是：______ / ______ / ______

我的理解：为什么 Day3 比 Day2 多这么多 token？______

---

## 2. Context Window — 上下文窗口

### 读完教材后，确认以下要点

- [ ] 我知道 Context Window = 输入 + 输出 token 的总上限
- [ ] 我知道 Attention 计算复杂度约 ______，窗口翻倍会让成本/延迟大约翻 ______ 倍
- [ ] 我知道长文本处理三种策略：______ / ______ / ______
- [ ] 我知道重要信息应该放在 prompt 的 ______ 位置

### 用自己的话概括

Context Window 就是：______

为什么不能无脑塞满？______

### 常见模型窗口（读完教材后，把不确定的查一下补全）

| 模型 | 上下文窗口 | 协议 |
|------|-----------|------|
| 豆包 ark-code-latest | ______ | OpenAI 兼容 |
| DeepSeek-V3 | ______ | OpenAI 兼容 |
| GPT-4o | ______ | OpenAI |
| Claude 3.5 Sonnet | ______ | Anthropic |
| Kimi k1.5 | ______ | Moonshot |

---

## 3. Temperature / 采样参数

### 读完教材后，确认以下要点

- [ ] 我知道 Temperature 控制的是 ______
- [ ] 我知道事实查询 / 代码生成推荐温度区间 ______
- [ ] 我知道通用任务推荐温度区间 ______
- [ ] 我知道创意写作推荐温度区间 ______
- [ ] 我知道 `temperature` 和 `top_p` 应该 ______
- [ ] 我知道 `top_k` 只在 ______ API 里有

### 用自己的话概括

Temperature 就是：______

生产环境中调温度时，我还要注意：______

### 对照脚本

`day4_principles.py` 里同一条 prompt、三种 temperature 的输出差异：

- temperature=0.3：______
- temperature=0.7：______
- temperature=1.0：______

我的观察：______

---

## 面试速记卡（读完后，用自己的话重写一遍）

```
Q: Token 和字符什么关系？
A: ________________________________________________

Q: Context Window 越大越好？
A: ________________________________________________

Q: Temperature 怎么选？
A: ________________________________________________

Q: 长文本怎么处理？
A: ________________________________________________
```

---

## 参考教材（必读清单）

### 1. Token / 分词

- **权威**
  - [OpenAI Tokenizer 工具（可视化）](https://platform.openai.com/tokenizer)
  - [tiktoken - OpenAI 官方 Python 分词库](https://github.com/openai/tiktoken)
- **中文**
  - [大模型 Token 与分词器详解 - 知乎](https://zhuanlan.zhihu.com/p/643434021)
  - [BPE 分词算法（原理）- 知乎](https://zhuanlan.zhihu.com/p/424631681)

### 2. Context Window / 上下文窗口

- **权威**
  - [Anthropic Long context tips](https://docs.anthropic.com/en/docs/build-with-claude/context-windows)
  - [OpenAI Model 页 context 列](https://platform.openai.com/docs/models)
- **中文**
  - [内存管理与上下文优化 - 腾讯云](https://cloud.tencent.cn/developer/article/2557090)
  - [从 Prompt 到上下文工程构建 Agent - 腾讯云](https://cloud.tencent.cn/developer/article/2586420)

### 3. Temperature / 采样参数

- **权威**
  - [OpenAI Chat Completions API 参数](https://platform.openai.com/docs/api-reference/chat/create)
  - [Anthropic Messages API 参数](https://docs.anthropic.com/en/api/messages)
- **中文**
  - [大模型采样参数完全指南 - 知乎](https://zhuanlan.zhihu.com/p/653927240)
  - Jimmy Song《提示词工程核心技术》里“温度参数”章节

### 4. 与本日脚本联动

- 读 Token 时，对照 `scripts/week1/day4_principles.py` 里的 `count_tokens()` 和运行结果
- 读 Temperature 时，对照脚本里的 0.3 / 0.7 / 1.0 三组输出差异

---

## 完成确认

全部读完后，把顶部“学习确认清单”五个 `[ ]` 都打上勾，并把填空补完。然后可以进入 week2 预习。
