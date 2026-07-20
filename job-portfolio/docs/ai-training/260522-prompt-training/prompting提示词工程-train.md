# Prompt 提示词工程 — 研发专题培训

```
> 时长：45 分钟 | 人数：5-10 人 | 侧重：研发日常场景
>
> ## 第 1 期：Prompt 精修与模板化 — 写好一条 prompt，建立可复用模板
> 教你"怎么让单个工具替你干活"
>
> 📌 **第 2 期预告**：项目级 AI 协作工程 — 多轮协作、大型代码库、AI 辅助测试
> 教你"怎么让一组工具+方法论替你干一整个工作流"
> 
> 参考资料：[提示词技巧](reference-prompting.md) | [需求拆解](reference-task-decomposition.md) | [上下文管理](reference-context-management.md)

```

## 时间分配总览

| 环节 | 时长 | 形式 |
|------|------|------|
| 1. 开场：两期培训规划与目标 | 5 min | 讲解 |
| 2. 核心原则：5 条铁律（具体/约束/分步/示例/参考） | 10 min | 讲解 + 对比演示 |
| 3. 四种标准化 Prompt 模式 | 8 min | 讲解 |
| 4. Prompt 模板参数化 | 10 min | 讲解 + 实操 |
| 5. 项目配置文件入门（CLAUDE.md / .cursorrules） | 4 min | 讲解 |
| 6. Q&A + 引子 | 8 min | 互动 |

---

## 1. 开场：两期培训规划与目标（5 min）

### 1.1 一个对比（1.5 min）

> **放一段"随手写的 prompt" vs "经过设计的 prompt"的输出对比**

**随手写：**
```
帮我优化这个函数
```

**经过设计：**
```
这个函数处理 10 万条数据时需要 30 秒，目标是降到 5 秒以内。
可以考虑批处理、缓存、或者换算法。
不要改函数签名。
```

> 引出核心观点：**Prompt 是新一代的"编程语言"，输入质量决定输出质量。AI 不会读心术，你说得越具体，结果越好。**

### 1.2 研发的独特优势（2 min）

- 结构化思维 → 天然适合写 prompt
- 能读懂代码 → 能验证 AI 输出
- 有调试经验 → 会迭代 prompt
- **一句话：研发是最容易用好 AI 的群体**

### 1.3 今天的目标（1 min）

- 掌握可复用的 prompt 写法，不靠"灵机一动"
- 结束就能在项目里用起来

---

## 2. 核心原则：5 条铁律（10 min）

> 专门针对 AI 编程场景的提示词技巧。不管你用 Claude Code、Cursor 还是 Copilot，以下原则都适用。

### 铁律 1：具体 > 模糊（2 min）

> AI 不会读心术。你说得越具体，结果越好。尽量压缩 AI 自由发挥的空间，让概率性转为确定性。

**对比演示：**

```
❌ "帮我优化这个函数"

✅ "这个函数处理 10 万条数据时需要 30 秒，
    目标是降到 5 秒以内。
    可以考虑批处理、缓存、或者换算法。
    不要改函数签名。"
```

**要点**：告诉 AI **什么数据、什么指标、什么目标**，而不是一个模糊的动词或者一句随心所欲的话，没有具体事实、约束和遵照的步骤。

**更多正反例：**

| # | ❌ 反例 | ✅ 正例 |
|---|---------|---------|
| 1 | `帮我写个登录` | `用 Gin + JWT 实现登录接口，入参 username+password，返回 access_token(2h) 和 refresh_token(7d)，错误时返回 {code, message}` |
| 2 | `这个接口有 bug` | `POST /api/order/create 返回 500，日志报 duplicate entry 'ORD-001'，怀疑是并发重复提交，看下怎么加幂等处理` |
| 3 | `给这个表加几个字段` | `给 users 表加 last_login_at(datetime) 和 login_count(int, default 0)，更新对应的 User model 和 migration` |

**lexyAdmin 真实案例：**
```
- ❌ `帮我给系统加个权限管理功能`
- ✅ `在 lexyAdmin 的 src/store/modules/permission.ts 里加一个菜单权限缓存，参照现有的 user.ts 里 SET_ROLES 的写法，用 Pinia action 实现，缓存 key 用 'menu-perms'，TTL 和登录态保持一致`
```

