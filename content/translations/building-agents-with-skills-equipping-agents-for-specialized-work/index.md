+++
title = "用 Skills 构建智能体：为专业化工作装备智能体"
date = 2026-03-25T12:00:00+08:00
lastmod = 2026-10-17
draft = false
author = "Hex4C59"
description = "介绍如何把领域工作流程写成 Agent Skills 文件，按需加载指令和参考资料、复用脚本，并与 MCP 连接的工具和数据配合完成专业工作。"
summary = "通用智能体还需要具体领域的工作方法。Skills 用文件记录这些方法，先展示名称和描述，再按需加载完整指令与参考资料；脚本则让常用操作可以反复执行。"
tags = ["智能体技能", "Claude Code", "模型上下文协议"]
categories = ["ai"]
topics = ["agent-skills", "claude-code", "mcp", "claude-agent-sdk", "agents"]
translation_category = "AI 与工具"
original_title = "Building agents with Skills: Equipping agents for specialized work"
original_url = "https://claude.com/blog/building-agents-with-skills-equipping-agents-for-specialized-work"
original_author = "Barry Zhang, Mahesh Murag, Keith Lazuka, Ryan Whitehead"
original_date = "2026-01-22"
original_site = "Claude Blog"
ShowToc = true
source_kind = "translation"
+++

