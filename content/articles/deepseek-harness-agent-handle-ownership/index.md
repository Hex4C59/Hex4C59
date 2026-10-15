+++
title = "DeepSeek Harness 源码解析（十）：Agent、AgentHandle 与实例所有权"
date = 2026-10-15
draft = false
author = "Hex4C59"
description = "从 AgentRegistry 追到真实 AgentLoop，解释 Agent 与销毁 handle 的区别、未发布 setup、创建公告、调用方与工厂所有权，以及取消、回滚和持久化句柄的清理边界。"
summary = "取得一个 Agent，不代表取得了销毁它的 handle。本文用真实运行时实验，区分调用方 Fiber、parentAgent 和 parentSession，再追踪创建、发布、回滚与共享清理。"
tags = ["DeepSeek Harness", "Agent", "资源管理"]
categories = ["ai"]
source_kind = "original"
series = ["DeepSeek Harness"]
series_order = 10
difficulty = "advanced"
article_type = "concept"
topics = ["coding-agent", "agent-lifecycle", "resource-ownership"]
frameworks = ["DeepSeek Harness", "Cordis"]
ShowToc = true
+++

用 `ctx.agents.get(id)` 取得 Agent，和用 `ctx.agents.create()` 创建 Agent，返回的东西不一样。

前者给出一个正在运行的对象，调用者可以提交输入、取消工作、等待当前活动结束；后者返回 `AgentHandle`，额外带有 `dispose()`，让创建方能结束这次实例的生命周期。AgentLoop 自己也是资源所有者：提供工厂的插件卸载时，它必须收回曾经创建的实例。

[第九篇](/articles/deepseek-harness-loader-config-hmr/)讲过配置怎样改变插件实例。这篇继续进入 Agent 层，面向已经认识 Context、Fiber 和 effect、希望读懂 dsh 创建与清理代码的开发者。这里先讲实例怎样建立、何时可见、谁负责销毁；Turn、Step 和模型请求循环留给后面的文章。

本文固定源码 **`d743267388641bc76f17c45ce8b4c231aed1d32c`**，核对日期 **2026-10-15**，Agent 与 AgentLoop 包版本均为 `0.2.1-alpha.2`。文末 36 组实验运行了真实 AgentRegistry、AgentLoop、Session 等实现；没有调用模型，也没有执行真实磁盘持久化或跨进程协议。[Agent manifest](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/package.json) · [AgentLoop manifest](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/package.json)

## 先分清四个对象

| 对象 | 负责什么 | 不能从它推断什么 |
| --- | --- | --- |
| `Agent` | 对外提供实例身份、输入、取消和活动等待等能力 | 不能仅凭拿到对象，就推断自己持有创建方的销毁 handle |
| `AgentHandle` | 包含 `agent` 和结束这次生命周期的 `dispose()` | 调用成功不表示持久化历史被删除 |
| `AgentRegistry` | 保存活实例、工厂入口与运行时 owner 关系 | 它不是具体的模型执行循环 |
| `AgentLoop` | 构造驱动器、组织 setup 与发布、管理清理 | 工厂挂载成功不表示某个 Agent 已创建或模型已返回 |