### 铁律 2：约束 > 自由（2 min）

> 没有约束的 AI 会发挥过度。有明确的边界和约束，AI能发挥效率。明确告诉它**什么不要做**，比告诉它做什么同样重要。

**对比演示：**

```
❌ "加个缓存"

✅ "给 getUserById 加缓存。
    用内存缓存（Map），不要引入 Redis。
    TTL 5 分钟。
    不要改其他函数。
    不要加新依赖。"
```

**常见约束清单**：
- `不要引入新的第三方依赖`
- `不要修改已有的 public 方法签名`
- `仅修改 xxx 文件，不要动其他文件`
- `不要过度抽象，保持代码平铺直叙`

**更多正反例：**

| # | ❌ 反例 | ✅ 正例 |
|---|---------|---------|
| 1 | `加个错误处理` | `给 OrderService 的所有 public 方法加 try-catch，catch 里打 log.Error 然后 return 统一错误码，不要吞掉原始 error` |
| 2 | `把这个接口改成异步的` | `把 POST /api/export 改成异步：接收请求后立刻返回 task_id，后台用 goroutine 处理，完成後写结果表。不要改其他接口。` |
| 3 | `做一下防重复提交` | `给下单接口加 Redis 分布式锁，key=order:lock:{user_id}，过期时间 5 秒，获取锁失败返回"操作太频繁"。不要用数据库锁。` |

**lexyAdmin 真实案例：**
```
- ❌ `给我加一个 API 接口`
- ✅ `在 src/api/user.ts 里加一个 updateProfile 接口，参照 getMine 的风格：用 http.request<UserInfoResult>('put', '/mine', { data })，返回类型复用现有的 UserInfoResult，不要新建类型文件`
```

### 铁律 3：分步 > 一次（2 min）

> 复杂任务拆成步骤，每步确认再继续。AI 一次做好一个小任务的成功率远高于一次做一个大任务。

**对比演示：**

```
❌ "重构整个认证模块"

✅ "重构认证模块，分三步走：
    第一步：先分析现在的问题，列出来让我确认。
    第二步：给出重构方案（2-3 个选项）。
    第三步：确认方案后再开始改代码。
    现在先做第一步。"
```

**核心理念**：
1. 每一步都是原子操作，每步有明确完成标准——能跑通、能测试、能验证。
2. 每一步都尽可能的描述清楚，如果能够添加验收条件最好；

**lexyAdmin 真实案例：**
```
- ❌ `在 lexyAdmin 里给我加一个设备监控页面`
- ✅ `在 lexyAdmin 里加设备监控页面，分四步：
    第一步：在 src/router/modules/ 下新建 monitor.ts，参照 system.ts 的路由结构，列出菜单配置让我确认。
    第二步：在 src/views/monitor/ 下创建设备状态页，用 RePureTableBar + vxe-table，先写死 mock 数据。
    第三步：在 src/api/ 下加监控相关接口，参照 api/user.ts 的 http.request 写法。
    第四步：联调接口 + 加按钮权限（用 RePerms 组件）。
    现在先做第一步，做完了跟我确认，我确认无误后再执行下一步。`
```

### 铁律 4：示例 > 描述（2 min）

> 给一个例子比描述半天清楚得多。1-3 个示例能显著提升输出质量（Few-shot）。

**对比演示：**

```
❌ "返回值用统一格式"

✅ "返回值统一用这个格式：
    {
      'code': 200,
      'data': { ... },
      'message': 'success'
    }
    错误时：
    {
      'code': 400,
      'data': null,
      'message': '参数 email 格式不正确'
    }"
```

**适用场景**：
1. API 返回格式、代码风格、错误处理模式、日志格式——任何需要"保持一致"的地方。
2. 重复不断的规则，可以提取成为原则，加入AI工具规范里。

**lexyAdmin 真实案例：**
```
- ❌ `写一个新的 Pinia store`
- ✅ `参照 src/store/modules/user.ts 的写法，新建一个 src/store/modules/device.ts：
    用 defineStore，state 返回 deviceList 和 currentDevice，
    actions 里写 fetchDeviceList 和 selectDevice，
    导出一个 useDeviceStoreHook。类型定义放在 types.ts。
    照这个格式写：
    {
      code: 0,
      data: { list: [...], total: 20 },
      message: 'success'
    }`
```

