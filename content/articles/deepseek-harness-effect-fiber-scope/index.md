+++
title = "DeepSeek Harness 源码解析（八）：effect、Fiber 与 Scope 怎样清理资源"
date = 2026-10-15
lastmod = 2026-10-17
draft = false
author = "Hex4C59"
description = "沿固定源码追踪 Cordis effect 与 Fiber 的资源所有权、逆序与并发清理、异步初始化和失败，再解释 dsh Scope 的双重释放入口与 Agent Loop 的有序卸载。"
summary = "同一个 effect 内会逆序等待，Fiber 上多个兄弟 effect 却会并行清理。本文用 22 组真实实现的聚焦实验解释卸载顺序、函数身份、重入、失败，以及 Scope 路由和资源寿命的区别。"
tags = ["DeepSeek Harness", "Cordis", "资源管理"]
categories = ["ai"]
source_kind = "original"
series = ["DeepSeek Harness"]
series_order = 8
difficulty = "advanced"
article_type = "concept"
topics = ["coding-agent", "plugin-architecture", "resource-lifecycle"]
frameworks = ["DeepSeek Harness", "Cordis"]
ShowToc = true
+++

[第七篇](/articles/deepseek-harness-event-dispatch/)讲到，插件卸载时会撤销它登记的监听器。但一个 Agent 退出时，还需要停止接收新工作、等待当前工作结束、撤下工具和监听器，再关闭会话写入通道。若当前任务还在使用工具，就不能提前撤下工具；若最后的事件还没写完，也不能提前关闭写入通道。资源需要按依赖顺序清理。

Cordis 会把初始化和对应的清理函数放进同一份登记，称为 effect；保存一次插件挂载状态和这些登记的运行实例，称为 Fiber。本文说资源“归谁持有”，就是问它的清理函数登记在哪一份名单上，谁退出时会调用它。

Cordis 的一个细节很容易影响判断：**同一个 effect 内的清理函数按逆序串行等待，Fiber 上多个兄弟 effect 的清理却会并行推进。** disposer 是用于请求清理的函数。把登记在同一个 Fiber 上的原 disposer 函数直接交给组合 effect，可以把它从 Fiber 的顶层名单移进组合内部；给它再包一层函数，可能让原函数仍留在顶层，与组合里的其他清理并行运行。

本文从这个区别出发，追踪资源归谁持有、什么时候开始撤销、调用方等到什么，以及失败后还有哪些动作能继续。读者需要能阅读函数调用和 Promise；生成器的用法会在对应片段旁说明，Context 和插件依赖则沿用前几篇的解释。配置表达式、Loader 和热重载的完整控制流程留给下一篇。

本文分析 [DeepSeek Harness `0.2.1-alpha.2`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/package.json)，源码取自[固定快照](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c)；核对日期为 2026-10-15。[vendored Cordis manifest](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/package.json)为 `4.0.5-alpha.1`。文末实验用 TypeScript 6.0.3 转译固定快照中的 Cordis、cosmokit 和 dsh-scope，在 macOS 27.0.1 arm64、Node `v25.9.0` 上运行了 22 组聚焦检查；dsh 业务调用的连接关系另由源码核对。

## 先分清 Context、Fiber、effect 和 Scope

这里的资源包括监听器、服务注册、作用域中的工具与提示词声明，也包括需要显式关闭的异步工作。清理的对象不总是操作系统句柄；从一张注册表中撤销当前插件的贡献，同样需要明确的寿命。

| 对象 | 在这条资源链中的职责 |
|---|---|
| Context | 插件访问服务、登记资源和创建子插件的入口；派生 Context 可以继续共享同一个 Fiber |
| Fiber | 一次插件应用的运行实例，记录配置、依赖是否齐备、正在进行的装载或卸载，以及顶层清理名单 |
| effect | 立即执行一段初始化，并收集它交出的清理函数；可将多项清理组合起来 |
| disposer | 请求释放已登记资源的函数；具体返回值与等待规则要看该入口 |
| dsh Scope | 创建一个空插件的 Fiber，让局部注册可以一起清理；再给 Context 增加 key，决定局部工具和提示词的查找范围，并筛选事件监听器 |

