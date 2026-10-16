+++
title = "DeepSeek Harness 源码解析（十一）：Preset、Persona 与默认模型怎样生效"
date = 2026-10-16
draft = false
author = "Hex4C59"
description = "从真实 Preset 注册表、Persona 和 Session Controller 追踪能力组合、修订保留、空白会话切换及模型选择，解释提示词和请求怎样使用同一次模型快照。"
tags = ["DeepSeek Harness", "Agent Preset", "模型选择"]
categories = ["ai"]
source_kind = "original"
series = ["DeepSeek Harness"]
series_order = 11
difficulty = "advanced"
article_type = "concept"
topics = ["coding-agent", "configuration", "model-selection"]
frameworks = ["DeepSeek Harness", "Cordis"]
ShowToc = true
+++

把一个会话从 `standard` 切到 `minimal`，工具和系统提示词会跟着变化，模型却可以继续使用刚才选中的那一个。反过来，把部署默认模型从 A 改成 B，已经发出过请求的会话也可能继续使用 A。

这两种结果都来自 dsh 对状态的分工：Preset 管能力组合，Persona 提供身份提示词，模型选择由另一条会话状态链决定。[第十篇](/articles/deepseek-harness-agent-handle-ownership/)讲过 Agent 怎样经过 setup、公告和销毁；这一篇继续看 setup 装进了什么，以及下一次模型请求从哪里取得选择。

本文面向已了解 Context、Scope 和 Agent 生命周期的开发者，基于 **DeepSeek Harness `0.2.1-alpha.2`**，核对日期为 **2026-10-16**。版本号取自[项目 manifest](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/package.json)，源码固定在该链接对应的提交。文末附 30 组真实运行时实验；其中的 `route-a`、`model-a` 等名称是合成数据，没有向模型服务发请求。

## 先分清三种“默认”

| 配置或状态 | 决定什么 | 何时读取 |
|---|---|---|
| Preset Registry 的 `default`、`selectedDefault` | 没有指定 Preset 时采用哪个能力组合 | 解析或挂载一个 Preset 时 |
| SystemPrompt 的部署 Persona、Preset 内的 Persona | 系统提示词中的身份段落和相关组装策略 | 按当前 Agent 的 Scope 组装提示词时 |
| AgentDefaultModel 的 provider、model、reasoningEffort | 没有会话选择和历史请求可沿用时采用哪个模型 | 入口读取默认选择时 |
| Session 的 `model/selection`、`request/header` | 本会话接下来选择什么、此前实际用了什么 | Session Controller 读取选择及重放投影时 |

这张表有一个前提：**入口要安装对应的组合逻辑。** `AgentRegistry.create()` 的核心合同是创建实例、调用 setup 和发布 handle；它不会因为系统存在 `agentPresets`、`agentDefaultModel` 服务，就替所有调用方自动选择一套策略。[核心创建合同](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L56-L118)