### 铁律 5：参考 > 从零开始（2 min）

> 指向已有代码比描述风格有效得多。让 AI "参照 xxx 写 yyy"。

**对比演示：**

```
❌ "写一个新的 API 接口"

✅ "参考 src/api/users.ts 的风格，
    写一个 src/api/orders.ts。
    路由、错误处理、返回格式都保持一致。"
```

**实践建议**：项目里维护一份"标准参考文件"（如规范实现的 Controller、Service、Model 各一个），写新功能时让 AI 参照。

**lexyAdmin 真实案例：**
```
- ❌ `给我写一个用户列表页`
- ✅ `参照 src/views/system/ 下现有页面的结构，写一个用户列表页：
    路由配置参照 src/router/modules/system.ts，
    API 请求参照 src/api/user.ts 的 http.request 写法，
    Store 参照 src/store/modules/user.ts 的 Pinia 写法，
    表格列用 RePureTableBar + vxe-table，
    权限控制用 RePerms 组件。`
```

**lexyBackend 真实案例：**

```
❌ "写个用户登录接口"

✅ "在 web/ 包下新建 UserAuthController：
  - 类上加 @RestController 和 @RequestMapping(\"api/auth\")
  - 注入 final UserAuthService，用 @RequiredArgsConstructor
  - 方法返回 R<LoginVO>，请求参数标注 @Valid
  - 登录成功调用 R.ok(data)，失败抛 BusinessException
  - 参照现有 admin/AdminAuthController 的风格"
```

代码规范与约定（lexyBackend AGENTS.md 精选）：

1. **统一响应格式**：所有 Controller 返回 `R<T>`，成功调用 `R.ok(data)`，失败调用 `R.fail(message)` 或抛出 `BusinessException`。
2. **分层职责**：
   - `Controller` 只负责参数接收与响应组装，不直接操作 Mapper
   - `ServiceImpl` 继承 `ServiceImpl<Mapper, Entity>` 并使用 MyBatis-Plus 提供的 `lambdaQuery()` / `lambdaUpdate()` 进行链式查询更新
   - `Mapper` 仅继承 `BaseMapper<Entity>`，目前项目内未使用 XML Mapper 文件
3. **判空与空值检查**：禁止手写 `obj == null`、`str == null || str.isEmpty()`、`list == null || list.isEmpty()` 等判空逻辑，必须统一使用 Hutool 工具方法：
   - 对象判空：`ObjectUtil.isNull(obj)` / `ObjectUtil.isNotNull(obj)`
   - 字符串判空（含 null、空串、纯空白）：`StrUtil.isBlank(str)` / `StrUtil.isNotBlank(str)`
   - 集合判空：`CollUtil.isEmpty(coll)` / `CollUtil.isNotEmpty(coll)`

---

## 3. 四种标准化 Prompt 模式（8 min）

> 以下四种模式覆盖了研发日常 90% 的场景。掌握模板，比背一万条技巧都管用。

### 模式 1：分析模式（先看后说）

```
先读 [文件/目录]，分析 [什么问题]。
列出你的发现，不要直接改代码。
等我确认后再动手。
```

**适用**：
1. 接手陌生代码、排查性能瓶颈、评估重构范围。
2. 适合做小范围的算法优化或者新控件引入。

**示例**：
```
读 src/services/order.ts，分析是否有并发安全问题。
重点关注库存扣减逻辑。列出你的发现，不要改代码。
```

**lexyBackend 真实案例：**
```
读 lexy-backend 的 OrderServiceImpl.java 中的 createOrder 和 cancelOrder 方法，
分析库存扣减和回滚逻辑是否有并发安全问题。

重点关注：
1. 乐观锁实现是否正确（update ... where stock >= quantity）
2. 幂等性处理（idempotencyHelper）在异常时是否会泄露
3. 事务边界是否合理（@Transactional 覆盖范围）
4. 库存日志记录是否可能在事务回滚后残留

列出你的发现，不要改代码，按严重程度排序。
```

### 模式 2：实现模式（明确需求）

```
在 [位置] 实现 [功能]。
要求：
1. [具体要求 1]
2. [具体要求 2]
参考 [现有文件] 的风格。
不要 [禁止事项]。
```

