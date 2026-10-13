+++
title = "智能体工程模式 09：红灯／绿灯测试驱动开发"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison 介绍如何用一句简短的红灯／绿灯 TDD 提示，让编程智能体先写测试、确认失败，再实现代码直到测试通过。"
summary = "测试先行可以帮助避免智能体写出无效或多余的代码。关键是实现前亲眼确认测试失败，再通过实现让它通过，以验证新代码确实受到测试覆盖。"
tags = ["智能体工程", "TDD", "自动化测试"]
categories = ["engineering"]
topics = ["agents", "agentic-engineering", "coding-agents", "testing", "tdd"]
translation_category = "工程实践"
series = ["智能体工程模式"]
series_order = 10
series_label = "红灯／绿灯测试驱动开发"
series_part = "测试与质量保证"
series_number = 9
original_title = "Red/green TDD"
original_url = "https://simonwillison.net/guides/agentic-engineering-patterns/red-green-tdd/"
original_author = "Simon Willison"
original_date = ""
original_site = "Simon Willison’s Weblog"
ShowToc = false
source_kind = "translation"
lastmod = 2026-10-11T21:22:32+08:00
+++

> **译文信息**
>
> - 原文：[Red/green TDD](https://simonwillison.net/guides/agentic-engineering-patterns/red-green-tdd/)
> - 作者：Simon Willison
> - 中文翻译与整理：Hex4C59（AI 辅助）
> - 翻译整理：2026-10-11
>
> 本文为非官方中文译文，依据提供的原文正文翻译。测试方法和模型能力方面的判断均为原作者的观点；示例提示词用于说明原文做法，译者未执行。

「**使用红灯／绿灯 TDD**」是一条简短得令人满意的指令，可以让编程智能体取得更好的结果。

TDD 是 Test Driven Development 的缩写，意为测试驱动开发。这是一种编程方式：确保写出的每一部分代码都有相应的自动化测试，证明它能正常工作。

最严格的 TDD 形式是测试先行。先编写自动化测试，确认测试失败，然后不断改进实现，直到测试通过。

事实证明，这种方式与编程智能体*非常契合*。使用编程智能体的一大风险，是它们可能写出无法正常工作的代码，或者写出不必要、根本不会被使用的代码，也可能两种问题同时出现。

测试先行有助于防范这两种常见错误，还能建立一套可靠的自动化测试，防止未来的改动破坏已有功能。随着项目规模扩大，新改动导致现有功能失效的可能性也会增加。一套全面的测试，是确保这些功能持续正常工作的最有效方式。

在实现代码、让测试通过之前，先确认测试确实失败，这一点很重要。如果跳过这一步，你可能写出一个原本就能通过的测试，结果它根本没有检验和验证你的新实现。

这就是「红灯／绿灯」的含义：红灯阶段观察测试失败，绿灯阶段则确认测试已经通过。

每个好的模型都能理解，「红灯／绿灯 TDD」是下面这条长指令的简写：「使用测试驱动开发，先写测试；在实现让测试通过的改动之前，确认测试失败。」

示例提示词：

> 编写一个 Python 函数，从 Markdown 字符串中提取标题。使用红灯／绿灯 TDD。

---

[上一篇原文：子智能体](https://simonwillison.net/guides/agentic-engineering-patterns/subagents/) · [下一篇原文：先运行测试](https://simonwillison.net/guides/agentic-engineering-patterns/first-run-the-tests/)
