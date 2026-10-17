+++
title = "DeepSeek Harness 源码解析（七）：五种事件派发怎样执行监听器"
date = 2026-10-15
lastmod = 2026-10-17
draft = false
author = "Hex4C59"
description = "沿 Cordis EventsService 追踪 emit、parallel、serial、bail 与 waterfall 的监听器选择、执行顺序、返回值、异常及清理，结合固定源码聚焦实验解释 fs 与 Agent 事件的实际用法。"
summary = "serial 会因 0 或空字符串停止，bail 会把 Promise 本身当作结果，waterfall 则由 next 决定是否继续。本文将五种派发逐项对照，并追踪过滤、监听器快照、once 与卸载边界。"
tags = ["DeepSeek Harness", "Cordis", "事件调度"]
categories = ["ai"]
source_kind = "original"
series = ["DeepSeek Harness"]
series_order = 7
difficulty = "intermediate"
article_type = "concept"
topics = ["coding-agent", "plugin-architecture", "event-dispatch"]
frameworks = ["DeepSeek Harness", "Cordis"]
ShowToc = true
+++

[第六篇](/articles/deepseek-harness-types-service-registration/)讲到，接口包通过模块增强，让 TypeScript 认识插件新增的服务和事件。类型声明能让编辑器识别文件系统包中的 `fs/observed`、`fs/write-intent`，但执行这些事件时，还要决定怎样调用监听器：一次读取完成后用 `emit` 记录观察结果，写入前却用 `waterfall` 等待策略插件给出决策。

为什么不用一个统一的 `emitAsync`？给 `serial` 注册多个监听器，为什么第二个返回 `0` 就让第三个不再执行？给 `bail` 注册 async 函数后，即使它最终返回 `false`，后续监听器为什么仍没有机会运行？

**Cordis 的五种派发决定了谁会执行、调用方等什么，以及一个返回值怎样影响后续工作。** 其中 `serial` 和 `bail` 都有提前停止规则；`waterfall` 则把控制权交给 `next()`。这些规则会影响初始化、文件策略和失败处理，不能只按名字理解成“同步广播”和“异步广播”。

本文面向会读函数调用和 Promise、但没读过该项目源码的开发者。Context 是插件访问服务和登记资源的入口，前几篇介绍过它的依赖机制。本文先追踪监听器如何进入一次派发，再分别看执行与失败路径，最后回到文件工具、Agent 和事件作用域。以下讨论普通字符串业务事件；内部更新 Hook 和完整 Fiber 清理算法留给后续章节。

本文分析 [DeepSeek Harness `0.2.1-alpha.2`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/package.json)，源码取自[固定快照](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c)；核对日期为 2026-10-15。[Cordis manifest](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/package.json)为 `4.0.5-alpha.1`。本文另用 TypeScript 6.0.3 转译固定快照的 Cordis/cosmokit 源文件，在 Node `v25.9.0` 上完成 18 组聚焦检查。

这些检查执行了原有事件服务和 Context，实现方法没有被替换为自写模拟器；转译不做完整语义类型检查。它们不等于 dsh 全量构建、所有插件组合、进程故障或模型请求已经验证。下载包和复现范围见文末。

## 从 `on()` 到这次派发的监听器列表

### 注册记录既包含函数，也包含拥有它的 Context

插件登记监听器时，框架还要记下它属于哪次插件挂载，才能在卸载时撤销这条登记。Cordis 用 Fiber 保存一次插件挂载的运行状态，用 effect 登记初始化及对应的清理函数。这里先关注它们怎样移除监听器，完整清理过程放在下一篇。

