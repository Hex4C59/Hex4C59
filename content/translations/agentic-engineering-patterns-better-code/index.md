+++
title = "智能体工程模式 04：AI 应该帮助我们写出更好的代码"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison 讨论如何用编程智能体减少技术债务、完成耗时的重构、探索技术方案，并通过持续复盘改进代码质量。"
summary = "编程智能体降低了重构和原型实验的成本。开发者可以把这些能力用于改进代码、验证技术选择，并把每次项目的经验记录为后续智能体任务的指引。"
tags = ["智能体工程", "代码质量", "重构"]
categories = ["engineering"]
topics = ["agents", "agentic-engineering", "coding-agents", "code-quality", "refactoring"]
translation_category = "工程实践"
series = ["智能体工程模式"]
series_order = 5
series_label = "AI 应该帮助我们写出更好的代码"
series_part = "基本原则"
series_number = 4
original_title = "AI should help us produce better code"
original_url = "https://simonwillison.net/guides/agentic-engineering-patterns/better-code/"
original_author = "Simon Willison"
original_date = ""
original_site = "Simon Willison’s Weblog"
ShowToc = true
source_kind = "translation"
lastmod = 2026-10-17
+++

> **译文信息**
>
> - 原文：[AI should help us produce better code](https://simonwillison.net/guides/agentic-engineering-patterns/better-code/)
> - 作者：Simon Willison
> - 中文翻译与整理：Hex4C59（AI 辅助）
> - 翻译整理：2026-10-11
>
> 本文为非官方中文译文，依据提供的原文正文翻译。正文中的「我」及质量、成本和实践方面的判断均指原作者；工具名称保留原文记录。Redis 场景用于说明如何验证技术选型，译者未执行相关实验。

许多开发者担心，把代码交给 AI 工具来写会降低质量：糟糕的代码产出得足够快，决策者就愿意忽略它的缺陷。

如果采用编程智能体确实降低了你交付的代码和功能的质量，就应该直接解决这个问题：找出流程中哪些环节损害了产出质量，再把它们改好。

使用智能体交付更差的代码，是一种*选择*。我们也可以选择交付[更好的代码](https://simonwillison.net/guides/agentic-engineering-patterns/code-is-cheap/#good-code)。

## 避免引入技术债务 {#avoiding-taking-on-technical-debt}

我喜欢从技术债务的角度思考如何交付更好的代码。技术债务源于取舍：按「正确的方式」做太耗时，于是我们在有限的时间内先把事情做完，再寄希望于项目能延续得足够久，让我们有机会偿还这笔债务。

应对技术债务最好的办法，就是一开始便不欠下它。

根据我的经验，有些常见的技术债务修复起来并不复杂，却很耗时间。

- 原来的应用程序编程接口（API）设计没有覆盖后来出现的一个重要场景。修复它需要修改几十处代码，因此，另加一个只有细微差别的新 API，再接受这份重复，反而更快。
- 我们早期给某个概念起了一个不合适的名字，比如用了 teams，而更合适的名称是 groups。但在整个代码库中统一改名工作量太大，于是只修改了用户界面中的名称。
- 系统逐渐积累了一些重复但略有不同的功能，需要合并和重构。
- 某个文件已经长到几千行，理想情况下应该拆成多个模块。

这些修改在思路上都很简单，但仍然需要专门投入时间。面对更紧迫的问题，往往很难为它们争取到时间。

## 编程智能体可以替我们处理这些问题 {#coding-agents-can-handle-these-for-us}

这类重构任务，是编程智能体的*理想*用途。

启动一个智能体，告诉它要改什么，再让它在后台完成修改，代码放在某个分支或独立工作目录（Git worktree）中。

我通常会使用异步编程智能体，例如 [Gemini Jules](https://jules.google.com/)、[OpenAI Codex 网页版](https://developers.openai.com/codex/cloud/)或[网页版 Claude Code](https://code.claude.com/docs/en/claude-code-on-the-web)。这样，我就能让这些重构任务继续进行，同时不打断自己在笔记本电脑上的工作。

通过拉取请求（Pull Request，PR）审查结果。如果改得好，就合并。如果已经接近要求，就再给它提示，告诉它哪些地方需要换一种做法。如果改得很差，就直接丢弃。

这些代码改进的成本已经降得足够低，让我们可以对轻微的代码异味和使用上的不便采取零容忍态度。这里的「代码异味」，指那些提示代码设计可能需要改进的迹象。

## AI 工具让我们能够考虑更多方案 {#ai-tools-let-us-consider-more-options}

任何软件开发任务，都有许多种解决问题的方式。有些影响很大的技术债务，来自规划阶段的错误选择：忽略了一个明显而简单的解决方案，或者选了一项技术，后来才发现它并不完全适合。

大语言模型（Large Language Models，LLM）可以帮我们发现那些明明摆在那里、我们却没有想到的方案。它们只会建议训练数据中常见的解决方案，不过这些往往就是最有可能奏效的[「无聊技术」（Boring Technology）](https://boringtechnology.club/)，也就是那些成熟、常见的技术。

更重要的是，编程智能体可以帮助我们开展**探索性原型开发**：先做出原型，再试验不同方案。

要对技术选择有把握，最好的办法就是用原型证明它确实适合当前用途。

对于一个预计有数千名并发用户的网站，用 Redis 来实现动态信息流，是个好选择吗？

要弄清楚，最好的方法是搭建这个系统的模拟版本，对它进行负载测试，看看哪些地方会出问题。

只需一条精心编写的提示词，编程智能体就能构建这样的模拟系统，将这类实验的成本降到几乎为零。既然成本这么低，我们还可以同时开展多个实验，测试几种方案，从中选出最适合当前问题的那一种。

## 拥抱复利式工程循环 {#embrace-the-compound-engineering-loop}

智能体遵循指令。我们可以根据此前学到的经验，持续改进这些指令，让后续任务取得更好的结果。

Every 公司的 Dan Shipper 和 Kieran Klaassen，把公司与编程智能体协作的方法称为[复利式工程（Compound Engineering）](https://every.to/chain-of-thought/compound-engineering-how-every-codes-with-agents)。每个编程项目完成后，他们都会复盘。他们把这个环节称为**复利步骤（compound step）**：把有效的做法记录下来，供智能体在后续任务中使用。

如果想让智能体取得最好的结果，我们就应该持续提高代码库的质量。小的改进会不断积累，产生复利效应。过去很耗时的代码改进，如今成本已经足够低，我们没有理由不在交付新功能的同时改善代码质量。有了编程智能体，我们终于可以兼顾这两件事。

---

[上一篇原文：积累你已经掌握的实现方法](https://simonwillison.net/guides/agentic-engineering-patterns/hoard-things-you-know-how-to-do/) · [下一篇原文：反模式——应该避免的做法](https://simonwillison.net/guides/agentic-engineering-patterns/anti-patterns/)
