+++
title = "DeepSeek Harness 源码解析（三）：源码目录、包依赖与文档地图"
date = 2026-10-14T21:31:52+08:00
lastmod = 2026-10-17
draft = false
author = "Hex4C59"
description = "沿 read 工具寻找真正的文件读取实现，区分 DeepSeek Harness 的目录归属、包依赖与运行时服务关系，建立从文档、manifest、插件入口到具体实现的源码阅读路线。"
summary = "找到 tool-fs，还没有找到真正读磁盘的代码。本文沿 read → ctx.fs → 文件系统提供者追踪实现，解释目录、peer 依赖与插件装配分别说明什么，并给出可复核的源码检索方法。"
tags = ["DeepSeek Harness", "Cordis", "源码阅读"]
categories = ["ai"]
source_kind = "original"
series = ["DeepSeek Harness"]
series_order = 3
difficulty = "intermediate"
article_type = "concept"
topics = ["coding-agent", "plugin-architecture", "source-code-navigation"]
frameworks = ["DeepSeek Harness", "Cordis"]
ShowToc = true
+++

[第二篇](/articles/deepseek-harness-request-lifecycle/)沿一次请求走过模型、工具和会话记录。读到工具执行时，你会遇到这样的代码：`ctx.fs.readText(...)`。工具已经叫作 `read`，执行函数也找到了，可这里的 `fs` 究竟是谁？它直接读取本机文件，还是把请求交给另一种后端？

在 DeepSeek Harness 中，声明“能读文件”的接口、实际读文件的实现、模型调用的工具，以及选择这些插件的配置，可能分属不同文件。**找到一个调用点以后，需要继续追踪服务定义、提供者和装配关系**：先看接口允许做什么，再找实现它的对象，最后确认应用配置选择了谁。目录名和依赖图分别提供一部分线索。

本文以文件读取为主线，建立三张用途不同的地图：代码归属在哪里、包之间依赖什么、运行时调用哪个服务。读者需要能阅读 TypeScript 的导入、函数和类继承，知道 `package.json` 的基本作用；不必先启动 dsh。本文与前两篇均分析 [DeepSeek Harness `0.2.1-alpha.2`](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c)，本次核对日期为 2026-10-14。

## 先分清三张地图回答的问题

假设要调整 `read` 返回内容的格式。你可以从 `packages/fs/tool-fs/` 找到工具实现，但真正读取文件的能力由它取得的 `ctx.fs` 提供。`tool-fs` 需要文件系统服务，至于应用把哪一种实现装到这个位置，还要查看插件配置。

把这些关系分开，阅读路径就清楚了：

| 地图 | 回答的问题 | 文件读取的例子 | 它没有直接回答什么 |
|---|---|---|---|
| 目录归属 | 哪个代码范围负责这项能力 | `fs`、`fs-local`、`tool-fs` 同属 `packages/fs/` | 包是否互相依赖、应用加载了谁 |
| 包依赖 | 一个包需要哪些代码或共享接口 | `tool-fs` 与 `fs-local` 都声明 `dsh-fs` 为 peer 依赖，要求使用方提供兼容的共享包 | 服务实例如何装配、函数调用顺序 |
| 运行时服务关系 | 消费方使用什么服务，谁提供它 | `tool-fs` 通过 `ctx.fs` 使用已装配的文件系统 | 所有代码分支、实际执行结果 |

