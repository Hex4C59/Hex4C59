+++
title = "DeepSeek Harness 源码解析（五）：Context、Service 与依赖注入如何协作"
date = 2026-10-15
draft = false
author = "Hex4C59"
description = "沿 ctx.fs 追踪 DeepSeek Harness 的 Cordis 服务解析，解释 Context 代理、Service 注册、inject 激活条件、服务域隔离和调用方追踪，并区分 Cordis 服务域与 Agent 注册 scope。"
summary = "配置行存在，不代表插件已经执行；子 Context 存在，也不代表服务已经隔离。本文从一个等待 fs 的工具插件出发，追踪服务怎样注册、查找、驱动消费者加载，以及同名服务如何在不同域中共存。"
tags = ["DeepSeek Harness", "Cordis", "依赖注入"]
categories = ["ai"]
source_kind = "original"
series = ["DeepSeek Harness"]
series_order = 5
difficulty = "intermediate"
article_type = "concept"
topics = ["coding-agent", "plugin-architecture", "dependency-injection"]
frameworks = ["DeepSeek Harness", "Cordis"]
ShowToc = true
+++

[第四篇](/articles/deepseek-harness-application-entrypoints/)讲到，Loader 会等待配置树处理完毕，再由启动策略判断哪些失败会阻止应用运行。如果一个普通插件缺少依赖，它可以留在等待状态，其他已经成功的插件继续工作。

把这个情况代入文件工具：假设配置中已经加入 `tool-fs`，却没有可用的文件系统服务。配置行明明存在，为什么模型仍得不到 `read` 工具？程序为什么没有立即进入工具注册代码，然后在 `ctx.fs` 上报一个空值错误？

**Cordis 用服务依赖决定插件主体何时执行，用服务域标签决定同名能力从哪里取得。** `Context` 负责承载和解析这些关系，`Service` 提供一套注册服务的方式，`inject` 则让消费者跟随提供者的可用状态加载或卸载。理解这几层之后，才能判断“插件已经写进配置”离“能力已经可以使用”还差什么。

本文面向能阅读 TypeScript、了解 dsh 应用组合的开发者。主线是 `tool-fs` 与 `fs`；随后解释子 Context、服务隔离与 Agent scope。这里的 Context 是插件运行环境，不是提交给模型的上下文窗口。类型声明合并、事件分派和完整 effect 卸载算法分别留给后续文章。

分析继续使用固定 commit [`d743267388641bc76f17c45ce8b4c231aed1d32c`](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c)，核对日期为 2026-10-15。dsh 根包版本是 `0.2.1-alpha.2`，该快照的 [`@deepseek-ai/cordis` manifest](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/package.json)声明 `4.0.5-alpha.1`。[vendor 记录](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/README.md)另列上游来源为 `4.0.0-rc.7`，并记录本地修改。本文以快照中的实现为准，不把上游文档直接当作该版本行为。

本文进行了静态源码核对，没有启动 dsh、运行 Cordis 行为测试或发送模型请求。下文的缺失依赖和隔离案例均为按源码推演的条件，代码节选用于解释机制，不是独立可启动的应用。

## 从 `tool-fs` 的依赖声明开始

