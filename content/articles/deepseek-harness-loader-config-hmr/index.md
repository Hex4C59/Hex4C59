+++
title = "DeepSeek Harness 源码解析（九）：Loader 怎样把配置变成运行中的插件"
date = 2026-10-15
lastmod = 2026-10-17
draft = false
author = "Hex4C59"
description = "沿着 EntryTree、配置表达式、volatile 引用、服务隔离与 dsh HMR，追踪一次配置变化怎样影响插件实例，并用 28 组固定源码实验核对完成边界。"
summary = "同样是改配置，有的字段原地更新，有的让 Fiber 清理后重启，有的只刷新子条目。本文追踪 Loader 的实际分支，再解释 dsh 怎样串行协调配置刷新、模块替换和失败恢复。"
tags = ["DeepSeek Harness", "Cordis", "热重载"]
categories = ["ai"]
source_kind = "original"
series = ["DeepSeek Harness"]
series_order = 9
difficulty = "advanced"
article_type = "concept"
topics = ["coding-agent", "plugin-architecture", "configuration"]
frameworks = ["DeepSeek Harness", "Cordis"]
ShowToc = true
+++

改了配置，插件什么时候真正用上新值？

如果每次都卸载整个应用，就需要重新清理资源和建立连接。如果只替换一个 JavaScript 对象，插件早已注册的工具、监听器和服务又不会自动跟着改变。dsh 负责把配置装成插件的 Loader 会按改动内容分别处理：普通字段变化通常让插件清理后重新初始化；允许运行中更新的字段则保留同一个引用，让插件下次读取时拿到新值，这类字段叫 volatile。

配置也可能只是把子条目放进一组（Group），或从另一个文件引入子条目（Include）。这两类配置可以继续把改动分发给各子条目。若变化的是已加载的模块代码，则由热模块替换（Hot Module Replacement，HMR）协调旧实例清理和新实例创建。

Fiber 是一次插件挂载的实例与生命周期边界，持有这次挂载登记的资源。这篇面向读过前面运行时文章、能阅读 TypeScript 的读者，追踪“谁决定让这些资源重新创建”。读完后，应当能判断一次配置编辑会保留哪个对象、重做哪段初始化，以及需要等待哪个完成信号。

本文分析 [DeepSeek Harness `0.2.1-alpha.2`](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c)，核对日期为 **2026-10-15**。Loader 的包版本为 `1.0.6-alpha.1`；Cordis 为 `4.0.5-alpha.1`。正文以该版本的本地源码为依据，文末附 28 组可重跑实验。文件监听、真实 Node 模块缓存替换和完整应用启动没有在这次实验中运行，对应部分明确按源码分析。[Loader manifest](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/package.json) · [Cordis manifest](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/package.json)

## 先看同一个修改怎样走向不同结果

假设一个插件同时有 `fixed` 和 `live` 两个字段。插件用 schema 声明字段的类型、默认值和更新规则，其中只有 `live` 标成 volatile。这里的 volatile 指“运行中可更新的配置引用”，与内存持久性无关。

| 改动 | Loader 选择的路径 | 运行中的结果 |
| --- | --- | --- |
| 原始配置完全相同 | `Entry.update()` 提前返回，除非调用要求强制处理 | 保留现有运行状态 |
| 只有有效 volatile 值变化，且满足快速路径条件 | 验证候选配置，更新原引用，通知 owner | 保留 Fiber、已解析配置与引用对象 |
| 普通字段变化 | 调用 `Fiber.update()` | 默认清理后重新执行插件；插件可拦截 |
| Group 的子条目列表变化 | Group 消费自己的更新 | 按子条目 id 增、改、删 |
| Include 的 patches 覆盖规则变化，path 不变 | Include 自行处理更新 | 保留文件树，重新按 patches 修改子条目 |
| 普通 entry 变为 disabled | 释放它的 Fiber | entry 仍在配置树，运行实例退出 |
| 已加载的模块代码变化 | HMR 分析依赖并替换受影响的 runtime | 旧实例清理后创建替换实例 |