下面可以切换这三种视角。目录图只画文件系统家族的三个代表包；依赖图只保留它们与 `dsh-fs` 有关的两条 peer 依赖箭头；服务图则展示共享 base 配置所选择的文件系统提供者。它们分别依据[目录说明](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/README.md)、[工具 manifest](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/tool-fs/package.json)与[base patch](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/base/cordis.patch.yml#L506)。省略的关系不代表不存在。

{{< interactive-diagram src="source-map.html" title="切换目录归属、包依赖与服务装配，比较同一项文件系统能力的三种关系" height="840" mobile-height="1120" compact-height="1060" >}}

一次调用的顺序，需要另查执行函数和事件处理。包依赖图里出现 `a → b`，只能先按该图的定义理解；它没有说明每次操作都会调用 `b`，也没有证明某个提供者已被加载。

## 根目录先帮助你缩小搜索范围

dsh 使用单仓库管理多个包。[`pnpm-workspace.yaml`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/pnpm-workspace.yaml)将 `vendor/*`、`packages/*/*`、`apps/*`、原生包和部分构建、文档项目纳入同一工作区。目录承担的职责不同，阅读时可以先用当前问题选择入口。

| 范围 | 在固定版本中负责什么 | 什么时候进入这里 |
|---|---|---|
| `apps/` | CLI、Web、Desktop 等应用入口与产品装配 | 找启动入口、界面行为和应用配置 |
| `packages/` | 按能力家族组织的 Harness 包 | 找服务、工具、状态与实现 |
| `vendor/` | 源码随仓库保存的 Cordis 及其基础库 | 追踪框架的服务、事件和加载机制 |
| `docs/` | 架构、子系统、开发与扩展文档 | 建立边界，再定位源码 |
| `scripts/` | 构建、生成、检查等仓库自动化 | 解释生成物和验证规则的来源 |
| `native/` | 原生源码与平台包 | 追踪相关系统能力和发布边界 |
| `python/` | Python SDK 与携带 dsh 的运行时 | 追踪 Python 调用、协议与运行时选择 |
| `benchmarks/`、`website/` | 性能检查材料与文档站点 | 检查基准方法或文档呈现方式 |

这是一张选入口的表，不是整个目录树。具体包表以 [`packages/README.md`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/README.md)及各家族 README 为准，避免在文章里维护一份很快过期的完整清单。

两个容易跳错的入口值得先说明。

`vendor/` 中的 Cordis 是项目保存的源码副本。它的 [manifest 和本地修改记录](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/README.md)列出了上游来源与修改。遇到服务访问或加载行为的问题，先读本仓库版本，才能知道应用使用了什么实现。

Python SDK 在这里通过标准输入输出上的 JSON-RPC 驱动配套 dsh 运行时；JSON-RPC 是以 JSON 消息表达远程调用的协议。[Python 目录说明](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/python/README.md)给出了客户端与运行时的分工。如果你要研究 Agent 的执行循环，仍需继续进入共享 Harness 代码。

## 一个能力家族里，包名分别表示什么角色

文件系统家族的 [README](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/README.md)先给出角色，再列包名。理解三个角色以后，才能判断该读哪一层。

**服务定义**描述使用者能够调用哪些方法。在 `packages/fs/fs/` 中，`FileSystem` 定义文件系统能力，并以 `fs` 这个键注册为 Cordis 服务。应用装入具体实现后，工具就可以通过 `ctx.fs` 取得该服务，不必在调用处固定某个本地实现。

**服务提供者**实现接口。`packages/fs/fs-local/` 中的 `LocalFileSystem` 处理本机文件；`packages/fs/fs-sandbox/` 中的 `SandboxedFileSystem` 在它的基础上加入写入范围等策略。不同实现的行为和限制，要分别查看代码。

**消费方**使用服务完成自己的工作。`packages/fs/tool-fs/` 注册模型可见的 `read`、`write`、`edit` 等工具，负责参数、读取窗口和结果格式；真正的文件访问交给 `ctx.fs`。

这三个角色是[能力边界文档](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/docs/architecture.md#capability-seams)中的组织方式。原文称可替换的能力边界为 *seam*，你可以把它理解为消费方与具体实现之间约定好的接口。一个包也可能承担多个角色，不能只看命名猜完整关系。

此外，家族里还可以有独立策略插件。`fs-observation-policy` 通过 `fs/*` 事件记录已读状态并约束修改；工具没有把它声明为必需服务。家族 README 明确说明，移除这个策略会改变修改行为，工具仍可使用提供者。这意味着检查实际行为时，除了接口与实现，还要确认哪些策略参与了装配。

## 沿着 `read` 找到真正读取文件的代码

现在把问题缩小为：固定版本中，一次普通文本读取，从工具进入哪个文件系统实现？

### 工具入口声明依赖并注册能力

[`tool-fs/src/index.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/tool-fs/src/index.ts#L23)声明了所需服务。以下是一行源码节选，需要在插件环境中使用，不能独立运行：

```ts
export const inject = ['tools', 'fs', 'systemPrompt', 'workingDirectory']
```

`apply()` 验证读取限制等配置，然后调用各工具的注册函数。`read` 的主体位于 [`src/read.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/tool-fs/src/read.ts#L77)，经 `ctx.tools.register()` 注册名称、参数和执行函数。

这里可以区分两条线索：导入告诉你代码引用了什么；`inject` 告诉你插件激活时需要哪些服务。它们解释的是不同层次的依赖，不能把 `package.json` 中的每个 peer 名称都直接翻译成这份注入列表。

### 执行函数决定怎样调用接口

`execute()` 先解析参数，再交给 [`resolveRegularReadTarget()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/tool-fs/src/read-target.ts#L19)解析路径并检查目标是不是普通文件。这个辅助函数使用 `ctx.fs.resolve()` 和 `ctx.fs.stat()`，也会处理目标不存在的情况。

随后，读取方式由文件大小信息决定。以下节选保留了该分支，需要上下文中的变量与服务，不能独立运行：

```ts
const chunks = info.size === undefined || info.size >= caps.streamMinSize
  ? await ctx.fs.streamText(target, exec.signal)
  : [await ctx.fs.readText(target, exec.signal)]
```

大小未知或达到阈值时，工具按片段读取；否则一次读取全文。工具接着从读取内容中选出本次要返回的行，添加行号并限制返回大小，这就是“读取窗口”，随后返回结构化结果，并发出 `fs/observed`。[源码中的读取分支](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/tool-fs/src/read.ts#L137)说明：如果问题是“返回的行号或截断格式不对”，应继续读窗口与渲染代码；如果问题是“读到了哪个路径、底层怎样取内容”，应继续查文件系统服务。

### 服务定义给出契约，提供者落实读取

[`FileSystem`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/fs/src/index.ts#L87)继承 Cordis 的 `Service`，构造时使用 `super(ctx, 'fs')`。它定义了接口和共同词汇。

在 [`LocalFileSystem`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/fs-local/src/index.ts#L175)中，`readText()` 转给 `readWholeText()`，`streamText()` 转给 `streamWholeText()`。若还要查这些方法怎样从本机文件取得数据，就继续进入同目录的 [`fsio.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/fs-local/src/fsio.ts)。

到这里，我们已经找到了本地读取实现，但还没有确认某个应用装配的 `ctx.fs` 就是它。接口能由谁实现，与这次应用选择了谁，需要分别检查。

### 共享 base 选择的是带策略的提供者

[`packages/bundle/base/cordis.patch.yml`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/base/cordis.patch.yml#L506)包含 `fs-sandbox` 配置项，加载 `@deepseek-ai/dsh-fs-sandbox`。[对应类](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/fs-sandbox/src/index.ts#L55)继承 `LocalFileSystem`，本篇的文本读取方法沿用父类实现；写入和编辑则有自己的策略处理。

因此，在这个未被后续 patch 替换的装配片段中，消费方取得的服务来自带策略的提供者，读取代码仍可沿继承关系追到 `fs-local`。要说明实际启动配置，还必须继续检查 profile 的 bundle 顺序与覆盖层。

[架构文档](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/docs/architecture.md#profiles-and-bundles)说明，profile 是一份有名字的应用组合配置；bundle 提供一组插件配置及配套代码，用户还可以用 patch 修改组合结果。因此，后加载的配置可能改变前面选择的服务提供者。它还指出 `sdk-minimal` 使用独立组合，并不应用共享 base。本文选取 base 解释追踪方法，不能据此宣称所有 dsh 应用都加载相同的文件系统提供者。

## `package.json` 和依赖图应该怎样读

文件读取的例子已经说明了服务关系。现在回头看包的描述文件 manifest，就能解释它为什么没有直接告诉我们完整调用路径。

### 三种依赖字段有不同用途

[`tool-fs/package.json`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/tool-fs/package.json)的 `peerDependencies` 包含 `@deepseek-ai/dsh-fs`、`dsh-tools` 等包，而 `dsh-fs-local` 出现在 `devDependencies` 中。这里没有一条 `tool-fs` 对 `fs-local` 的生产依赖把工具固定到本机实现。

`dependencies` 记录普通运行依赖，例如工具用来格式化差异的库；`devDependencies` 记录开发或测试所需依赖。peer 依赖通常表示需要由使用方提供兼容包；在 dsh 的[包约定](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/README.md#dependencies)里，它还承担了共享服务接口的组织含义：扩展依赖服务定义，具体提供者由装配选择。

一个字段仍不能解释所有运行条件。某项 peer 依赖可能用于类型或可选能力，插件也可能在代码里进行条件注册。例如 `tool-fs` 的 `read_image` 还要等待附件服务。判断能力何时可用，需同时读 manifest、插件入口和相关服务访问。

### 官方 module graph 只画了 peer 边

[`docs/module-graph.md`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/docs/module-graph.md)开头给出了精确口径：它展示 Harness 包之间的共享实例 peer 依赖，普通运行依赖与仅用于开发的关系没有画入。`a → b` 表示包 `a` 把包 `b` 声明为 peer。

生成器的[包收集代码](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/scripts/package-graph.ts#L35)读取 `packages/*/*/package.json`，取出 `peerDependencies`，再筛选 `@deepseek-ai/dsh-` 前缀。这也解释了为什么图里没有把整个 `vendor/` 和所有外部库展开。

所以它适合寻找共享接口和潜在影响范围。改了 `dsh-fs` 的契约，可以沿反向关系查看有哪些包声明依赖它；至于具体哪些路径受影响，还要逐个检查消费代码。若要计算安装或打包所需的完整依赖集合，必须考虑其他字段和发布入口，这张图的口径不足以回答。

服务相关的另一份图是 [`docs/capability-seams.md`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/docs/capability-seams.md)。它组织服务定义、已知实现与直接消费方，适合从 `ctx.fs` 这样的键反查角色。要确认某次启动的具体实例，仍需回到装配配置。

## 文档地图按当前问题选择入口

源码和文档应该互相校对。dsh 的包 README 往往包含用途、配置、源码地图、模型可见行为和限制；子系统文档则把多个包共享的契约集中解释。读文档时，先找它负责回答哪一类问题。

| 你要确认什么 | 优先入口 | 读完后继续检查 |
|---|---|---|
| 项目怎样组合，运行系统如何分工 | [架构文档](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/docs/architecture.md) | 配置与插件入口 |
| 服务、事件、插件如何工作 | [Cordis primer](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/docs/cordis-primer.md) | 本仓库 `vendor/cordis/` 实现 |
| 一个家族包含哪些角色 | `packages/<家族>/README.md` | 相关包 README |
| 某个包支持哪些参数、输出和扩展位置 | 该包 README 与 `src/` | 对应函数及相关测试 |
| 多包共享什么协议或状态规则 | `docs/subsystems/` | 定义方与各个消费方 |
| 包之间共享哪些接口 | `docs/module-graph.md` | manifest 与调用点 |
| 谁定义、实现和使用某服务 | `docs/capability-seams.md` | profile、bundle 与 patch |
| 怎样准备环境、构建与验证 | [开发指南](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/docs/development.md) | 当前脚本和检查入口 |

比如“编辑前为何必须先读取文件”，应进入[文件系统子系统文档](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/docs/subsystems/filesystem.md)和观察策略；“读取结果为什么截断”则先查工具的配置与窗口构造。两者同属文件系统家族，负责行为的代码范围却不同。

文档还会链接设计记录、故障复盘和内部维护说明。这些材料能解释某项决策当时的约束；当前行为仍以固定版本的契约和实现为依据。测试文件可以帮助发现失败条件，但读过断言只说明知道它检查什么，不能报告为运行通过。

## 用只读检索复核这条路线

下面的命令从 dsh 仓库根目录执行，只读取源码，不安装依赖，不构建、不启动应用。需要 Git 和 ripgrep（命令名为 `rg`）；本次已在固定基线上执行。

先确认版本并列出代表包文件：

```sh
git rev-parse HEAD
rg --files packages/fs/fs packages/fs/fs-local packages/fs/tool-fs
```

版本应对应 `d743267388641bc76f17c45ce8b4c231aed1d32c`。文件列表中能找到各包 manifest、README 和 `src/`；此命令用于定位，文件数量不作为稳定结论。

再从消费方追到服务定义与实现：

```sh
rg -n 'export const inject|ctx\.fs\.(readText|streamText)' \
  packages/fs/tool-fs/src/index.ts packages/fs/tool-fs/src/read.ts

rg -n 'class FileSystem|class LocalFileSystem|readText\(|streamText\(' \
  packages/fs/fs/src/index.ts packages/fs/fs-local/src/index.ts

rg -n 'class SandboxedFileSystem|fs-sandbox' \
  packages/fs/fs-sandbox/src/index.ts packages/bundle/base/cordis.patch.yml
```

第一组会找到工具需要的服务和文本读取调用；第二组定位接口、提供者与读取方法；第三组定位继承关系和 base 中的提供者配置。它们串起的是源码定位路线，没有触发一次实际文件读取。

最后确认包关系与图的生成口径：

```sh
rg -n '"peerDependencies"|"devDependencies"|"@deepseek-ai/dsh-fs"|"@deepseek-ai/dsh-fs-local"' \
  packages/fs/tool-fs/package.json packages/fs/fs-local/package.json

rg -n 'peerDependencies|startsWith' scripts/package-graph.ts
```

如果检索没有结果，先核对版本、文件位置与正则，不要直接判定能力被删除。若要进一步执行测试或启动应用，还需按当前开发文档准备环境；本篇没有做这部分验证。

## 带着一个问题继续读

现在，你已经可以从 `read` 找到工具参数与窗口处理，沿 `ctx.fs` 找到接口和本地实现，再用 base 配置解释提供者的选择。换一个问题时，也可以沿同一方法查角色和装配，只把具体入口替换成目标能力。

下一篇将专门研究 CLI、Web、Desktop 与 SDK 的入口和组合关系：应用怎样选择 profile，bundle 层如何叠加，后续 patch 又怎样改变插件树。本篇到这里保留一个明确条件：源码里存在某个提供者，还不足以说明某次启动使用了它。

本次分析以 [DeepSeek Harness `0.2.1-alpha.2`](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c) 的源码与文档为依据，完成只读检索和引用核对。没有运行 dsh、真实模型请求或项目行为测试，也没有验证跨平台隔离效果；上面的读取过程是静态分析，不是运行轨迹。

## 延伸阅读

- [第一篇：从代码补全到仓库级 Agent](/agent/deepseek-harness-agent-engineering/)：理解 Harness 要组织哪些职责。
- [第二篇：一次用户请求如何经过整个 dsh 系统](/articles/deepseek-harness-request-lifecycle/)：把本篇的入口放回执行链路。
- [DeepSeek Harness 系列总览](/series/deepseek-harness/)：查看后续主题与阅读顺序。
- [固定版本的文件系统工具 README](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/fs/tool-fs/README.md)：继续查参数、输出、失败条件和源码地图。
