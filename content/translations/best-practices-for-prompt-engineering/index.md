+++
title = "Prompt engineering 最佳实践"
date = 2026-03-25T12:00:00+08:00
lastmod = 2026-03-25T12:00:00+08:00
draft = false
author = "Hex4C59"
description = "Claude 团队整理的 prompt engineering 要点：表述清晰、补充动机与约束、示例与预填充、思维链与输出格式控制、串联与排错，以及与 context engineering 的关系。"
summary = "从「说清楚要什么」到预填充 JSON、思维链、串联多步提示；附技巧选择表与常见问题对策。"
tags = []
categories = ["Translations"]
topics = ["prompt-engineering", "claude", "llm", "context-engineering"]
translation_category = "AI 与工具"
original_title = "Best practices for prompt engineering"
original_url = "https://claude.com/blog/best-practices-for-prompt-engineering"
original_author = "Anthropic"
original_date = "2025-11-10"
original_site = "Claude Blog"
ShowToc = true
+++

> **译文信息**  
> - 原文：[Best practices for prompt engineering](https://claude.com/blog/best-practices-for-prompt-engineering)  
> - 作者：Anthropic  
> - 原文发布：2025-11-10  
> - 翻译发布：2026-03-25（东八区）

[Context engineering（上下文工程）](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) 在与 LLM 协作时已越来越重要，而 **prompt engineering（提示工程）** 是其必不可少的基础模块。

[Prompt engineering](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices) 指通过组织指令，让 AI 模型产出更好结果的手艺：如何措辞、如何规定风格、如何提供上下文、如何引导模型行为，以达成你的目标。

含糊指令与精心设计的提示之间的差距，可能就是「泛泛而谈」与「刚好是你需要的内容」之间的距离。结构糟糕的提示往往需要多轮来回澄清意图，而工程化良好的提示常常一次就能到位。

为帮助你上手，我们整理了团队内部的一些最佳实践，包含能立刻改善效果的实用方法：先从今天就能用的简单习惯讲起，再扩展到复杂项目可用的高阶手法。

## 如何使用 prompt engineering

最基础地说，prompt engineering 就是修改你传给 LLM 的查询。常见做法是在真正提出请求之前，先往查询里补充信息——但**该补充哪些信息、什么才是「对的信息」**，才是写出高质量、有效提示的关键。

### 核心技巧

下列 prompt engineering 技巧是高效人机协作的基础。坚持运用它们，通常能立刻看到回答质量的提升。

#### 表述明确、直接

现代 AI 模型对清晰、明确的指令响应非常好。不要默认模型会猜到你的意图——请直接说出来。用简单、无歧义的语言说明你到底要什么。

**核心原则**：告诉模型你希望**看到什么**。若要全面详尽的输出，就明确索要；若要特定功能，就逐条列出。像 Claude 这样的现代模型尤其受益于明确的指引。

**示例：创建数据分析看板**

- **含糊**：「做一个数据分析看板」
- **明确**：「创建一个数据分析看板。尽可能纳入相关功能与交互，不要只满足最低要求，做出功能完整的实现。」

第二版明确要求「全面功能」，并暗示希望模型在最低限度之上再多做一步。

**建议做法**：

- 开头用直接的动作动词：Write、Analyze、Generate、Create 等
- 省略铺垫，直奔请求
- 说明**输出里要包含什么**，而不只是「围绕什么主题写」
- 对质量与深度提出明确期望

#### 提供背景与动机

解释**为什么**某件事重要，有助于模型更好理解你的目标，从而给出更聚焦的回答。对能推理你深层意图的新模型尤其有效。

**示例：格式偏好**

- **较弱**：「绝对不要用项目符号」
- **更好**：「我更希望用自然段落而不是项目符号来回答，因为连贯的散文对我来说更好读、更像对话。项目符号显得太正式、太像清单，不符合我轻松学习的方式。」

第二版帮助模型理解规则背后的理由，从而在相关格式选择上做出更合理的判断。

**适合补充背景的场合**：

- 说明输出的用途或受众
- 解释某些约束为何存在
- 描述输出将如何被使用
- 说明你试图解决什么问题

#### 具体化

在 prompt engineering 里，「具体」意味着用明确的准则与要求来组织指令。你越清楚自己要什么，结果通常越好。

**示例：膳食计划**

- **含糊**：「给我一份地中海饮食的膳食计划」
- **具体**：「设计一份用于糖尿病前期管理的、地中海风格的膳食计划。每日 1800 大卡，侧重低升糖食物。列出早餐、午餐、晚餐和一份加餐，并给出完整的营养分解。」

**怎样才算足够具体？** 建议包含：

- 清晰约束（字数、格式、时间线等）
- 相关背景（受众是谁、目标是什么）
- 期望的输出结构（表格、列表、段落等）
- 任何要求或限制（饮食、预算、技术约束等）

#### 使用示例

示例并非总是必需，但在解释概念或展示特定格式时非常有用，即 one-shot / few-shot prompting：用「示范」代替纯描述，点明难以仅靠文字说清的细微要求。

**对现代模型的重要提示**：Claude 4.x 等先进模型会**非常仔细**地模仿示例里的细节。请确保示例鼓励的行为与你期望一致，并尽量减少你想避免的模式。

**示例：文章摘要**

无示例时：「摘要这篇文章」

```
以下是我想要的摘要风格示例：

文章：[一篇关于 AI 监管的文章链接]
摘要：欧盟通过全面的 AI 法案，针对高风险系统。关键条款包括透明度要求与人监督义务。2026 年生效。

请用同样风格摘要这篇文章：[你的新文章链接]
```

**适合用示例的情况**：

- 期望格式「展示比描述更容易」
- 需要特定语气或风格
- 任务涉及细微模式或惯例
- 简单指令无法稳定复现结果

**小技巧**：先从一个示例（one-shot）开始；若输出仍不符预期，再增加示例（few-shot）。

#### 允许 Claude 表达不确定

明确允许 AI 在不确定时**承认不知道**，而不是编造。这能减少幻觉、提高可靠性。

**示例**：「分析这些财务数据并识别趋势。若数据不足以得出结论，请直接说明，不要猜测。」

这一简单补充让模型可以承认局限，回答更可信。

在 [Claude](https://claude.ai/) 里试试上述做法。

## 高阶 prompt engineering 技巧

掌握核心习惯已经能走很远，但仍会遇到需要更复杂手法的场景。在构建 agent 式方案、处理复杂数据结构、或需要拆解多阶段问题时，高阶技巧特别有用。

### 预填充（prefill）模型的回复

预填充指由你先写出助手回复的开头，以引导格式、语气或结构。对强制输出格式、跳过开场白尤其有效。

**适合预填充的情况**：

- 需要模型输出 JSON、XML 等结构化格式
- 希望跳过对话式开场白，直接进入正文
- 需要维持特定人设或口吻
- 需要控制模型从哪里开始续写

**示例：强制 JSON 输出**

不用预填充时，Claude 可能会说：「这是您要的 JSON：{...}」

使用预填充（API）时：

```python
messages=[
    {"role": "user", "content": "Extract the name and price from this product description into JSON."},
    {"role": "assistant", "content": "{"}
]
```

模型会从左大括号后继续，只输出合法 JSON。

**说明**：在聊天界面中，可通过非常明确的文字近似实现：「只输出合法 JSON，不要任何前言。请从左大括号 `{` 开始回复。」

### 思维链提示（chain of thought）

思维链（CoT）提示要求模型在给出最终答案前先逐步推理，适合需要结构化思考的复杂分析任务。

**现代做法**：Claude 提供 [扩展思考（extended thinking）](https://www.anthropic.com/news/visible-extended-thinking) 能力，可自动进行结构化推理。在可用的情况下，一般更优先用扩展思考，而不是手写思维链。但在无法使用扩展思考、或你需要可审查的透明推理时，理解手动 CoT 仍然有价值。

**适合用手动思维链的情况**：

- 无法使用扩展思考（例如免费版 [Claude.ai](https://claude.ai/)）
- 需要可复查的透明推理过程
- 任务需要多步分析
- 希望确保模型考虑到特定因素

常见的三种实现方式：

**基础思维链**

在指令末尾加上「Think step-by-step」或中文等价表述，例如「请逐步思考后再写」。

```
Draft personalized emails to donors asking for contributions to this year's Care for Kids program.

Program information:
<program>
{{PROGRAM_DETAILS}}
</program>

Donor information:
<donor>
{{DONOR_DETAILS}}
</donor>

Think step-by-step before you write the email.
```

**引导式思维链**

在提示中划分明确的推理阶段。

```
Think before you write the email. First, think through what messaging might appeal to this donor given their donation history. Then, consider which aspects of the Care for Kids program would resonate with them. Finally, write the personalized donor email using your analysis.
```

**结构化思维链**

用标签把推理过程与最终答案分开。

```
Think before you write the email in <thinking> tags. First, analyze what messaging would appeal to this donor. Then, identify relevant program aspects. Finally, write the personalized donor email in <email> tags, using your analysis.
```

**说明**：即便有扩展思考，对复杂任务显式使用 CoT 仍然可能有益；二者可互补，而非互斥。

### 控制输出格式

对现代模型，控制格式有几种有效方式：

**1. 告诉模型「要做什么」，而不是只列「不要做什么」**

与其说「回复里不要用 markdown」，不如说「请用流畅的散文段落组织回答」。

**2. 让提示本身的格式贴近你想要的输出**

提示里用的格式会影响模型回复风格。若希望少用 markdown，提示里也应减少 markdown。

**3. 明确写出格式偏好**

需要细粒度控制时，例如：

```
When writing reports or analyses, write in clear, flowing prose using complete paragraphs. Use standard paragraph breaks for organization. Reserve markdown primarily for inline code, code blocks, and simple headings.

DO NOT use ordered lists or unordered lists unless you're presenting truly discrete items where a list format is the best option, or the user explicitly requests a list.

Instead of listing items with bullets, incorporate them naturally into sentences. Your goal is readable, flowing text that guides the reader naturally through ideas.
```

### Prompt chaining（提示串联）

与前面技巧不同，串联无法在一次提示里完成。它把复杂任务拆成多个顺序步骤，每步一条提示；上一步输出作为下一步输入。

这种做法用延迟换准确率：每一步更简单，整体更稳。通常在工作流或代码里实现，也可以在你收到回复后手动发下一条。

**示例：研究摘要**

1. **第一条**：「摘要这篇医学论文，涵盖方法、发现与临床意义。」
2. **第二条**：「审查上一条摘要的准确性、清晰度与完整性，给出分级反馈。」
3. **第三条**：「根据以下反馈改进摘要：[来自第 2 步的反馈]」

每一阶段用聚焦的指令做 refinement。

**适合串联的情况**：

- 复杂请求需要分步完成
- 需要迭代打磨
- 做多阶段分析
- 中间结果值得校验
- 单次提示结果不稳定

**权衡**：串联会增加延迟（多次 API 调用），但对复杂任务往往能明显提升准确率与可靠性。

## 你可能听说过的技巧

一些在早期模型上流行的 prompt 技巧，对 Claude 等现代模型已不那么必要，但仍可能出现在旧文档中，或在特定场景下有用。

### 用 XML 标签划分结构

XML 标签曾是组织长提示、标明数据边界的推荐方式。现代模型往往不依赖 XML 也能理解结构，但在少数场景仍有价值。

**示例**：

```
<athlete_information>
- Height: 6'2"
- Weight: 180 lbs
- Goal: Build muscle
- Dietary restrictions: Vegetarian
</athlete_information>

Generate a meal plan based on the athlete information above.
```

**XML 仍可能有用的场合**：

- 提示极复杂、混合多种内容类型
- 必须严格区分内容边界
- 面向较旧版本的模型

**现代替代**：多数情况下，清晰小标题、留白与明确用语（如「根据下列运动员信息……」）同样有效，且更轻量。

### 角色提示（role prompting）

角色提示通过在查询里设定「专家人设」来框定视角。这可以有效，但现代模型往往不需要过于用力的角色设定。

**示例**：「你是一位理财顾问。分析这个投资组合……」

**重要提醒**：不要过度收窄角色。「你是一个有帮助的助手」常常优于「你是从不犯错、只讲术语的世界级专家」——过于具体的角色可能反而限制模型的有用性。

**角色提示可能有用时**：

- 需要在大量输出中保持一致的语气
- 应用需要固定人设
- 希望为复杂主题提供「领域视角」的 framing

**现代替代**：很多时候直接说明想要的视角更有效：「分析该投资组合，侧重风险承受能力与长期增长潜力」，而不必硬套一个角色。

在 [Claude](https://preview.claude.ai/new) 中尝试。

## 综合使用

上文是单点技巧，真正威力在于**按场景组合**。Prompt engineering 的艺术不是堆砌全部技巧，而是为你的具体需求选对组合。

**多技巧组合示例**（原文示例首行在官网为笔误 `xtract`，译文按意图改为 `Extract`）：

```
Extract key financial metrics from this quarterly report and present them in JSON format.

I need this data for automated processing, so it's critical that your response contains ONLY valid JSON with no preamble or explanation.

Use this structure:
{
  "revenue": "value with units",
  "profit_margin": "percentage",
  "growth_rate": "percentage"
}

If any metric is not clearly stated in the report, use null rather than guessing.

Begin your response with an opening brace: {
```

这条提示结合了：

- 明确指令（提取什么）
- 背景（为何格式重要）
- 结构示例
- 允许不确定（不清楚则用 `null`）
- 格式控制（从左大括号开始）

## 如何选择技巧

并非每条提示都需要所有技巧。可参考下面的决策思路：

**从这里开始：**

1. 请求是否清楚、明确？若否，先提高清晰度。
2. 任务是否简单？若是，只用核心技巧（具体化、说清楚、给背景）。
3. 是否需要特定格式？考虑示例或预填充。
4. 任务是否复杂？考虑拆解（串联）。
5. 是否需要推理？使用扩展思考（若可用）或思维链。

**技巧速查**：

| 若你需要…… | 可使用…… |
| --- | --- |
| 特定输出格式 | 示例、预填充，或明确的格式说明 |
| 逐步推理 | 扩展思考（Claude 4.x）或思维链 |
| 复杂多阶段任务 | Prompt chaining |
| 可审查的推理过程 | 带结构化输出的思维链 |
| 抑制幻觉 | 明确允许说「不知道」 |

## 常见问题排查

即便意图良好，提示也可能带来意外结果。下面是对照表：

- **问题：回答太泛** → **对策**：提高具体程度、加示例，或明确要求「超出基础要求」。
- **问题：偏题或未抓住要点** → **对策**：更明确地说出真实目标，并补充「你为什么问这个」的背景。
- **问题：格式不稳定** → **对策**：加 few-shot 示例，或用预填充控制开头。
- **问题：任务过复杂、结果不可靠** → **对策**：拆成多条提示（串联），每条只做一件事并做好。
- **问题：多余开场白** → **对策**：用预填充，或写明「跳过前言，直接给答案」。
- **问题：编造信息** → **对策**：明确允许在不确定时说不知道。
- **问题：你只想要改代码，它却在给建议** → **对策**：动作写死：「请直接修改该函数」，而不是「能否给点修改建议？」

**小技巧**：从简单开始，只在需要时增加复杂度；每次只加一项改动，验证是否真的带来提升。

## 应避免的常见错误

- **不要过度工程化**：更长、更复杂的提示**并不**总是更好。
- **不要忽视基础**：核心提示含糊时，高阶技巧也救不了。
- **不要默认 AI 会读心**：意图不具体，就给模型留下误读空间。
- **不要一次用上所有技巧**：只选能解决你当前痛点的那些。
- **不要忘记迭代**：第一条提示很少一次完美，要测试与调整。
- **不要死守过时技巧**：对现代模型，XML 与过重角色提示往往不再必要；优先用明确、直接的说明。

## Prompt engineering 的补充考量

### 与长内容打交道

高阶 prompt 会通过额外 token 增加上下文开销：示例、多轮提示、长说明都会占上下文；**管理上下文**本身也是一门技能。

只在值得时使用这些技巧，并确保收益对得起 token。关于如何系统管理上下文，可参考 Anthropic 的 [context engineering 文章](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)。

**上下文感知能力的进步**：包括 Claude 4.x 在内的现代模型，在长上下文上的注意力已明显改善，有助于缓解历史上「lost-in-the-middle（中间信息被忽略）」的问题。

**为何任务拆分仍然有用**：即便上下文能力变强，把大任务拆成更小、更独立的块仍然有价值——不一定是因为「装不下」，而是因为**聚焦单一目标与边界**时，模型更容易把每一步做到最好。边界清晰、目标单一的任务，往往比在同一条提示里塞多个目标更稳。

**策略**：长上下文里把信息组织清楚，把最关键的内容放在开头或结尾；复杂任务则评估是否拆成若干聚焦子任务，以提高每一步的质量与可靠性。

### 怎样算一条「好提示」？

Prompt engineering 是技能，需要多试才能熟练。判断是否做对的唯一办法是实测对比：先自己动手试，你会立刻感受到「用技巧」与「不用技巧」的差别。

要真正精进，需要客观衡量提示效果——Anthropic 在 [prompt engineering 课程](https://anthropic.skilljar.com/claude-with-the-anthropic-api)（anthropic.skilljar.com）中讲的正是这部分。

**快速自检**：

- 输出是否符合你的具体要求？
- 是一次成功还是需要多轮迭代？
- 多次尝试下格式是否一致？
- 是否避开了上文列出的常见错误？

## 结语

Prompt engineering 本质上是**沟通**：用 AI 最容易正确理解你意图的方式表达。先熟练掌握文初的核心技巧，用到形成习惯；只有当真能解特定问题时，再叠加上高阶手法。

请记住：**最好的提示**往往不是最长或最复杂的那条，而是**用最少必要结构、稳定达成目标**的那条。练习多了，你会自然知道什么场景适合什么技巧。

向 context engineering 的演进，并没有削弱 prompt engineering 的重要性；相反，**prompt engineering 是 context engineering 里的基础积木**。每一条精心写的提示，都会与对话历史、附件、系统指令等一起，构成塑造模型行为的更大上下文，从而带来更好的结果。

今天就在 [Claude](https://preview.claude.ai/new) 里开始写提示吧。

## 延伸阅读

- [Prompt engineering 文档](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview)
- [交互式 Prompt engineering 教程](https://github.com/anthropics/prompt-eng-interactive-tutorial)（GitHub）
- [Prompt engineering 课程](https://anthropic.skilljar.com/claude-with-the-anthropic-api)
- [Context engineering 导读](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
