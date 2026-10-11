+++
title = "智能体工程模式 01：什么是智能体工程？"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison 解释智能体工程、编程智能体和工具循环，讨论软件工程师的职责，以及智能体工程与 Vibe Coding 的区别。"
summary = "编程智能体既能编写代码，也能执行代码。智能体工程利用这一能力开展迭代，同时由工程师明确问题、权衡方案、提供工具并验证结果。"
tags = ["Agent", "智能体工程", "编程智能体", "软件工程"]
categories = ["Translations"]
topics = ["agents", "agentic-engineering", "coding-agents", "vibe-coding"]
translation_category = "工程实践"
series = ["智能体工程模式"]
series_order = 2
series_label = "什么是智能体工程？"
series_part = "基本原则"
series_number = 1
original_title = "What is agentic engineering?"
original_url = "https://simonwillison.net/guides/agentic-engineering-patterns/what-is-agentic-engineering/"
original_author = "Simon Willison"
original_date = ""
original_site = "Simon Willison’s Weblog"
ShowToc = true
+++

> **译文信息**
>
> - 原文：[What is agentic engineering?](https://simonwillison.net/guides/agentic-engineering-patterns/what-is-agentic-engineering/)
> - 作者：Simon Willison
> - 中文翻译与整理：Hex4C59（AI 辅助）
> - 翻译整理：2026-10-11
>
> 本文为非官方中文译文，依据提供的原文正文翻译。正文中的「我」及相关定义、判断和计划均指原作者；工具和模型名称保留原文记录。

我用**智能体工程（Agentic Engineering）**这个术语，来描述借助编程智能体开发软件的实践。

什么是**编程智能体（Coding Agents）**？它们是既能编写代码，也能执行代码的智能体。常见的例子包括 [Claude Code](https://code.claude.com/)、[OpenAI Codex](https://openai.com/codex/) 和 [Gemini CLI](https://geminicli.com/)。

那么，什么是**智能体（Agent）**？要为这个词给出清晰的定义，一直是困扰 AI 研究者的难题，[至少可以追溯到 20 世纪 90 年代](https://simonwillison.net/2024/Oct/12/michael-wooldridge/)。不过，至少在 GPT-5、Gemini 和 Claude 这类大语言模型（Large Language Models，LLM）的领域中，我逐渐认可了下面这个定义：

> **智能体通过循环调用工具来实现目标。**

所谓「智能体」，就是这样一种软件：它带着你的提示词调用 LLM，并传入一组工具定义；随后执行 LLM 请求调用的工具，再把结果反馈给 LLM。

对于编程智能体，这些工具中包含能够执行代码的工具。

你通过提示词为编程智能体设定目标。随后，智能体循环生成和执行代码，直到实现这个目标。

代码执行是让智能体工程成为可能的关键能力。如果不能直接运行代码，LLM 输出的任何内容都只有有限的价值。有了代码执行能力，这些智能体就可以不断迭代，逐步构建出能够通过实际运行证明其有效的软件。

## 智能体工程

既然现在已经有了能够编写可运行代码的软件，那么我们人类还需要做些什么？

答案是：*还有非常多的事情*。

编写代码从来都不是软件工程师唯一的工作。这门手艺的核心，始终是弄清楚*应该编写什么样的代码*。任何一个软件问题，都可能有几十种解决方案，而每种方案都有各自的取舍。我们的工作是权衡这些选项，找到最适合具体情境与需求的方案。

如何让编程智能体取得好的结果，本身就是一个值得深入研究的课题，尤其是在这个领域正以令人目不暇接的速度持续演进的当下。

我们需要为编程智能体提供解决问题所需的工具，以恰当的详细程度描述问题，并对结果进行验证和迭代，直到我们确信它们能够以稳健、可信的方式解决问题。

LLM 不会从过去的错误中学习，但编程智能体可以做到，前提是我们主动更新指令和工具运行框架（tool harness），把过程中获得的经验融入其中。

如果运用得当，编程智能体可以让我们在选择项目时拥有更大的抱负。智能体工程应该帮助我们产出更多、质量更高的代码，解决更有影响力的问题。

## 这不就是 Vibe Coding 吗？

「Vibe Coding」这个词由 [Andrej Karpathy 于 2025 年 2 月提出](https://twitter.com/karpathy/status/1886192184808149383)。巧合的是，那时距离 Claude Code 首次发布只有三周。这个词描述的是这样一种做法：通过提示词让 LLM 编写代码，而你自己则「连代码的存在都忘了」。

有些人把这个定义扩展到所有使用 LLM 生成代码的情形，但我认为这是错误的。Vibe Coding 保持原本的定义更有用：我们需要一个词，来描述未经审查、停留在原型质量的 LLM 生成代码，并将其与作者已经打磨到可用于生产环境标准的代码区分开来。

## 关于本指南

正如它试图介绍的这个领域一样，《智能体工程模式》仍在持续建设之中。我的目标是识别并描述与这些工具协作的模式：这些模式能够切实取得成效，也不容易随着工具的进步而过时。

随着新技术和方法不断出现，我会继续增加章节。任何一章都不应被视为已经定稿。随着我们对这些模式的理解不断深入，我也会持续更新已有章节。