**适用**：新功能开发、写接口、加中间件。

**示例**：
```
在 src/api/user.ts 里加一个 updateProfile 接口。
参照 getMine 的风格，用 http.request<UserInfoResult>('put', '/mine', { data })。
返回类型复用现有的 UserInfoResult，不要新建类型文件。
```

**lexyBackend 真实案例：**
```
在 lexy-backend 的 admin/ 包下新建 AdminOrderController，
实现后台订单列表查询接口 GET /api/admin/order/list。

要求：
1. 类上加 @RestController 和 @RequestMapping("/api/admin/order")
2. 注入 final AdminOrderService，用 @RequiredArgsConstructor
3. 方法返回 R<PageResult<OrderListVO>>，入参用 OrderListQueryParam 并标注 @Valid
4. 调用 adminOrderService.listOrders(param)，参照 web/OrderController 的风格
5. 使用 StpKit.ADMIN.checkLogin() 校验管理员登录态
6. 不要引入新的依赖，返回类型复用现有的 OrderListVO
```

**lexyAdmin 真实案例：**
```
在 lexy-admin 的 src/views/system/ 下新建 order/ 目录，
实现后台订单管理页面 OrderList.vue。

要求：
1. 参照 src/views/system/user/index.vue 的页面结构
2. 表格展示订单号、客户邮箱、订单状态、总金额、创建时间
3. 顶部搜索栏：按订单号、客户邮箱、订单状态筛选
4. API 请求写在 src/api/order.ts，参照 src/api/user.ts 的 http.request 写法
5. 使用 RePureTableBar + vxe-table 展示表格
6. 状态列用标签展示（PENDING=待处理，PAID=已支付，SHIPPED=已发货等）
7. 不要改 layout 和 router 的全局配置
```

### 模式 3：修复模式（给证据）

```
我遇到了一个 bug：
- 预期行为：[A]
- 实际行为：[B]
- 错误信息：[贴日志/报错]
- 相关代码：[文件路径]
- 已尝试：[排查步骤]

先分析可能的原因（不要猜，看代码和日志）。
确认根因后再给修复方案。
只改必要的代码，不要顺手重构。
```

**适用**：
1. Bug 修复、线上问题排查。
2. 改BUG时，特别要注意约束好边界，显著禁止AI随意发挥。

**lexyBackend 真实案例：**
```
我遇到了一个 bug：
- 预期行为：订单取消后，SKU 的 stock 字段应该回滚，locked_stock 应该扣减
- 实际行为：并发取消多个订单时，部分订单的库存回滚没有生效，导致 locked_stock 数据不一致
- 错误信息：日志报 "Cancel order failed to release stock, skuId: xxx"，但 rows=0 时只打了 warn
- 相关代码：lexy-backend OrderServiceImpl.java 的 cancelOrder 方法第 342-350 行
- 已尝试：单步调试发现 cancelOrder 里先 selectById 查 SKU，再 update 回滚，两步之间有并发窗口

先分析根因（不要猜，看代码逻辑）。
确认根因后给出修复方案，只改必要的代码，不要顺手重构其他逻辑。
```

**lexyAdmin 真实案例：**
```
我遇到了一个 bug：
- 预期行为：登录后应该根据用户偏好语言自动切换界面语言
- 实际行为：登录后界面语言始终是英文，需要手动刷新页面才切换成功
- 错误信息：控制台没有报错，但网络面板看到 getMine 请求返回了 defaultLanguage: "zh"
- 相关代码：lexy-admin src/store/modules/user.ts 的 loginByUsername action
- 已尝试：在 loginByUsername 里加了 await getMine() 获取用户信息，但语言切换逻辑似乎执行了但没有生效

先分析 loginByUsername 中语言切换的执行时序，确认根因后再修复。
不要改动 i18n 插件的整体架构，只修复当前 bug。
```

**对比**：

| 方式 | 效果 |
|------|------|
| ❌ `这段代码报错了，帮我看看` | AI 只能猜，来回追问 3-5 轮 |
| ✅ 按模板结构化描述 | 通常一轮就能定位根因 |

### 模式 4：审查模式（定范围）

```
审查 [文件/PR]，重点关注：
1. [关注点 1，如性能]
2. [关注点 2，如安全]
3. [关注点 3，如边界情况]
按严重程度排序，给出修改建议。
```

