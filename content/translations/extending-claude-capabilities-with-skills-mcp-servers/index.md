+++
title = "用 Skills 与 MCP 服务器扩展 Claude 的能力"
date = 2026-03-25T12:00:00+08:00
lastmod = 2026-03-25T12:00:00+08:00
draft = false
author = "Hex4C59"
description = "说明 Model Context Protocol（MCP）与 Agent Skills 如何分工与协同：连接外部系统与沉淀工作流知识，并给出金融分析与会议筹备等实例及选型对照表。"
summary = "MCP 负责安全、标准化的工具与数据接入；Skills 负责领域知识与流程编排。二者组合可让 agent 按团队 playbook 产出一致结果，而非每次靠猜。"
tags = []
categories = ["Translations"]
topics = ["mcp", "agent-skills", "claude", "agents", "integrations"]
translation_category = "AI 与工具"
original_title = "Extending Claude's capabilities with skills and MCP servers"
original_url = "https://claude.com/blog/extending-claude-capabilities-with-skills-mcp-servers"
original_author = "Anthropic"
original_date = "2025-12-19"
original_site = "Claude Blog"
ShowToc = true
+++

> **译文信息**  
> - 原文：[Extending Claude's capabilities with skills and MCP servers](https://claude.com/blog/extending-claude-capabilities-with-skills-mcp-servers)  
> - 作者：Anthropic  
> - 原文发布：2025-12-19  
> - 翻译发布：2026-03-25（东八区）

**更新：** 我们已发布 [Agent Skills](https://agentskills.io/) 作为开放标准，以支持跨平台可移植性。（2025-12-18）

自 [推出 Skills](https://claude.com/blog/skills) 以来，客户最常问的两个问题是：「Skills 和 MCP 如何配合？」「什么时候该用哪一个？」

[Model Context Protocol（MCP）](https://modelcontextprotocol.io/docs/getting-started/intro) 把 Claude 接到第三方工具；Skills 则教 Claude **如何用好**这些连接。把两者结合起来，你就能构建遵循团队工作流的 agent，而不是总要纠偏的通用流程。

例如：连上 Notion 的 MCP 后，Claude 可以搜索你的工作区；再叠加一个会议筹备 Skill，Claude 就知道该从哪些页面取数、如何排版筹备文档、以及团队对会议纪要的标准是什么。连接从「可用」变成「好用」。

本文将拆解 Skills 与 MCP 的关系，说明如何组合它们以产出一致输出，并给出若干真实场景下的协作方式。

## 理解 Skills 与 MCP

你走进五金店想修一个坏掉的柜子。店里什么都有（木胶、夹具、替换铰链），但**该买什么、怎么用**是另一回事。

MCP 好比你能走进各个货架区；Skills 则像店员的专业经验。再全的库存，若不知道要什么、怎么用，也帮不上忙。Skill 就像那位带你一步步完成维修、指给你正确耗材、并示范正确手法的人。

更具体地说：**MCP 服务器**让 Claude 能访问你的外部系统、服务与平台；**Skills**提供 Claude 有效使用这些连接所需的上下文——在「有了权限」之后教它「该做什么」。没有 Skills 提供的上下文，Claude 只能猜你想要什么；有了 Skill，它可以按你们的 playbook 执行。

## 为什么 Skills 与 MCP 很合拍

MCP 负责**连接**：安全、标准化地访问外部系统。无论接 GitHub、Salesforce、Notion 还是内部 API，MCP 服务器都让 Claude 能触达你的工具与数据。

Skills 负责**专长**：把原始工具访问变成可靠产出的领域知识与工作流逻辑。Skill 知道何时查 CRM、结果里该看什么、如何排版输出、以及哪些边界情况要换处理方式。

这种分工让架构**可组合**：一个 Skill 可以编排多个 MCP 服务器；一个 MCP 服务器也可以支撑许多不同 Skill。新增连接时，现有 Skill 可以纳入它；打磨 Skill 时，它又能跨所有已连接工具生效。

#### 把 Skills 与 MCP 合用时，你会得到：

**清晰的发现（Discovery）**：Claude 不再乱猜该去哪找。会议筹备 Skill 可能规定：先看项目页，再看往期会议纪要，最后看干系人档案。研究 Skill 可能规定：从共享盘起步，与 CRM 交叉核对，再用网页搜索补洞。Skill 把「对哪些任务、哪些来源重要」这类机构知识编码进去。

**可靠的编排（Orchestration）**：多步流程变得可预期。没有 Skill 时，Claude 可能在凑齐信息前就拉数据并排版。Skills 明确顺序，让工作流每次执行方式一致。

**一致的表现（Performance）**：输出真正符合标准。泛泛的结果需要大改。Skills 定义团队眼中「完成」的样子：结构、详略、对受众的语气。

久而久之，团队会积累相互关联的 Skills 与连接，让 Claude 在自己领域里越来越专业。

延伸阅读：Tim O'Reilly 谈 [MCP 与 Skills 对开源 AI 意味着什么](https://www.oreilly.com/radar/what-mcp-and-claude-skills-teach-us-about-open-source-for-ai/)

*（配图说明，引自原文）Skills 与 MCP 如何协作：MCP 提供工具访问，Skills 提供工作流逻辑。*

#### Skills 与 MCP 可能重叠之处

MCP 服务器里也可能带有工具使用提示、常见任务的 prompt 等形式说明，让工具相关知识离工具更近。但这类说明**设计上应保持通用**。

经验法则：**MCP 的说明**覆盖如何正确使用该服务器及其工具；**Skill 的说明**覆盖如何把它们用于特定流程，或用于多服务器编排。

例如：Salesforce MCP 服务器可能规定查询语法与 API 格式；Skill 则会规定先看哪些记录、如何与 Slack 里的近期对话交叉引用、以及如何把输出整理成你们管道评审用的结构。

同时使用 MCP 与 Skills 时，注意**指令冲突**：若 MCP 要求返回 JSON，而 Skill 要求排成 Markdown 表格，Claude 只能猜谁优先。让 MCP 管连接，让 Skills 管呈现、顺序与工作流逻辑。

延伸阅读：Skills 如何通过 [渐进式披露（progressive disclosure）](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) 按需加载上下文，以及如何通过 [程序化工具调用（programmatic tool calling）](https://www.anthropic.com/engineering/advanced-tool-use) 高效编排 MCP 工具。

## Skills 与 MCP 合用的真实案例

下面看 Skills 与 MCP 在真实工作流里如何配合。两个例子：金融分析师为估值拉取实时市场数据；项目经理用 Notion 的 Meeting Intelligence Skill 做会议筹备。

两种情形里，都是 **MCP 提供工具访问，Skills 定义拿工具做什么**。

#### 金融分析：自动化可比公司估值 Skill

[Anthropic 发布了一套预置 Skills](https://www.anthropic.com/news/advancing-claude-for-financial-services)，覆盖常见金融工作流，其中包括可比公司分析（comparable company analysis）。可比公司分析是标准估值方法：分析师往往要花大量时间从多处拉财务指标、套用同一套估值方法论、并按合规要求排版——重复、易错，正是 Skills 与 MCP 联手的典型场景。

**Skill：** [Comparable company analysis](https://www.anthropic.com/news/advancing-claude-for-financial-services) 自动化该估值流程：从多源取数、统一方法论、按特定标准排版输出。

**MCP 服务器：** 连接 S&P Capital IQ、Daloopa、Morningstar 等以获取实时市场数据。

**工作流：**

1. Skill 识别要查询的数据源（Discovery）
2. MCP 连接拉取实时财务数据
3. Skill 应用方法论并排版输出（Orchestration）
4. Skill 按合规要求校验（Performance）

#### 会议筹备：Notion 的 Meeting Intelligence Skill

会议筹备很繁琐：要从项目文档、往期纪要、干系人信息等多处拉上下文，再合成 pre-read 与议程——这种多步流程往往每次都要重新解释一遍。

**Skill：** [Meeting Intelligence](https://notiondevs.notion.site/notion-skills-for-claude) 规定搜索哪些页面、如何组织输出、包含哪些章节。

**MCP 服务器：** Notion 连接，用于搜索、阅读与创建页面。

**工作流：**

1. Skill 识别要搜的相关页面（项目、往期会议、干系人等）（Discovery）
2. MCP 在 Notion 中搜索并取回内容
3. Skill 组织两份文档：内部 pre-read 与对外议程（Orchestration）
4. MCP 将两份文档写回 Notion，并做好组织与链接
5. Skill 确保输出符合格式标准（Performance）

## 何时用 Skills、何时用 MCP

Skills 与 MCP 解决的问题不同，但具体到某个工作流该选哪个，并不总是一眼就能看清。

#### 适合用 Skills 的场景

Skills 承载那些本来在你脑子里、或每次新人入职都要重新讲一遍的知识。最适合：

- **涉及工具的多步工作流**：从多处取数再生成结构化文档的会议筹备
- **一致性至关重要的流程**：每季财务分析必须同一套方法论、带强制检查点的合规评审
- **希望沉淀与共享的领域专长**：研究方法论、代码评审标准、写作规范
- **需要超越人员流动的流程**：把机构知识写成可复用说明

#### 适合用 MCP 服务器的场景

MCP 扩展 Claude 能访问、能操作的范围。在以下情况使用 MCP：

- **实时数据访问**：搜 Notion 页面、读 Slack、查数据库
- **在外部系统中执行动作**：建 GitHub issue、更新项目管理工具、发通知
- **文件操作**：读写 Google Drive、访问本地文件系统
- **API 集成**：接入没有原生 Claude 集成的服务

若在解释**怎么做**，那是 Skill；若需要 Claude **访问什么**，那是 MCP。

#### 速查表：Skills 与 MCP 的差异

| | Skills | MCP |
| --- | --- | --- |
| 本质 | 程序性知识 | 工具连接能力 |
| 作用 | 教 Claude 如何做某事 | 让 Claude 能访问某物 |
| 加载时机 | 相关时按需加载 | 连接后始终可用 |
| 内容 | 说明、脚本、模板、资源 | Tools、resources、prompts |
| Token 行为 | 按需加载，节省上下文 | 定义通常会预先加载 |
| 最适用 | 工作流、标准、方法论 | 数据访问、API 调用、外部动作 |

## 常见问题

#### Skills 会取代 MCP 吗？

不会。二者解决的问题不同。MCP 提供对外部工具与数据的连接；Skills 提供如何有效使用这些连接的程序性知识。最强的工作流往往**两者都用**。

#### 一个 Skill 能用多个 MCP 服务器吗？

可以。单个 Skill 可以同时协调多个 MCP 服务器。例如「技术竞品分析」Skill 可能在 Google Drive 搜内部研究、从 GitHub 拉竞品仓库、再通过网页搜索收集市场信息。

#### 能针对一个 MCP 服务器做多个 Skill 吗？

可以。Skill 能放大单一 MCP 连接的价值。Notion 用独立 Skill 分别覆盖会议筹备、研究、知识沉淀、从 spec 到实现等场景，可在[此处](https://claude.com/connectors/notion)查看。

## 上手

准备用 Skills 与 MCP 开建？可以按下面起步：

**Skills：**

- 在 [claude.ai](https://claude.ai/) 的 Settings → Capabilities 中启用 Skills
- 浏览 [skills library](https://github.com/anthropics/skills) 中的预置示例
- 阅读 [Skills 文档](https://docs.anthropic.com/en/docs/agents-and-tools/agent-skills)

**MCP：**

- 在 [MCP servers](https://github.com/modelcontextprotocol/servers) 中查找适合你工具的 server
- 阅读 [MCP 文档](https://modelcontextprotocol.io/introduction)
- 按 [MCP quick start](https://modelcontextprotocol.io/quickstart) 自建 server

**组合使用：**

- 先连接 MCP 服务器，再添加使用它的 Skill

## 相关文章

延伸阅读：如何用 Claude 的 agent 能力构建产品。

- [Skills explained: How Skills compares to prompts, Projects, MCP, and subagents](https://www.claude.com/blog/skills-explained)
- [Improving frontend design through Skills](https://www.claude.com/blog/improving-frontend-design-through-skills)
- [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
