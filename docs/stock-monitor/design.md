# 股票自选股监控系统 — 设计文档

## 1. 概述

本系统对 `sock.yml` 中配置的 7 只自选股进行盘中均线监控和盘后 AI 摘要，结果通过 QQ 邮箱推送。部署为 Docker 容器，24/7 运行于 token_hub_47 服务器。

### 1.1 核心需求

| 编号 | 需求 | 触发时机 |
|------|------|---------|
| R1 | 盘中监控自选股跌破/突破 5日、10日、20日均线，触发信号立即邮件通知 | 周一~五 9:00-15:30 |
| R2 | 收盘后生成当日市场整体走势摘要（AI），邮件发送 | 15:30 后 |
| R3 | 收盘后生成自选股表现表（纯数据 9 列：收盘价/涨跌幅/成交额/换手率/振幅/均线关系/走势特征），邮件发送 | 15:30 后 |

## 2. 架构决策

### 2.1 决策记录

| ID | 决策 | 选择 | 理由 |
|----|------|------|------|
| D1 | LLM 调用方式 | 连接池 + 主备 fallback | 复用现有 day1_api_basics.py 已验证的 provider 链；预创建 httpx client 复用以避免每次调用的 TCP 握手开销 |
| D2 | 摘要方案 | akshare 结构数据 → LLM → 自然语言 | 用户需求：让 AI 基于真实行情数据做分析，而非模板拼接数字；LLM 能捕捉走势特征和量价关系 |
| D3 | 运行时模式 | 24/7 守护进程（非交易时休眠） | Docker 容器需长期运行；退出即重启会形成非交易日的重启风暴；休眠是更优雅的方案 |
| D4 | 盘中轮询间隔 | 10 分钟（600s） | 用户指定；平衡 akshare 反爬限制和信号及时性 |
| D5 | 均线计算 | pandas `rolling(N).mean()`，基于前复权(前复权)数据 | pandas 零额外依赖；前复权保证均线连续性（不受除权除息干扰） |
| D6 | 信号去重 | 内存 `Set[str]`（key = code_ma_direction） | 同一均线方向一天内只告警一次；反向信号自动清除旧信号允许再次触发 |
| D7 | 部署方式 | Docker → token_hub_47 | 与现有 token-hub 项目同机部署；统一运维管理 |
| D8 | 邮件通道 | QQ 邮箱 SMTP（sjs1919@qq.com） | 复用 .env 已有配置；SMTP 直连无中间依赖 |
| D9 | 数据源迁移 | 东方财富 → 腾讯财经 | 2026-07-22: stock_zh_a_spot_em() 拉全市场5000+只股票(58页分页)导致服务器IP被东方财富封禁;改用 qt.gtimg.cn 个股API,7只自选股=7个请求 |

### 2.2 为什么 LLM 连接池

```
不良模式（每次新建 client）:
  请求1: New OpenAI() → New httpx.Client() → TCP握手 → API调用 → 丢弃
  请求2: New OpenAI() → New httpx.Client() → TCP握手 → API调用 → 丢弃
  → 每只股票额外消耗 2-3 个 RTT（约 100-300ms）

连接池模式（本系统）:
  启动: init_clients() → 每个 provider 创建 1 个 OpenAI + httpx.Client
  请求1: _client_pool["火山豆包"] → 复用已有连接 → API调用
  请求2: _client_pool["火山豆包"] → 复用已有连接 → API调用
  → 收盘 7 只股票 + 1 个市场摘要 = 8 次 LLM 调用，全部复用同一 TCP 连接
```

### 2.3 为什么表格纯数据、LLM 只做叙事