**适用**：
1. Code Review、上线前检查、安全审计。
2. 建议通过多轮询问和多个AI模型交叉验证，效果更佳。

**示例**：
```
审查 src/services/order.ts，重点关注：
1. 是否有 SQL 注入风险
2. 循环中是否有 DB 查询（N+1）
3. 金额计算是否用 BigInt 避免精度丢失
按严重程度排序。
```

**lexyBackend 真实案例：**
```
审查 lexy-backend 的 OrderServiceImpl.java 和 OrderController.java，重点关注：
1. 是否有空指针风险（ObjectUtil.isNull 是否覆盖所有分支）
2. 金额计算是否使用 BigDecimal 并设置了正确的舍入模式
3. 事务边界是否合理（@Transactional 是否在 public 方法上，内部调用是否会导致事务失效）
4. 是否出现魔法值（未命名定义的字面量数字/字符串）
5. 判空是否使用了 Hutool 工具类，而不是手写 == null
按严重程度排序，给出修改建议。
```

**lexyAdmin 真实案例：**
```
审查 lexy-admin 的 src/views/system/user/index.vue，重点关注：
1. 是否有内存泄漏（定时器、事件监听是否在组件卸载时清理）
2. 表格大数据量时是否有性能问题（是否做了分页，是否全量加载）
3. 表单校验是否完整（必填项、格式校验、边界值）
4. 权限控制是否正确使用 RePerms 组件
5. API 错误处理是否完善（ loading 状态、错误提示、重试机制）
按严重程度排序，给出修改建议。
```

### 反模式速查（2 min）

| 反模式 | 为什么不好 | 改成 |
|--------|-----------|------|
| "帮我写个网站" | 范围太大 | 拆成具体任务 |
| "优化一下" | 目标不明确 | 说清楚优化指标 |
| "写最好的代码" | "最好"没定义 | 说清楚标准 |
| 一次给 10 个需求 | AI 会顾此失彼 | 一次一个，确认后再下一个 |
| 不给错误信息就说"修 bug" | AI 只能猜 | 贴错误日志、复现步骤 |

---

## 4. Prompt 模板参数化（10 min）

### 4.1 为什么需要模板化（2 min）

**问题**：每次遇到类似任务都要重新写 prompt，效率低、质量不稳定。

**示例**：团队经常需要写 API 接口

```
❌ 每次重新写：
"在 src/api/user.ts 里加一个 updateProfile 接口..."
"在 src/api/order.ts 里加一个 createOrder 接口..."
"在 src/api/product.ts 里加一个 getList 接口..."
```

**解决方案**：抽象为参数化模板

```
✅ 一次写好模板，以后换参数复用：

在 src/api/{module}.ts 里加一个 {action}{Module} 接口，
参照 getMine 的风格：
用 http.request<{ReturnType}>('{method}', '{endpoint}', {config})。

要求：
- 返回类型复用现有的 {ReturnType}，不要新建类型文件
- 入参类型定义放在 types.ts
- 错误处理参照现有风格
```

### 4.2 参数化模板写法（3 min）

**模板结构**：

```
在 [位置] 实现 [功能]。
参照 [参考文件] 的风格。

具体要求：
1. [固定要求 1]
2. [固定要求 2]

约束：
- [固定约束 1]
- [固定约束 2]

可替换参数：
- {module}：模块名
- {action}：操作名
- {endpoint}：API 路径
```

**lexyAdmin 真实案例 — 参数化模板**：

```markdown
# 模板：新增 CRUD 页面

在 src/views/{module}/ 下新建 {Module}List 管理页面。
参考：src/views/system/user/ 的结构

功能要求：
1. 表格展示 {itemList}（{fields}），用 RePureTableBar + vxe-table
2. 顶部搜索栏：按 {searchFields} 筛选
3. 新增/编辑按钮弹 ReDialog，表单字段：{formFields}
4. API 接口写在 src/api/{module}.ts，参照 src/api/user.ts 的 http.request 写法

约束：
- 不要改 layout 和 router 的全局配置
- 按钮权限用 RePerms 组件
- 不要引入新的第三方依赖

请先说明实现思路和文件清单，再写代码。
```

### 4.3 团队模板库建立（2 min）

建议按场景分类存放：

