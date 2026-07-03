# 第一周 · Day 1 — 大模型谱系 + API 入门 + 主备 fallback

> **今日目标**：把模型当成一个函数来调，而不是一个聊天框；并建立主备容灾能力。
> **对应知识块**：① 大模型 API（编程化调用）必须章节①②
> **路线图位置**：`docs/企业级Agent开发加速路线.md` 第一周 Jul 1

---

## 今日学习清单

### 1. 大模型谱系（15min）

| 厂商 | 代表模型 | 特点 |
|------|---------|------|
| OpenAI | GPT-4o, GPT-4.1 | 综合能力最强，生态最成熟 |
| Anthropic | Claude Opus 4.8, Sonnet 4.6 | 代码能力强，长上下文（200K） |
| 开源/国产 | DeepSeek-V3, Qwen2.5, 豆包, Kimi | 可私有部署/国内易访问，成本低 |

**关键概念**：
- **Token**：模型计费的最小单位，≈0.75 个英文单词 / ≈0.5 个中文字
- **Context Window**：单次对话能处理的 Token 上限（Claude=200K, GPT-4o=128K）
- **Temperature**：输出随机性控制（0=确定 → 1=创意），代码生成 0.3-0.5

### 2. 知识块① 必须章节①②（30min）

> 参考资料：`docs/培训路线图分析.md` → 知识块 1

**必须章节①：Chat Completions API 请求/响应格式**
- 理解：`model` / `messages` / `system` / `max_tokens` / `temperature` 五个核心参数
- 搞懂：请求体 JSON → 模型推理 → 响应体 JSON 的完整链路

**必须章节②：Function Calling / Tool Use 参数定义**
- 理解：`tools` 数组的定义方式（name / description / input_schema）
- 对比：OpenAI Function Calling vs Anthropic Tool Use 的差异（概念相同，参数名不同）

### 3. 跑通第一个 API 调用（45min）

运行 `day1_api_basics.py`：
```bash
cd projects/agent-training
python week1/day1_api_basics.py
```
（Windows 终端若报 GBK 编码错：`PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python ...`）

### 4. 主备 fallback 架构（重点，1h+）

**这是 Day 1 的工程化核心，企业级 Agent 必备。**

> 📖 **理论文档**：`week1/day1_主备fallback架构.md`（面试导向，必读）

学习要点：
- LLM API 不是 100% 可用，单点不满足企业 SLA
- **五种容灾模式**：重试 / 主备 / 多活 / 熔断 / 降级（各解决什么问题）
- 重试 vs 切换的判断依据（看错误码：429/5xx 重试，401/402 切换，400 改请求）
- 代码实现：`day1_api_basics.py` 的 `call_with_fallback()`
- 当前实现的不足 + 生产级改进方向（熔断/超时/监控/降级）
- 生产级开源方案：LiteLLM / OpenRouter / Portkey

### 5. 多 Provider 配置实战（已完成的实操）

已在 `.env` 配置主备 Provider（详见记忆：`project-agent-training-providers`）：

| Provider | 角色 | 端点 | model | 状态 |
|---------|------|------|-------|------|
| DeepSeek | 主 | `api.deepseek.com` | `deepseek-v4-flash` | ✅ |
| 火山豆包 | 备1 | `ark.cn-beijing.volces.com/api/coding/v3` | `ark-code-latest` | ✅ |
| Kimi | 备2 | `api.kimi.com/coding/v1` | `kimi-for-coding` | ⏸️ 会员过期 |

**关键认知**：三家都是 OpenAI 兼容协议，代码层只差 `base_url + api_key + model`。学会一套协议 = 掌握所有国产模型。

---

## 今日产出

- [x] 理解 API 调用全链路（model → messages → 推理 → 返回）
- [x] 跑通第一个非流式 API 调用（DeepSeek）
- [x] 配置主备多 Provider（DeepSeek 主 + 豆包备 + Kimi 备禁用）
- [x] 实现主备 fallback（`call_with_fallback()`，主调失败自动切备用）
- [x] 验证 fallback 闭环（主正常 + 模拟主失效自动切豆包）
- [x] 掌握主备 fallback 理论（五种容灾模式、面试问答）—— 见 `day1_主备fallback架构.md`
- [ ] 理解 Function Calling / Tool Use 的概念（为 Day 2 做准备）

## 下一步

Day 2 → Function Calling / Tool Use 实战，在主备架构上叠加工具调用，Agent 闭环跑通。
工具：`query_orders()` 读 `week1/data/orders.csv`。