[`tool-fs/src/index.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/tool-fs/src/index.ts#L23)声明了四个必需服务：

```ts
export const inject = ['tools', 'fs', 'systemPrompt', 'workingDirectory']
```

这些名称分别对应工具注册、文件系统、系统提示词和工作目录能力。`apply()` 中才会调用 `applyReadTool()`、`applyWriteTool()`、`applyEditTool()` 等函数，将工具注册进运行时。

因此，缺少可用的 `fs` 时，等待发生在插件主体执行之前。不是 `read` 已经注册、直到模型调用时才发现无文件系统；在这个假设组合中，注册工具的主体尚未执行。`fs` 即使可用，其余三个依赖有一个不可用，主体也同样不能激活。

先用这组对象区分几件事：

| 对象 | 在这里负责什么 | 不能从它单独推断什么 |
|---|---|---|
| 模块导入 | 让程序取得插件代码、类型或工具函数 | 插件是否已挂载 |
| 配置行 | 声明 Loader 应加载什么及其选项 | 插件主体是否已成功执行 |
| Context | 提供插件可访问的服务与运行环境 | 所有名称都有可用实现 |
| 服务实现 | 例如满足 `fs` API 的具体提供者 | 所有消费者都能在自己的域里找到它 |
| Fiber | 管理一次插件挂载的状态与资源 | 模块只会在整个应用中挂载一次 |

一个插件模块可以有多个挂载实例。阅读时需要确认具体实例属于哪个 Context、声明了哪些依赖、当前处于什么状态，不能仅按模块路径判断运行结果。

## `new Context()` 创建的是代理与共享基础设施

[`Context` 构造函数](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/context.ts#L71)先创建服务隔离映射和 intercept 映射，再用 `ReflectService.handler` 建立代理，创建根 Fiber，并安装反射、插件注册、事件和日志等内置服务。

Context 上一些看起来很普通的方法，实际也是内置服务转发出来的：[`ReflectService` 构造函数](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/reflect.ts#L213)将 `get`、`provide` 等反射方法，`plugin`、`inject` 等注册方法，以及事件方法混入 `ctx`。

这解释了两种常见写法的关系：`ctx.plugin(...)` 转到插件注册服务，`ctx.get('fs')` 转到反射服务。`ctx.fs` 则通过 Context 的属性代理解析，走的检查与 `get()` 不完全相同。

### 插件挂载时，框架会给它一个自己的 Context

[`RegistryService.plugin()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/registry.ts#L316)解析插件入口，取得或建立模块的 runtime 记录，再创建一个新的 Fiber。runtime 记录描述共享的插件入口；Fiber 对应这一次具体挂载。

[`Fiber` 构造过程](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L236)使用 `parent.extend({ fiber: this })` 创建插件 Context。它继承父环境，但 `fiber` 指向本次挂载实例。服务注册、事件监听和 effect 因而可以知道资源由哪次插件挂载拥有。

相反，直接调用 `ctx.extend({ ... })` 只创建一个携带元数据的子 Context，不会顺便创建新的 Fiber。两者都能产生子 Context，却有不同的生命周期含义。

## `ctx.fs` 与 `ctx.get('fs')` 分别怎样读取

### 属性访问沿插件声明的依赖环境解析

[`ReflectService.handler.get`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/reflect.ts#L135)先处理 Context 上已有的普通属性和 accessor。对于服务属性，普通插件上下文会进入依赖读取检查。

这个检查从当前或关联的 Fiber 开始，先查看挂载期间保存的服务实现，再根据依赖声明与服务域继续判断是否可以沿父 Fiber 查找。如果遇到声明需要、但当前不可用的服务，会报告 inactive context；如果一路找不到合法读取路径，则报告 `without inject`。服务域改变时也不能随意跨过去找另一份实现。

所以，`ctx.fs` 并不是一次无条件的全局字典查询。插件通常通过 `inject` 声明必需服务，让框架在执行主体前准备依赖；祖先 Fiber 自己提供的服务，以及它已保存的依赖，也可能被子插件继承。若提供者和消费者只是兄弟插件，服务出现在共享存储中，并不会自动建立这条属性读取路径。不能把“此文件没有显式写 inject”一概判断为非法读取，还要看它挂载在哪个父环境中。

根 Context 有一个启动用的特例：它没有普通插件的 runtime，属性代理允许通过非严格模式取得服务。根环境中的临时调试读取，不能用来证明普通插件也拥有相同的读取权限与就绪条件。

### `get()` 绕过 inject 检查，默认只返回活跃提供者

[`get()` 与 `_getImpl()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/reflect.ts#L233)用当前 Context 对应名称的服务域标签查找实现。下面是 `_getImpl()` 的源码节选：

```ts
const key = this.ctx[symbols.isolate][name]
const impl = key && this.store[key]
if (!impl) return
if (strict && impl.fiber.state !== FiberState.ACTIVE) return
return impl
```

`ctx.get('fs')` 默认使用 `strict = true`，因此提供者还在加载、已经失败或正在卸载时，不会按活跃服务返回。调用方可以根据返回值决定是否提供可选功能。

这也不是完整的 inject 就绪检查：`get()` 不执行实现记录的可选 `check`，该判断在 Fiber 的 `_checkImpl()` 中进行。服务即使能被 `get()` 读到，也可能尚不满足依赖消费者的激活条件。

但一次 `get()` 不会自动把当前插件变成 `fs` 的依赖消费者。之后 `fs` 消失时，框架不会仅因这次读取就重载该插件；如果把返回值长期保存在闭包里，其后续有效性需要调用方自己处理。与此相对，`inject` 会把关系登记到 Fiber 中，用于后续变化通知。

| 写法或判断 | 直接表达的含义 |
|---|---|
| 插件中的 `ctx.fs` | 按当前挂载的服务依赖环境读取 |
| `ctx.get('fs')` | 在当前服务域探测活跃实现，绕过 inject 声明检查 |
| `ctx.get('fs', false)` | 允许读取尚未活跃提供者的值，不是常规就绪判断 |
| `'fs' in ctx` | Context 已知这个属性名称，不保证当前域已有可用实现 |
| TypeScript 接受 `ctx.fs` | 编译器知道字段类型，不证明运行时已注册或激活 |

`in` 的区别来自代理的 [`has` 分支](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/reflect.ts#L199)：服务名称一旦被声明，属性可以被认为存在，即使当前域没有对应实例。可选能力探测应检查可用服务，而不是仅检查名称。

## `Service` 怎样将一个实现放到名称下面

dsh 的 [`FileSystem`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/fs/src/index.ts#L87)继承 Cordis 的 `Service`，构造函数中调用：

```ts
constructor(ctx: Context) {
  super(ctx, 'fs')
}
```

[`Service` 构造函数](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/service.ts#L42)将服务实例与 Context、名称和调用追踪信息关联，再转到 `ctx.reflect.provide()`。具体文件系统实现继承这个入口，就能以 `fs` 提供能力；工具侧不需要直接导入那一份本地实现。

服务也可以由普通插件直接调用 `ctx.provide(name, value)` 提供，值不必是 `Service` 子类实例。`Service` 在具名注册之外提供了调用追踪、可调用服务与 intercept 配置等辅助机制，不能把它和一条字符串服务名当作同一个东西。

### 注册记录包含提供者，值本身还不代表就绪

[`provide()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/reflect.ts#L277)取得当前名称的服务域标签，建立包含 `name`、`value`、提供者 `fiber` 与可选可用性检查 `check` 的记录。记录进入共享反射存储，也进入提供者自己的 Fiber 存储。

同一服务域中已经有同名记录时，再次提供会抛错；框架不会默默选择“最后注册的一份”。换一个服务域可以放另一份同名能力，后文再解释。

注册动作由当前 Fiber 的 effect 管理。撤销时，框架移除共享存储中的记录，通知相关消费者并等待它们处理变化，然后清理提供者的本地记录。清理期间保留旧依赖供清理代码使用，和对新消费者公布服务是不同的时机。

`Service` 在构造时登记实例，也不等于消费者此刻就能运行。正常依赖检查还要求提供者的 Fiber 已经活跃；如果有自定义 `check`，还要通过这项可用性判断。异步初始化尚未完成时，单凭 JavaScript 对象已经创建，不能宣称服务已经准备好。

另一个实现细节是，依赖检查依据实现记录而非单纯判断 `value` 是否为真。[`_checkImpl()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L597)先取得活跃实现，再执行可选 `check`。没有额外检查时，记录的值为 `undefined` 也不等于记录已经撤销。服务提供方需要明确其 API 的就绪含义，消费方不能把 inject 理解成对任意返回值的校验。

### `set()` 受提供者所有权约束

[`set()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/reflect.ts#L254)要求当前域已经有实现，而且提供这条记录的 Fiber 就是当前 Fiber。消费者不能只因注入了 `fs`，便用 `ctx.set('fs', other)` 替换另一插件拥有的服务。

还要区分赋值与依赖变化通知：这份 `set()` 实现更新记录的 `value`，并没有自动调用 `notify()`。不能从“值已变更”推断所有消费者已经重新加载。常见的替换流程要通过提供者的生命周期与配置重载处理；不要随意调用内部通知方法来拼出未经验证的替换机制。

## `inject` 怎样让消费者等待、加载和重新等待

[`Inject.resolve()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/registry.ts#L71)将数组或对象声明转换成按名称索引的依赖映射。对象形式还可以携带对应服务的 intercept 配置。它不会因为 TypeScript 中某字段可选，就把列入声明的服务自动变成可选依赖。

Fiber 创建后，会为每项依赖调用 `_checkImpl()`，再执行 [`_refresh()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L611)。后者将当前依赖提供者的身份组成内部的加载代次标记；任意依赖缺失，就将这次挂载标记为 inactive。

以下按 `tool-fs` 缺少、随后取得 `fs` 的假设顺序推演。其他三个依赖均已可用，插件配置也有效：

1. 创建消费者 Fiber。`fs` 无可用实现，消费者保持 `PENDING`，主体 `apply()` 未执行。
2. 提供者完成加载，变为 `ACTIVE`。相关服务变化触发通知。
3. 消费者重新检查自己的四项依赖；都可用时进入 `LOADING`。
4. Fiber 解析插件配置，执行主体；成功后进入 `ACTIVE`，文件工具才被注册。
5. 若 `fs` 提供者失去活跃状态或撤销记录，消费者卸载自己的注册，回到等待依赖的状态。
6. 后续出现满足条件的提供者，消费者可以再次加载；若配置或主体抛错，则要按失败状态处理。

通知不是遍历所有插件后无差别重启。[`ReflectService.notify()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/reflect.ts#L314)只重新检查声明了相关依赖、且匹配服务域的 Fiber。一个私有域里的 `fs` 变化，不应仅因名称相同就让另一个域的消费者改用它。

[`_setEpoch()` 与 `_reload()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L625)负责将依赖组合变化转成卸载或重新加载。消费者可能经历短暂的 `UNLOADING`、`LOADING`，不能期待提供者变更后所有字段在同一同步语句中立即完成更新。

| 状态 | 对当前讨论最有用的含义 |
|---|---|
| `PENDING` | 正在等待依赖，插件主体尚不能运行 |
| `LOADING` | 配置解析或主体初始化正在处理 |
| `ACTIVE` | 这次挂载已经成功激活 |
| `FAILED` | 初始化或配置发生失败，要查具体原因 |
| `UNLOADING` | 正在释放本次挂载的资源 |
| `DISPOSED` | 这次挂载已被移除，不能当作可恢复的等待实例 |

表格只概括与依赖有关的稳定含义。完整 effect、异步清理、异常观察与父子 Fiber 结束顺序，留在后续生命周期文章中展开。

### `await ctx.plugin(...)` 不会无限等待缺失的服务

`plugin()` 返回的 Fiber 包装支持 `await`，但它调用的是 [`Fiber.await()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L704)：等待当前已有的生命周期工作结束，若记录了初始化错误就重新抛出，然后返回 Fiber。

缺少依赖的 Fiber 可以没有正在进行的生命周期工作，因此这次等待也可以结束，返回的状态仍为 `PENDING`。同理，Loader 等待当前树处理完毕，不代表每项服务都已经可用。

这正是第四篇启动审查仍然必要的原因。普通等待项可以被报告后继续留在树里；已启用的必需条目无法激活，则可能阻止应用启动。框架的等待机制和 dsh 的产品启动策略分工不同。

## 可选功能可以用 `get()` 探测，也可以挂一个小的依赖子插件

`get()` 适合在调用时判断某项能力是否存在，但如果需要“能力出现时注册、消失时撤销”，dsh 还使用 `ctx.inject()` 把这一小段工作独立管理。

`tool-fs` 的 [`read_image` 注册分支](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/tool-fs/src/index.ts#L71)就是例子：

```ts
ctx.inject(['attachments'], (imageCtx) => {
  applyReadImageTool(imageCtx)
})
```

[`RegistryService.inject()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/registry.ts#L300)把依赖声明和回调包装成一个普通插件，再调用 `plugin()`。这里没有另一套隐藏的等待器。

结果是：四项基础依赖齐全时，主工具插件可以注册文本读取和修改能力；缺少 `attachments` 时，只有这个子插件等待，图像读取工具不注册。以后附件服务出现或离开，子插件按依赖关系加载或卸载，主插件不必把全部工具都绑定到这项可选能力上。

因此，“可选”至少有两种组织方式：使用点临时探测，或者将依赖该能力的部分拆成受生命周期管理的子插件。选择取决于能力变化时是否需要增删注册，不能只看某个 TypeScript 字段有没有问号。

## 子 Context 为什么不会自动隔离服务

[`Context.extend()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/context.ts#L99)通过原型链建立子 Context，并把元数据定义为子对象自己的属性。没有另行改变服务域时，子 Context 仍继承同一套名称到标签的映射。

可以将服务解析中的两个索引概括成下面的关系。这里是算法示意，省略访问控制、活跃检查和代理包装，不是可独立调用的代码：

```text
label = context 的服务域映射[name]
implementation = root 的反射存储[label]
```

Context 看起来不同，只要 `fs` 对应的标签相同，就仍然选中同一条底层实现记录。不同服务域也仍可以共用同一个根反射存储；区分它们的是标签，而不是各复制一份整个应用。

[`Context.isolate('fs')`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/context.ts#L121)创建一个子 Context，只给 `fs` 换上新的标签。这个名字在该分支中的读取和提供，都使用新域；其他服务名称继续按原映射解析。

切换下面四种情况，重点观察 A、B 两个消费者的 `fs` 标签和提供者。图中的名称是解释机制的示意，不是 dsh 的默认配置快照。消费者只声明 `fs` 一项依赖，假设其他初始化均成功；状态是按源码推演的结果。

{{< interactive-diagram src="service-scopes.html" title="比较共享默认服务域、隔离后缺少实现、隔离后提供实现与相同 label 连通时的 fs 解析" height="1220" compact-height="1560" mobile-height="1640" >}}

### 新域中没有实现，就不会回退到默认域

假设默认域已经有一份 `fs`，然后创建 `branch = ctx.isolate('fs')`。在 branch 中挂载消费者，却不在这个新域提供 `fs`，消费者会等待；不会因为根环境中还有同名服务，就自动退回那一份。

这一点可以直接从 `_getImpl()` 的单次标签索引读出。隔离名称意味着选择另一个实现位置，不是给默认提供者叠加一层“优先尝试”。

如果在新域的提供者插件中注册第二份 `fs`，该分支消费者才可以使用它。全局默认域里的消费者仍使用原实现。两个同名提供者能够共存，是因为登记位置不同；同一域内重复提供仍会冲突。

### 相同 label 可以让不同分支接入同一服务域

`isolate(name, label)` 允许显式传入 Symbol 标签。对同一服务名，两处分支使用同一个 Symbol，可以接入相同的域。两个各自执行的 `Symbol('shared')` 虽然描述文本相同，仍是两个不同 Symbol；不能只按打印出来的名称判断它们共享。

Loader 的 YAML 选项还提供自己的映射方式：[`isolate` 配置处理](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/loader/src/config/isolate.ts#L71)将 `true` 对应到条目的局部 realm，将字符串 label 对应到共享的命名 realm。它最终仍为服务名分配 Symbol，但这与直接传给 `Context.isolate()` 的参数形式不同。

在 dsh 的 [standard preset](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/web-app/presets/standard.patch.yml#L45)中，planning 组使用 `isolate: { planMode: true }`，并在组内挂载对应提供者。这是真实的按服务名隔离组合；并不意味着组内代码已经获得操作系统级沙箱。服务解析与文件、进程权限仍是不同机制。

`intercept()` 也需要分开读：它为服务附加沿 Context 链合并的配置，合并逻辑在 [`Service[resolveConfig]`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/service.ts#L86)。它本身没有给服务换实现标签，不能用来代替 `isolate()`。

## 共享实现为什么还需要追踪调用方 Context

Service 构造时登记了 tracker 信息。读取服务时，[`getTraceable()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/utils.ts#L117)会对带 tracker 的对象建立追踪代理，使服务调用能够结合调用方的 Context 工作。

这对“一个共享注册服务，许多插件向它注册内容”尤其有用。若所有注册都只记在服务提供者的 Context 上，卸载某个消费插件时，就难以按该消费者的生命周期撤销它的贡献。

dsh 的 [`ToolsService.register()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/tools/src/index.ts#L1069)经过参数校验后，把 `this.ctx` 交给 `layers.effect()`。这份 Context 既参与注册的作用域选择，也参与 effect 所有权。追踪代理让共享服务的方法可以接上调用方，而不是把所有贡献无差别留在服务提供者身上。

具体的 [`createTraceable()` 与 shadow 方法](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/utils.ts#L165)还要同时处理提供方原有依赖与调用方环境，并不是简单修改原服务对象的 `ctx` 字段。直接把它概括成“服务全局单例，所以所有方法都只使用根 Context”会丢掉这一层。

由此还会影响调试：不同 Context 取得的服务可能是不同的代理外观，不能只用 `===` 判断它们是否采用同一底层实现。应沿服务域标签与提供者记录确认来源。

## Cordis 服务域与 dsh 的 Agent scope 是两种机制

dsh 的 [`ReactLoopAgent` 构造函数](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/agent.ts#L122)调用 `createScope(loopCtx, this)`，把得到的 Context 作为 `agent.ctx`。

但 [`createScope()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/scope/src/index.ts#L137)的关键动作是挂一个拥有生命周期的 scope 插件，再在它的 Context 上扩展一个身份标签：

```ts
const fiber = ctx.plugin(scope)
const scoped: Context = fiber.ctx.extend({ [kScope]: key })
```

它没有在这里对所有服务逐项执行 `isolate()`。这个身份供工具、提示词等按 scope 分层的注册表区分贡献，并配合事件路由与释放。

例如共享的工具服务内部使用 [`ScopedLayers`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/tools/src/index.ts#L834)，按调用 Context 的 scope 将工具贡献放进相应层。这可以让 Agent 看到自己的注册内容，而不必为每个 Agent 都复制整个 ToolsService。

| 机制 | 主要区分什么 |
|---|---|
| Cordis `isolate('fs')` | 同一个服务名选哪份实现 |
| 插件 Fiber 与其 Context | 哪次挂载拥有注册和清理工作 |
| dsh Agent scope | 共享注册表中的贡献与路由属于哪个 Agent 身份 |

这些机制可以组合，但没有一项单独等于独立进程或安全沙箱。后续读 preset、多 Agent 或工具权限时，应分别追踪服务提供者、注册层、事件对象和执行权限。

## 找不到服务时，按实现位置逐层检查

面对“配置里有工具，模型却看不到”，可以沿下面的顺序缩小范围：

1. 先确认模块对应的配置行确实进入树中，没有在 bundle 加载或配置禁用阶段被排除。
2. 找到消费者的 `inject`，检查全部依赖；不要只盯当前正在研究的 `fs`。
3. 确认提供者注册的名称与消费者一致，并查看提供者 Fiber 是否已活跃。
4. 比较两边该名称的服务域标签；隔离域缺失实现时不会自动采用默认域。
5. 区分 `PENDING`、`FAILED` 与已被 `DISPOSED` 的旧实例，再读加载或配置错误。
6. 如果服务可用、注册内容仍不对，再检查调用方 Context 与 dsh scope，而不是继续更换服务实现。

这是根据实现得到的阅读和排查顺序，不是本次真实故障的实验记录。源码仓库根目录可以用以下只读命令定位关键路径：

```sh
git rev-parse HEAD
rg -n 'export const inject|ctx.inject' packages/fs/tool-fs/src/index.ts
rg -n 'constructor|extend\(|isolate\(' vendor/cordis/src/context.ts
rg -n '_getImpl|provide\(|notify\(' vendor/cordis/src/reflect.ts
rg -n '_checkImpl|_refresh|_setEpoch|async await' vendor/cordis/src/fiber.ts
rg -n 'createScope|const scoped' packages/core/scope/src/index.ts
```

这些命令在本文基线执行，验证的是相关定义与调用位置。代码节选没有作为独立程序运行；服务激活与隔离案例的预期来自固定版本源码，没有扩大成整套 dsh 的运行或安全验证。

## 下一篇接着看类型声明与服务注册

到这里，`ctx.fs` 在运行时怎样被找到已经有了路径，但编辑器为何知道它的类型，仍是另一个问题。下一篇研究 Context 接口的声明合并、类型导入与运行时注册之间的对应关系，再看包边界怎样影响消费方取得类型信息。
