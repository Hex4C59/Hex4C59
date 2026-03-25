+++
title = "Skills 详解：与 prompts、Projects、MCP、Subagents 如何分工与配合"
date = 2026-03-25T12:00:00+08:00
lastmod = 2026-03-25T12:00:00+08:00
draft = false
author = "Hex4C59"
description = "说明 Claude 生态中 Skills、prompts、Projects、Subagents、MCP 各自解决什么问题、何时选用，以及如何组合成研究型 agent 等工作流。"
summary = "Skills 负责可复用的程序性知识与渐进式加载；Projects 承载长期背景与知识库；MCP 接数据与工具；Subagents 做隔离与分工；prompts 负责当下对话微调。"
tags = []
categories = ["Translations"]
topics = ["agent-skills", "claude", "mcp", "claude-code", "projects"]
translation_category = "AI 与工具"
original_title = "Skills explained: How Skills compares to prompts, Projects, MCP, and subagents"
original_url = "https://claude.com/blog/skills-explained"
original_author = "Anthropic"
original_date = "2025-11-13"
original_site = "Claude Blog"
ShowToc = true
+++

> **译文信息**  
> - 原文：[Skills explained: How Skills compares to prompts, Projects, MCP, and subagents](https://claude.com/blog/skills-explained)  
> - 作者：Anthropic  
> - 原文发布：2025-11-13  
> - 翻译发布：2026-03-25（东八区）

自 [Skills](https://www.anthropic.com/news/skills) 推出以来，不少人希望弄清 Claude 的 agent 生态里各组件如何协同。

无论你是在 [Claude Code](https://www.claude.com/product/claude-code) 里搭复杂工作流、用 API 做企业方案，还是在 [Claude.ai](https://claude.ai/) 上提升日常效率，**知道该伸手拿哪件工具、什么时候用**，都会显著改变你与 Claude 的配合方式。

本篇拆解每一块「积木」、说明选型时机，并展示如何组合出强有力的 agent 工作流。

## 理解你的 agent 能力积木

### Skills 是什么？

Skills 是包含说明、脚本与资源的文件夹；Claude 会在与任务相关时**发现并动态加载**它们。可以把它想成**分领域的培训手册**，让 Claude 在特定场景具备专长——从处理 Excel 表格到遵循组织的品牌规范。

**Skills 如何运作：** 遇到任务时，Claude 会扫描可用 Skills 寻找匹配项。Skills 采用 **progressive disclosure（渐进式披露）**：先加载元数据（约 100 tokens），让 Claude 判断是否与当前任务相关；需要时再加载完整说明（少于 5k tokens）；捆绑文件或脚本仅在确有需要时加载。

**何时用 Skills：** 当你需要 Claude **稳定、高效地完成专项任务**时选用。特别适合：

- **组织级工作流**：品牌规范、合规流程、文档模板  
- **领域能力**：Excel 公式、PDF 处理、数据分析  
- **个人偏好**：笔记体系、编码习惯、研究方法  

**示例：** 搭建 [品牌规范 Skill](https://github.com/anthropics/skills/tree/main/skills/brand-guidelines)，纳入公司色板、字体与版式规则。之后 Claude 做演示或文档时会自动套用这些标准，无需你每次重讲一遍。

进一步了解 Skills 可阅读 [官方说明](https://support.claude.com/en/articles/12512176-what-are-skills)，并浏览 [不断扩充的 Skills 库](https://github.com/anthropics/skills)。

### prompts 是什么？

[Prompts](https://docs.claude.com/en/prompt-library/library) 是你在对话中用自然语言给 Claude 的指令。它们是**即时、对话式、被动响应**的——你在当下提供语境与方向。

**何时用 prompts：**

- 一次性请求：如「总结这篇文章」  
- 对话中打磨：如「语气再专业一点」  
- 即时上下文：如「分析这些数据并指出趋势」  
- 临时指令：如「改成项目符号列表」  

**示例：**

请对本代码做一次全面的安全审查。我希望包括：

1. 常见漏洞，例如：

- 注入类（SQL、命令、XSS 等）  
- 认证与授权问题  
- 敏感数据暴露  
- 安全配置错误  
- 失效的访问控制  
- 密码学实现问题  
- 输入校验不足  
- 错误处理与日志问题  

2. 对每个问题请给出：

- 严重程度（Critical/High/Medium/Low）  
- 在代码中的位置（行号或函数名）  
- 为何构成风险、可能被如何利用  
- 具体修复建议（尽量附代码示例）  
- 防止同类问题的最佳实践  

3. 代码背景：\[说明代码用途、语言/框架与运行环境——例如「这是一个 Node.js REST API，负责用户鉴权并处理支付数据」\]

4. 其他考量：

- 是否存在 OWASP Top 10 类问题？  
- 是否符合 \[某框架/语言\] 的安全最佳实践？  
- 依赖是否存在已知漏洞？  

请按严重度与潜在影响排序输出。

**提示：** prompts 是你与 Claude 交互的主要方式，但**不会跨会话保留**。若同一套流程或专业知识会反复用到，可考虑固化成 Skills 或 Project 说明。

**何时改用 Skill：** 若在多个会话里反复输入同一段 prompt，就该做成 Skill。把「按 OWASP 标准做代码安全审查」「输出需含执行摘要、要点与建议」这类重复指令变成 Skill，可省去每次复述，并保证执行一致。

入门还可查看 [prompt 库](https://docs.claude.com/en/prompt-library/library)、[prompt 工程最佳实践](https://claude.com/blog/prompt-engineering-best-practices)，或使用 [智能 prompt 生成器](https://claude.ai/public/artifacts/3796db7e-4ef1-4cab-b70c-d045778f23ec)。

### Projects 是什么？

在所有付费计划中，[Projects](https://support.claude.com/en/articles/9517075-what-are-projects) 是自带聊天记录与知识库的**独立工作区**。每个 Project 有 **200K** 的上下文窗口，可上传文档、补充背景，并设置对该 Project 内**所有对话**生效的自定义说明。

**Projects 如何运作：** 上传到 Project 知识库的内容，在该 Project 下的所有会话中均可使用；Claude 会据此给出更贴合的回答。当知识体量接近上下文上限时，Claude 会无缝启用 **Retrieval Augmented Generation（RAG）**，将可用容量扩展约 **10 倍**。

**何时用 Projects：**

- **持久上下文**：应在每次对话中生效的背景知识  
- **工作区划分**：不同事项分开管理  
- **团队协作**：共享知识与对话历史（Team、Enterprise 计划）  
- **自定义说明**：该 Project 专属的口吻、视角或方法  

**示例：** 建一个「Q4 产品发布」Project，放入市场调研、竞品资料与产品规格；该 Project 下任意会话都能用到这些材料，无需重复上传或复述。

**何时改用 Skill：** Projects 为**某一摊子工作**提供持久背景——公司代码库、研究课题、长期客户项目等。**Skills 教的是「怎么做」**。一个 Project 可以装下产品发布的全部背景，而一个 Skill 可以教 Claude 你们团队的写作规范或 code review 流程。若在多个 Project 里复制同一段说明，更适合抽成 Skill。

更多见 [Projects 说明](https://support.claude.com/en/articles/9517075-what-are-projects)。

### Subagents 是什么？

[Subagents](https://docs.claude.com/en/docs/claude-code/sub-agents) 是带有**独立上下文窗口**、**自定义 system prompt** 与**特定工具权限**的专用 AI 助手。在 Claude Code 与 Claude Agent SDK 中可用；它们独立处理子任务，再把结果交回主 agent。

**Subagents 如何运作：** 每个 subagent 有独立配置——你定义其职责、解题方式与可用工具。Claude 可根据描述自动把任务派给合适的 subagent，你也可以显式指定某一个。

**何时用 subagents：**

- **任务专精**：代码审查、测试生成、安全审计  
- **上下文管理**：主对话保持聚焦，把专项工作交出去  
- **并行处理**：多个 subagent 可同时处理不同方面  
- **工具约束**：限制为安全操作（例如只读）  

**示例：**

```text
创建一个 code-reviewer subagent，仅允许 Read、Grep、Glob，不允许 Write 或 Edit。你改代码时，Claude 会自动把质量与安全审查交给该 subagent，降低误改代码的风险。
```

**何时改用 Skill：** 若多种 agent 或会话都需要同一套专长——如安全审查流程、数据分析套路——应做成 **Skill**，而不是写进每个 subagent。Skills **可移植、可复用**；subagents 为**特定工作流量身定制**。用 Skills 传授任何 agent 都能用的专长；用 subagents 当你需要**独立执行**、**特定工具权限**与**上下文隔离**时。

更多见 [subagents 文档](https://code.claude.com/docs/en/sub-agents)。

### MCP 是什么？

MCP 在 AI 应用与你现有的工具、数据源之间提供**通用连接层**。

**Model Context Protocol（MCP）** 是开放标准，用于把 AI 助手接到数据所在的外部系统——内容库、业务工具、数据库与开发环境等。

**MCP 如何运作：** MCP 用统一方式把 Claude 接到工具与数据源。不必为每个数据源各写一套集成，只需按同一协议对接。**MCP server** 暴露数据与能力；**MCP client**（如 Claude）连接这些 server。

**何时用 MCP：** 当你需要 Claude：

- **访问外部数据**：Google Drive、Slack、GitHub、数据库  
- **使用业务工具**：CRM、项目管理平台  
- **连接开发环境**：本地文件、IDE、版本控制  
- **对接自研系统**：内部工具与数据源  

**示例：** 通过 MCP 把 Claude 接到公司 Google Drive，即可搜索文档、读取文件、引用内部知识，而无需手动上传——连接可持续存在并随数据更新。

**何时改用 Skill：** MCP 让 Claude **连上数据**；Skills 教 Claude **拿数据做什么**。若在说明「如何用工具、如何走流程」——例如「查库必须先按日期范围过滤」「Excel 报表必须用这些公式」——那是 **Skill**。若首先要让 Claude **能访问**数据库或 Excel 文件，那是 **MCP**。二者常一起用：MCP 负责连通，Skills 负责程序性知识。

进一步了解 MCP 见 [Anthropic 介绍](https://www.anthropic.com/news/model-context-protocol)；自建 server 见 [MCP 文档](https://modelcontextprotocol.io/docs/develop/build-server)。

## 如何协同发力

真正威力来自**组合使用**。每一块职责不同，合在一起可搭出复杂的 agent 工作流。

### 对照：如何选型

| 维度 | Skills | Prompts | Projects | Subagents | MCP |
| --- | --- | --- | --- | --- | --- |
| **提供什么** | 程序性知识 | 逐轮即时指令 | 背景知识 | 任务委派 | 工具与数据连通 |
| **持久性** | 跨会话 | 单次会话 | 在 Project 内 | 跨会话（会话级配置） | 持续连接 |
| **内含** | 说明 + 代码 + 资源 | 自然语言 | 文档 + 上下文 | 完整 agent 逻辑 | 工具定义 |
| **加载时机** | 按需动态 | 每轮对话 | 在 Project 中始终可用 | 被调用时 | 常时可用 |
| **能否含代码** | 能 | 否 | 否 | 能 | 能 |
| **最适用** | 专项能力 | 快速请求 | 集中式上下文 | 专项任务执行 | 数据访问 |

### 示例工作流：研究型 agent

下面用多块积木拼一个**竞品分析**向的研究 agent。

**步骤 1：搭建 Project**

创建 「Competitive Intelligence」Project 并上传：

- 行业报告与市场分析  
- 竞品产品文档  
- CRM 中的客户反馈  
- 以往研究摘要  

在 Project 说明中加入：

从我们的产品战略视角分析竞品。关注差异化机会与新兴趋势。结论需有具体证据与可执行建议。

**步骤 2：用 MCP 接数据源**

启用例如：

- Google Drive（共享研究文档）  
- GitHub（竞品开源仓库）  
- Web search（实时市场信息）  

**步骤 3：编写专项 Skills**

例如 `competitive-analysis` Skill：

```text
# My Company GDrive Navigation Skill

## Overview
Optimized search and retrieval strategy for Meridian Tech's Google Drive structure. Use this skill to efficiently locate internal documents, research, and strategic materials.

## Drive Organization

**Top-level structure:**
- `/Strategy & Planning/` - OKRs, quarterly plans, board decks
- `/Product/` - PRDs, roadmaps, technical specs
- `/Research/` - Market research, competitive intel, user studies
- `/Sales & Marketing/` - Case studies, pitch decks, campaign materials
- `/Customer Success/` - Implementation guides, success metrics
- `/Company Ops/` - Policies, org charts, team directories

**Naming conventions:**
- Format: `YYYY-MM-DD_DocumentName_vX`
- Final versions marked with `_FINAL`
- Drafts include `_DRAFT` or `_WIP`

## Search Best Practices

1. **Start broad, then filter** - Use folder context + keywords
2. **Target document owners** - Sales materials from Sales/, not root
3. **Check recency** - Prioritize documents from last 6 months for current strategy
4. **Look for "source of truth"** - Files with `_FINAL`, `_APPROVED`, or in `/Archives/Official/`

## Research Agent Workflow

1. Identify topic category (product, market, customer)
2. Search relevant folder with targeted keywords
3. Retrieve 3-5 most recent/relevant documents
4. Cross-reference with `/Strategy & Planning/` for context
5. Cite sources with file names and dates
```

**步骤 4：配置 subagents（仅 Claude Code / SDK）**

例如 `market-researcher`：

```text
name: market-researcher
description: Research market trends, industry reports, and competitive landscape data. Use proactively for competitive analysis.
tools: Read, Grep, Web-search
---
You are a market research analyst specializing in competitive intelligence.

When researching:
1. Identify authoritative sources (Gartner, Forrester, industry reports)
2. Gather quantitative data (market share, growth rates, funding)
3. Analyze qualitative insights (analyst opinions, customer reviews)
4. Synthesize trends and patterns

Present findings with citations and confidence levels.
```

以及 `technical-analyst`：

```text
name: technical-analyst
description: Analyze technical architecture, implementation approaches, and engineering decisions. Use for technical competitive analysis.
tools: Read, Bash, Grep
---
You are a technical architect analyzing competitor technology choices.

When analyzing:
1. Review public repositories and technical documentation
2. Assess architecture patterns and technology stack
3. Evaluate scalability and performance approaches
4. Identify technical strengths and limitations

Focus on actionable technical insights that inform our product decisions.
```

**步骤 5：激活研究 agent**

当你问 Claude：「分析我们前三名竞品如何定位新的 AI 功能，并指出我们可以利用的缺口」，大致会发生：

1. **Project 上下文载入**：使用已上传的研究材料并遵循 Project 说明  
2. **MCP 连接生效**：在 Drive 中搜最新竞品简报、拉取 GitHub 数据  
3. **Skills 介入**：competitive-analysis Skill 提供分析框架  
4. **Subagents 执行**（在 Claude Code 中）：market-researcher 汇总行业信息，technical-analyst 看技术实现  
5. **Prompts 微调**：你用对话补充：「尤其关注医疗行业的 enterprise 客户」  

**结果：** 一份综合竞品分析，融合多数据源、遵循你的分析框架、调用专项能力，并在整个研究 Project 中保持上下文连贯。

## 常见问题

#### Skills 具体怎么工作？

Skills 借助 [progressive disclosure](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) 保持高效。执行任务时，Claude 先扫 Skill 元数据（描述与摘要）做匹配；命中后再加载完整说明；若含可执行代码或参考文件，则仅在需要时再加载。

因此可以同时启用很多 Skills 而不轻易撑爆上下文——Claude 只取当下所需。

#### Skills 与 subagents：怎么选？

**用 Skills：** 希望任意 Claude 实例都能加载、复用的能力。Skills 像培训材料，让 Claude 在多种对话里更擅长特定任务。

**用 subagents：** 需要为特定目的设计的、可独立跑完流程的完整助手。Subagents 像各有工位与权限的专员。

**一起用：** 让 subagent 带上专项 Skill。例如 code-review subagent 可加载某语言的 best-practice Skill，兼顾独立性与可迁移的专长。

#### Skills 与 prompts：怎么选？

**用 prompts：** 一次性指令、即时上下文、多轮对话微调。Prompts 被动且随会话结束而失效。

**用 Skills：** 会反复用到的流程或专业知识。Skills 更主动——Claude 知道何时启用——且跨会话保留。

**一起用：** Skills 打底，prompts 针对当前任务补充语境与微调。

#### Skills 与 Projects：怎么选？

**用 Projects：** 某一 initiative 下所有对话都应知晓的背景知识。Projects 提供相对静态、持续在场的参考资料。

**用 Skills：** 程序性知识与可执行代码，仅在相关时加载。Skills 提供动态专长，节省上下文。

**一起用：** 既要长期背景又要专项能力。例如「产品开发」Project 放规格与用户研究，再配合撰写技术文档、分析反馈数据的 Skills。

**关键差异：** Projects 说「你需要知道这些」；Skills 说「事情要这样做」。Projects 是工作所处的知识库；Skills 是随处可用的能力——不限于某次对话或某个 Project。

#### Subagents 能用 Skills 吗？

可以。在 Claude Code 与 Agent SDK 中，subagents 与主 agent 一样可使用 Skills，从而形成「专员 + 可移植专长」的组合。

例如：`python-developer` subagent 使用 pandas-analysis Skill 按团队规范做数据变换；`documentation-writer` subagent 使用 technical-writing Skill 统一 API 文档格式。

## 上手

准备用 Skills 开建？可以按角色起步：

**[Claude.ai](https://claude.ai/) 用户：**

- 在 Settings → Features 中启用 Skills  
- 在 [claude.ai/projects](https://claude.ai/projects) 创建第一个 Project  
- 下一次分析任务试着把 Project 知识与 Skills 一起用  

**API 开发者：**

- 在 [文档](https://docs.anthropic.com/) 中查看 Skills 相关 API  
- 参考 [skills cookbook](https://platform.claude.com/cookbook/skills-notebooks-01-skills-introduction)  

**Claude Code 用户：**

- 通过 [插件市场](https://code.claude.com/docs/en/plugin-marketplaces) 安装 Skills  
- 同样可参考 [skills cookbook](https://platform.claude.com/cookbook/skills-notebooks-01-skills-introduction)  