```
shared/docs/ai-prompt-templates/
├── crud-page.md          # 新增 CRUD 页面
├── api-endpoint.md       # 新增 API 接口
├── bug-fix.md            # Bug 修复
├── code-review.md        # 代码审查
├── refactor.md           # 重构
└── test-generation.md    # 生成测试
```

**使用方式**：写新功能时，复制对应模板，替换变量即可。

---

## 5. 项目配置文件入门（4 min）

### 5.1 为什么需要项目配置文件（1 min）

**问题**：每次新对话都要告诉 AI "我们用 Vue 3 + TypeScript"、"不要引入新依赖"，重复且易遗漏。

**解决方案**：把项目约定写入配置文件，每次对话自动加载。

### 5.2 CLAUDE.md 基础结构（2 min）

在项目根目录创建 `CLAUDE.md`：

```markdown
# CLAUDE.md — 项目规范

## 技术栈
Vue 3.4 + TypeScript + Vite + Pinia

## 代码规范
- 命名：组件 PascalCase，函数 camelCase
- 类型：所有 API 入参出参必须定义 interface
- 注释：复杂逻辑用中文注释

## 架构约定
- API 层：src/api/，统一用 http.request<T>
- Store 层：src/store/modules/，用 defineStore
- 视图层：src/views/，按模块分目录

## 禁止事项
- 不要引入新的 UI 库
- 不要修改已有的 public 方法签名
- 不要用 any

## 常用命令
- npm run dev：启动开发服务器
- npm run test:unit：跑单元测试
```

**效果**：每次启动 Claude Code，这些约定自动进入上下文，不需要重复说明。

### 5.3 CLI 与 Trae 的规则联动（1 min）

> 我们团队的工作流：**Claude Code CLI 主力干活，Trae IDE 辅助看代码**。两套工具的规范如何配合？

**定位差异**：

| 维度 | Claude Code (CLI) | Trae (IDE) |
|------|-------------------|------------|
| 使用场景 | 复杂任务、多轮协作、大型重构 | 快速浏览、单文件修改、代码审查 |
| 上下文能力 | 200K tokens，可执行命令、读写文件 | 128K-200K tokens，实时补全 |
| 规范载体 | `CLAUDE.md` | `.trae/rules/*.md`（兼容 Cursor 格式） |
| 规则深度 | 完整规范：架构、分层、禁止事项、命令 | 精简版：代码风格、命名、常见约束 |

**联动策略**：

1. **以 `CLAUDE.md` 为唯一源头** —— 项目规范在此维护，保持权威
2. **`.trae/rules/project-rules.md` 做精简同步** —— 只保留 Trae 高频触发场景需要的规则（如命名规范、禁止魔法值、分层约束）
3. **避免双轨漂移** —— 规范变更时，先改 `CLAUDE.md`，再同步 `.trae/rules/`，不要各自独立维护

**实践建议**：

在 `.trae/rules/project-rules.md` 中维护精简版：

```markdown
# Trae 项目规则精简版
- 命名：类大驼峰，方法/变量小驼峰，常量全大写下划线
- 判空：禁止手写 == null，统一用 Hutool ObjectUtil/StrUtil/CollUtil
- 分层：Controller 只接参响应，不直接调 Mapper
- 响应：Controller 返回 R<T>，禁止返回裸对象
- 魔法值：禁止出现任何未经命名定义的字面量
```

---

## 6. Q&A + 第二期引子（8 min）

### 常见问题

**Q1：AI 生成的代码直接能用吗？**

> 不能。始终 Review、跑测试、理解逻辑后再合入。AI 是副驾驶，不是自动驾驶。

**Q2：公司代码能贴给外部 AI 吗？**

> 【待确认公司信息安全策略】建议敏感业务逻辑脱敏后再问，或用本地部署的模型。另外——代码已经在文件里了，不要让组员往对话框贴大段代码，教他们用"读 xxx 文件"的方式。

**Q3：同一个 prompt 不同模型效果差异大吗？**

> 有差异。Claude 偏严谨、GPT 偏流畅、DeepSeek 偏效率。建议团队固定一个模型做对比评估。

**Q4：怎么衡量 prompt 写得好不好？**

> 三个标准：① 一次成功率（不需要反复追问）② 输出可用率（修改量少）③ 可复用性（同类任务换个参数也能用）

