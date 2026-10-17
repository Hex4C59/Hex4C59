+++
title = "Skill：不改模型、不写代码，教会 Agent 做专家级别的事"
date = 2026-03-23T17:30:00+08:00
draft = false
author = "Hex4C59"
description = "用博客写作示例解释 Skill 如何提供项目规范、操作步骤和验收标准，以及发现、读取和按需加载参考资料的过程与限制。"
summary = "Skill 是供 Agent 读取的任务说明。本文区分它与工具、系统指令和微调的作用，说明何时读取主文件、何时查参考，以及为什么保存文档不等于模型永久学会。"
tags = ["Agent Skills", "提示词工程", "知识管理"]
categories = ["ai"]
series = ["agent-engineering"]
series_order = 12
difficulty = "beginner"
article_type = "concept"
topics = ["skill", "knowledge", "prompt", "agent", "architecture"]
frameworks = ["Cursor", "OpenAI"]
ShowToc = true
source_kind = "original"
lastmod = 2026-10-17
+++

在这个系列里，我们花了大量篇幅讨论 Agent 的执行能力：[Tool Use](/agent/tool-use-core-of-agent/) 让它能连接外部世界，[MCP](/agent/mcp-model-context-protocol/) 让工具生态可以标准化复用，[工具接口设计](/agent/tool-interface-design/)让工具真正好用。

但有一个问题，讨论工具时往往不会深入触碰：**Agent 知道该怎么用这些工具吗？**

不是"能不能调用"的问题——模型显然可以生成工具调用请求。而是"知不知道在什么场景下、用什么策略、按什么顺序、以什么标准来使用它们"的问题。

举一个具体的例子：你给一个 Coding Agent 接上了文件读写、代码搜索、终端执行这些工具。它能用。但它知道你的项目用 Hugo 而不是 Next.js 吗？它知道你的博客文章要用 TOML front matter 而不是 YAML 吗？它知道你的 Agent 系列文章必须以"先给结论"开头吗？

这些不是工具能力的问题，是**领域知识**的问题。模型训练时不可能覆盖每个人的每个项目、每个团队的每套规范、每个领域的每种最佳实践。

Skill（技能）把这些项目知识整理成可读取的任务说明。本文面向会写简单代码、未配置过 Skill 的读者，解释它如何被发现、何时读取正文和参考资料，以及与工具怎样配合。标题中的“专家级别”表达应用目标，不能仅靠写一份文档保证达到。

---

## 先给结论

1. **Skill 是一种结构化的知识模块，用来教 Agent 在特定领域或任务中如何正确行动。** 它不是工具，不改模型权重，本质上是"写给 Agent 看的操作手册"。
2. **Skill 解决的核心问题是：通用模型缺少特定领域的操作知识。** 模型很聪明，但它不知道你的项目结构、你的编码规范、你的部署流程——除非你告诉它。
3. **Skill 和 Tool 是互补关系，不是替代关系。** Tool 提供"能做什么"（能力），Skill 提供"该怎么做"（知识）。一个知道用锤子的人，和一个知道钉子该往哪钉的人，不是同一回事。
4. **Skill 可以复用和共享，通常不需要为此训练模型。** 保存说明后，Agent 仍需在相关任务中读取它；这不会让模型永久记住内容，也不免除调用与维护成本。
5. **Skill 正在从个人实践走向生态化。** Cursor、Codex 等产品已经原生支持 Skill 机制，社区共享的 Skill 库正在形成。

---

## 从一个真实场景说起

假设你有一个 Hugo 博客，里面有一个 Agent 专题系列。你希望 AI 助手帮你写下一篇文章。

你对它说："帮我写一篇关于 Guardrails 的博客。"

在这个假设中，如果 Agent 没有从其他指令或文件获得项目规范，就可能出现这些不符合要求的写法：