```
设计原则：表格用数据直接驱动，LLM 只负责需要"解读"的叙事部分。

收盘总结四板块分工：
  - 大盘概况表（数据）：5 指数收盘/涨跌幅/成交额/成交额环比
                      + 全市场成交额（上证+深证求和）
  - 自选股表（数据）：9 列，收盘价/涨跌幅/成交额/换手率/振幅/均线关系/走势特征
    · 走势特征由规则判定（涨跌幅 + 振幅 -> 强势上涨/稳步上涨/窄幅震荡等），非 LLM
  - 市场特征（LLM）：5-8 个要点，从指数分化判断情绪/资金/结构/技术面
  - 后市展望（LLM）：3-4 句话短期趋势判断

为什么不为每只股票单独调 LLM（旧设计已废弃）：
  - 旧设计 7 只股票 × 1 LLM = 7 次调用，慢且贵，个股摘要易被截断
  - 表格 9 列已能直观呈现量价关系和均线状态，走势特征规则足够
  - LLM 集中火力做市场特征 + 后市展望（共 2 次调用），性价比更高

build_stock_snapshot 仍构建 price/ma/trajectory JSON，但 trajectory 当前未被表格使用，
保留是为后续若恢复个股 LLM 摘要预留。
```

## 3. 数据流

### 3.1 盘中监控流程

```
┌──────────┐  每10分钟   ┌──────────────┐  7股批量合并   ┌────────────┐
│  main.py │───────────>│ data_fetcher  │──────────────>│ 腾讯 qt    │
│  调度器   │           │ get_realtime  │               │qt.gtimg.cn │
└────┬─────┘           │ _quotes()     │               └────────────┘
     │                 └──────┬───────┘
     │  7只自选股              │  每只分别取历史K线（前复权）
     │  实时价+名称            ↓
     │                 ┌──────────────┐
     │                 │ data_fetcher  │  web.ifzq.gtimg.cn
     │                 │ get_latest_ma │  fqkline/get?qfq
     │                 │ _values()     │  rolling(5/10/20).mean()
     │                 └──────┬───────┘
     │                        │ {"MA5": 34.5, "MA10": 36.1, ...}
     ↓                        ↓
┌──────────────┐     ┌──────────────┐
│ ma_monitor   │←────│ 7只 × 均线值  │
│ check_stock()│     └──────────────┘
│ 去重检测     │
└──────┬───────┘
       │ 新信号 List[MASignal]
       ↓
┌──────────────┐     ┌──────────────┐
│ mail_sender  │─────>│ QQ SMTP      │
│ HTML 邮件    │      │ sjs1919@qq   │
└──────────────┘     └──────────────┘
```

### 3.2 收盘摘要流程

```
交易时间结束 (15:30)
       │
       ↓
┌──────────────┐     ┌──────────────────┐
│ summarizer   │─────>│ data_fetcher     │  腾讯 web.sqt.gtimg.cn（5指数批量）
│ build_market │      │ get_all_index_   │  含成交额/环比（本地JSON持久化）
│ _table()     │      │ data()           │
└──────┬───────┘     └──────────────────┘
       │ market_table: 5指数 + 全市场成交额(上证+深证求和)
       ↓
┌──────────────┐     ┌──────────────────┐
│ summarizer   │─────>│ data_fetcher     │  腾讯 qt（7股批量实时）
│ build_stock  │      │ get_realtime_    │  + web.ifzq K线（每股均线）
│ _table()     │      │ quotes + hist    │
└──────┬───────┘     └──────────────────┘
       │ stock_table: 7 × 9列（纯数据，无 LLM）
       ↓
┌──────────────┐     ┌──────────────────┐
│ summarizer   │      │ llm_client       │  1. 市场特征（5-8要点, max_tokens=800）
│ generate_    │─────>│ call_with_       │  2. 后市展望（3-4句, max_tokens=400）
│ market_char  │      │ fallback()       │
│ + outlook()  │      │ 主:火山豆包      │
└──────┬───────┘      │ 备:DeepSeek      │
       │              │ 末:数据拼接兜底  │
       │              └──────────────────┘
       │ {market_table, market_characteristics, stock_table, outlook}
       ↓
┌──────────────┐
│ mail_sender  │  build_summary_html(summary)
│ 四板块HTML   │─────> QQ SMTP
└──────────────┘
```