API Session 入口在 `composeAgent()` 中显式解析 Preset，并返回一个 setup：先给新 Agent 安装会话模型选择，再把它挂到对应 Preset 修订。没有 Preset 服务时，入口仍安装模型选择。本文的创建实验直接运行了这个真实入口辅助类，再把 setup 交给真实 AgentLoop。[入口组合](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/api/session-controller/src/agent.ts#L377-L398)

## Preset 会提前挂载一棵插件树

一个 Preset 声明包含 `id`、可选显示信息、排序值和 `plugins` 列表。`agent-preset` 插件把声明交给 Registry；它本身不接管使用旧修订的 Agent。这个插件还声明了 `EntryGroup.key`，让子配置保留原始表达式，等各子插件真正激活时再求值。[声明插件](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset/src/index.ts#L1-L30) · [定义与结构校验](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/definition.ts#L1-L39)

下面是按仓库配置删节的结构示意，省略工具列表和部署前提，不能单独当成完整启动配置：

```yaml
- id: preset-example
  name: '@deepseek-ai/dsh-agent-preset'
  config:
    id: example
    plugins:
      - id: persona
        name: '@deepseek-ai/dsh-persona'
        config:
          prefix: You are a helpful software engineer assistant.
      # 这里继续声明这个 Preset 需要的工具及其他组合插件。
```

仓库的 Web bundle 通过多个 patch 文件声明 `standard`、`ptc`、`minimal`、`cordis`，Registry 的部署默认值为 `standard`。这里的名字是这个版本随 Web bundle 提供的声明，其他入口可以组合不同集合。[Web 默认声明](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/web-app/cordis.patch.yml#L568-L577) · [bundle patch 列表](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/web-app/package.json#L41-L53) · [standard 配置](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/web-app/presets/standard.patch.yml#L1-L24)

Registry 的选择顺序是 `显式 id ?? selectedDefault.get() ?? default`。其中 selectedDefault 是可更新的用户默认值，default 来自部署。它们都只选出要找的 id；找不到或组合损坏时仍按对应错误处理，不会偷偷退回另一个健康 Preset。显式空字符串也不会触发 `??` 的回退。本文实验核对了部署默认、用户默认和显式选择分别生效。[默认选择与 Schema](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L53-L76)

注册会立即创建一个 Registry 所有的 Scope，在里面挂载插件树。它不是等每个 Agent 到来时再复制安装一遍：同一修订的工具、提示词和其他作用域贡献，可以被多个 Agent 的 Scope 继承。本文实验创建三个真实 Agent，两个加入同一修订，第三个加入另一 Preset；它们看到各自的工具，根作用域的工具列表仍为空。[修订激活](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L78-L124)

### 挂载成功还要经过审计

PresetTree 复用 Loader 的条目机制，但 `write()` 是空实现：这棵运行时树自身不负责把声明写进配置文件。树的创建也会恢复声明方 entry 原有的 subtree/subgroup，避免夺走外层 Loader 的结构身份。[运行时树](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/mount.ts#L1-L27)

挂载会检查启用条目的导入、激活和缺失依赖。失败的声明保留在 roster 中，带 `broken` 诊断，其他健康 Preset 可以继续使用。`resolve()` 返回这份诊断，真正要保留并挂载修订的 `retain()` 才以 `agent-preset/invalid` 拒绝；不能把“查到了 id”理解成“组合已可用”。未知 id 则是 `agent-preset/not-found`。[诊断与列表](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L126-L211) · [保留前的检查](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L232-L249)

缺服务的 PENDING 条目需要再判断。挂载先允许它留下；后续诊断等待 Host Loader 树稳定，再重新审计。若服务只是尚未激活，条目会自行变为可用。实验先观察到 `waiting for exampleLateService`，提供该服务后再次解析，同一声明恢复正常。因此，不要在 Host 条目自己的激活过程中等待这类完整诊断，否则可能等到自己。[条目审计](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/mount.ts#L112-L146) · [重新诊断](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L126-L148)

Preset 内注册服务还要显式使用合适的 `isolate` 服务域。否则提供者可能写入根域，让本来属于一套组合的服务影响其他会话。挂载检查这种根域泄漏，并拒绝有问题的声明；实验分别核对了直接提供服务的拒绝与隔离组的成功。`serviceFor()` 可以按 Agent 实际加入的修订查找其中的服务。[泄漏检测](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/mount.ts#L46-L110) · [挂载提交](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/mount.ts#L198-L216)

这些都是同进程插件的组合检查。`isolate` 管服务解析域，Scope 管贡献可见性；这里没有进程、文件系统或网络沙箱。检查到某次挂载合法，也不能推出任意插件未来的所有副作用都已得到隔离。

## 同一个 Preset id，可以同时存在两个修订

Registry 给每次成功激活创建独立的 `Generation`，记录 Scope、挂载结果、使用者数量 `users` 和 `retired` 标记。Agent 加入时，把自身 Scope 的父链连接到这代 Scope，同时登记退出时释放引用的 effect。这个可见性父链，与上一章的 `parentAgent`、调用方 Fiber 所有权各有用途。[Generation 与 Binding](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L31-L51) · [绑定与引用计数](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L251-L291) · [Scope 父链](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/scope/src/index.ts#L40-L89)

撤下一个声明时，Registry 先从当前声明表删除它，再把旧修订标为 retired。只有 **retired 且 users 为零**，才释放它的 Scope。于是可以重新注册同名 `standard`：之后创建的 Agent 加入新修订，已经加入旧修订的 Agent 保留原来的工具和提示词。[撤下与回收](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L85-L101) · [回收条件](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L150-L159)

下面从“旧 Agent A 及子 Scope C 仍保留 G1，新 Agent B 已加入 G2”的时点开始。切换退出步骤，观察声明列表和实际存活修订为何不同。G1/G2 是本文用于区分两代对象的标记。

{{< interactive-diagram src="preset-revisions.html" title="同名 Preset 的两代修订与引用计数：旧 Agent 和子 Scope 保留 G1，新 Agent 加入 G2，最后一个使用者退出后才能回收" height="1480" compact-height="1260" mobile-height="1520" >}}

`composeFrom(childCtx, parentCtx)` 继承的是父作用域实际加入的那一代。即使当前声明表里的同名 Preset 已经换成 G2，子 Scope 仍可加入 G1；它不重新用 id 查询“最新版”。本文实验让 A 退出后，C 继续保留 G1，直到 C 退出才观察到旧修订被回收。[继承确切修订](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L293-L319)

这里的共享也值得保留在脑中：同一修订里的插件可能被多个 Agent 使用。需要每 Agent 独立状态的插件，应根据作用域和 Agent 身份管理状态，不能仅凭“我挂在 Preset 里”就把插件自身的普通字段当成每会话私有字段。保留一个挂载修订，也不会冻结插件的所有内部状态和外部依赖；本文替换实验撤下并重新登记的是整份声明，插件内部的动态更新仍要按各自合同判断。

除了 Agent，`acquireScope()` 返回的只读租约也会持有一份引用。冷会话展示等读取结束后必须释放租约；实验确认，声明撤下后租约仍保留修订，重复调用它的异步释放只扣除一次。`inspectCompositions()` 可以查看所有保留修订，传 Agent Context 则只查看它加入的那代。[读取租约](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L364-L380) · [实际修订检查](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L160-L172)

### 管理界面读到的是哪份信息

`list()` 返回当前声明，包括 broken 项；先按 order 排序，未填 order 的放后面，再按 id 排序。远程 roster 另外标记哪个 id 是默认值。`readDocument()` 输出声明中的插件列表 YAML，并保留 `!!js`；它用于阅读声明，没有把运行后的所有动态注册反向合成为原配置。[列表与文档读取](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L174-L230)

这与查看“所有保留修订”不同。声明表里只有新 standard，旧 Agent 仍保留旧 standard，是两个接口分别描述当前声明与实际使用者的结果。显示名字也有独立规则：内置 id 且没有自定义 name 时走内置翻译；提供了 name 的声明保留作者文案，不能只凭 id 就把自定义名字替换掉。[显示信息解析](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/display.ts#L38-L73)

## 空白会话切换 Preset，必须留下日志

Preset 可以在会话仍为空白时切换。公开的 `select()` 按 Agent id 串行排队，再读取 `turnBoundary` 投影；如果已有打开的 Turn，或 `lastTurn > 0`，就以 `agent-preset/locked` 拒绝。因此，“现在 Agent 是 idle”不等于“会话从未开始”。[选择与锁定](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L340-L362)

一次成功选择先重绑定 Scope，再追加 `agent-preset/selected`。Session 的创建 header 保持最初的 Preset，当前组合由 `agentPreset` 投影从 header 加后续选择事件恢复。否则，用户空白时切到了 minimal，重新读取历史却仍按创建时的 standard 组合，工具和提示词就会与会话实际经历不一致。[选择日志与投影](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/session.ts#L1-L44)

本文实验观察到的三份状态是：

```text
创建 header.agentPreset  = standard
当前 agentPreset 投影   = minimal
当前可见工具             = minimal 的工具
```

底层 `recompose()` 只做重绑定和工具变化通知，空白检查由调用方负责，也不替调用方追加这条选择日志。实验在已打开 Turn 的 Agent 上直接调用它，确实能改变组合而不改变投影。这说明开发者应使用带完整政策的入口，不能把低层方法当作等价的用户操作。[低层重绑定合同](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/agent-preset-registry/src/index.ts#L326-L338)

按 id 排队也只说明多次 select 的处理顺序。源码先重绑定、后 append，没有把任意插件副作用、并发工作启动与所有持久化失败包装成一个数据库事务；本文实验没有把它扩大为这类保证。

## Persona 如何覆盖部署身份

SystemPrompt 全局注册了两个具名段落：`deployment:persona-prefix` 和 `deployment:persona-suffix`。Preset 内的 Persona 在自身 Scope 下注册同名段落。组装时，近处 Scope 中同名贡献覆盖远处及全局贡献，再按顺序排列。[Persona 注册](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/persona/src/index.ts#L60-L75) · [按 Scope 合并](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/system-prompt/src/index.ts#L610-L629)

Persona 的配置不多，但每项都会改变组装结果：

| 字段 | 默认与作用 | 容易遗漏的条件 |
|---|---|---|
| `prefix` | 必填，身份前缀模板 | 空串仍占据同名位置，渲染时再丢弃空段落 |
| `suffix` | 默认空串，排在内置指导段落之后 | 省略也会覆盖掉部署 suffix，不会自动沿用它 |
| `complete` | 默认 false | true 时 prefix 成为唯一系统提示词段落 |
| `includeRuntimeContext` | 默认 true | false 抑制可省略的动态 Context，required Context 仍保留 |

[配置字段](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/preset/persona/src/index.ts#L30-L54)

“空文本”与“不注册这个贡献”会得到不同结果。空文本先遮住部署身份，最后被 `renderPrompt()` 丢弃；卸载这份 Persona 后，部署身份才重新可见。Persona 若挂在全局，会与 SystemPrompt 已有的同名全局注册冲突并失败。本文实验分别检查了空文本、恢复与全局冲突。[空段落渲染](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/system-prompt/src/index.ts#L277-L290)

### complete 不会删除工具

`complete: true` 约束系统提示词段落。SystemPrompt 在 waterfall 变换后，仍把有效的 complete 段落恢复为唯一 section；工具目录和动态 Context 是 assembly 中另外的字段。出现多个有效 complete 段落会报错。[完整提示词的组装](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/system-prompt/src/index.ts#L648-L683)

实验同时安装工具、普通指导、complete Persona 和两个 Context，再设置 `includeRuntimeContext: false`。结果为：系统提示词只有 Persona prefix；工具仍在；可选 Context 被移除，required Context 保留。这里没有推导出“所有运行时信息都已消失”。仓库 minimal Preset 同时设置 complete 与禁用可选运行时 Context，仍继续声明自己的终端等工具。[minimal 配置](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/web-app/presets/minimal.patch.yml#L1-L30)

`includeRuntimeContext: true` 表示这份 Persona 不增加抑制项；如果部署或外层 Scope 已经抑制可选 Context，它不会把那些贡献强行打开。组装检查的是全局和 Scope 父链中是否存在抑制项。[抑制项的合并](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/system-prompt/src/index.ts#L610-L615)

### 模板变量严格解析

Persona 模板里的完整 `{{name}}` 会在渲染时解析。合法名字匹配 `[a-z][a-z0-9_]*`；未注册名字、当前值为 undefined、带点号等非法完整引用都会报错。孤立的 `{{` 没有后续闭合时按普通文字保留，替换后的值不会再次扫描。[变量规则](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/system-prompt/src/index.ts#L191-L195) · [插值实现](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/system-prompt/src/index.ts#L336-L375)

因此，`{{model}}` 能否渲染，取决于这次 assembly 是否真正提供了 model 变量。配置里写了花括号，并不会自动发起服务查询或从任意 JavaScript 对象读取属性。

## 默认模型服务只管理默认选择

`AgentDefaultModelConfig` 把 provider、model、reasoningEffort 都声明为 volatile 引用。`currentSelection()` 每次读这些引用，返回一个独立对象；省略 reasoningEffort 时，返回值也省略该字段。本文用真实 Loader 更新配置，核对 provider/model 的变化和 reasoningEffort 的清除。[默认模型服务](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-default-model/src/index.ts#L22-L72)

`saveSelection()` 是另一个操作。它要找到服务所属的配置 entry 和 ConfigEditor，才能提交完整配置；缺少其中任一项就返回，并不直接改写内存里的默认值。连续保存进入同一个 Promise 队列，按提交顺序执行；某次写入失败会拒绝该调用，但不会堵住后续保存。[保存队列](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-default-model/src/index.ts#L74-L94)

实验先在没有 ConfigEditor 时保存，默认值保持原样；另用受控编辑接口卡住并拒绝第一次保存，确认第二次等待后继续执行，且使用提交当时捕获的字段。它验证的是队列和接口行为，没有验证文件落盘、权限或崩溃恢复。

API 的模型切换操作还会先校验并解析请求的 provider/model，再记录会话选择，随后尝试保存为部署默认值。保存失败只记录警告，会话选择已发生的变化保留。因此，排查“这次选择生效了，重开后默认值没保存”时，要分别检查两条结果。[模型命令处理](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/api/session-controller/src/commands.ts#L153-L177)

## 本会话下一次用什么模型

API Session Controller 给每个 Agent 安装一份模型选择引用。初始化时先读取 `modelSelection` 投影中的 pending；之后每次读 `current`，按下面的顺序取得结果：

1. 有已选择、尚未被对应请求消费的值，使用它。
2. 否则，有日志中的最近 `request/header`，沿用那次实际请求的 provider/model。
3. 前两者都没有，读取当前部署默认值。

[会话选择读取](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/api/session-controller/src/agent.ts#L279-L325)

这解释了开头的情况：尚无请求历史、也没有会话选择的 Agent 可以随默认值变化；有请求历史的会话沿用历史路由。本文同时创建两个真实 Agent，一个保留空白，一个追加受控请求头，再更新默认配置，实际观察到前者读到新默认，后者继续读旧模型。

`selectForNextRequest()` 先追加 `model/selection`，再更新执行缓存。投影区分 `lastUsed` 和 `pending`：前者是已记录请求的模型，后者是待消费的选择。请求头只有与 pending 的 provider、model、reasoningEffort 全部相同，才把 pending 清掉；另一条路由的请求不能消费它。会话事件监听器还会同步清理内存中的匹配选择。[选择日志与缓存](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/api/session-controller/src/agent.ts#L328-L352) · [选择投影](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/api/session-controller/src/model-selection-projection.ts#L29-L80) · [请求消费监听](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/api/session-controller/src/index.ts#L192-L204)

reasoningEffort 还有一处细节：恢复历史请求选择时，如果请求头标记这个 effort 来自 adapter 默认值，就不把它恢复成会话主动选择。否则，provider 自动给出的默认 effort 会被固化成用户意图，下一次组装的含义就变了。[历史 effort 的处理](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/api/session-controller/src/agent.ts#L294-L311)

这套顺序属于 API Session 的策略。直接给 AgentLoop 配置 provider/model，或从另一个 SDK、Headless 入口创建 Agent，仍应检查该入口安装了什么选择逻辑。不能把这张优先级表当成 LLM adapter 内部所有配置的总覆盖规则。

## 提示词和请求必须使用同一份选择

如果提示词刚写着“你正在使用模型 A”，请求发出前 UI 又选择了 B，应该把当前请求发给谁？dsh 的 `installModelSelection()` 在组装开始时捕获 `selection.current`，等待后续组装完成，再把这个捕获值存入 `selection.assembled`，并覆盖本次 assembly 的 provider/model 变量。[组装快照](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/model-selection.ts#L81-L96)

后面的 `agent/request` 监听器使用 assembled，而不是再读可能已经变化的 current。它在其他请求配置处理完成后覆盖 provider/model，并先删除继承来的 reasoningEffort；只有捕获值显式包含 effort 时才重新加入。这样，“改选模型但省略 effort”可以回到新模型的默认行为，同时保留 temperature 等其他请求字段。[请求覆盖](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/model-selection.ts#L97-L116)

下面对照“组装后改选 B”和“组装前已经选择 B”。观察 current、assembled、提示词变量和请求配置分别在哪一步变化；A/B 都是实验中的合成路由。

{{< interactive-diagram src="model-selection-snapshot.html" title="模型选择的六步时序：提示词组装捕获 current，当前请求读取 assembled，后来的改选在下一次组装生效" height="1840" compact-height="1930" mobile-height="2250" >}}

30 组实验中的快照案例按真实入口执行：先组装 A 的提示词，再把 current 改成 B，然后运行 Agent 的真实 request waterfall。结果是本次提示词变量与请求配置都为 A；下一次组装变成 B。实验直接调用这些真实机制，没有把合成配置送到网络 adapter。

模型路由改变时，`agent/pre-step` 还可能向下一次获准请求追加用户角色的模型变化说明。它比较 assembled 与最近请求头的 provider/model；初次请求、仅 effort 改变、被拒绝或中止的步骤、某些没有请求的空步骤都不追加。请求头尚未成功记录前失败，下次仍可能重新加入说明。这些条件保护的是会话对模型变化的可解释记录。[模型变化说明](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/model-selection.ts#L39-L59) · [pre-step 条件](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/model-selection.ts#L117-L132)

## 配置里的 id 还要与会话身份分开

AgentLoop 的 `agents[]` 配置可以在插件启动时创建 Agent。这里的 `id` 是稳定配置标签，也用作未指定 sessionId 时的新会话 id 前缀。显式 `sessionId` 提供固定身份；挂载持久化后端时，已有物化历史就走恢复，没有历史才创建。`resumeSessionId` 则直接要求恢复，两种精确身份不能同时声明，同一批配置也不能重复占用同一个精确身份。[配置身份与校验](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L303-L339) · [启动分支](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L389-L428)

launcher 还可以通过 `configuredAgentIdentities` 提供会话身份，并替换对应配置里的 sessionId/resumeSessionId。这样，改写模型路由的配置层不会顺带丢掉 launcher 指定的会话身份。这部分是本次静态源码核对，没有把它列入 30 组运行实验。[launcher 身份覆盖](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L272-L301)

Preset 的 id 命名能力组合，AgentLoop 配置 id 命名启动条目，SessionId 命名一次会话身份。读配置时，把这三个名字分别标出来，再检查入口将它们传到哪里，会比从相同字符串猜关系可靠。

## 用 30 组实验复现这些差异

[下载完整实验包](preset-persona-model-examples.zip)，解压后运行：

```sh
npm ci --ignore-scripts --no-audit --no-fund
DSH_SOURCE=/path/to/deepseek-harness npm run verify
```

源码 checkout 需要对应本文固定版本与提交。`run.mjs` 会检查提交和可达包的状态，扫描静态运行 import/export，将真实源码转译到独立临时目录。结束或失败后清理自己的产物，不向 dsh checkout 安装依赖。

本次实际环境为 macOS `27.0.1 arm64`、Node `v25.9.0`。运行闭包包含 **35 个工作区包、144 个模块**；外部运行依赖固定为 zod `4.4.3`、js-yaml `4.3.2`、semver `7.8.5`、resolve.exports `2.0.3`，转译器为 TypeScript `6.0.3`，校验值保存在随包 lock 中。

| 范围 | 实际观察 |
|---|---|
| Preset 声明与挂载 | 默认与显式选择、同修订共享、错误诊断、PENDING 恢复、禁用条目、服务隔离 |
| 修订与切换 | 旧修订保留、子 Scope 继承、租约释放、空白选择入日志、Turn 锁定、队列失败后继续 |
| Persona | Scope 覆盖、空文本与恢复、全局冲突、严格变量、complete 与工具/Context 的分工 |
| 默认模型 | volatile 更新、独立返回对象、缺编辑器时不保存、保存顺序与拒绝后的继续 |
| 会话模型选择 | 默认与历史路由、pending 投影、匹配消费、adapter 默认 effort、组装快照、变化说明 |
| 入口边界 | 切 Preset 保留会话模型；直接核心创建不会自动组合 Preset |

所有涉及 Agent 的主线都运行真实 AgentLoop、Session 和相关投影；工具是合成贡献，配置编辑接口是受控适配器。没有调用真实模型、执行实际工具任务、运行完整 Web/IPC 产品链路，或验证配置文件与日志后端的磁盘持久性。转译只检查语法，不代表全仓库语义类型检查。

继续定位源码，可以在固定版本仓库根目录运行：

```sh
rg -n 'register\(|retain\(|collect\(|composeFrom|async select' packages/preset/agent-preset-registry/src/index.ts
rg -n 'auditRows|leakedServices|mountPreset' packages/preset/agent-preset-registry/src/mount.ts
rg -n 'complete|includeRuntimeContext|PERSONA_' packages/preset/persona/src/index.ts
rg -n 'currentSelection|saveSelection|volatile' packages/core/agent-default-model/src/index.ts
rg -n 'selectionFor|composeAgent|selectForNextRequest|consumeSelection' packages/api/session-controller/src/agent.ts
rg -n 'selection.current|selection.assembled|agent/request|agent/pre-step' packages/core/agent/src/model-selection.ts
```

下一篇进入 Turn、Step、Inbox 与执行状态转换，沿一次输入怎样唤醒 Agent、怎样在 Step 边界继续或停止往下读。到那里，Preset 提供的工具与提示词、会话选择捕获的模型，才会一起进入实际执行循环。
