# 股票自选股监控系统

## 功能

| 功能 | 触发时机 | 说明 |
|------|---------|------|
| 均线告警 | 盘中实时 | 突破/跌破 MA5/MA10/MA20 立即邮件通知 |
| AI 摘要 | 收盘后 | LLM 分析市场+个股走势，生成自然语言摘要邮件 |

## 快速开始

### 1. 配置自选股

编辑 `sock.yml`：

```yaml
stocks:
  - "600584"   # 长电科技
  - "002384"   # 东山精密
  - "688008"   # 澜起科技
  - "688147"   # 微导纳米
  - "300502"   # 新易盛
  - "688012"   # 中微公司
  - "688072"   # 拓荆科技
```

### 2. 安装依赖

```bash
pip install akshare pandas openai httpx pyyaml python-dotenv
```

### 3. 运行

```bash
cd projects/agent-training
python -m scripts.stock_monitor.main
```

## Docker 部署

```bash
# 构建
docker build -t stock-monitor:latest .

# 部署到 token_hub_47
docker save stock-monitor:latest | ssh token_hub_47 "docker load"
scp docker-compose.yml .env sock.yml token_hub_47:/opt/stock-monitor/
ssh token_hub_47 "cd /opt/stock-monitor && docker compose up -d"
```

## 运行时间

- 24/7 守护进程，交易时间自动监控，非交易时间自动休眠
- 盘中每10分钟轮询一次
- 收盘后自动发送 AI 摘要邮件

## 架构

```
sock.yml  ─→  config.py  ─→  main.py（调度器）
.env      ─→                 │
                             ├─ 盘中循环
                             │   ├─ data_fetcher  ← 腾讯 qt.gtimg.cn（个股）
                             │   ├─ ma_monitor    → 信号检测
                             │   └─ mail_sender   → QQ邮箱
                             │
                             └─ 收盘触发
                                 ├─ data_fetcher  ← 腾讯 sqt（指数）+ 新浪（全市场）
                                 ├─ llm_client    ← OpenAI (连接池)
                                 ├─ summarizer    → AI摘要
                                 └─ mail_sender   → QQ邮箱
```

## 注意事项

- **数据源**：使用腾讯财经 API（`qt.gtimg.cn`），非东方财富。详见下方「数据源踩坑记录」
- LLM 摘要质量取决于 provider 能力（火山豆包/DeepSeek）
- 如 LLM 全部不可用，摘要回退为纯数据拼接
- 不构成投资建议

## 数据源踩坑记录（2026-07-22）

### 踩坑一：东方财富 IP 被封

**问题**：stock-monitor 在 token_hub_47 上运行一段时间后，所有轮询报 `RemoteDisconnected`，收盘摘要市场数据是旧的。

**根因**：
1. 原始代码使用 akshare `stock_zh_a_spot_em()` — 底层请求东方财富 API，每次拉取全市场 5000+ 股票（约 58 页分页数据），只为从中筛选 7 只自选股
2. 每 10 分钟轮询 × 58 页 = **2262 HTTP 请求/天**
3. 东方财富反爬机制将服务器 IP（47.106.114.104）加入黑名单
4. akshare 默认每次新建 `requests.Session`，不带浏览器 UA

### 踩坑二：指数数据源选择

**问题**：需要三大指数（上证/创业板/科创50）+ 中证全指的成交量、成交额、环比。

**踩坑过程**：
1. 先用 `ak.stock_zh_index_spot_em()` → **失败**（东方财富 IP 被封）
2. 改用腾讯 `qt.gtimg.cn` 批量获取指数 → 但 qt 端点的**指数格式与个股不同**（指数 field 4=涨跌额，个股 field 4=昨收），导致 `change_pct` 解析出 3839% 的离谱值
3. 最终用腾讯 **sqt** 端点（`web.sqt.gtimg.cn`）：格式与个股一致，field 4=昨收，field 37=成交额(万元)

### 踩坑三：全市场统计的"隐藏数据源"

**问题**：需要全市场涨跌家数、中位数收益、总成交额/量及其环比。

**发现**：`ak.stock_zh_a_spot()` 走的是**新浪数据源**，不走东方财富！虽然 IP 被封，但这个函数依然可用。5529 只股票约 16 秒拉完，每天收盘只拉一次。

### 踩坑四：指数成交额环比无数据

**问题**：指数 K 线 API（`web.ifzq.gtimg.cn`）只返回 OHLCV（开盘/最高/最低/收盘/成交量），**没有成交额字段**。用 `volume × close` 估算指数成交额完全不对（指数成交额 = 成分股成交额之和，不是成交量 × 指数点位）。

**方案**：每天收盘后将当日的指数成交额/成交量保存到 JSON 文件，第二天加载做环比。首次运行无昨日数据，环比字段为空，第二天起准确。

### 踩坑五：LLM 摘要被截断

**问题**：部分个股 AI 摘要为空或被截断（如 "该股当日高开" 后面就没了）。

**根因**：
1. `max_tokens=300` 对中文文本太小（1 个中文字约 2-4 tokens）
2. DeepSeek 偶尔返回 `finish_reason="stop"` 但 `content=""`（空内容）

**修复**：个股 `max_tokens` 从 300 → 500，市场从 300 → 600，并在 `llm_client.py` 添加 `finish_reason` 诊断日志。

### 当前数据源架构

| 数据 | 来源 | API | 请求量 |
|------|------|-----|--------|
| 个股实时行情 | 腾讯财经 | `qt.gtimg.cn` | 1 次/轮询（7 股合并） |
| 个股历史 K 线 | 腾讯财经 | `web.ifzq.gtimg.cn` | 1 次/股 |
| 四大指数 | 腾讯财经 | `web.sqt.gtimg.cn` | 1 次/收盘（4 指数合并） |
| 全市场统计 | **新浪**（akshare 封装） | `stock_zh_a_spot()` | 1 次/收盘 |
| 指数环比 | 本地 JSON 缓存 | 文件读写 | 0 次 HTTP |

### 教训

1. **akshare 不只有一个数据源**：`_em` 后缀走东方财富，`stock_zh_a_spot()` 走新浪，一个被封不代表全挂
2. **腾讯不同端点格式不同**：`qt` 端点的指数格式与个股格式不一致，`sqt` 端点更标准但需要验证字段位置
3. **K 线 API 数据不全**：有 OHLCV 但没有成交额
4. **环比需要本地持久化**：无法从实时 API 获取昨日数据时，自己存
5. **中文 max_tokens 要放大**：300 tokens ≈ 100-150 个中文字，对摘要来说不够