### 3.3 完整时间线

```
09:00 ───────────────────────────────────── 15:30 ───────> 次日 09:00
 │                                            │
 ├─ 每10分钟轮询 ──> 有信号则发邮件            │
 │                                            │
 │  data_fetcher.get_realtime_quotes() [腾讯qt]  │
 │  data_fetcher.get_latest_ma_values()[腾讯K线] │
 │  ma_monitor.check_stock()                  ├─ 收盘触发
 │  mail_sender.send_email() [if signals]     │
 │                                            │
 │                                            │  summarizer.generate_close_summary()
 │                                            │    build_market_table()  [腾讯sqt]
 │                                            │    build_stock_table()   [腾讯qt+K线]
 │                                            │    generate_market_char() [LLM ×1]
 │                                            │    generate_outlook()     [LLM ×1]
 │                                            │  mail_sender.send_email() [四板块HTML]
 │                                            │
 └────────────────────────────────────────────┘──── 休眠至次日09:00 ────
```

## 4. 模块职责

### 4.1 config.py — 配置中心

**职责**：从 `sock.yml`（自选股/监控参数）和 `.env`（密钥/Provider/SMTP）加载全量配置。

**对外接口**：
| 函数 | 返回值 | 说明 |
|------|--------|------|
| `load_config()` | `AppConfig` | 单次调用，返回完整配置 |
| `get_enabled_providers(cfg)` | `List[ProviderConfig]` | 过滤已启用且 key 有效的 provider |

**核心类型**：
- `AppConfig`: 顶层聚合 → stocks, moving_averages, monitor, email, providers
- `ProviderConfig`: 单个 LLM 供应商（name, api_key, base_url, model, enabled）
- `EmailConfig`: SMTP/收件人配置
- `MonitorConfig`: 交易时间/轮询间隔

**依赖**：`sock.yml`（本地），`.env`（本地），`pyyaml`，`python-dotenv`

---

### 4.2 llm_client.py — LLM 连接池

**职责**：管理 OpenAI 兼容 LLM 客户端的生命周期。启动时预创建连接池，提供带 fallback 的调用接口。

**对外接口**：
| 函数 | 说明 |
|------|------|
| `init_clients(config)` | 启动时调用一次，为每个 enabled provider 创建 `OpenAI(httpx.Client)` |
| `call_llm(provider, sys, usr, ...)` | 指定 provider 调用 LLM，复用连接池中的 client |
| `call_with_fallback(config, sys, usr, ...)` | 按 providers 顺序链式尝试，主调失败自动切备用 |
| `close_clients()` | 退出时关闭所有 client（释放 TCP 连接） |

**设计要点**：
- `trust_env=False` 绕过 Windows 系统代理（避免死代理导致 SSL EOF）
- `httpx.Limits(max_keepalive_connections=5)` 控制连接池大小
- `httpx.Timeout(120.0)` 120 秒超时（LLM 生成可能需要较长时间）
- Fallback 日志可追踪每次使用了哪个 provider

**依赖**：`config.ProviderConfig`，`openai`，`httpx`

---

### 4.3 data_fetcher.py — 数据获取

**职责**：封装行情数据获取。腾讯财经为主（qt/sqt/ifzq），akshare 仅用于代码名映射与遗留全市场统计。持久 Session + UA + Retry 防反爬。

