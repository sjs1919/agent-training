# 第一周串讲 - 从 API 调用到可控 Agent

> **定位**：week1 三天的整体串讲，把 Day1→Day2→Day3 串成一条主线，并记录巩固阶段（2026-07-08）踩到的两个环境坑及修复原理。
> **一句话主线**：Day1 跑通调用 + 主备 fallback → Day2 加工具成 Agent → Day3 加 Prompt 工程让 Agent 可控。**三天在同一份代码上叠加，不是三个孤立 demo**。

---

## 一、知识主线：三天演进

| Day | 主题 | 在前一日叠加了什么 | 核心代码 | 认知跃迁 |
|-----|------|------------------|---------|---------|
| **1** | API 入门 + 主备 fallback | —（自包含底座） | `call_llm` + `call_with_fallback` | OpenAI 兼容协议一套通吃国产模型（豆包/DeepSeek/Kimi） |
| **2** | Function Calling / Tool Use | `call_with_fallback` 加 `tools` 参数 + Agent 循环 | `TOOLS` + `query_orders` + `run_agent` | Tool Use 是 Agent 的"手"——没有工具只能聊天不能干活 |
| **3** | System Prompt 工程化 | `messages` 初始化换三层 Prompt，循环体沿用 Day2 | `build_system_level_prompt` + `SCENARIO_PROMPT` + `build_user_message` | Prompt 是工程产物（有结构、有版本、可维护），不是"随便写句话" |

**演进的关键**：每一日都不重写前一日的底座，只往上叠。
- Day2 的 `call_with_fallback` 是 Day1 的增强版（签名从 `(system, user)` 变 `(messages, tools)`），主备链路一字未改。
- Day3 直接 `from day2_function_calling import PROVIDERS, TOOLS, call_with_fallback, execute_tool, query_orders`，只新写 Prompt 构造，Agent 循环体复制自 Day2。

```
代码复用关系：
day1  [PROVIDERS + call_llm + call_with_fallback]  ← 自包含
        │
day2  [PROVIDERS(同) + TOOLS + query_orders + run_agent]  ← call_llm 签名升级支持 tools
        │
day3  [import day2 全部能力] + [三层 Prompt 构造 + structured output]  ← 只动 messages 初始化
```

---

## 二、核心底座：`call_with_fallback`

三天的公共底座是主备 fallback。理解它，就理解了 week1 的工程骨架：

```python
def call_with_fallback(messages, tools=None, ...):
    for p in PROVIDERS:                # 按注册表顺序逐个试
        if not p.get("enabled"): continue       # Kimi 禁用 -> 跳过
        if not _is_real_key(p["api_key"]): continue
        try:
            return call_llm(p, messages, tools)  # 第一个成功即返回
        except Exception as e:
            log.append(f"❌ {p['name']} 失败")
    raise RuntimeError("所有 provider 均失败")
```

**价值**：
- 主调限流/故障时业务不中断（Day1 演示 2：改坏主 key → 自动切 DeepSeek）。
- 切换成本几乎为零——同协议，加 provider 只在 `PROVIDERS` 列表追加一项。
- Day2/Day3 的所有调用都走这个函数，所以"主备能力"自动继承。

> ⚠️ 技术债（培训阶段可接受）：Day1 和 Day2 各自重复定义了一份 `PROVIDERS`。Day3 通过 import 复用了 Day2 的。生产环境应抽到公共 `common.py`。

---

## 三、巩固踩坑：两个环境问题及修复（2026-07-08）

跑通验证时，三个脚本全部**第一个 print 就崩**。排查发现两个独立的 Windows 环境坑，都已修复并写入脚本（开箱即跑）。

### 坑 1：Windows GBK 编码崩溃

**现象**：
```
UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f680' (🚀)
```
脚本第一个 `print("🚀 ...")` 直接抛异常，Day1/2/3 全中（都有 emoji + 中文）。

**根因**：Windows 上 Python 默认 `stdout` 编码跟随系统 locale（中文 Windows = GBK），GBK 编码不了 emoji（🚀 是 4 字节字符）。不是代码写错，是运行环境编码问题。

**修复**（已写入三个脚本）：
```python
import sys
sys.stdout.reconfigure(encoding="utf-8")   # Python 3.7+ 支持
sys.stderr.reconfigure(encoding="utf-8")
```

**原理**：`reconfigure` 在运行时把 stdout 的编码切到 UTF-8，emoji/中文都能正确输出。替代方案是跑的时候带 `PYTHONUTF8=1` 环境变量（Python 3.7+ UTF-8 模式），但那样不开箱即跑。Day3 guide 原本写的 `PYTHONUTF8=1 python day3.py` 现已不需要——脚本内置了。

### 坑 2：httpx 走系统死代理 → SSL EOF

**现象**：编码修好后，主 provider 报 `openai.APIConnectionError: Connection error.`，但 `curl` 直连豆包端点 0.2s 返回 401（网络明明通）。

**诊断关键**：day1 的 `except` 把堆栈吞了只打印一句。写最小复现拿完整 traceback，栈里暴露了真因：
```
File ".../httpcore/_sync/http_proxy.py", line 316, in handle_request
    stream = stream.start_tls(**kwargs)
httpcore.ConnectError: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation
```

栈里有 `http_proxy.py` —— **httpx 走了 HTTP 代理**，在代理隧道上建 TLS 时代理返回异常 EOF。

**根因**：cc-switch（本机 provider 管理工具）退出后，Windows **系统级代理设置（注册表）** 残留、指向已死的本地端口。`openai` 底层的 httpx 默认 `trust_env=True`，会读系统代理，于是走到死代理 → TLS 握手 EOF。而 `curl` 不读系统代理，所以直连正常——这就是"curl 通、openai 不通"的原因。