- front matter 用了 YAML 而不是 TOML
- 没有 `series_order`、`difficulty`、`article_type` 这些你自定义的字段
- 时区写成了 UTC 而不是 +08:00
- 缺少"先给结论"这个你的系列必有的章节
- 代码示例用了 JavaScript 而不是你习惯的 Python + OpenAI SDK
- 没有引用系列里其他文章的链接

这些问题每一个都很小，但组合起来，意味着你拿到的草稿需要大量手动修改。

而如果这个 Agent 在执行前先读了一份 Skill，里面清楚写着你的 front matter 格式、文章结构规范、代码风格偏好和跨文章引用惯例——它生成的内容就能直接接近你的标准。

**这就是 Skill 最直观的价值：让 Agent 从"通用地聪明"变成"在你的场景里真正好用"。**

---

## Skill 到底是什么

用最简单的定义：

> **Skill 是一份写给 Agent 看的结构化文档，告诉它在特定任务中应该遵循什么知识、什么流程、什么标准。**

它通常包含三个部分：

### 1. 元数据：Agent 怎么发现它

```yaml
---
name: write-agent-blog
description: >-
  Write blog posts for the Hugo + PaperMod Agent series. Use when the user asks
  to create, draft, or write a new Agent blog post.
---
```

`name` 标识这份 Skill，`description` 说明它处理什么任务、何时适用。在支持按描述选择 Skill 的宿主中，Agent 会先查看列表中的 `description`，再按任务决定是否读取正文；用户也可以明确指定。

因此，要区分三个动作：发现列表中有这份说明、读取它的内容、按内容执行。第一步发生了，不代表后两步必然完成。

### 2. 知识内容：Agent 需要知道什么

这是 Skill 的核心部分。它可以包含：

- **项目结构信息**：哪些目录放什么文件、配置文件在哪
- **格式规范**：front matter 模板、代码风格、命名约定
- **工作流程**：创建新内容的步骤、部署流程、测试流程
- **领域概念**：特定业务的术语定义、设计约束
- **示例**：好的输出长什么样、坏的输出长什么样

优先写**当前任务需要、又不能靠通用知识推断的要求**。例如，不必大篇幅介绍 Markdown 语法，而应说明本项目使用哪种 front matter、代码依赖什么 SDK、文章有哪些验收条件。必要的背景仍可保留，不能因为模型可能知道就省掉执行所需的前提。

### 3. 参考资料：太长的内容怎么办

如果某些知识量很大（比如完整的 API 文档、几十条编码规则），不应该全塞进一份文件里。正确的做法是**渐进式披露**：

```markdown
## 快速上手
[核心指令，30 行以内]

## 详细参考
- 完整的 front matter 字段说明，见 [reference.md](reference.md)
- 历史文章的风格示例，见 [examples.md](examples.md)
```

这就是渐进式披露：主文件给出操作步骤，并说明什么情况下需要读哪份参考。Agent 按当前任务读取必要内容，可以减少一次加载的篇幅；是否完整，还要检查必读参考是否实际读过。

---

## Skill 和其他概念的区别

这是很多人初次接触 Skill 时最容易混淆的地方。

### Skill vs Tool

这是最根本的区别。

| | Tool | Skill |
|---|---|---|
| 本质 | 可执行的能力 | 结构化的知识 |
| 做什么 | 让 Agent 能"做"某件事 | 让 Agent 知道"怎么做好"某件事 |
| 形态 | API、函数、命令行工具 | 文档、指令、模板、示例 |
| 运行时行为 | Agent 调用它来产生副作用 | Agent 读取它来指导决策 |
| 例子 | `read_file`、`search_web`、`run_command` | "如何写 Agent 博客"、"代码审查标准" |

一个比喻：Tool 是 Agent 的**手**，Skill 是 Agent 的**经验**。

你可以给一个人一把手术刀（Tool），但如果他不知道人体解剖结构（Skill），这把刀没有意义。反过来，一个外科医生没有手术刀也做不了手术。两者缺一不可。

### Skill vs System Prompt

System prompt 也可以给 Agent 传递指令，但两者的设计目标不同。