**对外接口**：
| 函数 | 数据源 | 用途 |
|------|--------|------|
| `get_code_name_map()` | akshare `stock_info_a_code_name()` | 代码→名称映射（内存缓存，上交所/深交所接口不受 IP 封影响） |
| `get_realtime_quotes(codes)` | 腾讯 `qt.gtimg.cn`（7股批量1请求） | 盘中实时行情快照 |
| `get_hist_data(code, days)` | 腾讯 `web.ifzq.gtimg.cn` fqkline（前复权） | 历史日K线 + 自动计算 MA5/10/20 |
| `get_latest_ma_values(code)` | `get_hist_data()` | 最新均线值（MA5/10/20） |
| `get_all_index_data()` | 腾讯 `web.sqt.gtimg.cn`（5指数批量） | 五指数收盘/涨跌/成交额 + 环比（本地JSON持久化） |
| `get_market_stats()` | akshare `stock_zh_a_spot()`（新浪源） | 全市场涨跌家数/中位数 -- 当前主路径未调用，遗留接口 |
| `build_stock_snapshot(code, name, rt_data)` | `get_hist_data()` + 实时行情 | 自选股表用的 JSON 快照（price/ma/trajectory） |
| `build_market_table()`（summarizer） | `get_all_index_data()` | 大盘概况表（纯数据，上证+深证求和得全市场成交额） |

**数据时序**：
- 实时行情：腾讯 qt 近实时（非东方财富 15 分钟延迟）
- 历史 K 线：前复权（腾讯 `qfq`），保证均线连续性
- 防反爬：持久 Session + 浏览器 UA + Retry(3) + `_rate_limit()` 0.15-0.4s

**依赖**：`akshare`（代码名映射 + 遗留统计），`pandas`，`requests`

---

### 4.4 ma_monitor.py — 均线监控

**职责**：检测盘中价格与均线的交叉信号，去重避免重复告警。

**对外接口**：
| 方法 | 说明 |
|------|------|
| `check_stock(code, name, price, ma_values)` | 返回新触发的 `List[MASignal]` |
| `reset_day()` | 新交易日清空触发记录 |
| `clear_reverse(code, ma, direction)` | 反向信号清除旧记录 |

**信号模型**：
```python
@dataclass
class MASignal:
    code: str          # 600584
    name: str          # 长电科技
    price: float       # 当前价
    ma_type: str       # MA5 / MA10 / MA20
    ma_value: float    # 均线值
    direction: str     # 向上突破 / 向下跌破
    timestamp: str     # 2026-07-21 14:30:00
```

**去重逻辑**：
```
同一日：600584_MA5_向上突破 只触发一次（Set 记录）
反向信号：600584 突破 MA5 后，若再次跌破，clear_reverse() 清除旧的"向上突破"记录
```

**依赖**：无外部依赖（纯内存逻辑）

---

### 4.5 summarizer.py — 收盘总结（数据表格 + LLM 叙事）

**职责**：收盘后生成结构化收盘总结 dict，表格纯数据驱动，LLM 只做市场特征 + 后市展望两段叙事。共 2 次 LLM 调用（旧设计 8 次已废弃）。

**对外接口**：
| 函数 | 说明 |
|------|------|
| `generate_close_summary(config)` | **主入口**，返回 `{market_table, market_characteristics, stock_table, outlook}` |
| `build_market_table()` / `build_stock_table(config)` | 大盘概况表 + 自选股表（纯数据，无 LLM） |
| `generate_market_characteristics` / `generate_outlook` | 市场特征 + 后市展望（共 2 次 LLM，旧 8 次已废弃） |

**Prompt 设计**：
- 市场特征：`MARKET_CHAR_SYSTEM_PROMPT`（资深A股分析师，5-8要点）从指数分化判断情绪/资金/结构/技术面
- 后市展望：`OUTLOOK_SYSTEM_PROMPT`（3-4 句明日展望，客观中性不做确定性预测）

**容错**：
- LLM 全部不可用：市场特征回退 `_fallback_market_characteristics`（纯数据拼接），展望返回"需 LLM 支持"提示
- 单只股票数据不足时标注"数据不足"

**依赖**：`data_fetcher`（快照 JSON），`llm_client`（call_with_fallback）

---

### 4.6 mail_sender.py — 邮件发送

**职责**：通过 QQ SMTP 发送 HTML 格式邮件。盘中发均线信号表，盘后发四板块收盘总结。