**诊断陷阱**（记录以防再踩）：
- `env | grep proxy` → **空**（代理不在环境变量里）
- `urllib.request.getproxies()` → **`{}`**（urllib 没合并注册表代理）
- 但 httpx 仍走代理——它读代理的路径和 urllib 不完全一致

**修复**（已写入 day1/2 的 `call_llm`，day3 import day2 自动继承）：
```python
import httpx
client = OpenAI(
    api_key=provider["api_key"],
    base_url=provider["base_url"],
    http_client=httpx.Client(trust_env=False),   # 绕过系统/注册表代理直连
)
```

**原理**：`trust_env=False` 让 httpx 忽略所有环境变量和系统代理设置，强制直连。对培训脚本是正确的——脚本应自包含，不受系统代理污染。

### 诊断方法论（可复用）

1. **curl 通 + openai 不通** → 问题在 client 层，不在网络/端点。
2. **别吞异常** → 排查时先拿完整 traceback（`traceback.print_exc()`），栈里的模块名（`http_proxy.py`）直接指明走代理。
3. **Windows 上 Python 网络库读代理**有三套：环境变量、`urllib.getproxies()`、系统注册表——三者可能不一致，httpx `trust_env` 默认会读到最全的那套。

---

## 四、验证结果（2026-07-08 巩固）

三个脚本修复后全部跑通，主 provider 火山豆包（`ark-code-latest`），备用 DeepSeek（`deepseek-v4-flash`，验证可调通）。

| Day | 验证点 | 结果 |
|-----|--------|------|
| **1** | 主豆包调用 + fallback 切 DeepSeek | ✅ 主成功；改坏主 key → 401 → 自动切 DeepSeek 成功 |
| **2** | Function Calling Agent 闭环 + 复现年份 bug | ✅ 3 场景闭环；演示 3 填 `2025-07-05` → 0 条（bug 复现） |
| **3** | 三层 Prompt 修年份 bug + JSON Schema | ✅ 演示 3 填 `2026-07-05` → **11 条**（bug 修复）；JSON 解析成功 |

**年份 bug 修复对比**（Day2 → Day3，同一句"7月5号之前要交付的"）：

| | Day2（无日期注入） | Day3（系统级注入今天日期） |
|---|---|---|
| 模型填的 due_before | `2025-07-05` | `2026-07-05` |
| 返回结果 | 0 条 | 11 条 |

根因：模型没有内置"今天"的概念，默认用训练数据里的旧年份。系统级 Prompt 注入 `今天是 {date.today().isoformat()}` 后，模型按当前年份推断。

---

## 五、遗留观察（非阻塞，记录备查）

两个 `ark-code-latest` 的偶发输出异常，**非代码 bug**（同一脚本多次跑，演示 2/3 都正常）：
- Day2 演示 1 最终回答只有一个"以"字。
- Day1 演示 2 切到 DeepSeek 时返回内容为空（调用成功 exit 0，但 content 空）。

**应对**：生产环境加输出校验 + 空结果重试；培训阶段记录即可。`ark-code-latest` 是 Auto 模式（后端自动选模型），偶发行为可能来自后端模型切换。

---

## 六、面试速记卡（week1 整体）

```
Q: week1 三天的演进关系？
A: Day1 建 API 调用 + 主备 fallback 底座 → Day2 在底座上加 tools 参数和
   Agent 循环（Tool Use）→ Day3 只改 messages 初始化换三层 Prompt。
   三天在同一份 call_with_fallback 上叠加，不重写底座。

Q: 主备 fallback 怎么实现的？
A: PROVIDERS 注册表（name/key/base_url/model/enabled）+ call_with_fallback
   按序逐个试，第一个成功即返回。加 provider 只改注册表一处。同协议
   （OpenAI 兼容）是切换成本为零的前提。

Q: Function Calling 的 Agent 循环？
A: 发 system+user+tools → 模型返回 tool_calls → 代码执行工具 → 结果追加
   到 messages（role=tool）→ 再调模型 → 直到模型返回纯文本（完成）或
   超过 max_turns。核心：工具结果要按 tool_call_id 回传。

Q: 三层 Prompt 架构？
A: 系统级（身份+能力边界+上下文+安全，固定）→ 场景级（任务规则+输出格式
   +Few-shot，可配置）→ 用户级（用户输入，XML 标签隔离防 Injection）。

Q: 怎么修"模型用错年份"？
A: 系统级 Prompt 注入 date.today()，并明确"交期年份默认当前年份"。
   模型没有内置"今天"，必须显式告诉它。

Q: Windows 上 Python 调 LLM API 的两个坑？
A: ① stdout 默认 GBK 编码不了 emoji → sys.stdout.reconfigure(utf-8)。
   ② httpx trust_env=True 读系统死代理 → SSL EOF → 传
   http_client=httpx.Client(trust_env=False) 直连。
```

---

## 七、下一步

- **Day4**（本周收尾）：原理速览——Token / Context Window / Temperature 的底层含义，打磨 week1 Demo。
- **week2**（7/7-11，已欠 2 天）：RAG + Agent 概念。week1 的主备 + Function Calling + Prompt 工程是 week2 的前置。

> week1 的产出已成型：一个主备容灾、能调工具、Prompt 可控的生产调度 Agent。
> week2 在此基础上加 RAG（让 Agent 读外部知识）和 Agent 概念体系，为 week3（MCP + LangGraph 写真 Agent）铺路。
