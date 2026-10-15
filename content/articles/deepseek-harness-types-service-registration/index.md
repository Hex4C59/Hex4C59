+++
title = "DeepSeek Harness 源码解析（六）：类型声明如何接上服务注册"
date = 2026-10-15
draft = false
author = "Hex4C59"
description = "沿 ctx.fs 追踪 DeepSeek Harness 的 Context 声明合并、类型导入、运行时注册与声明产物，结合可复现的 TypeScript 实验区分编译器看见字段和进程取得服务。"
summary = "import type {} 能让编译器认识 ctx.fs，却不会挂载文件系统服务；源文件中的类型入口，也不保证原样保留在发布声明中。本文从这两个差异出发，解释 Context、包边界与运行时实现怎样接在一起。"
tags = ["DeepSeek Harness", "Cordis", "TypeScript"]
categories = ["ai"]
source_kind = "original"
series = ["DeepSeek Harness"]
series_order = 6
difficulty = "intermediate"
article_type = "concept"
topics = ["coding-agent", "plugin-architecture", "type-system"]
frameworks = ["DeepSeek Harness", "Cordis", "TypeScript"]
ShowToc = true
+++

[第五篇](/articles/deepseek-harness-cordis-context-services/)解释了 `ctx.fs` 在运行时怎样沿依赖和服务域找到实现。现在换到编译器这一侧：Cordis 的 Context 类没有亲自声明每个 dsh 服务，编辑器为什么仍能补全 `ctx.fs`？文件工具里一行没有导入任何名字的 `import type {}`，又在做什么？

**声明合并让编译器认识字段，服务注册让具体运行环境取得实现。** 两条路径通过 `fs` 这个约定的名称接在一起，但并不互相代替。编译器接受 `ctx.fs`，不代表这次挂载已经取得文件系统；运行时有可用服务，也不代表某个独立 TypeScript 工程已经包含它的声明。

本文面向能阅读 TypeScript、已了解 Cordis 服务和 inject 的开发者。继续沿文件系统接口、工具消费方和本地提供方追踪，再看 Host/Client 的类型检查边界和包发布入口。这里的 Program 指 TypeScript 为一次检查加载的源文件、声明文件及其依赖集合，不是 dsh 的插件树。