这些分支分布在 [Entry](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/entry.ts#L117-L197)、[Group](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/group.ts#L48-L89)、[Include](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/include/src/index.ts#L190-L201) 和 [dsh HMR](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/hmr/src/index.ts#L631-L729) 中。

下面可以对照四条轨迹。前三条来自本文已运行的 Loader 实验；HMR 一栏是固定源码的正常替换路径。图中的序号表示因果顺序，不表示耗时；“完成后快照”也不表示每一帧都在采样真实应用。

{{< interactive-diagram src="configuration-paths.html" title="配置变化的四条路径：普通重启、volatile 就地提交、无效候选与 HMR 模块替换" height="2200" compact-height="2120" mobile-height="2480" >}}

## 配置树里保存的不是插件本身

Loader 同时处理四类对象，先分清它们，后面的更新才不会混在一起。

| 对象 | 保存什么 | 用来回答什么问题 |
| --- | --- | --- |
| `EntryTree` | entry 索引、根组、导入基准 URL | 到哪里找条目和模块？ |
| `EntryGroup` | 一份有顺序的子 entry 配置列表 | 哪些条目属于这组？ |
| `Entry` | 原始 options、父组、Fiber 与原始模块命名空间 | 这行配置现在对应哪个实例？ |
| `Fiber` | 已解析配置、注入依赖、资源与生命周期状态 | 插件当前能否运行，怎样清理？ |

`EntryOptions` 的核心字段是 `id`、`name`、`config`、`group`、`disabled` 和 `inject`；隔离插件再补充 `isolate`、`intercept`。`name` 告诉 Loader 从哪里导入插件模块，称为模块说明符；`id` 则让 Loader 找到要更新的那一行配置。同一个模块可以被多行配置使用，所以不能用模块名代替配置条目的身份。[Entry 定义](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/entry.ts#L9-L73) · [扩展字段](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/isolate.ts#L5-L14)

Group 把子条目放在同一棵 tree，子条目的树内 id 仍直接进入同一个 `store`。Include 则建立另一棵文件树，外层通过 `entry.subtree` 指向它。`resolve('include:leaf')` 表示先找到 Include 条目，再到它引入的子树中找 leaf，冒号分隔的是这两棵树。普通 Group 仍在原树内，嵌套一组不会增加一个冒号。`Entry.id` 也会把拥有这棵子树的外层 entry id 补作前缀。[树的构造与定位](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/tree.ts#L15-L79) · [组内创建](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/group.ts#L20-L28)

因此，这个版本要求同一棵 tree 中用作身份的 id 不相互冲突。`ensureId()` 为缺失 id 生成随机值；显式提供重复 id 时，`EntryGroup.create()` 会复用 store 中已有的 Entry。不能假设嵌套一层 Group 就获得一套独立 id 空间。

### 一行配置怎样落成 Fiber

`loader.create()` 先把 options 插进目标组的列表，调用所属树的 `write()`，再创建或更新 Entry。Entry 初始化时执行以下过程：

1. 由父树导入 `name`。`cordis:` 前缀查 `loader.builtins`；相对模块依据树的 `baseUrl` 解析。
2. 用 `unwrapExports()` 处理默认导出与兼容导出形态。
3. 经 `loader/patch-context` 更新 entry Context 的继承、服务隔离和拦截配置。
4. 调用 `registry.plugin()` 创建 Fiber，将 entry 的原始 `config` 交给它。
5. 保存 Fiber 与**未拆默认导出之前的模块命名空间** `moduleNamespace`。模块命名空间就是导入时得到的导出对象；保存它，可以在热重载时确认旧实例实际来自哪次模块加载。

`_initTask` 用来合并同一条目的并发初始化；导入失败会记录错误并结束，不能把 `await loader.create()` 理解为“插件必定 ACTIVE”。后续还要看 Fiber 状态、依赖与错误。[创建和导入](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/tree.ts#L81-L129) · [Entry 初始化](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/entry.ts#L209-L238)

Loader 根树的 `write()` 是空操作。文件持久化由 Include 提供，不能从“调用了 write”推断已经写入磁盘。[根树 write](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/index.ts#L171-L178)

## 一份配置有原始值，也有运行值

下面是说明配置处理的 YAML 片段，不是可独立启动 dsh 的完整组合：

```yaml
- id: example
  name: './example.js'
  config:
    limit: !!js "ctx.get('limits').parallel"
    label: 'agent-${name}'
```

Include 给 `!!js` 注册了自定义 YAML 类型。读取后，`limit` 暂时成为 `{ __jsExpr: "ctx.get('limits').parallel" }`，`label` 则仍是普通字符串。Loader 的 `interpolate()` 递归遍历对象和数组，只在遇到这种表达式节点时求值；这里没有 `${...}` 字符串模板替换。[YAML 类型](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/include/src/index.ts#L9-L23) · [表达式求值](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/utils.ts#L3-L32)

Fiber 准备插件配置时，会先通过 `internal/config` 回调链求出表达式的值，再交给插件的 Config schema 检查类型、填充默认值。`Entry.options.config` 保存原始形式，`Fiber._config` 保存供生命周期使用的原始输入，`Fiber.config` 是经过钩子和 schema 处理的运行值。后者可能已有默认值、转换结果和 volatile 引用，不能拿它冒充原文件。[Loader 配置钩子](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/index.ts#L104-L127) · [Fiber 配置解析](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L640-L674)

### 为什么不能在读取 YAML 时就求值

Group 和 Include 的配置里还装着别的 entry。父级若立即递归求值，子条目的表达式就会在错误的 Context 中执行：它可能还没进入应有的服务隔离域，声明的依赖也可能尚未就绪。

Loader 因此把带 `EntryGroup.key` 标记的 Group、Include 等条目视为装着子配置的容器，跳过对子配置的提前求值，等各子 Fiber 激活时再处理；同一 entry 下的普通子插件也不会重复执行这次 entry 插值。本文实验让子插件依赖一个尚未提供的服务：Group 挂载并稳定后，表达式求值次数仍为 0；补齐服务后，子 Fiber 才求值得到结果。Include 的 `path`、`enableLogs` 等自身字段也保持字面值，不在这个钩子里支持 `!!js`。[载体判断](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/index.ts#L104-L113) · [Include 标记](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/include/src/index.ts#L158-L167)

表达式也没有自动订阅其读取的所有值。`disabled` 表达式在读取有效禁用状态时求值；普通配置表达式在相应解析路径中求值。外部对象变了，并不表示 Loader 会自动再次计算所有相关表达式。[禁用状态](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/entry.ts#L75-L99)

这里还有一个明确的权限边界：求值器使用 `new Function`、`with (ctx)` 和 `eval`，并非安全沙箱。服务隔离不会把 JavaScript 表达式隔离成低权限代码。应将可写入 `!!js` 的配置视为可信代码输入；这与后面动态扩展的受控运行入口是两件事。

## 普通更新怎样触发清理和重启

`Entry.update()` 先合并 options，更新时传入 `null` 或 `undefined` 会删除对应字段，随后检查有效 disabled 状态。普通 entry 被禁用就释放 Fiber，保留配置条目；重新启用后，它可以重新初始化成新的 Fiber。带 `group: true` 的容器条目自身保持可运行，但子条目会检查祖先 options，所以仍会受组的禁用条件影响。实验分别核对了这两种情况。[Entry.update 主分支](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/entry.ts#L75-L157)

若原 Fiber 仍存在，Entry 比较新旧 options，发出 `loader/partial-dispose`，再更新 Context。`_patchContext()` 在配置变化或处理 Group 时调用 `fiber.update(rawConfig, true)`。这里的 `true` 是 `noSave`：这次变化已来自配置树，不应再被 Fiber 的保存钩子反向写回。[Context 更新](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/entry.ts#L101-L109)

ACTIVE Fiber 会先解析候选配置，再进入 `internal/update` waterfall。默认末端更新 `fiber.config` 并调用 `restart()`：清理旧资源，重新执行插件。实验中的轨迹是 `apply A → dispose A → apply B`，**Fiber 对象和 uid 保持不变**。这与 HMR 创建替换 Fiber 的路径不同。[Fiber.update](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L718-L752)

插件可以注册自己的 `internal/update` 监听器并消费更新，不调用 `next()`。Group 正是这样保留自己，再按 id 对子条目并发执行创建、更新和删除。Include 在 path 不变时也消费更新，显式保存新的 `this.config`，再重新应用 patches；path 改变才交回默认重启。[局部更新链](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/events.ts#L139-L155) · [Group 差分](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/group.ts#L48-L89)

拦截也有责任边界：默认末端不执行，`fiber.config` 不会由它自动替换。插件必须自己处理新配置和必要的子任务。本文实验中的自定义监听器接收了 B，Fiber 的默认解析配置仍保留 A；不能看到 `internal/update` 发出就认为所有状态已经更新。

Loader 还会监听 `internal/plugin`，把 entry 关联和额外 inject 要求接到 Fiber 上。如果插件主动释放自己的 entry 根 Fiber，Loader 会把该 entry 标为 disabled 并请求写回；子插件卸载、整棵树退出、Loader 的禁用处理，以及先删 runtime 的 HMR 路径会被分别排除。这样，一次主动退出不会被误当成需要立刻再次启动的配置条目。本文实验确认：主动 dispose 后，声明仍在树中，disabled 变为 true。[entry 关联与自卸载](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/index.ts#L129-L166)

### `await` 写在哪里，含义差很多

以下是等待已存在 Fiber 更新的最小片段，省略 Context 和插件创建：

```ts
fiber.update(nextConfig, true) // 返回 undefined；不是清理完成的 Promise
await fiber.await()           // 等待当前 Fiber 生命周期稳定，并暴露它的错误
```

`EntryTree.await()` 则不断收集当前树里的 `_initTask` 或 `fiber.inertia`，用 `Promise.allSettled()` 等待，直到没有待处理任务。它能等树内活动稳定，但不会把每个插件的失败统一向上抛出；PENDING 也可以处于暂时没有任务的稳定状态。[树的等待](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/tree.ts#L35-L49)

等待也可以成为依赖可用性条件。Loader 的服务检查读取调用方对 loader 的拦截配置；启用 `await: true` 时，只要树里仍有待处理任务，它暂时不向该依赖方报告可用。entry 完成初始化和 Fiber 稳定后会通知服务检查。本文用一段尚未完成的异步 apply 核对了这条路径：consumer 先是 PENDING，放行后才 ACTIVE。它仍然是“当前任务是否排空”的条件，不代替应用级启动审查。[Loader 可用性检查](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/index.ts#L175-L178)

移除条目还有一层区别：`EntryGroup.remove()` 发起 `fiber.dispose()` 后立即把 entry 从 store 删除。此时，新的 `loader.await()` 可能已无法收集这个旧 Fiber。实验故意让清理停在受控 Promise 上，证明 Loader 的等待先返回；放行清理并等待事先保存的旧 Fiber 后，资源才真正释放。[移除实现](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/group.ts#L37-L45)

这也解释了 dsh 的 `reconcileProfilePatches()` 为什么在更新前保存旧 Fiber 列表：更新根 Include 后，先等待这些旧实例，再等待当前 Loader，最后比较新增或变化的激活失败。这样既等旧资源清理，也等新条目完成当前初始化，才能判断这次应用配置更新是否成功；单独等待其中一个通用 API 覆盖不了这些步骤。[profile 更新完成边界](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/app-boot/src/index.ts#L275-L305)

还有一个已实验核对的限制：给 ACTIVE entry 只改 `name`，不会在这个分支自动重新导入模块。`_init()` 位于没有活 Fiber 的初始化路径，`_patchContext()` 也不会因 `name` 变化就换 callback。需要替换代码时，应沿明确的卸载、重新创建或 HMR 路径处理，不能把原始 options 的变化等同于实现已经更换。

## volatile 为什么能绕过重启

插件初始化时注册的监听器，之后可能一直使用当时传入的 config 对象。如果运行时只给 `fiber.config` 赋一个新对象，监听器保存的旧对象并不会被替换。volatile 因而保留引用本身，让调用者每次用 `.get()` 取当前快照，也就是最近一次已提交的值。

下面是实验用插件的缩略片段，完整版本在下载包：

```ts
const Config = z.object({
  fixed: z.string().default('A'),
  live: z.string().default('one').volatile(),
})

function apply(ctx, config) {
  ctx.on('example/read', () => config.live.get())
}
```

Schemastery 为标记字段生成 Volatile 引用；cosmokit 则复制快照，并冻结它及其中的嵌套对象，防止读取方直接改掉当前值。`get()` 返回当前快照；运行时提交新快照时保留引用身份。支持普通对象和数组，不接受函数、循环结构或任意类实例。[引用与快照实现](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cosmokit/src/volatile.ts#L1-L86)

### 先比较原始配置，再验证运行结果

Loader 先检查原始配置是否只改了允许热更新的部分，再解析候选配置，确认求值和验证后的普通字段也没变。两次检查都通过，才能保留原插件。

就地更新至少要同时满足：只有 `config` 字段变化；Fiber 已是 ACTIVE；entry Context 的父级没变；按当前插件的 schema 比较后，普通原始值保持相同。`equalExceptVolatile()` 只利用 Schemastery 元数据做比较，不在比较时执行表达式、验证器或配置钩子。[快速路径条件](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/entry.ts#L141-L153)

它忽略固定对象路径上的 volatile 字段；普通对象节点可以按声明的对象默认值比较。数组结构、未知字段、包含子字段的父级表达式，以及 schema 再次引用自身形成的循环等情况，仍严格比较原始输入。没有 Schemastery schema 就不会猜哪些字段可热改。[原始比较器](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/diff.ts#L7-L45)

满足条件后，`_commitVolatile()` 再走完整 `internal/config` 和 schema，拿到候选运行值。如果候选的普通有效值也相同，才把变化的快照提交进原来的引用，收集字段路径，最后发出 `loader/volatile-update`。所有值先提交，再通知，事件只通知登记在这个 owner Fiber 上的监听器，不会广播给同插件的其他实例。顶层整体 volatile 配置用空路径 `[]` 表示，多个变化字段则是多个路径数组。[提交与通知](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/entry.ts#L164-L197)

第一次原始比较还不能代替第二次有效比较。例如普通字段保存相同的 `!!js` 节点，但节点读取的服务值已经改变；这次改 volatile 字段时重新求值，普通结果从 A 变成 B。Loader 会回退到普通更新。本文实验确实得到两次 apply，而不是强行保留旧插件。

### 无效值保留在哪一层

如果候选验证失败，Loader 记录警告，保留现有运行引用；新的原始 options 和 `_config` 已经保留。实验把字符串 volatile 字段改成数字 42，运行中仍读到 `one`，Fiber 仍 ACTIVE，但原始配置已是 42。之后重新激活时，这份原始输入仍可能导致验证失败。

因此，**就地更新失败并不自动回滚原始配置**。监听 `loader/volatile-update` 的回调若抛错，值也已经提交；Loader 记录错误，不撤销快照。需要“先校验再保存文件、失败恢复”的产品行为，应看 dsh 的 ConfigEditor：它在 HMR 队列内，先解析验证，再修改 patch 文件并调用 profile 协调，失败路径尝试恢复。不能从通用 Entry 更新直接推断出同样的事务保证。[ConfigEditor.edit](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/config-editor/src/index.ts#L87-L153)

这套引用在业务里也有明确使用方式。`AgentDefaultModelConfig` 把 provider、model、reasoningEffort 声明为 volatile，`currentSelection()` 每次读取 `.get()`。已经复制出的某次选择不会神奇变化；需要新值的操作重新读取引用。[默认模型配置](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-default-model/src/index.ts#L45-L80)

## isolate 改的是服务解析域

[第五篇](/articles/deepseek-harness-cordis-context-services/)已经解释了 Context 的服务可见性。Loader 的 `isolate` 把这种能力写进 entry 配置：Context 先把服务名映射成一个 Symbol，再按这个 Symbol 查找服务实现。不同条目可以把同一服务名映射到不同 Symbol；只有提供者和消费者使用同一个 Symbol，消费者才会取得那份服务。这里的一套映射范围叫服务解析域。

| 配置 | Symbol 的归属 | 典型结果 |
| --- | --- | --- |
| 没有为该服务配置 isolate | 继承父组的映射 | 使用父级可见服务 |
| `isolate: { cache: true }` | 该 entry 的 `LocalRealm` | 两个独立 entry 各有自己的 cache 域 |
| `isolate: { cache: 'blue' }` | 该 Loader 隔离钩子维护的命名 `GlobalRealm` | 同标签条目共享 cache 域 |

`true` 不是“所有隔离条目共用一份”。本文两个 entry 都设为 true，分别提供同名服务，实际得到不同 Symbol 和各自的 A、B 实现。另一个实验让 provider 和 consumer 都选 blue，consumer 可以激活，根 Context 看不到那份服务。[Realm 与标签选择](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/isolate.ts#L25-L89)

调整 entry 的父组或隔离配置时，`loader/patch-context` 先构造新映射，比较旧新 Symbol，更新 Context 的原型及 isolate/intercept 映射，再继续 Fiber 更新。实现还利用内部 delimiter 标志判断哪些已有服务实现应随条目迁移，并通知依赖这些服务的 Fiber 重新检查。失去引用的命名域会回收。因此，移动条目既可能改变服务提供在哪里，也可能让原来的消费者失去依赖或让新消费者取得依赖。[隔离迁移与通知](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/isolate.ts#L91-L172)

移动条目的实验也展示了这个效果：一个 consumer 原来在根组等待服务，移动到拥有 blue 域的 Group 后，继承新的映射并激活。这个结果只说明 Context 和依赖解析改变，不能据此推断 Fiber 的旧资源所有权已被任意重挂。

`intercept` 另外提供按 Context 作用的服务配置；`inject` 声明或补充服务依赖。它们不能互相代替。服务隔离也不会隔离文件系统、网络、进程或 JavaScript 全局对象；若需要这些权限限制，必须继续读对应运行边界。

## Include 怎样保留文件和子树

Include 将文件读取、patch 应用、子树更新和写回连接起来，但不是一个数据库事务。

读取时，YAML 走自定义 schema，JSON 走 `JSON.parse()`，其他支持的模块格式走导入；顶层必须是 entry 数组。文件只有解析并通过形状检查后，才提交新的 `content` 和 `data`。运行中 `refresh()` 读到无效或不可读内容，会记录警告，保留此前有效树；初次启动面对已存在的坏文件则直接失败，不会借 `initial` 覆盖它。[读取与启动](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/include/src/index.ts#L213-L263) · [运行中刷新](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/include/src/index.ts#L274-L287)

`applyEntryPatches()` 有 patch 时先复制 entry 列表，按树内 id 建索引。普通 patch 可用 name 检查目标是否仍是预期模块，字段覆盖按项赋值，`config` 并非自动深合并。`insert` 是 entry 数组；没有目标 id 就插入根，有 id 就插入对应 Group，并把新条目纳入索引，让后续 patch 能继续修改它。找不到目标或 name 不匹配时警告并跳过。[patch 语义](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/include/src/index.ts#L57-L140)

文件写回先合并同轮待写入状态，随后通过 `writeQueue` 串行执行：序列化到 `.tmp`，再 rename 替换目标。特定占用或权限错误会有限重试；停止 Include 时会 flush 待写任务。这样，读文件的一方较少看到只写了一半的内容；但源码没有在这里通过 fsync 保证数据已经同步到持久存储，不能据此保证掉电后仍能恢复。`loader.await()` 也没有把这个独立写队列纳入任务列表。[写队列](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/include/src/index.ts#L265-L340)

写回还有两个不同入口。通过 entry 修改原始配置，保留 `!!js` 节点后写回，可以继续得到表达式；直接 `fiber.update()` 默认会触发 Loader 保存钩子，保存的是解析后的配置，若 schema 有 `simplify` 则先调用它。本文同样的 `2 + 3` 输入，前一路保存 `!!js`，后一路保存数字 5。这不是序列化器随机丢了标签，而是进入保存钩子时对象已经不同。

## dsh 的热重载还要协调代码、配置和旧实例

HMR 是 Hot Module Replacement，指应用运行期间替换已加载模块。这个仓库有两个相关包：`vendor/hmr` 保留基础实现；dsh 的 base 组合实际配置的是 `@deepseek-ai/dsh-hmr`，位于 `packages/boot/hmr`。后者不能用前者的短流程代替。[base 配置](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/base/cordis.patch.yml#L24-L32)

base 条目在缺少 `profileContext` 时禁用，配置 `root: []` 表示不默认监听整棵源码目录。HMR 有 profile 上下文时仍会显式监听 profile manifest、profile patch 和 home patch；其他组合还可以继续禁用或覆盖这个条目。不能从“包存在”推断所有启动方式都已开启源码热重载。

### 配置刷新和模块替换共用一个队列

`runExclusive()` 把本次操作接在 `operations` Promise 后，等前一项结束再运行。它还用 AsyncLocalStorage 在后续异步调用中保留“当前已在事务中”的标记，拒绝从同一事务内部再次发起事务，避免排队等待自己。队列尾部会用 catch 处理前一项的失败，使后续操作仍能排队；关闭后拒绝新事务。profile 配置刷新还要等 `appReady`，避免启动尚未完成就重组配置。[串行协调](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/hmr/src/index.ts#L249-L350)

精确配置监听与普通模块监听是不同入口。`watchConfig()` 可处理新增、变化、删除及开始时还不存在的父目录；同一条路径重复注册会报错。它默认等待文件写入稳定后再刷新。刷新期间若又收到通知，就用 dirty 标志记下“还需要再刷一次”，当前刷新结束后补做。销毁时关闭 watcher 并等待尚未完成的刷新；如果正从当前事务里卸载自身，则避开等待自己结束而无法继续的死锁。[精确配置监听](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/hmr/src/watch-config.ts#L27-L103)

模块监听先对变化去重，并把短时间连续到来的通知合成一批（debounce），再放进同一队列。已由专门配置监听接管的路径会跳过；Include 文件变化走 `include.refresh()`；模块缓存中的文件进入替换分析；宿主入口依赖图中的文件请求 `loader.exit()`；其余未处理变化发出 `hmr/change`。HMR 本身不负责真的重启进程，`Loader.exit()` 基类是空钩子。[变化分流](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/hmr/src/index.ts#L354-L444)

### 模块名解析到哪里，旧实例实际来自哪里

HMR 需要 Node 的内部模块加载器，构造时拿不到就报错。Loader 按实际存在的 API 识别 v1/v2 形态，而非只看 Node 大版本；普通 Loader 没有内部接口时仍有正常 import 路径。这不构成对任意未来 Node 版本的兼容保证。[内部加载器适配](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/internal.ts#L104-L143)

分析变化时，HMR 遍历 ModuleJob 的依赖；ModuleJob 是 Node 为模块保留的加载任务记录。分析会跳过 `node:` 和 `node_modules`，找出受改动影响的插件入口。更细的一步是：已加载的 entry 用先前保存的 `moduleNamespace` 对象找到原 ModuleJob，而非重新按 name 解析。这里比较的是不是同一个导出对象，不只是模块名称是否相同。假设包的 exports 从 `old.js` 改成 `new.js`，当前仍运行的实例来自 old.js；HMR 必须先认出它原来对应哪个入口，不能被新的解析结果带到另一份代码。[命名空间定位](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/hmr/src/index.ts#L89-L134) · [入口与依赖分析](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/hmr/src/index.ts#L528-L585)

共享同一 runtime 的不同 entry 仍可能来自不同的模块命名空间。`ReloadModules` 为每个旧命名空间保存对应的新实现，并分别记录旧 Fiber 和对应配置。同一模块的重复 entry 也继续是多个实例。若某实例没有 entry 可帮助定位，却对应多个不同的新插件回调（replacement callback），代码无法判定该选谁，就会报歧义错误。[替换实现的对应关系](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/hmr/src/index.ts#L138-L204)

`package.json` 变化还会使 node_modules 外相关包的配置缓存失效。manifest 仅作为配置时不主动替换插件；作为 JSON 模块或宿主依赖时仍按相应路径处理。`package-manifest.ts` 封装 Node 包读取和解析缓存的适配。它不意味着更新已安装包版本就能免重启，也没有覆盖所有 Worker 和 TSX loader。[包缓存适配实现](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/hmr/src/package-manifest.ts) · [当前限制](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/hmr/README.zh.md)

### 成功和回滚分别保证到哪一步

正常替换的源码顺序是：

1. 备份并清除受影响的 ESM loadCache 和 CommonJS cache。
2. 保存旧 runtime 的 Fiber 列表；有对应 entry 时取它当前的原始配置。
3. 先重新导入所有要替换的入口。导入失败时恢复缓存，旧 runtime 尚未进入删除阶段。
4. 删除旧 runtime，并等待事先保存的旧 Fiber 完成清理。
5. 根据命名空间对应关系创建新 Fiber，恢复 entry 关联，等待新 Fiber 激活路径稳定。
6. 再等待 Loader，更新所有匹配 entry 的模块命名空间，发出 `hmr/reload`。

第 4 步确保删除 runtime 后继续等待尚未结束的清理；第 5 步也防止“调用注册成功”被当成“插件启动成功”。同样不能把稳定的 PENDING 自动读成 ACTIVE。[缓存、导入与实例替换](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/hmr/src/index.ts#L603-L729)

新实例激活失败时，HMR 恢复缓存，尝试删除已创建的替换 runtime，等待它们清理，再用旧实现与保存的配置重新注册。恢复过程也可能失败并记录警告；这不是把旧内存、网络连接和所有外部副作用倒带。初始化代码若在文件或外部系统产生了不可撤销的动作，HMR 无法仅靠换回模块替它撤销。

仓库的 `modules.spec.ts`、`coordination.spec.ts` 和 `reconciliation.spec.ts` 分别提供模块替换、队列与配置协调的测试材料；本文读过这些路径，但没有把本次 28 组 Loader 实验冒充成这些 HMR 测试已运行。[模块测试](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/hmr/tests/modules.spec.ts) · [协调测试](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/hmr/tests/coordination.spec.ts)

## 动态扩展仍要选择明确的挂载入口

配置编辑、安装包、替换模块和运行一段动态插件是不同动作，进入的生命周期入口也不同。Loader 提供 create/update/remove，并不自动替扩展完成安装、权限审查、客户端分发或产品层回滚。

例如 host 动态扩展的 `startHostHalf()` 没有直接把字符串交给 Loader。它接收沙箱产出的插件，在 `cordis-dynamic` 组 Fiber 下经 `guardedPlugin()` 注册子 Fiber，并等待当前初始化过程结束；启动失败就先释放再抛错。插件本身合法、但缺少 inject 声明的服务时，仍可停在 PENDING，由 `missingServices()` 报告缺失项。停止时则请求 Fiber dispose，并等待清理结束。[Host half 生命周期](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/extensions/cordis-host-runner/src/lifecycle.ts#L1-L57)

这个例子把本篇边界接回实际系统：Loader 树管理声明式条目；Fiber 管理实例资源；HMR 协调替换；动态 runner 决定自己如何挂载受控子插件。它们复用 Cordis 生命周期，但不必全走同一个 `loader.create()`。扩展包安装、guard 允许什么、浏览器端如何加载，将留到系列的扩展章节逐项核对。

## 用 28 组实验核对这些分支

[下载完整实验包](loader-config-examples.zip)。解压后，在实验目录执行以下命令。`DSH_SOURCE` 指向上述固定提交的干净源码副本；npm 只给实验目录安装 TypeScript `6.0.3`、js-yaml `4.1.1` 及其依赖，不在 dsh checkout 安装包。

```sh
npm ci --ignore-scripts --no-audit --no-fund
DSH_SOURCE=/path/to/deepseek-harness npm run verify
```

`run.mjs` 会验证提交与五个 vendor 源码目录的状态，将真实 cosmokit、Cordis、Schemastery、Loader 和 Include 转译进临时目录，再执行场景；完成或失败后移除临时目录。转译只检查语法诊断，不等于全仓库语义类型检查。

本次环境为 macOS `27.0.1 arm64`、Node `v25.9.0`、TypeScript `6.0.3`。28 组全部通过，核心观察如下；完整断言和生成每组输出的程序都在下载包中。

| 实验范围 | 已观察到的行为 |
| --- | --- |
| 表达式、Group 和 PENDING | 原始节点保留；普通字符串不插值；子配置等到子 Fiber 可以激活才求值 |
| 普通更新和自定义拦截 | 相同配置不重启；普通变化清理后再 apply；不调用 next 可以消费更新 |
| 完成边界 | `Fiber.update()` 返回 undefined；移除后仅等 Loader 不能覆盖已离树的旧 Fiber |
| volatile | 引用身份保留、先提交再通知、只通知 owner；混合变化或普通有效值变化则重启 |
| 无效候选 | 原始输入保留，运行引用维持旧值；不虚构原始配置回滚 |
| 服务隔离与移动 | 同标签共享服务域，true 各自独立；移动到合适的域后依赖可以满足 |
| Include 和 patches | 子树 id、坏文件保留旧树及恢复、原地分发 patch、插入后继续修改均符合断言 |
| 保存入口与模块名 | entry 更新保留表达式标签；Fiber 默认保存解析值；只改活 entry 的 name 不自动换实现 |

没有启动真实模型请求、文件监听或 HMR 缓存替换。HMR 的时间顺序来自源码；实验中的受控 Promise 用来暴露等待边界，没有用固定 sleep 猜测调度顺序。

要继续定位实现，可在固定提交的仓库根目录执行：

```sh
rg -n 'async update|_commitVolatile|private async _init' vendor/loader/src/config/entry.ts
rg -n 'interpolate|internal/update|internal/plugin' vendor/loader/src/index.ts
rg -n 'applyEntryPatches|async refresh|flushWrite' vendor/include/src/index.ts
rg -n 'runExclusive|watchConfig|partialReload|updateEntries' packages/boot/hmr/src/index.ts
rg -n 'previousFibers|reconcileProfilePatches' packages/boot/app-boot/src/index.ts
rg -n 'startHostHalf|missingServices' packages/extensions/cordis-host-runner/src/lifecycle.ts
```

当“配置已经改了”与“插件仍像旧版本”同时出现时，可以沿着本文的对象逐层检查：entry 保存了什么原始输入，Fiber 是否 ACTIVE、是否执行过解析，volatile 是否已提交，旧实例是否真正清理，HMR 是否定位到原命名空间。每个问题都对应一个可观察的对象或等待点。

下一篇进入 Agent 本身：追踪 `Agent`、`AgentHandle` 与实例所有权，解释应用怎样拿到一个 Agent，以及谁负责让它停止。