[Context.extend()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/context.ts#L99) 用 `Object.create(this)` 派生 Context。单独调用 `ctx.extend(...)` 没有创建新的 Fiber，资源仍归原 Fiber。实验从派生 Context 登记清理，卸载原插件后，该清理执行一次。

[RegistryService.plugin()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/registry.ts#L316) 才会为一次插件应用创建 Fiber。相同插件回调可以对应多个 Fiber，每个实例分别记录自己的 `ctx`、配置与寿命。注册表把这些实例汇集在同一个 runtime 记录中，但每次挂载的资源仍由各自的 Fiber 持有。[Fiber 构造函数](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L234) 为子实例建立 Context，并通过父 Fiber 的 effect 登记它的释放入口。

Scope 的实现位于 `packages/core/scope`。它建立在这套 Fiber/effect 机制之上，后文会分别检查它的路由关系和真实的父子所有权。

## effect 立即初始化，交回一份清理入口

[Fiber.effect()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L418) 先检查 Fiber 是否仍可登记资源，再运行初始化。一个最小的说明性片段如下；这里的数组只用于展示顺序，完整可运行的断言在实验包中：

```ts
const trace: string[] = []
const stop = ctx.effect(() => {
  trace.push('setup')
  return () => { trace.push('cleanup') }
}, 'example/resource')
// 此刻 trace 为 ['setup']
await stop()
// 此刻 trace 为 ['setup', 'cleanup']
```

effect 返回的 stop 由框架包装。它既是手动释放入口，也留在 Fiber 的清理名单中，供插件卸载时调用。手动释放后，正常完成的登记会从名单移除，避免以后再次释放同一项。

[_execute()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L356) 接受几种初始化结果：清理函数、产生清理函数的同步/异步迭代器，或解析为清理函数的 Promise。实现也允许 null/undefined 表示没有清理项；返回 `42` 等无效结果则抛出 `TypeError('Invalid effect')`。

生成器可以执行一段代码，再通过 `yield` 逐项交出值；这里交出的是清理函数。effect 在初始化时收集这些函数，通常等到撤销时才调用它们。仅把清理代码写进生成器的 finally，不会把它加入这份名单，不能代替显式登记。

### await effect 等初始化，不会自动清理

异步 effect 返回的包装函数还带有 [wrapper.then](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L555)。因此它既可调用，又是一个可等待对象：

```ts
const stop = ctx.effect(async () => {
  const resource = await acquire() // 假设的业务资源获取函数
  return () => resource.close()
})
const readyStop = await stop
await readyStop()
```

这是调用形状示意。`await stop` 等初始化完成并取得清理入口，这次 await 没有关闭资源；调用 readyStop 才请求释放。实验用受控 Promise 代替 acquire，观察到 `setup → ready`，调用 readyStop 后才出现 cleanup。

直接调用 stop 也可以请求释放：若初始化尚未结束，框架会先等它结束，再清理已经得到的资源。

插件主体只创建异步 effect 后直接返回时，单独 await 插件不会补齐该 effect 的就绪等待。本次实验也核对了对应写法：在插件的异步主体中显式 `await stop`，Fiber 会保持 LOADING，也就是仍在初始化，直到这项 setup 完成。

## 两层“逆序”为什么产生不同的完成顺序

### 同一个 effect 内：后提交的清理先执行，并等待它结束

[同一个 effect 的 dispose](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L431) 把当前 effect 收到的清理函数取出、反转，再按 Promise 链连接。同步部分会直接运行；一旦遇到异步结果，后续清理接到前一项完成之后。

说明性的组合写法为：

```ts
const stop = ctx.effect(function* () {
  yield releaseA
  yield releaseB
})
```

如果 releaseB 返回一个待完成的 Promise，releaseA 要等它成功完成后才进入。聚焦实验控制 B 的完成时机，轨迹为 `B:start → B:end → A`。这里的顺序依赖来自同一个 effect 内部的组合。

### Fiber 顶层：逆序取名单，各项清理并行推进

[DisposableList.clear()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/utils.ts#L27) 也会反转名单，但调用它的 [Fiber._unload()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L675) 随后使用了 `Promise.all()`。相关源码节选如下：

```ts
await Promise.all(this._disposables.clear().map(async (dispose) => {
  try {
    await composeError(async (info) => {
      await Promise.resolve()
      info.error = new Error()
      await runDisposable(dispose)
    }, this._runner.getOuterStack)
  } catch (reason) {
    this.ctx.logger.error(reason)
  }
}))
```

因此，先登记 A、后登记 B 的两个兄弟 effect，会按逆序开始清理，却可以同时停在各自的 await。实验先等 A、B 都已进入清理，再先放行 A，得到 `B:start → A:start → A:end → B:end`。

父子 Fiber 也不能简单理解成“子树全结束后才碰父插件自己的资源”。子 Fiber 的 disposer 登记在父 Fiber 上，是父清理名单中的一项；其他兄弟项仍可同时推进。父卸载需要等这些任务，但有严格顺序的资源应另外组合。

## yield 确切 disposer，为什么会改变所有权

[collect()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L450) 在收集一项清理函数时，会把这个函数从当前 Fiber 的顶层名单移除，再放入当前 effect 的内部名单。比较的是不是同一个函数对象。两个函数即使最终调用同一个关闭方法，也不因此被当作同一项。若该函数带有框架记录的 effect 信息，还会成为当前 effect 的诊断子项，供检查组合关系时查看。

这使下面两种形状具有不同含义。片段中的 scope 来自 createScope，releaseB 和 releaseTail 代表说明性的业务清理：

```ts
ctx.effect(function* () {
  yield releaseTail
  const scope = createScope(ctx, key)
  yield scope.rawDispose
  yield releaseB
})
```

rawDispose 原本已登记在当前 Fiber 上。直接 yield 它后，该项从顶层移入组合内部；清理顺序变成 B、Scope、tail。若 Scope 的清理异步停住，tail 也会等待。

把中间一行改成 `yield () => scope.rawDispose()` 时，组合收集到的是新函数。原来的 rawDispose 仍在 Fiber 顶层，因而可能在 B 尚未完成时就由 Fiber 并行启动。它改变了清理任务之间的等待关系。

图中对照三组已经执行的输入。实线表达持有关系，下面的轨迹表达先后；时间间距仅为排版，不是耗时。涉及 Scope 的资源都是实验中的合成登记，不是实际 Agent 运行日志。

{{< interactive-diagram src="resource-ownership.html" title="比较兄弟 effect、直接 yield Scope rawDispose 和包装函数三种资源持有方式及清理轨迹" height="1660" compact-height="1760" mobile-height="2070" >}}

### “同一个 owner”是这项收编成立的条件

这里的 owner 指登记资源时归属的 Fiber。collect 从执行这个 effect 的 Fiber 名单中删除函数。如果原 disposer 属于另一个 Fiber，当前名单里没有它，直接 yield 也不会替另一个 Fiber 转移所有权。业务可以通过函数等待别处清理，但不能据此宣称原所有者已经解绑。

真实的 [组合 Scope 清理](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L610) 特意在创建 Scope 的原 Fiber 上嵌套 rawDispose。只有从这份原始登记名单中移除 rawDispose，才能让组合独自安排它的执行顺序；仅照抄 yield 的写法并不足够。

[getEffects()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L568) 可以显示标签与组合子项，帮助检查“资源登记在哪一层”。这些是诊断元数据，不能当成文件句柄或所有外部任务都已释放的证明。

## 初始化没结束就卸载，迟到的资源归谁处理

[提前登记 wrapper](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L520) 在执行用户初始化之前，先把 effect 的 wrapper 放进 Fiber 名单。这样，即使初始化函数在返回前又触发了本插件的卸载，清理方也已经能够找到这项登记。这种从正在执行的函数中再次进入卸载流程的情况，就是这里的同步重入。

wrapper 还记录初始化是否仍在执行。如果卸载发生在 setup 尚未返回时，清理先等待一份专门的 Promise，直到 setup 返回后才继续；源码把这份等待称为 setup barrier。异步 setup 已经返回 Promise 时，则等待那项初始化任务。两种情况都要先取得初始化交出的清理函数，再执行它，避免只清空当时的名单而漏掉迟到的资源。

实验让一个异步 effect 卡在获取资源的 Promise 上，然后卸载 Fiber。放行后，轨迹是 `acquired → cleanup`，Fiber 最后进入 DISPOSED。另一个实验在同步 setup 内调用 owner.dispose，观察到 `setup → setup:return → cleanup`。

### async 生成器的 epoch 检查不等于取消所有异步工作

[异步迭代器分支](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L383) 在每次取下一项之前比较 epoch，也就是本次执行是否仍然有效的标记。标记变更后，不再继续申请下一项；但已经发出的 `iter.next()` 仍可能需要等待，迟到交出的清理函数仍需收集。

它没有给任意 Promise 注入 AbortSignal，也没有强制让一个永不完成的初始化结束。setup 或某项 cleanup 一直 pending，相关卸载就可能一直等待。业务需要自己的停止协议与完成条件。

### 初始化失败会处理已经登记的资源

同步生成器已经 yield 一份资源，然后初始化抛错时，effect 会请求回滚并把原错误抛给调用方。若回滚异步进行，wrapper 在完成前仍保留为 owner 可见的任务，供 owner 卸载加入这份等待。

异步初始化拒绝也有回滚处理。实验分别核对同步抛错和 async 生成器失败，已提交的清理各执行一次。这个结论只涉及已经交给 effect 的清理函数；若业务先获取资源、尚未登记就抛错，框架无法凭空补出它的关闭方法。

## “第二次调用无事发生”和“等到清理结束”是两件事

[公开 wrapper 的入口](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L504) 在首次请求撤销后使 runner 失效。正常返回给用户的 disposer 再次被调用时，这个版本会返回 undefined；第一次清理若仍在等待，第二次调用不会自动返回同一份 Promise。

内部的 [runDisposable()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L114) 则另有处理：它调用 disposer 后，还会查询 effectInertia 中记录的、尚未完成的清理 Promise。这样，即使另一处已经开始释放，Fiber 或直接持有这个函数的组合 effect 仍可以等待同一项任务。

本次实验先手动启动子 effect 的异步清理，再进入持有它的外层组合。重复调用子 disposer 得到 undefined，但外层较早登记的 tail 没有提前运行；放行子清理后，tail 才执行一次。

因此，业务若会从多条路径同时发起退出，并要求每个调用者都观察到相同的完成与失败，应显式共享一份清理 Promise。下一节的 Scope.dispose 正是这样的入口。

## Scope 同时提供确切身份与共享完成

[createScope()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/scope/src/index.ts#L137) 的关键源码节选为：

```ts
const fiber = ctx.plugin(scope)
const scoped: Context = fiber.ctx.extend({ [kScope]: key })
let disposing: Promise<void> | undefined
return {
  ctx: scoped,
  rawDispose: fiber.dispose,
  dispose: () => (disposing ??= quiesceFiber(fiber)),
}
```

scope 是共享的空插件回调，每次调用仍创建独立 Fiber。通过 scoped Context 登记的监听器、工具或其他 effect，都加入这次子 Fiber 的清理名单；kScope 则标明这些注册属于哪个作用域，供工具查找和事件筛选使用。

[ScopedLayers.effect()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/scope/src/store.ts#L226) 展示了局部注册怎样随 Scope 撤销。它把一个作用域中的注册保存在一层表中，称为 layer；修改表时，也把撤回这次修改的 undo 函数交给登记 Context 的 effect。清理时先调用 undo，再移除已经为空的局部 layer，并按选项发送变化通知。从表中撤掉登记之后，业务对象是否还需要异步关闭，要由相应业务 API 另外负责。

rawDispose 保留原 Cordis 函数，适合交给同 owner 的组合 effect。dispose 会共享第一次创建的 Promise，适合多条退出路径等待同一个 Scope 结束。

[quiesceFiber()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/scope/src/index.ts#L115) 先请求 fiber.dispose，再持续等待 fiber.inertia；即使原 disposer 已被另一方调用，也会继续追踪尚未结束的卸载。实验先调用 rawDispose，再同时调用两次 dispose：两次得到同一份 Promise，Scope 中的异步清理完成后才一起结束。

### 路由祖先和 Fiber 父子不能互相代替

[scopeParents](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/scope/src/index.ts#L39) 保存 key 的祖先关系，用来决定查找注册时可以向哪些祖先继续查找，以及派发事件时哪些监听器能入选。它不修改 Fiber.parent，也就不改变哪个 Fiber 卸载时会清理哪个子实例。

如果都从 ownerCtx 创建 A、B 两个 Scope，即使 B 的 options.parent 指向 A 的 key，二者的 Fiber 仍是 ownerCtx 的两个子项。实验撤销 A 后，B 仍为 ACTIVE，B 的监听器仍能执行；之后卸载真实 owner，B 才随它退出。

需要某个 Scope 随另一个 Scope 的真实 Fiber 生命周期退出时，应从相应的 scoped Context 创建它，并另外考虑正确的路由 key 关系。单独设置 parent key 只表达路由/可见性祖先。

## Fiber 的状态、身份和过渡任务分别说明什么

[子 Fiber 的 disposer](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L265) 首先把子 Fiber 的 uid 置为 null，并撤销相应 runtime 登记，再驱动卸载。当前资源可能仍在异步清理。因此，注册表中查不到它、uid 已清空，与清理全部结束并不是同一时刻。

| 状态或字段 | 本文需要关注的含义 |
|---|---|
| PENDING | 尚未激活，例如依赖不足；初始发布时也处于此状态，内部观察者可能已经登记资源 |
| LOADING | 插件初始化正在进行，尚未完成当前装载 |
| ACTIVE | 当前激活已经完成；之后仍可能因依赖变化而卸载 |
| UNLOADING | 当前清理正在进行，effect 拒绝再登记新资源 |
| FAILED | 装载中的初始化或配置失败已被记录；await 可把装载错误抛给调用方 |
| DISPOSED | 该普通子 Fiber 已被移除并结束当前清理，实例不能再 restart |
| inertia | 当前装载或卸载的 Promise；后续过渡可能替换它，需要循环等待 |

[Fiber 状态判断](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L574) 根据 uid、错误和 epoch 判断稳定状态；LOADING/UNLOADING 则在过渡开始时显式设置。[_refresh() 与 _setEpoch()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L611) 把所需服务的提供方 uid 组成一个执行标记。提供方变化后，旧标记不再有效，框架便让当前装载或卸载接着进入必要的清理或重载，避免继续使用旧依赖。

本次实验先移除服务提供方，消费插件释放一次资源、回到 PENDING，uid 保持不变；提供新服务后，同一消费 Fiber 再次进入 ACTIVE。[_reload()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L646) 在进入插件主体前检查执行标记；另一个实验在 LOADING 状态、插件主体执行前的异步检查点到来之前请求 dispose，插件主体最终没有运行。

PENDING 也有自己的清理路径。Fiber 发布给 internal/plugin 观察者时，观察者可能先登记资源；即使插件主体始终没有启动，dispose 仍需撤销这些登记。本次检查核对了这一分支。

销毁时的 [emitPluginDisposed()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L120) 对每个通知回调分别处理异常和拒绝，把它们交给 logger。它不等待观察者的异步工作完成，也不把普通观察者失败当作跳过所有权清理的理由；logger 本身抛错仍可能使流程拒绝。

### await、restart 和 delete 不能只看方法名

[Fiber.await()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L704) 循环等待 inertia，并在最后重新抛出装载错误。`await ctx.plugin(...)` 使用这条路径，但 PENDING 没有在途过渡时也可以返回；它不能无条件证明所需服务已经齐备。

[restart()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L718) 对普通插件保留 uid，先使当前执行失效，再重新检查依赖并等待。普通 dispose 则清空 uid；之后 restart 会得到 INACTIVE_EFFECT。[根 Fiber 分支](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L331) 是例外：根 Fiber 的 dispose 实际调用 restart，本次实验看到它清理后仍为 uid 0、ACTIVE。

[registry.delete()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/registry.ts#L258) 从注册表移除 runtime 并对其 Fiber 发起 dispose，返回的是 runtime 对象。写 `await registry.delete(plugin)` 不会因此等到所有清理结束。[update()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L736) 也没有把整个更新链的 Promise 直接返回；其中还有 internal/update 拦截，完整更新确认需要沿具体调用方和 Loader 继续看。

## 清理失败之后，哪些工作还能继续

一个组合 effect 内部用成功路径的 then 连接较早登记的清理。如果当前函数同步抛错，或其 Promise 拒绝，这份组合中的后续清理会被截断。

Fiber 顶层则对每个独立清理任务分别捕获异常并记录日志，所以另一个兄弟 effect 仍能完成。实验让一个组合持有 older、failed 两项，同时在 Fiber 上登记另一兄弟：实际观察到 `failed → sibling`，older 没有运行，错误被 logger 保存；logger 未抛错时，Fiber.dispose 正常结束。

因此，dispose 的 Promise 正常结束不能单独证明每一项资源释放成功。业务如果要求“一项失败后仍继续其余清理”，需要在自己的组合内部显式尝试后续步骤，并汇集失败，不能只依赖外层 Fiber 的捕获。

真实的 [Agent Loop 的 teardown](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L544) 就明确实现了这份业务合同。它共享一份 disposing Promise，先停止新工作、取消驱动并通过 whenIdle 等当前工作结束，再清理 Scope、关闭会话写入 handle、撤销 Agent/Session 注册，最后移除工厂和调用方对这次实例的跟踪记录。各阶段失败被收集，后面的必要步骤仍继续，最后再报告汇总错误。

这条顺序保护的是仍在收尾的运行实例。Scope 过早卸载可能撤掉收尾需要的声明或监听器，写入 handle 过早关闭则会影响最后的事件处理。具体哪些资源跨过哪些阶段，仍由相应业务拥有者安排。

[ToolRuntime.presentAs()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/tools/src/index.ts#L983) 也用组合生成器依次提交工具呈现模式与提示词 section 的撤销；[AgentRegistry.register()](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L437) 则保留注册 effect 的确切函数身份，供拥有退出顺序的调用方组合。资源 API 返回函数时，调用方应先判断它是否还承担所有权关系，再决定能否随手包装。

## 下载并复现 22 组局部行为检查

[下载生命周期实验包](resource-lifecycle-examples.zip)，解压后进入 `resource-lifecycle-lab`。需要 Git、Node.js 22 或以上、固定 commit 的 deepseek-harness checkout；本次实际验证为 Node `v25.9.0` 和 TypeScript 6.0.3。下面是占位路径，应替换为自己的源码位置：

```sh
npm install --ignore-scripts
DSH_SOURCE=/path/to/deepseek-harness npm run verify
```

run.mjs 会确认 commit，并拒绝 Cordis、cosmokit、dsh-scope 相关源码目录存在修改的情况。随后将这三部分真实实现转译到本次创建的临时目录，加载并逐项断言；不会为 dsh 安装工作区依赖。

22 组检查覆盖本文的顺序、并发、函数身份、异步初始化、回滚、清理失败、重入、状态、依赖变化、父子 Fiber、Scope 完成语义及路由祖先。受控 Promise 由脚本显式放行，成功时输出 22 条 PASS，末尾 JSON 报告 commit、实际版本和观察结果。

这些是固定实现的聚焦运行证据。转译没有进行完整语义类型检查，也没有启动 dsh 应用、真实文件工具或模型网络请求；Agent Loop 的生产调用关系来自静态研究，不能把本实验当成完整产品退出验收。

在 dsh 源码根目录，下面六条只读命令可以定位本文主线，均已执行核对：

```sh
git rev-parse HEAD
rg -n 'effectInertia|runDisposable|effect\(|const wrapper|_execute|_unload|_reload' vendor/cordis/src/fiber.ts
rg -n 'class DisposableList|clear\(' vendor/cordis/src/utils.ts
rg -n 'quiesceFiber|rawDispose|createScope|scopeParents' packages/core/scope/src/index.ts
rg -n 'const teardown|yield created.scope.rawDispose|unfollowScope' packages/core/agent-loop/src/index.ts
rg -n 'getEffects|async await|async restart|update\(' vendor/cordis/src/fiber.ts
```

## 下一篇沿 Loader 追踪配置如何改变这棵资源树

现在可以分别检查一项注册的 Fiber、组合 effect、清理 Promise 和 Scope key。Loader 接收一份配置变化后，怎样决定复用、更新或移除这些实例，还需要另一条控制链。下一篇继续研究配置表达式、隔离、热重载与动态扩展，并把本篇的生命周期规则放回真实装配流程。