[`EventsService.on()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/events.ts#L288)先规范化选项、检查当前 Fiber，并通过 `ctx.reflect.bind()` 包装回调，再触发框架内部的 `internal/listener` 拦截点。普通事件进入事件名对应的 Hook 数组。

Hook 是一条注册记录，保存注册方 `ctx`、回调，以及 `prepend`、`global` 等选项。事件服务之后会根据注册方 Context 判断这条记录能否接收事件，并据此找到负责清理它的插件。

[`register()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/events.ts#L254)通过当前 Fiber 的 effect 加入记录，并登记对应的移除动作。默认从数组尾部加入，`prepend: true` 则从头部加入；布尔参数 `true` 是 prepend 的简写。连续 prepend 时，后注册者排在前面；没有另一个按数字排序的通用优先级字段。

普通注册完成后返回 disposer，也就是用于撤销的函数。插件卸载时框架会清理相应 effect，从以后派发所选的列表中移除监听器。不过，已经开始执行的异步工作和当前派发已经取得的回调，不会仅因移除记录就自动消失。

### 一次 dispatch 会先解析接收者，再筛选 Hook

五种派发共用 [`dispatch()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/events.ts#L166)。它支持两种形状。下面只是调用形状示意，事件名和参数须对应实际声明：

```ts
ctx.emit('some/event', payload)
ctx.emit(receiver, 'some/event', payload)
```

第二种形式最前面的对象或函数是派发接收者，在普通函数监听器中作为 `this`。接收者还可能携带 `[Context.filter]`：事件服务会用这个函数检查各监听器的注册方 Context，决定选中谁。接收者不是监听器收到的第一个普通参数；payload 仍从事件名后开始传递。

非 `internal/` 事件会先产生一条 `internal/dispatch` 诊断事件，然后读取接收者上的过滤器。监听器满足以下任一条件才会入选：标记了 `global`、本次没有过滤器、或过滤器接受它的注册方 Context。入选回调再绑定到这次接收者；监听器内部的 `reflect.bind()` 还会追踪相应的 this 与参数。

所以，先问“这次选中了哪些 Hook”，再问“选中的回调怎样执行”。五种调度方式不会补回已经被过滤掉的监听器。

### 执行顺序来自本次列表，而非监听器完成的先后

过滤与 `map()` 会生成本次派发的回调列表。之后才由 `emit` 等方法迭代它。因此，监听器 A 执行时撤销 B，B 若已被当前列表捕获，这次仍可能执行；A 新注册的 C 通常从下一次派发开始出现。

本次实验先注册 A、B，再 prepend P：第一轮中 A 撤销 B 并添加 C，实际得到 `P → A → B`；第二轮才是 `P → A → C`。这里的快照保存回调名单，不是深拷贝 payload。多个监听器仍可能看到同一个可变对象。

## 先对照五种派发的等待与停止规则

下表描述普通监听器的主要行为。其中“bail 值”指会使 serial 或 bail 提前停止、直接作为结果返回的值，具体条件列在“怎样继续”一栏。公共派发前的诊断与过滤也能抛错，不能把表格扩展成任意框架错误都已被转换或聚合。

| 方法 | 怎样继续 | 调用方得到什么 | 普通监听器失败时 |
|---|---|---|---|
| `emit` | 依次调用，不等返回的 Promise | `undefined` | 同步抛错立即退出，后续不调用；异步拒绝不由本方法收集 |
| `parallel` | 按列表启动，等待每项都确定成功或失败 | 成功时为 `undefined` 的 Promise | 回调抛错或拒绝纳入结果，全部结束后抛 AggregateError |
| `serial` | 逐个 await，遇到既非 null、false，也非 undefined 的结果便停止 | 解析为首个 bail 值的 Promise，否则解析为 undefined | 首个抛错或拒绝使派发拒绝，后续不调用 |
| `bail` | 同步逐个调用，使用与 serial 相同的停止条件 | 首个 bail 值，否则 undefined | 同步抛错向外传播；不等 Promise 的最终结果 |
| `waterfall` | 当前监听器自己决定是否调用 next | 最外层监听器或终点的返回值 | 按实际调用链传播同步异常或返回的 Promise 拒绝 |

没有监听器时，emit 和 bail 返回 undefined，parallel 和 serial 返回解析为 undefined 的 Promise；waterfall 则直接调用生产方提供的终点函数。空名单不会替它生成一份业务结果。

图中可以切换派发方法与“正常结果／同步异常”两组输入，比较哪些监听器被调用、谁被跳过，以及调用方何时取得结果。顺序表示实验控制的先后关系，不是耗时测量；waterfall 使用带 next 的独立监听器组，不能把它当作其余四种方法的同签名回调。

{{< interactive-diagram src="event-dispatch.html" title="切换五种 Cordis 事件派发及正常和同步异常场景，比较监听器执行、等待、停止与返回顺序" height="1510" compact-height="1740" mobile-height="1900" >}}

## `emit`：不等待 Promise，也不隔离同步异常

[`emit()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/events.ts#L195)的核心只有一次同步调用循环，源码节选为：

```ts
this.dispatch('emit', args).map(cb => cb(...args))
```

它会进入每个回调的同步部分。async 函数在第一次等待前所做的工作，也会在这个调用过程中开始；返回 Promise 后，emit 继续下一个回调，不把这些 Promise 组成一个待等待的结果。

实验让 A 返回一份受控 Promise，B 同步记录调用。emit 返回时，轨迹是 `A:start → B`；手动放行 A 后，才出现 `A:end`。写成 `await ctx.emit(...)` 也不能补上这份等待：调用方等待的是 emit 已返回的 undefined。

同步抛错是另一条路径。A 如果直接 throw，数组的 map 会中断，B 不再执行，异常从 emit 调用处传播出去。“不等待”不等于“失败只记日志，然后继续广播”。

监听器返回的 Promise 若以后拒绝，emit 本身没有安装汇总或捕获处理。需要观察异步工作的生产方必须另有完成与错误处理；不要在约定同步完成的通知事件里偷偷启动一项无人持有的异步操作。

## `parallel`：等全部结束，再报告所有监听器错误

[`parallel()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/events.ts#L184)在 async 包装中调用每个回调，将结果交给 `Promise.allSettled()`：等每项成功或失败都已确定，也就是 settled，再筛出 rejected 项。源码节选：

```ts
const results = await Promise.allSettled(this.dispatch('emit', args).map(async cb => cb(...args)))
const errors = results.filter((result): result is PromiseRejectedResult => result.status === 'rejected')
if (errors.length) throw new AggregateError(errors.map(error => error.reason))
```

即使 A 同步 throw，包装它的 async 函数也只会产生一个拒绝结果，列表中的 B、C 仍会被启动。某项先失败不会自动取消其他项，最终错误也要等全部 settled 后才抛出。

实验让 A 拒绝、B 保持 pending、C 同步 throw。所有回调都已开始；只让 A 失败时，派发尚未结束。B 完成后，调用方才取得含 A、C 两个原因的 AggregateError，也就是保存多项失败原因的聚合异常。错误列表按对应的监听器结果顺序组织，不是按失败先后重排。成功返回值则被丢弃，不会自动收集成业务结果数组。

这里的“并行”是异步任务可以交错等待，不是给每个监听器分配一个 CPU 线程。回调的同步部分仍按列表次序进入；如果某个回调先执行大量同步工作，后一个回调仍要等它交还控制权。

还有两项边界：一个监听器永远不结束，allSettled 就无法全部结束；方法本身没有超时或取消其他回调的机制。若事件携带 AbortSignal，需要具体监听器配合它，而不是由 parallel 看到参数后自动完成取消。

### 这个版本的诊断 mode 有一处容易误读

上面的真实代码是 `this.dispatch('emit', args)`。因此，这份快照的 parallel 在 `internal/dispatch` 中报告的 mode 也是 `emit`。实验依次调用五种方法，观察到 `emit、emit、serial、bail、waterfall`。

这是固定版本的实现事实，不是建议把两个方法视为同一种调度。排查轨迹时，需要同时看真实调用方法与等待方式；本文没有修改这处实现，也不推断其他版本相同。

## `serial`：逐个等待，而且会提前停止

[`serial()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/events.ts#L205)每次 await 一个回调，然后用 `isBailed()` 判断是否直接返回：

```ts
for (const cb of this.dispatch('serial', args)) {
  const result = await cb(...args)
  if (isBailed(result)) return result
}
```

这不是“把所有监听器串行跑完”的保证。判断函数在 [`events.ts` 开头](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/events.ts#L13)：

```ts
return value !== null && value !== false && value !== undefined
```

因此，undefined、null、false 表示继续；`0`、空字符串、NaN 和对象都满足停止条件。不要用 JavaScript 的真值判断代替它。

实验中 A 先等待再返回 false，B 返回空字符串，C 留下记录。实际调用方等待 A，然后进入 B；B 的空字符串成为结果，C 没有执行。若 A 或 B 抛错、返回拒绝 Promise，serial 会拒绝，并跳过剩余回调。

这也解释了一种容易漏掉的编码错误：本来只是想向数组记录一项，却把 `items.push(...)` 写成箭头函数的隐式返回。push 返回数组的新长度；如果这个值进入 serial，便可能意外截断后面的监听器。声明为通知型事件时，应保持约定的 void 返回，不用无关的值参与派发决策。

## `bail`：立即判断返回对象，Promise 也算一个值

[`bail()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/events.ts#L218)与 serial 使用同一项停止判断，但没有 await：

```ts
for (const cb of this.dispatch('bail', args)) {
  const result = cb(...args)
  if (isBailed(result)) return result
}
```

同步决策回调返回 false 时，它会继续寻找下一个结果。async 回调则立即返回 Promise；Promise 既不是 null，也不是 false 或 undefined，因此 bail 会当场返回它，不再调用后面的回调。

实验让 A 返回 `Promise.resolve(false)`。调用方最后 await 得到 false，但 B 始终没有执行。外面加 await，只能取得已经选中的 Promise 的最终结果，不能回到 bail 的监听器循环中继续派发。

所以，bail 适合与同步返回约定配合。若需要按异步结果逐个寻找处理者，要检查是否应该选择 serial；也要同时检查事件本身的类型与生产方契约，不能仅在消费方擅自换一个方法。

## `waterfall`：由 next 连接调用链

[`waterfall()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/events.ts#L235)将派发的最后一个参数取作终点函数，再给监听器传入一个共享 next。相关源码节选：

```ts
const cbs = this.dispatch('waterfall', args)
const inner = args.pop()
const next = () => {
  const cb = cbs.shift() ?? inner
  return cb(...args)
}
args.push(next)
return next()
```

next 每次从当前名单中取出一个回调；名单耗尽后进入生产方提供的 inner。一个典型的包装顺序是 `A:before → B:before → inner → B:after → A:after`。

这份 waterfall 不是“把 A 的返回值作为 B 的第一个参数”。后续收到的是原来的事件参数与 next。返回值沿普通函数调用向外传回：A 想取得 B 的结果，需要调用 next，再决定怎样返回或修改它。next 没有用于替换参数的入口；给它传入一个新值，也不会把该值作为下一层的首个参数。

### 不调用 next，就不会自动进入后面

是否继续由调用 next 决定，和返回值是否满足 bail 条件无关。A 即使返回 undefined，只要没有调用 next，B 和 inner 就不会执行。

异步包装也需要把结果留在调用链上。监听器可以 `return next()`，也可以 `const value = await next()` 后返回自己的结果；若只是调用 next，却不返回或等待它，外层便不能据此追踪后续异步工作的完成与拒绝。

这个版本也没有保护“next 只能调用一次”。实验中，一个监听器调用两次 next；没有其他监听器时，inner 实际执行了两次。若 inner 带有写入等副作用，重复执行的后果属于调用方需要避免的行为，不能假定框架已经去重。

## 回到 dsh：为什么观察用 emit，写入决策用 waterfall

### `fs/observed` 是同步记录，不是异步存储屏障

文件工具的 [`read.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/tool-fs/src/read.ts#L160)在文件读取成功之后发出观察事件，相关调用为：

```ts
ctx.emit('fs/observed', target, { kind: 'present', version: info.version }, exec)
```

这次调用没有显式派发接收者，target 是普通事件参数。观察策略插件的 [`fs/observed` 监听器](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/fs-observation-policy/src/index.ts#L124)同步更新自己的记录；注释明确要求同步且不抛错，因为成功修改或读取已经发生。

这里的非抛错是插件约定，不是 emit 帮它兜底。把监听器改成 async 写日志，也不会让事件生产方自动等待持久化完成。

### `fs/write-intent` 占一个决策位置

[`write.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/tool-fs/src/write.ts#L121)先解析目标，再通过 waterfall 取得写入意图。源码节选为：

```ts
const intent = await ctx.waterfall('fs/write-intent', target, exec, () => undefined)
```

末尾的默认函数返回 undefined，对应没有额外写入意图时的路径。观察策略插件则注册了一个[不调用 next 的监听器](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/fs-observation-policy/src/index.ts#L116)，直接返回它计算的意图 Promise。由于它没有调用 next，排在后面的策略和默认函数都不会执行，本次写入就使用它给出的结果。

生产方 await 这份结果，然后才调用 `ctx.fs.writeText(...)`。策略计算失败会使这条调用链拒绝；事件服务没有为它自动挑选另一份策略，也没有把任意多个策略的结果合并成一个更严格的对象。

因此，prepend 和装配顺序在这里会改变先遇到哪个决策者。事件名本身不规定冲突消解，waterfall 也不自动赋予策略安全性；仍需检查具体插件与默认函数怎样约定输入、结果和失败处理。

### `agent/created` 用 serial 等待初始化监听器

Agent 注册表的 [`announce()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L550)以 `entry.carrier` 为接收者，对 `agent/created` 执行 serial 并等待。函数还在派发前标记公告已开始，避免创建监听器再次调用公告入口时，重复发出同一个 Agent 的创建通知。

这里需要按顺序等待创建监听器，某个监听器失败会使等待拒绝。serial 的提前停止规则仍然存在，事件监听器需要遵守其返回约定；方法名不会把不合约的返回值变成 void。

## 事件作用域由派发接收者过滤，不由名称前缀隔离

`fs/`、`agent/` 这样的前缀方便组织事件词汇，但没有自动创建私有总线。普通的 `ctx.emit('event', ...)` 没有接收者过滤器时，事件服务会选中同一根总线中该名称的 Hook；从某个子 Context 发出，并不单独构成私有投递。

dsh 用 [`scopeTarget()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/scope/src/index.ts#L170)构造专门的接收者：先保留基础对象的过滤条件，再根据注册方 Context 的 scope 判断。未标记 scope 的监听器被接纳，当前 key 或其祖先 scope 的监听器也可接纳；位于被派发 key 下层的 scope 不会因此被选中。

例如，假设 R 是 A 的祖先 scope，B 又是 A 的下级。向 A 派发时，在基础过滤条件也通过的前提下，未标 scope、R 和 A 中的监听器可以入选，B 中的监听器不会仅因它位于 A 下级而入选。

前面的 `entry.carrier` 就带着这份筛选信息。carrier 决定通知投递给哪些监听器，业务对象仍可以作为显式事件参数传递；用 payload 替换 carrier 可能丢掉过滤器，因此不能只看事件名就推断某个 Agent 会收到谁的通知。

`global: true` 则在事件服务的 Hook 过滤中直接放行。这是框架级投递选项，和“未标记 scope 的监听器可通过 dsh carrier”处在不同层次。作用域过滤也不是操作系统权限检查。

## `once` 和卸载还要考虑已捕获的回调

[`once()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/events.ts#L311)创建一个包装回调，进入它时先调用 disposer，再调用用户函数。因此，如果用户函数自己重入发出同名事件，新的派发通常已经看不到这条记录。本次最小重入检查得到一次调用。

但这份实现没有额外的“已调用”标志。另一个实验让前面的普通监听器先发起一次嵌套派发：once 在内层被执行并移除，外层已捕获的名单中仍有它。外层继续时，这个包装又执行一次，最终计数为二。

所以，在本版本中不能把 once 当成跨任意嵌套派发的全局一次性事务。若业务要求即使在重入下也只提交一次，需要业务状态或专门的互斥条件，而不是仅凭监听器从数组移除。

同样，Fiber 卸载能撤销注册，却不自动取消已经运行的 Promise，不会回滚先前监听器的副作用，也不能删除别的派发已经保存的回调名单。完整的 effect 持有、异步清理与父子结束顺序，下一篇再追踪。

## 复现固定源码的 18 组聚焦检查

[下载事件实验包](event-dispatch-examples.zip)。解压后进入 `event-dispatch-lab` 目录。包内只有检查脚本、说明和 TypeScript 版本声明，不复制 dsh 源码。需要 Node.js 22 或以上，并准备固定 commit 的 deepseek-harness checkout；下面的路径是占位示意，使用自己的实际位置。

```sh
npm install --ignore-scripts
DSH_SOURCE=/path/to/deepseek-harness npm run verify
```

入口 `run.mjs` 会确认源码 commit，并拒绝 Cordis/cosmokit 目录中已有修改的情况，然后将这两个包的源文件转译到本次创建的临时目录，加载其中的真实 Context 与 EventsService。TypeScript 的版本固定为 6.0.3；这里不执行仓库完整的 build 或 typecheck。

18 组检查覆盖 bail 值、emit 的异步完成和同步抛错、parallel 的全量等待与错误聚合、serial 停止及失败、bail 的 Promise、waterfall 的包装/截断/异步/重复 next、注册次序与快照、once 两种重入、接收者过滤、Fiber 撤销、空监听器以及诊断 mode。受控 Promise 由脚本放行，没有用 sleep 猜测竞争顺序。

脚本逐项断言，预期出现 18 条用例 PASS 和一条 `PASS 10 figure fixtures`，随后给出 commit、Node/TypeScript 版本及观察结果。配图的十组输入也由真实事件服务执行并断言，属于演示轨迹，不是实际 dsh 业务日志。每项使用自己的根 Context，结束后释放；临时转译输出也会清理。本次在 Node `v25.9.0` 下全部通过，未触发真实工具、网络模型或用户文件操作。

在 dsh 源码根目录，下面的只读命令可以定位文章主线：

```sh
git rev-parse HEAD
rg -n 'isBailed|dispatch\(|async parallel|emit\(|async serial|bail\(|waterfall\(' vendor/cordis/src/events.ts
rg -n 'register\(|unregister\(|once\(|on\(' vendor/cordis/src/events.ts
rg -n 'fs/observed|fs/write-intent' packages/fs/tool-fs/src/read.ts packages/fs/tool-fs/src/write.ts packages/fs/fs-observation-policy/src/index.ts
rg -n 'scopeTarget|Context.filter|scopeOf' packages/core/scope/src/index.ts
rg -n 'agent/created|async announce' packages/core/agent/src/index.ts
```

这些命令已经执行。真实 dsh 的事件含义还取决于生产方、监听方和装配配置；聚焦实验确认调度规则，不能替代应用级取消、持久化、权限或恢复验证。

## 下一篇追踪监听器背后的资源所有权

事件监听器会跟着 Fiber 的 effect 被清理，工具与服务注册也采用类似的所有权关系。下一篇从插件挂载与卸载继续，追踪 effect、Fiber、Scope 和异步清理，解释一次配置变更或插件移除怎样释放它创建的资源。
