+++
title = "构建有效的 Agent 自动化"
date = 2026-10-10T12:00:00+08:00
draft = false
author = "Hex4C59"
description = "Lance Martin 与 CJ Avilla 介绍如何通过 Claude Managed Agents 构建定时简报自动化，涵盖来源读取、发布确认、持久记忆、权限和预算控制。"
summary = "以一个读取 Slack 与 GitHub、按计划发布简报的参考实现为例，说明来源游标、失败报告、发布前复核、去重与确认、只读用户偏好，以及凭据隔离和单次运行预算的设计。"
tags = ["Agent", "自动化", "Claude", "Managed Agents", "记忆"]
categories = ["ai"]
topics = ["agents", "automation", "managed-agents", "memory", "slack", "github", "claude"]
translation_category = "AI 与工具"
original_title = "Building effective agent automations"
original_url = "https://claude.dev/blog/building-effective-agent-automations/"
original_author = "Lance Martin and CJ Avilla"
original_date = "2026-10-08"
original_site = "Claude Developer Blog"
ShowToc = true
source_kind = "translation"
lastmod = 2026-10-11T00:56:39+08:00
+++

> **译文信息**
>
> - 原文：[Building effective agent automations](https://claude.dev/blog/building-effective-agent-automations/)
> - 作者：Lance Martin、CJ Avilla
> - 原文发布：2026-10-08
> - 中文翻译：Hex4C59
> - 翻译整理：2026-10-10
>
> 本文为非官方中文译文。正文中的「我们」指原文作者及其团队；产品状态、模型名称、命令和配置均保留原文记录。示例用于说明参考实现，译者未执行其中的资源创建、凭据配置或消息发布操作。

**一份参考实现的逐步讲解，以及常见失败模式。**

随着 AI 加快我们的工作节奏，跟上进展变得越来越难。在 Anthropic，我们经常使用简单的 Agent 自动化来帮忙。它们通常按计划运行，在后台收集上下文，并主动告诉我们需要了解的事情。但构建有效的 Agent 自动化并不容易：它们可能失去对某个来源的访问权限，却没有任何人察觉；也可能不遵循我们的偏好。

我们使用 Claude Managed Agents（beta）构建了一份参考实现：按计划读取自定义来源，例如 Slack 和 GitHub 仓库，追踪与上次运行相比发生了哪些变化，再把你需要知道的信息发布出去，例如发布到 Slack。本文会逐步讲解实现过程，分享参考实现，并提供一条可在 Claude Code 中运行的命令，帮你配置 Agent。

## 获取代码

参考实现可通过原文中的链接获取。要进行交互式引导，请在 Claude Code 中运行以下命令。`claude-api` skill 可以按照本文的指导帮助你设置 Agent：

```text
/claude-api managed-agents-onboard https://claude.dev/blog/building-effective-agent-automations/
```

使用这份参考实现，需要一个 Slack 应用，通过清单创建，以及一个 GitHub token。所提供的文件如下，都是 Claude API 资源的配置，包括 Agent、运行环境、记忆存储、凭据保管库和部署。

```text
daily-brief/
├── agent.md                        model, tools, instructions
├── deployment.md                   schedule, time zone, budget, input message
├── environment.yaml                network allowlist
├── memory_store_preferences.yaml   user preferences
├── memory_store_state.yaml         the agent's bookmarks, ledger, notes, and run records
├── vault.yaml                      the vault that holds the credentials
├── claude-lock.json                resource IDs, written by ant apply
└── slack/manifest.yaml             one bot app
```

这些文件分别用于：

- `agent.md`：模型、工具和指令。
- `deployment.md`：调度、时区、预算和输入消息。
- `environment.yaml`：网络允许列表。
- `memory_store_preferences.yaml`：用户偏好。
- `memory_store_state.yaml`：Agent 的来源游标、已报告事项台账、笔记和运行记录。
- `vault.yaml`：保存凭据的保管库。
- `claude-lock.json`：由 `ant apply` 写入的资源 ID。
- `slack/manifest.yaml`：一个机器人应用的清单。

`ant apply` 是 ant CLI 中的一条命令。它读取这些文件，在你的 Claude API 工作区中创建资源，再将资源 ID 记录到 `claude-lock.json`。平台负责存储和运行工作区中的这些资源。

下面各节会用到这条命令。配置完成后，自动化会在 Anthropic 的基础设施上按计划运行，因此你的机器不需要一直运行任何进程。

## 总览

我们要构建的 Agent 包含六个组成部分，下面按此顺序介绍：

1. **来源（Sources）**：一份带有名称的待读取位置列表。
2. **发布目标（Destination）**：Agent 可以写入的唯一位置。
3. **Agent**：`agent.md` 中的模型、工具和运行步骤。
4. **调度（Schedule）**：一份 cron 调度计划。
5. **记忆（Memory）**：你的偏好，以及 Agent 自己的记忆。
6. **运行约束（Guardrails）**：对只需读取的位置提供只读访问权限，并为每次运行设置支出上限。

> **原文图注**：Agent 的架构。调度唤醒 Agent，Agent 读取各个来源，并向一个发布目标发送简报，供读者阅读。记忆保存 Agent 的状态和读者偏好，运行约束则围绕 Agent 生效。

## 来源

Agent 默认读取两类来源：Slack 频道和 GitHub 拉取请求。需要读取的频道与仓库，列在你的偏好文件中。也可以扩展模板，使用其他来源。

> **原文图注**：突出显示来源的架构图。来源为只读，通过 MCP 或 HTTPS 访问，使用保管库提供的凭据，并将信息传给 Agent。

### 给 Agent 提供独立、范围受限的凭据

在 Managed Agents 中，凭据保存在保管库（vault）里。Agent 可以引用这些凭据，但真实值始终留在保管库中，不会进入运行 Claude 代码的沙箱。相关说明可参阅原文链接。

**MCP 服务器（GitHub）**：Agent 通过运行在沙箱外的代理调用 MCP 工具。代理会找到保管库中 URL 与服务器相匹配的凭据。

**Shell（Slack）**：Agent 在沙箱内通过 bash 工具使用 `curl` 调用 Slack API。沙箱中只有一个不透明占位符 `$SLACK_BOT_TOKEN`。请求离开沙箱时，平台会针对你允许的主机，将占位符替换为真实 token。

使用 ant CLI 和仓库中的模板文件创建保管库：

```bash
ant apply vault.yaml
```

这会在你的 Claude API 工作区中创建保管库，由平台保存，并将其 ID 记录到 `claude-lock.json`。随后，通过 TypeScript SDK 将每项凭据加入保管库。下面示例展示了如何加入 Slack 凭据：

```typescript
const vaultId = process.env.VAULT_ID!; // the vault's ID, from claude-lock.json

await client.beta.vaults.credentials.create(vaultId, {
  display_name: "SLACK_BOT_TOKEN",
  auth: {
    type: "environment_variable",
    secret_name: "SLACK_BOT_TOKEN",
    secret_value: process.env.SLACK_BOT_TOKEN!,
    networking: { type: "limited", allowed_hosts: ["slack.com"] },
    injection_location: { header: true },
  },
});
```

代码首行注释的意思是：从 `claude-lock.json` 获取保管库 ID。

创建保管库并加入所有凭据后，将它关联到部署。把 `claude-lock.json` 中的保管库 ID，复制到部署文件 `deployment.md` 的 `vault_ids` 中。

### 从上次读到的位置继续

一个常见错误，是要求 Agent 读取固定时间窗口，例如「过去 24 小时」。运行晚了会留下空档，运行早了又会重复读取。更好的做法，是为每个来源提供一个游标（bookmark）。每次运行结束时，Agent 将自己在各个来源读到的最新条目的时间戳写入同一个 `bookmarks.json` 文件，每个来源对应一个条目，例如：`"slack": "2026-09-14T13:02:11Z"`。

下次运行从这些游标开始，因此读取窗口可以伸缩，覆盖自上次运行以来的全部内容。游标位于名为 `state` 的记忆存储中。这是一个由文本文件组成的文件夹，平台会在每次运行时将其挂载到沙箱的 `/mnt/memory/` 下，并在运行之间保留。Agent 用普通文件工具读写它，`agent.md` 中的指令会告诉它具体如何操作。

### 不要把读取失败误认为平静的一天

如果 MCP 服务器不可用，或者其 token 已过期，运行仍会开始，只是缺少该服务器的工具。会话日志会记录错误，但 Agent 从这个来源看不到任何内容，于是报告「没有新消息」。

`agent.md` 中的三条规则有助于解决这个问题。来源读取失败时，Agent 会：保留该来源原有的游标位置；根据其他来源生成简报；并在简报末尾用一行说明未能读取什么，例如「本次运行无法读取拉取请求」，让读者知情。

## 发布目标

我们的模板向一个 Slack 频道发布简报，每次运行都生成一条带日期的消息。

> **原文图注**：突出显示发布目标的架构图。确认当天简报尚未发布之后，Agent 向一个目标发布消息，由该目标将简报交给读者。

Agent 在沙箱中使用 bash 工具向 Slack 发布，使用的机器人 token 与读取时相同。

发布不需要任何组件批准。Agent 通过 bash 命令发送消息，而内置 bash 工具默认运行时不会请求批准。`slack.com` 也在 Agent 运行环境，也就是沙箱的允许列表中。发布只需一个请求：

```bash
curl -s https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{"channel": "C0123456789", "text": "Daily brief, Tue Sep 15 ..."}'
```

请求中的示例消息是「每日简报，9 月 15 日星期二……」。

### 确认消息发布成功后，再记录它

确认发布成功后，Agent 才更新已报告事项的台账和来源游标。如果记录与实际发布的内容不一致，会产生两种问题。如果 Agent 记录了一条实际上没有发布成功的消息，游标就会向前移动，那些条目将永远无法报告。如果它因为不确定第一次是否成功而再次发布，读者就会收到两份相同简报。

`agent.md` 中的三条规则防止这种情况。第一，Agent 在频道最近的消息中查找当天标题，如果这一期已经存在，就不再发布。第二，只有 Slack 返回 `"ok": true` 和消息的 `ts`，才算发送成功。第三，只有获得确认之后，Agent 才更新台账和游标。如果结果不明确，它将本次运行标记为「可能已发布」（`maybe posted`），其他状态一概不改，确保不会丢失内容。

Agent 会在记忆存储中保留运行记录，路径为 `runs/<date>.md`。发布前，将运行标记为 `posting`；随后标记为 `posted` 并记录消息 ID，或者标记为 `maybe posted`。

## Agent

在 Claude Managed Agents 中，Agent 是一份带版本的配置，包括模型、系统提示和工具。每次运行都遵循配置中的运行步骤，执行完后停止。

> **原文图注**：突出显示 Agent 的架构图。Agent 由模型和提示组成，提示中包含运行循环与判断规则。

在我们的参考实现中，Agent 配置位于 `agent.md`：

```markdown
---
name: Daily brief
model: claude-sonnet-5-5
mcp_servers:
  - type: url
    name: github
    url: https://api.githubcopilot.com/mcp/
tools:
  - type: agent_toolset_20260401
    configs:
      - name: web_search
        enabled: false
      - name: web_fetch
        enabled: false
  - type: mcp_toolset
    mcp_server_name: github
    default_config:
      permission_policy:
        type: always_allow
---

[Eight numbered run steps; the full text is in agent.md in the repo.]
```

最后一行方括号内的说明是：「八个带编号的运行步骤，完整文本见仓库中的 `agent.md`。」原文此处只展示配置摘录。

文件头部元数据（front matter）提供 Agent 名称、模型、工具和 MCP 服务器，正文则提供 Agent 指令。MCP 工具默认会请求批准，但后台运行时没有人批准，因此 GitHub 工具集设置为 `always_allow`，同时使用只读 GitHub token。

### 保持简报简短

`agent.md` 引导 Claude 保持简洁。原文指令如下：

```text
4. Decide. An item earns a line when the reader would act on it today, or it changes a decision they are about to make. When unsure, leave it out. Most days that is a few items, sometimes none. A count ("12 open reviews") is not an item; link the ones that are blocked. An item already in the ledger and still open is carried as one marked line ("still waiting, day 3"), not re-reported; a closed item is dropped without comment. Do not bring back a topic the preferences file has retired.
```

中文译文：

> **4. 决定。** 如果读者今天会据此采取行动，或者它会改变读者即将作出的决定，这个事项才值得占据一行。不确定时就省略。大多数日子只有几个事项，有时一个也没有。一个数量，例如「12 项尚未完成的审查」，本身不算事项；应当链接到那些被阻塞的审查。台账里已经记录、但尚未解决的事项，只保留一行并明确标记，例如「仍在等待，第 3 天」，不要重新报告；已结束的事项直接移除，无需说明。不要重新提起偏好文件已经停用的话题。

### 发布前重新检查所有尚未解决的事项

从 Agent 读取来源，到实际发布之间，事项可能已经发生变化。因此，`agent.md` 要求 Agent 在发布前，再次检查每项内容的实时状态：

```text
5. Verify. The world moved while you read. For every item you will report, re-check its live source just before posting: resolved since you read it, drop it; still open but changed, fix the line; cannot confirm, drop it and list it in the run record's cuts. One stale "still waiting on you" costs more trust than ten missing items, so never hedge an item's status: assert it or drop it. Every link is copied from the source's own link field (a pull request's html_url, a Slack permalink), never assembled by hand.
```

中文译文：

> **5. 验证。** 在你阅读时，情况已经发生了变化。对于准备报告的每一项内容，都要在发布前重新检查其实时来源：如果在你读取后已经解决，就移除；如果仍未解决但发生变化，就修正这一行；如果无法确认，就移除，并将其列入运行记录的删减项（cuts）。一条过时的「还在等你处理」，比遗漏十个事项更损害信任，因此绝不要含糊表述事项状态：明确断言，或者移除。每个链接都从来源自身的链接字段复制，例如拉取请求的 `html_url` 或 Slack 永久链接，绝不手动拼接。

## 调度

在 Claude Managed Agents 中，Agent 只是一份配置文件，真正运行它的是部署（deployment）。部署指定 Agent、运行环境，以及每次运行的第一条消息，还包含调度、保管库、记忆存储和预算。每次调度触发时，平台都会启动一个全新的 Agent 会话。

> **原文图注**：突出显示调度的架构图。定时部署会在每次运行时唤醒 Agent。

在模板中，部署由 `deployment.md` 表达，文件正文就是第一条消息：

```markdown
---
name: Daily brief
agent: ./agent.md
environment_id: ./environment.yaml
schedule:
  type: cron
  expression: "32 7 * * 1-5"
  timezone: America/New_York
vault_ids: [vlt_...]   # the vault you create under Sources
resources:
  - path: ./memory_store_preferences.yaml
    access: read_only
    instructions: The reader's preferences. Re-read them every run. Never write here.
  - path: ./memory_store_state.yaml
    access: read_write
    instructions: Your state. Bookmarks, ledger, notes, proposals, and run records.

---

Write today's brief.
The reader's time zone is America/New_York. Work out every date in that zone.

Follow your run steps in order. Today's edition is titled "Daily brief, <weekday> <month> <day>".
```

其中的英文说明分别是：

- `vault_ids` 的注释：在「来源」一节创建的保管库。
- 偏好存储的指令：读者的偏好，每次运行都重新读取，绝不写入这里。
- 状态存储的指令：你的状态，包括来源游标、台账、笔记、提案和运行记录。
- 正文：编写今天的简报。读者时区是 `America/New_York`，所有日期都按这个时区计算。按顺序执行运行步骤，今天这一期的标题为「每日简报，<星期> <月份> <日期>」。

以下命令会创建部署，并按其中指定的路径关联 Agent、运行环境和记忆存储：

```bash
ant apply deployment.md
```

要测试部署而不必等待调度，可以手动启动一次运行：使用 `claude-lock.json` 中的 ID，执行 `ant beta:deployments run --deployment-id <id>`。

### 按你的时区计算日期

一个常见缺陷，是 Agent 因为按服务器时区计算日期，而把今天早上称为「昨天」。在 `deployment.md` 中，`timezone` 字段决定运行何时触发；正文的第二行，则告诉 Agent 在处理日期时应该使用哪个时区。

## 记忆

每次运行都从一个全新沙箱开始，没有上一次运行的记忆。没有记忆，反馈就无法保留下来。但过时记忆又可能让 Agent 混淆：某个事项明明已经解决，它却仍然报告为正在等待；或者某个事项仍未解决，它却因为「已经报告过」而将其忽略。

> **原文图注**：突出显示记忆的架构图。状态由 Agent 读写；偏好由读者写入，Agent 只能读取。

模板维护两个记忆存储，它们都是挂载在 `/mnt/memory/` 下的文件夹，参见「来源」一节：

- **`preferences`**：属于你，Agent 只能读取。包含要读取的频道和仓库、哪些内容应省略、长度上限、发布目标，以及何时停止。
- **`state`**：属于 Agent，可读写。包含来源游标、已报告事项的台账、每次运行的记录、对你偏好的修改提案，以及各来源行为的笔记，例如「只返回最新 50 个条目」。

`ant apply deployment.md` 会创建偏好存储，但不会创建里面的文件。首次运行前，使用仓库中的 `scripts/seed-preferences.sh`，将你的 `preferences.md` 写入其中。

### 每次运行开始时，重新读取偏好

一个常见问题，是将偏好的副本固化在提示中，导致 Agent 继续应用你已经修改过的旧规则。应当让 Agent 每次运行都重新读取文件。如果无法读取，它应该停止并说明原因，而不是按默认设置继续运行。

### 记录已经报告过的事项，报告其变化

Agent 在 `ledger.md` 中维护所有已报告事项的台账，避免简报重复。每一行记录该事项何时报告、来自哪里、一个不会改变的 ID，例如 Slack 消息时间戳或拉取请求编号，以及最后已知的状态：

```text
2026-09-09 slack:C0123456789 1788963600.000100 refund thread: customer waiting on a decision
2026-09-11 github 481 review blocked, day 2 (still waiting)
2026-09-11 slack:C0234567891 1789117333.000300 enterprise escalation: owner named, in progress
```

三个示例事项依次为：退款讨论中，客户正在等待决定；第 2 天，审查仍被阻塞、继续等待；企业客户的升级处理事项已指定负责人，正在进行中。

## 运行约束

由于自动化按计划在「后台」运行，我们对 Agent 能做什么、能花多少钱都设置了限制。

> **原文图注**：突出显示运行约束的架构图。围绕 Agent 的边界限制交互轮数、时间和支出，并有由专人关注的心跳信号。

### 限制它能做什么

Agent 会读取别人编写的消息和 issue，而这些文本可能被解释为指令。应当限制它即使遵循这些指令，也能执行的操作范围。在我们的示例中，GitHub token 和偏好存储都是只读的，运行环境只能连接允许列表中的主机。植入的指令仍然可能改变简报内容，也可能通过 Agent 在多次运行之间保留的笔记发挥作用。但它不能写入 GitHub，也不能修改你的规则。

Slack 是个例外：同一个 token 也用于发布。因此，只将机器人邀请到它需要读取或发布的频道。

### 根据实际运行设置支出上限

支出上限可以防止成本失控。起初，将它设为一次正常运行成本的三到五倍；看到实际费用后，再逐步收紧。达到上限的运行会暂停，而不是失败，因此上限设置过低时，表现出来的可能是简报突然没了消息。上限就是 `deployment.md` 中的 `budget`。每次运行都获得完整额度，达到上限后，以 `budget_reached` 作为停止原因暂停：

```yaml
budget:
  type: limit
  max_list_cost:
    amount: "500" # a string, in cents: "500" is $5.00
    currency: USD
```

注释说明：`amount` 是以美分为单位的字符串，`"500"` 表示 5.00 美元。

## 开始使用

我们的参考实现可以归纳为六条规则：

1. 从每个来源的游标位置继续读取，不使用固定时间窗口。
2. 将读取失败报告为无法读取，绝不当成没有新消息的一天。
3. 发布前重新检查每个事项。
4. 只有 Slack 确认后，才算发布成功，然后再更新游标和台账。
5. 每次运行都从 Agent 无法修改的存储中重新读取偏好。
6. 对只需读取的位置提供只读权限，并限制每次运行的支出。

Claude Code 可以引导你完成本文介绍的配置。首先，更新：

```bash
claude update
```

然后，使用 `claude-api` skill：

```text
/claude-api managed-agents-onboard https://claude.dev/blog/building-effective-agent-automations/
```

`claude-api` skill 会读取本文，提出配置方案，在项目的 `agents/` 文件夹中写入文件，再通过 `ant apply` 创建资源。将它作为起点，再根据自己的来源、发布目标或记忆偏好定制 Agent。

---

## 译注

- **Agent** 保留英文；**agent automation** 译为「Agent 自动化」，指按计划自主读取来源、判断信息并执行发布等操作的系统。
- **Bookmark** 译为「来源游标」，指每个来源已读取到的位置；**ledger** 译为「台账」，记录哪些事项已经报告及其最后已知状态。两者分别用于衔接读取窗口和避免重复报告。
- **Vault、deployment、guardrails** 分别译为「凭据保管库」「部署」「运行约束」。文中的部署是运行配置与资源的组合，不等同于本博客网站的发布。
- 14 段命令、配置和指令摘录保留原文内容；其中的英文注释、消息和指令另附中文解释。`vlt_...`、频道 ID、日期和 `claude-sonnet-5-5` 等均沿用原文示例，不代表译者验证了相应资源或服务。
- 原文只摘录了 `agent.md` 配置，八个运行步骤的全文未包含在所提供文本中，本文不补写缺失部分。
- 所提供文本不含架构图及部分超链接，本文翻译并保留了七处图注。参考实现、Slack 清单和相关平台文档入口，请参阅[原文页面](https://claude.dev/blog/building-effective-agent-automations/)。

原文著作权归原作者及 Anthropic 所有。本文为非官方中文译文；如需核对技术细节或措辞，请以原文为准。