> **译文信息**  
> - 原文：[Building agents with Skills: Equipping agents for specialized work](https://claude.com/blog/building-agents-with-skills-equipping-agents-for-specialized-work)  
> - 作者：Barry Zhang, Mahesh Murag, Keith Lazuka, Ryan Whitehead  
> - 原文发布：2026-01-22  
> - 翻译发布：2026-03-25（东八区）

Skills 把领域专长写进智能体可以读取并使用的文件，让通用智能体掌握专业工作的方法，足以应对真实工作。

过去一年变化很大。[MCP](https://modelcontextprotocol.io/) 成了智能体连接外部工具与数据源的行业标准，业界与开发者社区快速跟进。[Claude Code 发布](https://www.anthropic.com/news/claude-3-7-sonnet)，成为通用编程智能体。我们还推出了 [Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)，现已提供开箱即用的生产级智能体。

但在构建与部署这些智能体的过程中，我们反复遇到同一道鸿沟：智能体有推理和行动能力，却不总有**有效完成真实工作所需的专长**。这促使我们[创建 Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)。Skills 是由文件组织起来的集合，把工作流、最佳实践、脚本等**领域专长**打包成智能体可以访问并应用的格式。它们把「能干的通才」变成「有经验可循的专家」。

本文将说明，我们为何不再为各个领域分别构建大量智能体，转而选择 Skills，以及这一转变如何改变我们扩展智能体能力的方式。

## 新范式：有代码就够了

我们曾以为不同领域的智能体会截然不同：编程、研究、金融、营销等智能体似乎各自都需要专用工具与配套框架。行业一度倾向于「按领域造智能体」。但随着模型智能水平提升、智能体能力成熟，我们逐渐转向了另一种做法。

我们逐渐把**代码**不仅看作一种用例，更看作智能体完成几乎所有数字工作的**接口**。Claude Code 是编程智能体，也是恰好通过代码工作的通用智能体。

设想用 Claude Code 生成一份财务报告：它可以调用 API 做研究，在文件系统里保存数据，再用 Python 分析数据并汇总发现。这些工作都通过代码完成；配套执行环境可以简单到只有 **bash** 和文件系统。

但**通用能力不等于领域专长**。当我们把 Claude Code 用于真实工作时，这道缺口就暴露出来。

## 缺失的一环：领域专长

你会希望谁替你报税：一位从零推导的数学天才，还是一位报过成千上万份申报的经验丰富的税务师？多数人会选择后者——不是因为更聪明，而是因为**具备对的专长**。

今天的智能体有点像那位数学天才：擅长在陌生情境里推理，却常常缺少资深从业者**长期积累的经验与方法**。在恰当引导下它们能做出惊人成果；但往往缺少关键上下文、难以吸收你所在组织的专长，也不会自动从重复任务中学习。

Skills 把领域专长写成智能体可以**按需逐步读取和使用**的文件，补上这一缺口。

## 什么是 Agent Skills？

Skills 为智能体打包**领域专长**与**完成具体任务的步骤和方法**。

```text
anthropic_brand/
├── SKILL.md
├── docs.md
├── slide-decks.md
└── apply_template.py
```

我们刻意让格式保持简单，因为**文件**可以直接用于现有工具链：用 Git 管理版本、放在 Google Drive，或与团队共享。因此，创建 Skill 的人不必局限于工程师；产品经理、分析师与领域专家已经开始把各自的工作流程写成 Skills。

## 渐进式披露

Skills 可以承载大量信息。为了节省上下文空间，并让多个 Skills 可以一起使用，我们采用**渐进式披露**，也就是按需要逐步展示内容：运行时最初只向模型展示文件头部的元数据（YAML front matter 中的 `name` 与 `description`）。

```yaml
---
name: Anthropic Brand Style Guidelines
description: Anthropic's official brand colors and typography…
---
```

若 Claude 判断需要某个 Skill，它会读取完整 `SKILL.md`。若还需更多细节，Skill 可包含 `references/` 目录，仅在需要时加载补充文档。

这种**三层**设计让你能为智能体配备成百上千个 Skills 而不撑爆上下文——元数据约 **50 tokens**，完整 `SKILL.md` 约 **500 tokens**，参考文件 **2000+ tokens** 且仅在确需时载入。

## Skills 可把脚本当作工具

传统工具有时说明不清，模型难以修改或扩展它们，工具说明还容易挤占上下文。代码则可以用自身的写法说明行为，模型也能修改，而且代码不必一直保留在上下文里。

一个真实例子：我们反复看到 Claude 写同一段脚本，用来把 Anthropic 的幻灯片样式套到演示稿上。于是我们让 Claude 把它存成给自己用的工具：

```python
# anthropic/brand_styling/apply_template.py
import sys
from pptx import Presentation

if len(sys.argv) != 2:
    print("USAGE: apply_template.py <pptx>")
    sys.exit(1)

prs = Presentation(sys.argv[1])
for slide in prs.slides:
    ...
```

`slide-decks.md` 中的对应说明只需引用该脚本：

```markdown
## Anthropic Slide Decks
- Intro/outro slides
  - background color: `#141413`
  - foreground color: oat
- Section slides:
  - background color: `#da7857`
  - foreground color: `#141413`

Use the `./apply_template.py` script to update a pptx file in-place.
```

## Skills 生态

Skills 生态成形很快，目前我们观察到三类主要建设方向：

### 基础型 Skills（Foundational）

提供人人需要的基础能力：处理文档、电子表格、演示稿等。它们记录了生成和处理文档的最佳实践。可在公开仓库中查看[基础 Skills](https://github.com/anthropics/skills/tree/main/skills/public)的具体形态。

### 合作伙伴 Skills（Partner）

随着 Skills 成为智能体对接专业化能力的标准方式，企业正在构建 Skills，让自己的服务可被智能体直接调用。[K-Dense](https://github.com/K-Dense-AI/claude-scientific-skills)、[Browserbase](https://github.com/browserbase/agent-browse)、[Notion](https://www.notion.so/notiondevs/Notion-Skills-for-Claude-28da4445d27180c7af1df7d8615723d0) 与[许多其他方](https://claude.com/blog/organization-skills-and-directory)正在创建与自身服务直接集成的 Skills，在保持 Skills 格式简单的前提下扩展 Claude 在特定领域的能力。

### 企业 Skills（Enterprise）

组织构建专有 Skills，记录内部流程与领域专长。它们把具体工作流程、合规要求与组织积累的知识保存下来，让智能体能够在企业场景中有效工作。

## 我们看到的趋势

随着采用面扩大，几种模式正在浮现，也暗示这一范式可能走向何方。它们影响我们如何看待 Skill 设计以及为 Skill 开发者建设的工具。

### 复杂度在上升

早期 Skills 多为简单文档引用；现在出现更复杂的多步工作流，需要协调数据拉取、复杂计算以及跨多种工具的格式化输出。

- **简单**：「状态报告撰写」（约 100 行）——模板与版式  
- **中等**：「财务模型构建」（约 800 行）——数据拉取、用 Python 做 Excel 建模  
- **复杂**：「RNA 测序流程」（2500+ 行）——协调 HISAT2、StringTie、DESeq2 等分析  

### Skills 与 MCP

[Skills 与 MCP 服务器](https://claude.com/blog/extending-claude-capabilities-with-skills-mcp-servers)天然互补。例如「竞品分析」Skill 可能协调网页搜索、经 MCP 访问的内部数据库、Slack 消息记录与 Notion 页面，综合成一份完整报告。

### 非开发者参与创建

Skill 的创建正从工程师扩展到产品经理、分析师与各学科的领域专家。借助 **skill-creator** 等工具的交互式引导，他们可以在约 30 分钟内创建并测试第一个 Skill。我们也在改进工具与模板，让任何人都能更轻松地沉淀与分享专长。

## 完整架构

综合起来，正在成形的智能体架构大致包含四层：

1. **Agent loop（智能体循环）**：决定下一步做什么的核心推理系统  
2. **Agent runtime（智能体运行时）**：执行环境（代码、文件系统）  
3. **MCP servers**：连接外部工具与数据源  
4. **Skills library**：领域专长与程序性知识  

每一层职责清晰：循环负责推理，运行时负责执行，MCP 负责连接，Skills 负责引导。这种拆分让系统可理解，也让各部分能独立演进。

设想在这一架构上只增加一个 Skill：[frontend design skill](https://github.com/anthropics/claude-code/tree/main/plugins/frontend-design) 会立刻改变 Claude 的前端能力——在排版、色彩理论与动效上给出专门指导，且仅在构建 Web 界面时激活。渐进式披露意味着只在相关时加载。扩展新能力的路径是直接的。

## 向新垂直领域部署 Skills

「通用智能体 + MCP + Skills」这一模式，已经在帮助我们把 Claude 用到更多专业领域。

### 金融服务

在推出 Skills 后不久，我们通过[面向金融服务的 Claude](https://www.anthropic.com/news/claude-for-financial-services)为金融专业人士增强了 Skills，例如：

- **DCF 模型构建**：搭建现金流折现（DCF）模型，含恰当的 WACC 计算与敏感性分析
- **可比公司分析**：生成带相关倍数与对标的可比公司表  
- **财报分析**：处理季度业绩并撰写投资更新报告  
- **首次覆盖**：构建含财务模型的完整研究报告  
- **尽职调查**：用标准化框架组织并购分析  
- **推介材料**：按行业惯例制作客户演示  

### 医疗与生命科学

我们也通过 Skills 强化了[医疗与生命科学](https://www.anthropic.com/news/healthcare-life-sciences)方向的能力，使 Claude 对研究人员、临床人员与医疗开发者更有用，例如：

- **生物信息学套件**：面向 scVI-tools、Nextflow 部署等的 Skills，用于管理基因组流程与单细胞 RNA 测序  
- **临床试验方案生成**：加速临床研究中的方案撰写  
- **科学问题遴选**：帮助研究者找出有影响力的研究问题，并明确其范围
- **FHIR 开发**：帮助开发者编写更准确的健康数据互操作代码，更快连接医疗系统并减少错误  
- **事先授权审核**：对照承保要求、临床指南与患者记录，减轻行政负担、加快患者获得所需照护  

## 标准化 Agent Skills

为实现这一愿景，我们正在将 [Agent Skills](https://agentskills.io/) 作为**开放标准**发布。与 MCP 一样，我们认为 Skills 应在工具与平台间可移植——无论你使用 Claude 还是其他 AI 平台，同一个 Skill 都应能工作。我们已与生态中的成员协作推进该标准，并乐见早期采用。

当有人第一次使用 AI 智能体时，它理应已经知道你和团队在意什么——因为 Skills 捕获并传递了这些专长。随着生态壮大，社区中他人构建的 Skill 也能让你的智能体更有用、更可靠、能力更强——无论他们使用哪一家 AI 平台。

## 入门与延伸阅读

我们正在逐步确定通用智能体的整体架构，Skills 则提供了一种交付与分享新能力的方式。价值来自大家共同构建的知识库：把专长记录下来，在团队间传递，让每一个智能体都比上一个更强。

**资源：**

- [Don't Build Agents, Build Skills Instead](https://youtu.be/CEvIs9y1uog)（YouTube 视频）  
- [Skills 文档](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)  
- [GitHub 仓库](https://github.com/anthropics/skills)  
- [Skills cookbook](https://platform.claude.com/cookbook/skills-notebooks-01-skills-introduction)  
- [在 Claude 中使用 Skills](https://support.claude.com/en/articles/12512180-using-skills-in-claude)  
- [Skills API 快速入门](https://platform.claude.com/docs/en/build-with-claude/skills-guide)  
- [Skills 最佳实践文档](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)  

### 致谢

Barry Zhang, Mahesh Murag, Keith Lazuka, Ryan Whitehead