| | System Prompt | Skill |
|---|---|---|
| 作用范围 | 全局，影响所有对话 | 按需加载，只影响相关任务 |
| 内容量 | 通常较短（几百到几千 token） | 可以很长（通过渐进式披露） |
| 可复用性 | 绑定在单个 Agent 配置里 | 可以跨项目、跨 Agent 共享 |
| 发现方式 | 手动配置 | Agent 自动匹配 |
| 适合的内容 | 身份设定、全局行为规则 | 特定任务的领域知识和操作流程 |

简单说：System prompt 定义 Agent "是谁"，Skill 定义 Agent "在某个领域里该怎么做"。

### Skill vs Fine-tuning

这是一个更重要的对比，因为两者在某种程度上解决的是同一个问题——让模型在特定领域表现更好。

| | Fine-tuning | Skill |
|---|---|---|
| 修改对象 | 模型权重 | 上下文（prompt / 文档） |
| 成本 | 训练数据、计算与部署开销 | 编写维护文档、读取与执行的开销 |
| 生效速度 | 训练与部署后验证 | 相关任务读取新版说明后验证 |
| 迭代速度 | 慢（重新训练） | 快（修改文档即可） |
| 适用模型 | 只影响被微调的那个模型 | 适用于任何能读上下文的模型 |
| 深度 | 深（改变模型的内在行为模式） | 浅（引导模型的当前行为） |
| 适合场景 | 需要改变模型核心行为（风格、格式、推理方式） | 需要补充领域知识和操作规范 |

**如果缺的是项目规则和步骤，可以先尝试 Skill，再判断是否需要 fine-tuning（微调）。** Skill 把说明放进任务输入，微调则用训练样本改变模型参数。若模型无法完成基础判断或操作，仅补文档也不一定够用；应在目标任务中验证。

---

## Skill 是怎么工作的

一个完整的 Skill 工作流程：

![Skill 工作流程](skill_workflow.svg)

### 关键机制：自动发现

Skill 系统最巧妙的地方在于**自动发现**——Agent 不需要用户显式指定使用哪个 Skill，而是通过 `description` 字段自动匹配。

`description` 帮助 Agent 判断适用范围，但触发还受宿主是否发现该文件、用户要求和可用上下文影响。描述应让执行者知道做什么、什么时候读，不能只写一个宽泛主题。

**好的 description：**

```yaml
description: >-
  Write blog posts for the Hugo + PaperMod Agent series. Use when the user asks
  to create, draft, or write a new Agent blog post, or when they want to add
  content to the Agent section of the blog.
```

这段描述同时包含了两个关键信息：**做什么**（Write blog posts for the Agent series）和**什么时候触发**（when the user asks to create, draft, or write）。

**不好的 description：**

```yaml
description: "帮助写作"
```

太模糊了。Agent 无法判断这个 Skill 是帮写博客、帮写邮件还是帮写代码注释。

### 存储位置

Skill 通常有两种存储位置：

| 类型 | 路径 | 适用场景 |
|------|------|---------|
| 个人级别 | `~/.cursor/skills/skill-name/SKILL.md` | 你个人的通用规范（代码风格、commit 格式） |
| 项目级别 | `.cursor/skills/skill-name/SKILL.md` | 特定项目的规范（跟代码一起提交，团队共享） |

表中的目录是产品配置示例，不是所有宿主通用的路径。项目级说明可以跟代码仓库一起共享；团队成员仍需使用能发现并读取它的宿主和配置。clone 仓库只取得文件，不等于模型已经读过规范。

---

## 怎么设计一个好的 Skill

### 原则一：只写 Agent 不知道的

这是最重要的原则。Agent 的上下文窗口是有限的，Skill 占据的每一个 token 都在和其他信息竞争空间。

```markdown
<!-- 不需要写这些 -->
Markdown 是一种轻量级标记语言，使用 # 表示标题...
Python 是一种编程语言，使用 def 定义函数...

<!-- 需要写这些 -->
本项目使用 TOML 格式的 front matter，不是 YAML。
所有 Agent 系列文章必须包含 series = ["agent-engineering"]。
代码示例统一使用 Python + openai SDK，async 风格。
```