源码基线仍是 [`d743267388641bc76f17c45ce8b4c231aed1d32c`](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c)，核对日期为 2026-10-15。[dsh 根包](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/package.json)版本为 `0.2.1-alpha.2`，快照中的 [Cordis manifest](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/package.json)为 `4.0.5-alpha.1`。[锁文件](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/pnpm-lock.yaml#L22670)将 TypeScript 固定到 `6.0.3`，本篇语言实验也使用这个版本。

dsh 部分是静态源码分析；文末另有实际执行的独立语言实验。实验不加载 Cordis，不模拟插件依赖、服务域或生命周期，也不构成 dsh 全量类型检查、运行测试或模型请求的证据。

## `fs` 字段来自接口包的声明合并

Cordis 在 [`context.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/context.ts#L16)同时导出了 `interface Context` 和同名的 `class Context`。前者描述可访问的类型形状，后者提供构造函数与运行实现；TypeScript 允许同名接口补充类的实例类型。Cordis 的[包入口](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/index.ts#L2)再将它们导出。

文件系统接口包没有修改 Cordis 源文件，而是在自己的 [`fs/src/index.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/fs/src/index.ts#L45)中扩展模块。下面只保留 Context 成员，省略同一块中的 Events 增强：

```ts
declare module '@deepseek-ai/cordis' {
  interface Context {
    fs: FileSystem
  }
}
```

它表达的是：**当这份声明进入当前 Program 时，Cordis 导出的 Context 类型具有一个 `FileSystem` 类型的 `fs` 字段。**

这份文件顶部已经有 import 和 export，本身就是模块。这里的 `declare module` 属于模块增强，也就是补充已经解析到的模块导出。单独复制几行到一个没有顶层 import/export 的脚本文件，不能直接假定仍有相同的解析含义。

这个动作不会给 `Context.prototype` 写入属性，不会创建 FileSystem 实例，也不会执行 `provide()`。它为类型检查提供信息；运行对象仍由第五篇追踪的代理、服务存储和 Fiber 管理。

同一处声明还扩展了 [`Events`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/fs/src/index.ts#L50)，登记 `fs/write-intent`、`fs/edit-intent` 和 `fs/observed` 的参数及返回类型。它们补充的是事件 API 的静态词汇，事件究竟按什么顺序执行，仍要看调度实现；下一篇再展开。

### 字段写成必需，不表示所有 Context 实例都已经有服务

这里声明的是 `fs: FileSystem`，没有问号。类型检查因此允许消费方直接写 `ctx.fs.readText(...)`，但这不是一份描述每个 Fiber 当前状态的证明。

在同一个 Program 中，多个 Context 实例可以采用同一份静态类型，其中一些运行环境有文件系统，另一些还没有。Context 的服务域标签、提供者是否活跃、当前插件有没有合法依赖读取路径，都不是这个字段声明编码进去的状态。

这份类型更适合描述插件在约定环境下如何使用能力。让插件主体等到必需服务可用，是运行时 `inject` 的职责。不能因为声明省略了问号，就跳过装配和激活检查。

## 没有导入名字的 `import type {}` 为什么有用

文件工具的 [`read.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/tool-fs/src/read.ts#L7)包含下面两个类型入口。这里省略了位于它们之间的其他导入：

```ts
import type { Context } from '@deepseek-ai/cordis'
import type {} from '@deepseek-ai/dsh-fs'
```

第一行取得 Context 类型。第二行没有给本文件增加一个可引用的名字，却让编译器解析文件系统包的类型入口，把其中的模块增强纳入当前 Program。这样，本文件便可以按文件系统接口使用 `ctx.fs`。

它不是 JavaScript 的副作用导入。`import type` 在 JavaScript 输出中会被擦除，因此这条语句不会要求运行进程为它求值文件系统模块，更不会安装本地文件系统提供者。

还有一个阅读源码时很容易误判的情况：删除第二行后，本地检查不一定立即报错。Program 中的其他文件、另一个类型导入或聚合入口，可能已经把同一份增强加载进来。声明的可见范围是当前 Program，并非“只对写了这行 import 的文件生效”。

显式类型入口让消费方表达自己依赖哪份类型信息。判断它能否独立编译，仍应检查实际文件集合与解析结果，不能依赖大型工作区恰好加载了许多其他声明。

### 看到包名，要继续追到实际类型入口

类型解析首先要找到目标模块。工作区内的 [`tsconfig.base.json`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/tsconfig.base.json)为 Cordis 和 dsh 包设置了指向源码的 `paths` 映射；包的 manifest 则另外声明发布入口。

因此，“编辑器里能跳转到源码”和“外部工程能从安装后的声明文件取得同样信息”，需要分别检查。模块增强作用于编译器实际解析到的模块与导出；不能只比较两段 import 的包名文本，就断定两个工程加载了同一份定义。

## 运行时从具体提供方进入 `provide()`

文件系统接口包还导出了 [`FileSystem`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/fs/src/index.ts#L87) 抽象类。它在构造时调用：

```ts
constructor(ctx: Context) {
  super(ctx, 'fs')
}
```

这是运行代码，和上面的模块增强承担不同工作。具体的 [`LocalFileSystem`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/fs-local/src/index.ts#L68)继承 FileSystem，其构造函数通过 `super(ctx)` 进入这个注册入口。

真实装配位置可以从 [sdk-minimal 的 patch](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/sdk-minimal/cordis.patch.yml#L38)看起。相关配置节选为：

```yaml
- id: filesystem
  name: '@deepseek-ai/dsh-fs-local'
```

Loader 加载相应插件后，Cordis 在执行这次 Fiber 时，对类入口进行[构造调用](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L251)。随后，FileSystem 构造函数转入 [`Service`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/service.ts#L42)，后者调用 `ctx.reflect.provide(name, self, check)`，由反射服务登记实现。

这条路径要区分三个阶段：取得模块导出、挂载插件、实际执行提供方的构造与初始化。导入一个类，不等于已经用某个 Context 构造它；配置行存在，也不等于它的 Fiber 已成功激活。

接口包与实现包也不是同一个包。`@deepseek-ai/dsh-fs` 给出能力接口和注册基类，`@deepseek-ai/dsh-fs-local` 提供本地实现。消费工具依赖接口包，不必在自己的文件里直接导入这一份后端。

| 位置 | 对应的约定 | 实际作用 |
|---|---|---|
| Context 模块增强 | `fs: FileSystem` | 描述字段的静态类型 |
| FileSystem 构造函数 | `super(ctx, 'fs')` | 以运行时名称注册当前实例 |
| tool-fs 的 inject | `'fs'` | 声明消费者激活所需的能力 |
| 具体提供方与配置 | LocalFileSystem、filesystem 条目 | 决定装配哪份实现 |

这些名称要保持对应，但对应关系并不是由一处声明自动生成的。源码审查需要把三条 `fs` 约定和实际装配位置一起核对。

## 把声明可见与实现可用分开观察

下面的图把两条路径并列。切换四种条件，观察静态字段检查和运行时消费者状态怎样分别变化。

图中的运行时假设消费者声明了 `inject: ['fs']`，其他初始化均成功；“实现可用”还包括同一服务域、提供者 ACTIVE 和可选检查通过。缺少声明时，图只讨论已有 JavaScript 进入运行时后的条件，不表示带类型错误的工程已经成功构建。它是源码关系推演，不是 dsh 运行采样。

{{< interactive-diagram src="types-and-runtime.html" title="比较 Context.fs 声明可见性与运行时 fs 实现可用性，两条路径分别决定静态检查和消费者激活" height="1300" compact-height="1560" mobile-height="1720" >}}

只有声明时，编辑器可以接受字段访问，消费者仍可能等待。只有实现时，运行环境可以满足服务需求，而缺少增强的独立 TypeScript Program 仍可能报告没有这个字段。

这四种组合可以帮助我们按失败发生的层次查问题：字段类型缺失时查类型入口，实现缺失时查装配、依赖和服务域。给类型问题补一行 import，不能当作运行故障已经修复。

## `get()` 的返回类型承认缺失，重载也保留宽松入口

第五篇解释过 `ctx.get('fs')` 可以绕过 inject 声明检查进行探测。它的[类型重载](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/reflect.ts#L17)也与直接属性不同：

```ts
get<K extends string & keyof this>(name: K, strict?: boolean): undefined | this[K]
get(name: string, strict?: boolean): any
```

在 FileSystem 增强已可见、参数保留为已知的 `'fs'` 字面量时，第一个重载给出 `FileSystem | undefined`。这使消费方有机会在可选能力路径中处理缺失。直接属性的 `FileSystem` 类型，并没有自动变成同样的探测 API。

第二个重载则允许类型表面之外的字符串名称，并返回 `any`。它是开放扩展的入口，也削弱了静态检查：一个拼错的服务名可能仍被接受，所得值不会继续受到具体接口的约束。

[`provide()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/reflect.ts#L44)也有类似的宽松重载。因此，不能把“有一个按 Context 字段关联值类型的重载”理解为“所有错误注册都会被编译器拒绝”。文末实验保留了这组重载的简化形状，验证错误值仍可匹配宽松入口。

这类类型提示有用，但不是封闭的注册证明。需要核对的运行条件仍包括：服务名是否正确、谁拥有实现、提供者是否就绪、消费者是否在同域，以及当前挂载是否具有合法读取路径。

## Program 边界为什么会影响 Host 与 Client

声明合并在当前 Program 中起作用。若把两个运行世界的声明无差别放进同一次检查，它们对同名字段的不同定义就可能相遇。

dsh 的[根 tsconfig](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/tsconfig.json)是 solution 文件：`files` 为空，通过 references 指向 Host 和 Client 两个检查单元。solution 用来组织多个项目，并不把所有源文件自动拼成一个共同的 Context 类型世界。

这项拆分在源码中有具体对应：

| 字段 | Host 声明 | Client 声明 |
|---|---|---|
| `Context.sessions` | [`SessionStore`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/session/src/index.ts#L39) | [`ISessions`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/api/session-controller/src/client/index.ts#L91) |

两边服务处在不同的运行边界，对同一字段给出了各自的接口。[Host 配置](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/tsconfig.host.json#L2)和 [Client 配置](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/tsconfig.client.json#L2)说明了避免同名 Context 增强在一个 Program 中相遇的原因。

这也区分了两种常被统称为“隔离”的事情：TypeScript 项目边界决定哪些声明一起检查，Cordis 服务域决定运行时哪个名称找到哪份实现。调整 tsconfig 不会给运行进程创建私有服务域，调用 `ctx.isolate()` 也不会替编译器拆开声明集合。

本篇没有运行 dsh 的 Host/Client 全量检查。文末的冲突用例只验证最小接口增强的语言行为；真实检查单元的范围，以本基线配置和各包 references 为准。

## 源码可见与发布声明可见，需要分别检查

### 工作区先通过源码与项目引用建立类型关系

基础配置使用 `moduleResolution: bundler`、严格检查、声明输出、相对导入扩展名重写等选项。文件系统包自己的 [`tsconfig.json`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/fs/tsconfig.json)将源码目录设为 `src`，输出目录设为 `lib/types`，并列出 Cordis 等项目引用。

项目引用负责组织编译依赖，`paths` 负责源码层的模块定位。它们和 pnpm 的包依赖声明、运行时插件装配分别工作，不能互相当作替代证据。比如 manifest 中列了 peer dependency，不等于消费者的 Program 必然已经导入了那份模块增强；列出文件系统接口依赖，也不等于安装并挂载了本地后端。

### 发布入口指向生成的声明与 JavaScript

[`@deepseek-ai/dsh-fs` manifest](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/fs/package.json)的根导出包含以下条件对象节选：

```json
{
  "types": "./lib/types/index.d.ts",
  "default": "./lib/index.js"
}
```

类型消费方和 JavaScript 加载方因而有各自的入口。配置中的源码路径能工作，还不足以证明这些发布文件已经生成、被收录，且在外部模块解析方式下可消费。

根 [`tsdown.config.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/tsdown.config.ts#L19)的普通 Host 构建读取已由 TypeScript 发出的 JavaScript，再生成包的 `lib` 输出；它关闭了自己的 dts 生成。这条构建路线不能概括成“打包器看到源文件，就顺便把所有声明正确发布了”。

本次没有执行 dsh 全量构建，也没有检查该快照的实际发布 tarball。这里核对的是源码、配置和 manifest 的连接关系。

### 类型导入甚至可能不保留在消费方的 `.d.ts` 中

还有一个需要直接观察产物的细节。最小实验的消费文件写了：

```ts
import type { Context } from './runtime.js'
import type {} from './fs-contract.js'

export function readThroughContext(ctx: Context): string {
  return ctx.fs.readText('hello.txt')
}
```

编译器在检查函数体时能看到增强。实际 JavaScript 输出中，两条类型导入都已经消失：

```js
export function readThroughContext(ctx) {
    return ctx.fs.readText('hello.txt');
}
```

本次 TypeScript 6.0.3 的声明输出则为：

```ts
import type { Context } from './runtime.js';
export declare function readThroughContext(ctx: Context): string;
```

函数的公开签名只需要 Context 与 string，输出没有保留 `fs-contract` 这条类型入口。模块增强仍存在于 `fs-contract.d.ts` 自己的文件中，但一个外部 Program 只加载上述消费函数声明和 Context 基础声明时，不会因此自动取得这份增强。

实验进一步编译了两个外部消费方：未引入 contract 的版本访问 `ctx.fs` 得到 `TS2339`，显式引入后通过。这里的结论是**需要核对最终声明依赖路径**，不是“所有类型导入都会从 `.d.ts` 消失”，也不是断言真实 dsh 包必然输出完全相同的内容。

dsh 还提供 [`verify-node-next-types.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/scripts/verify-node-next-types.ts#L1)：扫描声明中的相对扩展名，检查预期输出存在，再建立外部 NodeNext 消费工程检查公开入口。脚本启用了 `skipLibCheck`，其覆盖条件不能扩大成所有声明内部及 Host/Client 组合均已验证。本篇没有运行这个脚本；它要求先完成对应构建。

## 亲自验证：一个不加载 Cordis 的语言实验

[下载完整实验](types-registration-examples.zip)，解压后进入 `types-registration-lab` 目录。需要 Node.js 22 或以上；实验的开发依赖精确固定为 TypeScript 6.0.3，不依赖 dsh 工作区。

```sh
npm install --ignore-scripts
npm run verify
```

实验中的 Context 是一个空类，FileSystem 是仅含 `readText()` 的示意接口。`mountFs()` 用普通对象赋值给一个实例增加能力；它不是 Cordis 的 `provide()` 实现，不负责注入、隔离或资源清理。

脚本对以下条件分别检查，负例按预期诊断通过，不是把报错忽略掉：

| 检查 | 实际观察 |
|---|---|
| 当前 Program 包含模块增强 | 消费函数编译通过 |
| 当前 Program 没有该增强 | `ctx.fs` 报 `TS2339` |
| 同一字段被增强为不兼容类型 | 报 `TS2717` |
| 简化的 get/provide 重载 | 已知 get 可选；宽松入口接受 any 及不匹配的提供值 |
| 检查 JavaScript 与声明输出 | 类型导入从 JS 擦除；增强保留在自己的声明文件 |
| 另建外部声明消费 Program | 缺少 contract 时字段不可见，引入后通过 |
| 只导入提供方模块 | 挂载计数仍为 0，新实例的 `fs` 仍为 undefined |
| 只给实例 A 执行挂载函数 | A 可读取，B 仍缺少能力，直接读取抛 TypeError |

本次运行使用 Node `v25.9.0`、TypeScript `6.0.3`，8 组检查通过。编译输出创建在临时目录中，检查后清理；末行会报告检查数量和实际版本。完整入口是下载包中的 `verify.mjs`，各个 tsconfig 用显式文件列表控制 Program，避免反例意外加载旁边的增强文件。

这组实验回答的是语言行为。Cordis 会在依赖缺失时阻止消费者主体激活，还会检查服务域、所有权和生命周期；不能把实验里普通对象的 TypeError 直接写成真实 dsh 相同阶段的报错。

## 沿着失败所在的层次排查

遇到字段报错或服务缺失时，可以按下面顺序区分问题：

1. 编译器说没有 `fs`：先查当前 Program 是否包含对应增强、import 解析到哪里，以及使用的是源码还是发布声明。
2. 本地工作区通过、外部工程失败：查 manifest 的 types/exports、实际生成文件、声明里的导入路径及消费方解析模式。
3. 同名增强冲突：查是否把 Host 与 Client 或其他不同类型世界混进了一次检查，不先把冲突字段改成 any。
4. 类型检查通过、插件仍等待：回到运行时查提供方挂载、名称、活跃状态、全部 inject 依赖和服务域。
5. 某个 Context 能读、另一个不能读：分别查实例所属的 Fiber 和域；同一静态 Context 类型不代表同一运行环境。
6. 名称或提供值明显不对却未报类型错误：检查是否匹配了宽松重载，以及变量类型是否已经变成 any。

在 dsh 源码根目录，以下只读命令可以定位本篇主线：

```sh
git rev-parse HEAD
rg -n 'declare module|interface Context|fs:' packages/fs/fs/src/index.ts vendor/cordis/src/context.ts
rg -n 'import type|ctx.fs' packages/fs/tool-fs/src/read.ts
rg -n 'super\(ctx|reflect.provide' packages/fs/fs/src/index.ts packages/fs/fs-local/src/index.ts vendor/cordis/src/service.ts
rg -n 'lib/types|"types"|"exports"' packages/fs/fs/package.json packages/fs/fs/tsconfig.json
rg -n 'get<K|provide<K|get\(name: string|provide\(name: string' vendor/cordis/src/reflect.ts
```

这些命令已在本文固定版本执行，确认的是定义与连接位置。语言实验与 dsh 静态研究使用不同的验证范围，后续复查时也应保留这个区别。

## 下一篇继续追踪事件怎样执行

服务类型说明“可以调用什么”，服务注册说明“从哪里取得实现”。取得事件服务后，`emit`、`serial`、`parallel`、`bail` 和 `waterfall` 又会给同一组监听器带来不同的执行、返回值与异常处理方式。下一篇沿实际事件调用继续阅读这些调度差异。