**对外接口**：
| 函数 | 说明 |
|------|------|
| `send_email(config, subject, html_body)` | 发 HTML 邮件（config 为 EmailConfig，main.py 传 config.email） |
| `build_signals_html(signals)` | 均线信号 → 表格 HTML（红涨绿跌） |
| `build_summary_html(summary)` | 收盘总结 dict → 四板块富文本 HTML |

**依赖**：`smtplib`（标准库），`config.EmailConfig`

---

### 4.7 main.py — 调度器

**职责**：24/7 守护进程，协调所有模块按时间线执行。

**核心循环**：
```
while True:
    if 非交易日 → sleep(1小时) → continue
    if 非交易时间 → sleep(1分钟) → continue
    run_monitor_loop()  # 盘中轮询 + 收盘摘要，返回时已是收盘后
```

**`run_monitor_loop()` 内部**：
```
if 当前时间 > 15:30 → 直接发摘要，return
while 在交易时段:
    取实时行情 → 取均线 → 检测信号 → 有信号则发邮件
    sleep(10分钟)
收盘后发摘要
```

**依赖**：所有其他模块

## 5. 配置层

### 5.1 sock.yml（用户可编辑）

```yaml
stocks: [600584, 002384, 688008, 688147, 300502, 688012, 688072]
moving_averages: [5, 10, 20]           # 监控哪些均线
monitor:
  check_interval_seconds: 600           # 盘中轮询间隔
  trading_start: "09:00"
  trading_end: "15:30"
email:
  enabled: true
  to_emails: [sjs1919@qq.com]          # 收件人
```

### 5.2 .env（敏感信息，不入 Git）

```
VOLC_API_KEY=...        # 主 LLM provider（火山豆包）
DEEPSEEK_API_KEY=...    # 备用 LLM provider
SMTP_HOST=smtp.qq.com   # QQ 邮箱 SMTP
SMTP_PORT=587
SMTP_USERNAME=sjs1919@qq.com
SMTP_PASSWORD=...
```

## 6. 部署架构

```
token_hub_47 (47.106.114.104)
├── /opt/token-hub/          # 已有 Go 后端
└── /opt/stock-monitor/      # 本系统
    ├── Dockerfile
    ├── docker-compose.yml
    ├── .env                  # 敏感配置（不入 Git）
    ├── sock.yml              # 自选股配置
    ├── requirements.txt
    ├── scripts/
    │   └── stock_monitor/
    │       ├── config.py
    │       ├── llm_client.py
    │       ├── data_fetcher.py
    │       ├── ma_monitor.py
    │       ├── summarizer.py
    │       ├── mail_sender.py
    │       └── main.py
    ├── logs/                 # 日志持久化（挂载卷）
    └── data/                 # 指数环比 JSON 持久化（挂载卷 ./data:/app/data，见 §7）
```

Docker 容器名：`stock-monitor`，与 `token-hub` 容器共享 Docker 网络。

## 7. 限制与假设

| 限制 | 说明 |
|------|------|
| 数据源 | 腾讯财经 qt/sqt/ifzq 端点；东方财富 akshare `_em` 函数已弃用（服务器 IP 被封） |
| 反爬风险 | 持久 Session + UA + Retry + `_rate_limit` 0.15-0.4s；10 分钟轮询在安全范围 |
| 交易日判断 | 仅按周一至周五判断，不排除中国节假日（需手动维护） |
| 均线精度 | 基于前复权日线收盘价，盘中均线值可能因当日未收盘而有偏差 |
| 指数成交额环比 | K线 API 无成交额字段，靠 `data/index_stats_yesterday.json` 自存；docker-compose 已挂载 `./data:/app/data` 持久化，容器重启不再丢环比（首次部署或换卷当日环比为空，次日自愈） |
| LLM 可用性 | 依赖 .env 中 provider 至少一个可用；全部不可用时市场特征回退数据拼接、展望提示不可用 |
| 单容器单实例 | 不支持水平扩展（信号去重是内存级别） |