### 原则二：具体胜过泛化

```markdown
<!-- 太泛了，Agent 不知道具体要怎么做 -->
请写出高质量的文章。

<!-- 具体到可执行 -->
每篇文章必须以"先给结论"章节开头，包含 3-5 条编号的核心判断。
每条判断必须加粗关键句，然后用 1-2 句话展开。
```

### 原则三：用示例传递隐性知识

有些知识很难用规则描述清楚，但一看示例就懂了。

```markdown
## 文章开头的写法

好的开头示例（从已有文章中提取）：

> 在前面几篇文章里，我们把 Agent 的执行能力搭起来了：ReAct 让它边推理边行动，
> Planning 让它在长任务里保持全局视图。但有一个能力一直没有专门讨论……

特点：引用系列前文 → 提出空白点 → 引出本篇主题。
避免：不要用"大家好，今天我们来聊聊……"这类开头。
```

### 原则四：控制长度，渐进披露

Skill 的主文件建议控制在 **500 行以内**。超出的内容拆分到参考文件中。

```markdown
## 快速上手
[核心规则和模板，150 行]

## 深入了解
- 完整字段说明：[reference.md](reference.md)
- 风格示例库：[examples.md](examples.md)
```

主文件应写明参考资料的读取条件，例如修改 front matter 前必须核对字段说明，延续文风时再看示例。这样执行者知道哪些资料不可省略，哪些仅在特定任务中需要。

---

## 一个完整的 Skill 示例

以"给 Hugo 博客写 Agent 系列文章"这个场景为例：

```
write-agent-blog/
├── SKILL.md           # 主文件：核心规范和流程
```

**SKILL.md 的核心内容（节选）：**

```markdown
---
name: write-agent-blog
description: >-
  Write blog posts for the Hugo + PaperMod Agent series. Use when the user asks
  to create, draft, or write a new Agent blog post.
---

# Write Agent Blog Post

## Front Matter 模板

每篇 Agent 文章使用 TOML front matter：

（模板内容）

## 文章结构

1. 开头 2-3 段：设定问题，引用系列前文
2. 先给结论：3-5 条核心判断
3. 问题分析：为什么这件事重要
4. 核心概念：定义和架构
5. 实现细节：Python 代码示例
6. 失败场景：至少 2-3 个
7. 总结：3-5 条要点

## 代码风格

- Python + openai SDK，async/await
- 代码注释用中文
- 使用 gpt-4o 作为默认模型
```

当用户对 Agent 说"帮我写一篇关于 Guardrails 的博客"时，Agent 会：

1. 发现 `write-agent-blog` 这个 Skill 和任务相关
2. 读取 SKILL.md，获得项目规范
3. 按照规范中的 front matter 模板、文章结构和代码风格来生成内容

整个过程对用户来说是透明的——你不需要每次都告诉 Agent "记得用 TOML"、"记得写先给结论"。

---

## Skill 和 MCP 的关系

在 [MCP](/agent/mcp-model-context-protocol/) 那篇里，我们讨论了工具生态的标准化。MCP 解决的是"Agent 怎么连接外部工具"的问题。

Skill 解决的是另一半："Agent 连上工具之后，怎么用好它们。"

![MCP 与 Skill 的分工](skill_vs_mcp.svg)

两者可以组合：MCP（Model Context Protocol，模型上下文协议）约定怎样发现并调用外部工具，Skill 说明某项任务该选择哪些工具、按什么顺序使用、怎样检查结果。两者都不能代替实际授予的权限。

---

## Skill 的生态趋势

Skill 不是某个产品的私有概念，它正在成为 Agent 生态中的一个通用模式。

### 已经支持 Skill 机制的产品