`Agent` 的基础类型在 `types.ts` 中只声明 id，运行时类型文件再合并 `ctx`、`session`、`options`、`inbox`、`status` 和操作方法。这与[第六篇的类型声明合并](/articles/deepseek-harness-types-service-registration/)是同一种组织方式。具体实现类叫 `ReactLoopAgent`；不要把接口名当成一个可直接 `new Agent()` 的构造器。[基础接口](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/types.ts#L14-L18) · [运行时接口](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/runtime-types.ts#L163-L242)

`AgentHandle` 的公开形状很小，下面是对应接口的节选：

```ts
interface AgentHandle {
  agent: Agent
  dispose(): Promise<void>
}
```

Registry 的 `get()` 返回裸 Agent，`create()`、`resume()` 才返回 handle。这里说的“所有权能力”是 API 的责任划分：可信的同进程组合代码仍可能拿到 Context 或 Fiber，不能把这个接口差异当成隔离不可信代码的安全沙箱。[Handle 合同](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L146-L163) · [查询与创建](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L382-L415)

## 谁拥有资源，不能只看 parentAgent

先看最容易写错的地方。一个子实例可以同时涉及三种关系：

- **调用方 Fiber**：从哪个 Context 调用工厂，生命周期 effect 就登记到哪个 owner。这决定该调用方退出时会收回哪些资源。
- **`parentAgent`**：显式传给工厂、保存到 AgentRegistry entry 的运行时关系。`roots()` 和 `isOwnedBy()` 查询它。
- **`meta.parentSession`**：写入 Session 的持久谱系，表示历史从哪个 Session 派生，不决定当前进程由哪个 Fiber 清理。

代码分别处理它们：Registry 把访问服务时的 Context 当作 `ownerCtx` 传给工厂；AgentLoop 在 `ownerCtx` 登记 lifecycle effect；发布时另把 `parentAgent` 交给 `agents.enter()`，Session 元数据则在准备 Session 时进入另一条路径。[调用方绑定](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L391-L415) · [owner effect](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L601-L622) · [运行时 owner 写入](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L650-L662)

下面三种情况都用同一个父 Agent P。切换调用方式，观察 P 退出后子实例 C 的去向。结果来自本文真实运行时实验；图中只比较与 P 有关的清理，工厂提供者依然持有另一层清理责任。

{{< interactive-diagram src="agent-ownership.html" title="调用方 Fiber、parentAgent 与 parentSession 是独立关系：三种创建方式的资源所有权对照" height="1620" compact-height="1320" mobile-height="1720" >}}

| 创建方式，省略其他参数 | Registry 认为 C 属于 P？ | P 的 Scope 退出时 C 会被收回？ |
| --- | --- | --- |
| `P.ctx.agents.create({ parentAgent: P })` | 是 | 是，生命周期登记在 P 的 Context 上 |
| `root.agents.create({ parentAgent: P })` | 是 | 不会仅因这个字段而收回；调用方仍是 root |
| `P.ctx.agents.create({})` | 否，C 仍列在 roots 中 | 会，生命周期仍登记在 P 的 Context 上 |

表中的结果来自只挂载核心运行时的实验，没有挂载 Subagent 管理器等上层消费者。其他模块仍可持有 handle，另行安排子实例清理；这会增加清理入口，但不改变创建时 effect 的登记位置。

这是当前实现的实际分工。`isOwnedBy(id, parent)` 只是比较 entry 保存的 owner 是否为那个**确切 Agent 对象**，不会迁移 effect，也不会执行销毁。同 id 的另一个对象无法通过这次比较。[owner 与 roots 查询](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L570-L600)

因此，调用方希望这几种关系一致时，必须分别传对 Context、`parentAgent` 和必要的 Session 元数据。真实 SubagentManager 使用自己的私有 Scope 作为调用 owner，显式传 `parentAgent` 并保留 handle；需要停止子树时再按 `ownedChildren` 安排清理。这正是将资源所有权与业务父子关系分开使用的例子。[Subagent 挂载入口](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/subagent/subagent/src/manager.ts#L900-L923) · [管理器的 owner](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/subagent/subagent/src/manager.ts#L154-L176) · [子树清理](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/subagent/subagent/src/manager.ts#L1114-L1151)

## Registry 把创建交给工厂，仍要保留调用方

`AgentRegistry` 作为 `agents` 服务挂载，保存活实例 Map、一个 factory slot，以及进程内的 initiator 上下文。AgentLoop 构造时调用 `ctx.agents.setFactory(this)`；同一 Registry 重复注册工厂会报错，返回的 effect disposer 在卸载时清空 slot。[Registry 构造](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L245-L283) · [工厂注册](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L346-L374)

没有工厂时，Registry 仍可登记一个外部已经构造好的 Agent，但 `create()` 会拒绝。它不会偷偷帮调用者装上 AgentLoop，也不会把 `register()` 当作创建 Session 的替代品。本文实验分别检查了缺工厂、裸登记与真实创建的结果。

委托时有一个细节：factory slot 保存原始对象，必要时经 `symbols.original` 去掉已有代理；每次 create/resume 再通过 `getTraceable(ownerCtx, target)`，以调用方 Context 重新追踪 Service 工厂。实际调用用 `Reflect.apply` 显式传 receiver 和 `ownerCtx`。这样既保留工厂提供者的依赖来源，又让新资源归属于本次访问服务的调用方。

AgentLoop 内部至少有三个 Context，不能全部替换成一个“当前上下文”：

| 名称 | 来源 | 用途 |
| --- | --- | --- |
| `loopCtx` | AgentLoop 的运行时注册 Context | 驱动器使用的基础服务、工厂提供者生命周期 |
| `ownerCtx` | 访问 `agents.create/resume` 的调用方 | 持有创建事务和返回实例的生命周期 effect |
| `agent.ctx` | 为新驱动器建立的 Scope | 挂载本 Agent 的工具、监听器及其他组合贡献 |

`ReactLoopAgent` 构造时从 loop Context 建立自己的 Scope，再创建 Inbox、运行时上下文和系统提示词投影。这些对象与该实例的 Session 连接起来，但构造动作本身还没有把它放进两个公开 Registry。[驱动器构造](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/agent.ts#L122-L138)

## 创建要经过“未发布”的阶段

程序化入口是 `agents.create({ sessionId, agentOptions, setup, ... })`。调用方给出一个 SessionId，Agent 与 Session 共用这个身份。`meta`、`seed`、创建期 `signal` 和 `parentAgent` 分别承担元数据、初始历史、创建取消和运行时关系的职责。[创建参数](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L56-L118)

正常路径可以拆成六个观察步骤：准备 Session；建立驱动器与清理入口；完成 setup 和可选 commit；插入两个 Registry；发出 Session 公告并等待 Agent 公告；最后将 handle 交回调用方。下面可以对照正常创建与创建监听器失败的路径。

{{< interactive-diagram src="agent-publication.html" title="Agent 创建、注册公告与回滚的六步时序：setup 未发布阶段和监听器失败后的清理" height="1800" compact-height="1720" mobile-height="2200" >}}

### 先准备 Session，再交付实例

`createAgent()` 先调用 `sessions.prepare()`，用 `SessionPreparation` 包住尚未发布的 Session。有持久化后端时取得写 handle；之后 `setupAndPublish()` 把 Session、调用方 Context、setup 和创建期信号交给 `prepare()`。[createAgent](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L750-L786)

准备阶段与公开存储分开，允许初始化失败时不向普通消费者暴露半成品。SessionPreparation 的同步、幂等释放也只是管理这次未发布准备所持有的状态，不等于“销毁一个已经公开的 Agent”。[SessionPreparation](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/session/src/preparation.ts#L1-L48)

`prepare()` 在资源创建前就接好取消和清理入口，使用可填充的 machine、detachSession、detachAgent 等位置。新驱动器建立后，caller owner 和工厂侧的跟踪都能找到同一份清理过程。Scope 的原始 disposer 也会被确切收编，以免它作为并发兄弟先退出、破坏清理顺序。[预先登记生命周期](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L497-L622)

### setup 完成前，普通查找看不到它

setup 收到两个参数：`agentCtx` 和新 Agent。它可以在专属 Context 中完成组合，异步注册子插件或其他资源；完成后还可返回带同步 `commit()` 的对象，在公开前重新验证会变化的前置条件。

本文实验在 setup 和 commit 中查询 `agents.get(id)`、`sessions.get(id)`，结果均为 undefined。随后，创建监听器开始执行时，两个对象已经可查，但外部 `create()` 的 Promise 仍未完成。这三个时间点分别对应“已构造”“已插入”“已交付”，不能合成一个 created 状态。[setup 与 commit 顺序](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L789-L815)

setup 是可信的同进程组合代码，拿到完整 Agent Context；“只组合，不驱动 Agent”是调用合同，不是运行时沙箱。应在 create 完成后再提交普通工作，不要在 setup 里靠调用驱动方法绕过发布顺序。[setup 合同](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L100-L118)

### 插入之后，还要等公告

以下是按实际控制流缩写的顺序，省略取消检查、持久化和 finally；它不是可独立运行的代码：

```ts
const prepared = prepare(ownerCtx, id, options, session)
const finalizer = await setup?.(prepared.agent.ctx, prepared.agent)
finalizer?.commit()

sessions.enter(session)
agents.enter(prepared.agent, parentAgent)
sessions.announce(session)
await agents.announce(prepared.agent, 'startup', signal)
return { agent: prepared.agent, dispose }
```

真正的 `publish()` 保存两个 detach closure，先公告 Session，再等待 `agents.announce()` 的 serial 监听器。Registry 在派发前就标记公告已经开始，阻止重入或第二次 announce；监听器抛错会拒绝，并跳过后续监听器。[公开与公告](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L650-L666) · [Agent 公告](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L537-L559)

初始化被放在 `runMaintenance()` 内，排在它后面的唤醒输入要等当前初始化任务结束。创建监听器也不能等待这个 Agent 的 `whenIdle()`，或等待负责当前创建的 owner 自己销毁：前者在等包住自己这次派发的初始化任务，后者可能要反过来等这次派发结束，形成循环等待。[初始化维护阶段](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L818-L834) · [事件等待合同](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/runtime-types.ts#L245-L261)

## 插入、公告与注销为什么分成三个方法

普通调用方可以用 `register(agent)` 登记一个已经构造的 Agent；工厂为了控制顺序，会直接使用更底层的 `enter()` 和 `announce()`。

`enter()` 检查 Agent id 与 Session id 一致，再检查 Map 中有没有同 id 的活 entry。返回的 detach closure 捕获的是**这次 entry 对象**；注销时再次比较 Map 中的确切对象，避免过期清理误删后来同 id 的新生命周期。[entry 插入与精确注销](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L459-L509)

这不是只做一次 `delete(id)` 就够的场景。本文还让两个相同 id 的准备过程竞争：第一个卡在 setup，第二个先发布；第一个随后因冲突失败，它的回滚没有删除获胜者的 Agent 或 Session。

如果 entry 还没开始公告就被撤回，不发 `agent/disposed`，因为外界从未收到它的 created。如果公告已经开始，即便后面的监听器失败，也需要配对 disposal，让之前已经观察到创建的消费者有机会收回自己的状态。

还有一个重入边界：在 `agent/created` 监听器中调用该 entry 的 detach，Registry 只先记下请求，直到整轮 serial 派发结束才真正移除。实验中的第二个监听器仍能查到同一个 Agent，`agent/disposed` 出现在两者之后。[延迟 detach](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L479-L492)

`register()` 返回的是 Cordis 的 awaitable effect disposer，必须先等登记完成；它遵循单次调用约定，重复调用可以返回 undefined。工厂返回的 handle 则有另一层共享清理，下面会看到区别。[register 的清理身份](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L418-L441)

## dispose 需要等待完整的退出过程

裸 Agent 的 `cancel()` 取消当前活动，并按参数处理 Inbox；`whenIdle()` 等待当前活动收敛。它们没有代替工厂 handle 去关闭 Session 写 handle 或从 Registry 注销。

对公开 Agent，输入方法也各有边界：`followup()` 提交普通后续输入，`steer()` 送到最近的 Step 边界，`inject()` 放入模型侧上下文但不主动唤醒驱动器。这里只说明它们属于 Agent 的使用能力，具体的 Inbox 和 Step 执行留到后文。[Agent 操作接口](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/runtime-types.ts#L176-L241)

handle 的清理按下面的依赖关系展开：

| 顺序 | 动作 | 为什么要等到这里 |
| --- | --- | --- |
| 1 | 中止创建期等待；若公告正在进行，等待公告结束 | 创建监听器仍可能使用 Scope 与 Session |
| 2 | `machine.cancel({ kind: 'disposed' })`，再 `whenIdle()` | 当前驱动或维护任务必须先退出 |
| 3 | 释放 Agent Scope | 工具、投影、监听器等实例资源此时才能撤下 |
| 4 | 等待持久化写 handle 的 `close()` | 它可能还要排空最后的写入 |
| 5 | 从 AgentRegistry、SessionStore 解除登记 | 活实例查询在前面的清理期间仍有意义 |
| 6 | 释放工厂及 owner 的跟踪关系 | 后续重复清理不再启动第二次资源释放 |

这段顺序在 `teardown()` 中显式实现，不是靠多个普通兄弟 effect 自然排队。[共享清理实现](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L535-L622)

`disposing ??= ...` 让所有竞争入口等待同一份底层清理。外层 `dispose` 本身是 async 方法，每次返回的 Promise 不必是同一个对象；关键是不会重复清理，也不会让后来的调用绕过已经开始的等待。实验同时调用两次 handle.dispose，把 Scope 释放卡住，再确认清理只开始、结束各一次。

### status 为 idle，也可能还没退出所有活动

ReactLoopAgent 的公开 status 只有 idle/running；内部 maintenance 阶段对外仍显示 idle。`whenIdle()` 会等待 `activityDone`，若等待期间出现替换活动，还要继续追踪新的完成信号。[内部阶段与 status](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/agent.ts#L122-L151) · [maintenance 与等待](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/agent.ts#L183-L242)

本文用真正的 `runMaintenance()` 保持一个活动，status 的确是 idle。调用 handle.dispose 后，活动先收到 abort，但 Scope 和两个 Registry 仍保留。放行活动后才观察到：`work exit → scope cleanup → agent/disposed → session/disposed`。因此，UI 上读到 idle 不能代替资源释放的完成屏障。

### 清理失败发生在哪一层，也影响结果

AgentLoop 会收集停止、Scope 释放和写 handle 关闭的失败，继续完成后续解除登记，再抛出单个错误或 AggregateError。实验里的写 handle.close 拒绝时，两次竞争的 handle.dispose 观察到同一个错误，两个活 Registry 仍已清空。[失败收集](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L550-L590)

但普通 Scope effect 的 disposer 抛错，可能先被 Cordis Fiber 的卸载逻辑记录，而不是继续拒绝到 factory。本文另一组实验得到的就是“Scope effect 失败已记录、handle 清理完成、Registry 已解除”的结果。不能把“外层会收集失败”扩写成“所有底层资源错误都必定到达同一个 Promise”。[Fiber 的卸载捕获](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/vendor/cordis/src/fiber.ts#L675-L701)

注销时的 `agent/disposed` 监听器也有自己的异常处理：Registry 捕获同步抛错，并为异步拒绝接上警告日志，继续通知其他观察者。这与创建时 serial 监听器拒绝整个创建的合同不同。[disposal 通知](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L512-L525)

## 创建失败会回滚，但已经送达的通知不会消失

“创建失败”至少有几种不同的外部可见程度。

| 失败位置 | 失败前可见什么 | 回滚需要做什么 |
| --- | --- | --- |
| setup 或 commit | 只有未发布的准备对象 | 释放 Scope 与写 handle，不制造 created/disposed 公告 |
| `session/created` 监听器 | Session 公告已开始，Agent 公告尚未开始 | 撤回两份登记，只配对已经开始的 Session 公告 |
| `agent/created` 后续监听器 | 前面的消费者已看见两个对象 | 释放并撤回，配对 Agent 和 Session disposal |
| owner 在创建监听器等待期间退出 | 创建尚未向调用方返回，但监听器已拿到实例 | 发出取消，保留资源直到当前公告派发结束，再完成回滚 |

对应的实验分别观察到“没有创建公告”“只有 Session 的创建/销毁配对”和“Agent、Session 均配对”。这提供可跟踪的生命周期边，不会让先收到 created 的监听器忘掉自己已经做过的事情。[公告状态与配对](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L496-L559) · [初始化回滚](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L818-L834)

setup 的异步函数也不会因为 Promise 竞争失败而被 JavaScript 强制终止。AgentLoop 可以停止等待、触发清理，并拒绝在已关闭的 Scope 中继续登记资源；回调若还持有自己的外部任务，仍需遵守其取消合同。实验在 owner 卸载后重新向旧 agentCtx 登记 effect，实际得到拒绝。[创建取消辅助](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L161-L201)

创建期 signal、owner Fiber 卸载和工厂卸载都能进入准备阶段的取消/清理路径。创建完成后的普通用户停止用 `agent.cancel()`，要结束实例则等待 handle.dispose；不要把创建期 signal 当作日后所有工作的控制器。

## 工厂提供者也必须收回它创建的实例

调用方对自己创建的 Agent 负责，但工厂插件可能先于调用方卸载。Agent 还依赖这个插件的驱动实现和投影，此时保留一个看似活着的 handle 没有意义。

FactoryOwnership 因此保存 live Agent 的 dispose 集合，以及创建、恢复和配置启动中尚未结束的任务。开始退出时先停止接纳、发出 abort，随后并行等待现有 dispose 和启动任务，把失败收集后交回。[工厂所有权](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L103-L158)

AgentLoop 还把共享 Inbox/Turn 投影的撤销包在整个事务清理外层，尽量使驱动收敛期间仍能读到需要的投影。本文创建了两个不同 caller Fiber 各自拥有的实例：卸载其中一个 caller 只收回自己的 Agent；卸载工厂提供者则收回两者。之后 Registry 仍存在，但创建入口已没有可用工厂。[工厂事务 effect](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L365-L388)

配置创建的 Agent 也走同一套驱动和清理，但调用方就是 AgentLoop 自己，公开便捷入口 `agentLoop.create()` 返回裸 Agent；程序化 `agents.create/resume` 返回 handle。配置里的逻辑 id、显式 sessionId、恢复与默认模型如何组合，将在下一篇继续读。[配置创建入口](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L688-L701)

## resume 先取得日志写所有权，再恢复活实例

`resume()` 要求持久化服务，不能在没有后端时偷偷退化成 fresh create。实际恢复流程先 `open(id, 'write')`，再读取日志；若尾部存在中断的 Turn，还会计算修复收尾事件并追加。然后用恢复后的历史、元数据和继承边界准备 Session，重新进入 setup 与 publish。[恢复实现](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent-loop/src/index.ts#L843-L925)

读取和写入获取可能比调用方活得更久。这里把 caller signal、owner Fiber 退出和工厂退出合成信号；取消后若 backend 才交回写 handle，仍要把这个迟到资源关闭。本文用受控内存后端让 open 停住，先卸载 caller，再交出 handle：resume 已拒绝，read 没有执行，迟到 handle 最终被关闭。

另一组实验运行了真实 resume 主线，核对 write-open 在 read 之前，公开来源为 resume，原来的 parentSession 保留；没有显式 parentAgent 时，恢复后的实例仍是当前进程的运行时根。**持久谱系没有自动变成活实例所有权。**

handle.dispose 从 SessionStore 移除的是这次活对象，并关闭它持有的写 handle。删除历史日志、归档 Session 或清理工作区是另外的产品动作，本篇的 dispose 顺序没有授权它们自动发生。

## initiator 说明因果来源，不替代 owner 或 subject

Registry 还用 AsyncLocalStorage 传播同进程异步调用链的 initiator。父 Agent 发起创建时，setup 的 Agent 参数指向新子实例，而 `currentInitiator()` 可以仍指向父 Agent。本文用真实创建核对了这两个对象不同，边界之外的 initiator 则恢复为 undefined。[initiator 合同](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L233-L243) · [继承与显式清除](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L285-L344)

这回答“是谁引发这条调用”，不证明 Agent 仍活着，也不提供授权，更不会自动填上 parentAgent。跨 Worker、进程、日志和传输边界，身份仍要显式携带和校验。Registry 给 Typert 注册的 lookup/context provider 也只按 id 解析活 Agent 及其 Context，没有把包含 dispose 闭包的 AgentHandle 变成可直接在线路上传递的对象。[查找桥接](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/core/agent/src/index.ts#L255-L269)

## 用 36 组实验核对生命周期

[下载完整实验包](agent-ownership-examples.zip)。解压后在实验目录执行，源码指向上述固定提交：

```sh
npm ci --ignore-scripts --no-audit --no-fund
DSH_SOURCE=/path/to/deepseek-harness npm run verify
```

`run.mjs` 检查源码提交与可达工作区包的状态，再把真实运行模块转译到临时目录。此次静态运行依赖闭包为 **18 个工作区包、82 个模块**，外部运行依赖使用固定 `zod 4.4.3`，转译器为 `TypeScript 6.0.3`。它不在 dsh 仓库安装完整依赖，结束或失败后清理自己的临时目录；语法转译检查也不代表全仓库语义类型检查。

本次实际环境是 macOS `27.0.1 arm64`、Node `v25.9.0`。36 组全部通过，覆盖范围如下。

| 实验范围 | 已核对的结果 |
| --- | --- |
| Registry 与 handle | 缺工厂拒绝；裸查询与 handle 不同；同 id、错误 id、精确对象与旧 detach 的边界 |
| setup、commit、公告 | 未发布查询、串行等待、重入拒绝、监听器失败、公告配对、派发中延迟 detach |
| caller 与 factory | 分别卸载的影响、过期 Context 拒绝、owner 中断尚未完成的 setup |
| 三种 parent 关系 | caller Scope、parentAgent、parentSession 的独立作用，及 initiator 与 setup subject 的差异 |
| 真实清理与并发 | 重复 dispose 共用清理；maintenance 的 idle 状态；驱动退出、Scope、两个 Registry 的顺序 |
| 持久化接口边界 | setup 失败时关闭、close 等待与拒绝、迟到 create/open handle 的释放、真实 resume 主线 |

Registry 专项中的 8 组使用最小合成 Agent，核对登记和公告；其余运行真实 AgentLoop 驱动器。持久化接口用可控的内存适配器观察顺序，**没有验证 JSONL、SQLite、文件锁、崩溃持久性或真实模型调用**。所有等待边界都由受控 Promise 放行，没有用固定 sleep 推测调度。

继续定位源码，可在固定提交的仓库根目录运行：

```sh
rg -n 'interface AgentHandle|setFactory|async create|async resume' packages/core/agent/src/index.ts
rg -n 'enter\(|announce\(|isOwnedBy|roots\(' packages/core/agent/src/index.ts
rg -n 'class FactoryOwnership|private prepare|setupAndPublish|initializeAgent' packages/core/agent-loop/src/index.ts
rg -n 'detachSession|detachAgent|publication|unfollowOwner' packages/core/agent-loop/src/index.ts
rg -n 'constructor\(|get status|runMaintenance|whenIdle' packages/core/agent-loop/src/agent.ts
rg -n 'parentAgent:|agents.create\(' packages/subagent/subagent/src/manager.ts
```

读到这里，再遇到“Agent 已创建”或“Agent 已销毁”，就可以继续追问一个明确的时间点：对象构造了，还是两个 Registry 已插入？公告已经开始，还是 create 已返回？取消已送达，还是 Scope、写 handle 与登记都已退出？这些问题分别有可检查的入口，handle.dispose 则把需要共同完成的清理收在同一个生命周期里。

下一篇继续看 Agent Preset、Persona 与默认模型：这些配置怎样进入刚刚建立的 Agent 世界，以及调用方、部署和 Session 选择之间怎样决定实际模型。