**Q5：AI 用着用着变笨了怎么办？**

> 对话太长，上下文溢出了。解决方法：
> - Claude Code：`/clear` 开新对话
> - 或者手动总结：`我们刚才做了这些事：[3 句话总结]。现在继续做 [下一个任务]。`
> - 重要约定写在 `CLAUDE.md` / `.trae/rules/project-rules.md` 里，每次对话自动带上，不会丢失。

**Q6：AI 编造不存在的 API 怎么办？**

> 没给足参考信息。让它先 `grep/search` 确认有没有这个方法，再写代码。不要假设它能"记住"你的项目。

### 一句话总结

> **Prompt 工程的本质：把你脑子里想的，结构化成 AI 听得懂的。**
>
> **五个字记住：具体、约束、分步、示例、参考。**

### 第二期引子

第 1 期解决的是"怎么写好一条 prompt"。第 2 期将解决"怎么带 AI 做一个完整项目"：

- **多轮对话管理**：对话长了 AI 变笨怎么办？如何断点续传？
- **大型代码库**：几百个文件的项目，怎么让 AI 不迷路？
- **AI 辅助 TDD**：让 AI 帮你写测试，覆盖边界情况
- **Claude Code 深度工作流**：`settings.json`、hooks、MCP 接入

**一句话预告**：Prompt 工程是写得好，协作工程是做得成。


## 附录 A：讲师备忘 — 进阶内容速查

> 以下内容不在 45 分钟正课内，但如果学员追问或后续安排进阶培训时使用。

### 需求拆解速成（Task Decomposition）

**拆解三原则：**
1. **原子操作** — 每个任务 AI 能一次做对。`"重构整个用户模块"` → 拆成 4 个小任务。
2. **明确完成标准** — `"优化性能"` → `"getUserList 接口响应时间从 3s 降到 500ms 以内，跑 ab -n 1000 -c 10 验证"`。
3. **清晰依赖关系** — 画任务 DAG，无依赖的并行做。

**标准拆解模板（新功能开发）：**

```
第一轮：设计 — 分析需求，给出 2-3 个技术方案，确认方案
第二轮：数据层 — 创建模型/表，写数据访问层，验证 CRUD
第三轮：业务层 — 实现核心逻辑，写单元测试，验证通过
第四轮：接口层 — 实现 API，加校验和权限，写接口测试
第五轮：收尾 — 错误处理、日志、文档、回归测试
```

**重构拆解：**

```
第一步：写测试覆盖现有行为（安全网）
第二步：小步重构（每次只改一个点）
第三步：每次改完跑测试
第四步：重复第二步和第三步
第五步：清理（删除过渡代码、更新文档）
```

### 上下文管理速成（Context Management）

**核心认知**：上下文不是越大越好。塞太多无关信息，AI 反而注意力分散。

| 工具 | 上下文窗口 | 配置文件 |
|------|-----------|---------|
| Claude Code | 200K tokens | `CLAUDE.md` |

**四条核心策略：**

1. **精确喂入，不要全塞** — `"看整个 src/ 找 bug"` → `"看 src/services/auth.ts 的 refreshToken 函数"`
2. **写好项目配置文件** — `CLAUDE.md` / `.trae/rules/project-rules.md` 自动加载，每次对话自动带上关键上下文
3. **长对话定期刷新** — 感觉 AI 变笨时 `/clear` 开新对话，或手动总结当前进度
4. **用文件传递上下文，不用对话框** — 代码在文件里就让 AI 读文件，不要贴 500 行到对话框

**常见上下文问题：**

| 问题 | 原因 | 解决 |
|------|------|------|
| AI 回答不准确 | 上下文不够或太杂 | 精确引用相关文件 |
| AI 越来越笨 | 对话太长，上下文溢出 | 开新对话，带上配置文件 |
| AI 忘了之前的约定 | 早期消息权重降低 | 重要约定放在 `CLAUDE.md` 里 |
| AI 编造不存在的 API | 没给足参考信息 | 让它先 grep/search 确认 |
| AI 重复做已经做过的事 | 不记得之前的进度 | 用 todo/plan 追踪进度 |

---

> **编写说明**：正文为 45 分钟培训课件，附录 B 为讲师进阶参考，按需取用。