- **Cursor**：通过 `.cursor/skills/` 目录支持项目级和个人级 Skill
- **Codex (OpenAI)**：通过 `~/.codex/skills/` 支持 Skill，并提供可安装的 Skill 列表
- **Claude Code**：通过 `CLAUDE.md` 文件实现类似机制（虽然叫法不同，但本质一样）
- **Windsurf**：通过 `.windsurfrules` 支持项目级规则

上面同时列了 Skill 与项目规则文件的例子。它们都能传递任务说明，但不能因此认为是同一种机制：是否按任务加载、如何触发、从哪里读取，仍要按对应产品和版本检查。这份列表用于比较说明文件的用途，具体支持情况需查看所用版本。

### Skill 共享与社区

当 Skill 的格式和存储方式变得标准化之后，社区共享就成了自然的下一步。

想象一个场景：你要开始一个新的 Python 项目，你可以直接安装社区里已有的 Skill：

```bash
# 假设的 Skill 安装命令
codex skills install python-best-practices
codex skills install git-commit-conventions
codex skills install docker-deployment
```

在这个假设中，安装只是把说明文件放到宿主可发现的位置；执行相关任务时，Agent 还要读取内容，并检查其中步骤是否适合当前项目。命令仅作设想，不能当作真实安装入口。

这和 npm / pip 包管理的逻辑是一样的——只不过管理的不是代码依赖，而是**知识依赖**。

---

## Skill 的局限性

Skill 不是万能的，了解它的边界同样重要。

### 上下文窗口的限制

Skill 的内容需要被注入到模型的上下文中。如果 Skill 太长（几千行），它会显著压缩模型可用于处理任务本身的上下文空间。这就是为什么渐进式披露如此重要——核心内容要精简，详细参考按需加载。

### 不能替代深层能力

如果模型本身不具备某种能力（比如精确的数学计算、特定编程语言的高级语法），Skill 教不会它。Skill 能教"怎么做"，但前提是模型有"做"的基础能力。

这就像给一个不会游泳的人写一份详细的游泳教程——教程再好，他跳进水里还是可能出问题。Skill 的价值建立在模型已有能力的基础上。

### 依赖 description 质量

如果 Skill 的 `description` 写得模糊或者与任务不匹配，Agent 可能根本不会触发这个 Skill。描述精确有助于选择，但文件是否被发现、宿主如何加载、用户怎样指定，也会影响实际使用。

### 版本管理和一致性

当项目规范变化时，Skill 也需要同步更新。如果 Skill 过时了但没人维护，Agent 反而会按照过时的规范行事，造成更多混乱。好在项目级 Skill 跟代码放在一起，可以跟随代码一起做版本管理。

---

## 总结

回到最初的问题：Agent 有了工具之后，还缺什么？缺的是知识——不是通用知识，是**你的场景里的特定知识**。

Skill 把项目知识写成可读取的文档，不必为传递这些规则重新训练模型。Agent 仍需在相关任务中读取、执行并检查结果，文档也需要随项目维护。

五个核心要点：

1. **Skill 是写给 Agent 看的操作手册。** 它不改模型、不写代码，用自然语言文档告诉 Agent 在特定领域该怎么做。
2. **Tool 提供能力，Skill 提供知识。** 两者互补。工具让 Agent 能做事，Skill 让 Agent 做对事。
3. **Skill 可以减少重复交代项目规则。** 但只有被发现、读取并执行时才会影响任务，规范变化后也要维护。
4. **好的 Skill 只包含 Agent 不可能自己知道的信息。** 不要重复模型已有的知识，只补充你的项目、你的团队、你的领域特有的规范和经验。
5. **Skill 生态正在形成。** 从个人文档到团队共享，再到社区安装，Skill 有潜力成为 Agent 知识层的"包管理器"。

从更长远的视角看，Skill 代表了一种新的人机协作模式：**你不需要成为 AI 专家才能让 Agent 在你的领域里变得专业，你只需要把你的专业知识写成 Agent 能理解的格式。** 这可能是 Agent 走向真正普及的关键一步。

---

*上一篇：[MCP：让 Agent 的工具生态不再各自为战](/agent/mcp-model-context-protocol/)*
