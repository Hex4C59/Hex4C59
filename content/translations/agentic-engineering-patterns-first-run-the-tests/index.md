+++
title = "智能体工程模式 10：先运行测试"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison 介绍为什么应在编程智能体会话开始时先运行测试，以及这条简短提示词如何帮助智能体了解项目并建立测试习惯。"
summary = "先运行测试，让智能体找到测试入口、了解项目规模，并在后续改动中继续验证和补充测试。文中给出适用于作者 Python 项目的 uv run pytest 提示。"
tags = ["Agent", "智能体工程", "编程智能体", "自动化测试", "pytest"]
categories = ["Translations"]
topics = ["agents", "agentic-engineering", "coding-agents", "testing", "pytest"]
translation_category = "工程实践"
series = ["智能体工程模式"]
series_order = 11
original_title = "First run the tests"
original_url = "https://simonwillison.net/guides/agentic-engineering-patterns/first-run-the-tests/"
original_author = "Simon Willison"
original_date = ""
original_site = "Simon Willison’s Weblog"
ShowToc = false
+++

> **译文信息**
>
> - 原文：[First run the tests](https://simonwillison.net/guides/agentic-engineering-patterns/first-run-the-tests/)
> - 作者：Simon Willison
> - 中文翻译与整理：Hex4C59（AI 辅助）
> - 翻译整理：2026-10-11
>
> 本文为非官方中文译文，依据提供的原文正文翻译。正文中的「我」、项目配置和模型行为方面的判断均指原作者。`uv run pytest` 是作者项目中的命令示例，译者未执行。

与编程智能体协作时，自动化测试已经不再是可选项。

过去不写测试的理由，是测试耗时，而且代码库快速演进时，不断重写测试的成本很高。但当智能体只需几分钟就能把测试整理妥当时，这些理由就不再成立了。

测试对于确认 AI 生成的代码确实能做到它声称的事情，也*至关重要*。如果代码从未执行过，那么部署到生产环境后能否正常工作，就只能靠运气了。

测试还是帮助智能体快速熟悉现有代码库的好工具。试着向 Claude Code 或类似工具询问某项已有功能，看看它们会做什么：它们很可能会找到并阅读相关测试。

智能体本来就倾向于进行测试，而现有测试套件的存在，几乎肯定会进一步促使它测试自己做出的新改动。

每次针对一个现有项目开始新的智能体会话，我都会先发出下面这条提示词，或者它的某种变体：

> 先运行测试。

在我的 Python 项目中，我已经[配置好 pyproject.toml](https://til.simonwillison.net/uv/dependency-groups)，因此也可以改用这条提示词：

> 运行 `uv run pytest`。

这两条提示词的英文原文分别是「First run the tests」和「Run "uv run pytest"」，都只有四个词，却有几方面的作用：

1. 它告诉智能体，项目里有一套测试，并让它必须弄清楚如何运行。这几乎可以确保智能体今后也会运行测试，检查自己的改动有没有破坏已有功能。
2. 大多数测试框架会让智能体大致知道有多少个测试。测试数量可以间接反映项目的规模和复杂程度，也会提示智能体：如果想进一步了解项目，就应该搜索测试代码。
3. 它让智能体进入重视测试的工作状态。已经运行过测试后，智能体之后再添加自己的测试，就成了很自然的下一步。

与[「使用红灯／绿灯 TDD」](https://simonwillison.net/guides/agentic-engineering-patterns/red-green-tdd/)类似，「先运行测试」这条只有四个英文单词的提示词，也能唤起模型已经掌握的一整套软件工程实践。

---

[上一篇原文：红灯／绿灯测试驱动开发](https://simonwillison.net/guides/agentic-engineering-patterns/red-green-tdd/) · [下一篇原文：让智能体执行手动测试](https://simonwillison.net/guides/agentic-engineering-patterns/agentic-manual-testing/)

[上一篇中文译文]({{< relref "/translations/agentic-engineering-patterns-red-green-tdd/" >}}) · [系列目录]({{< relref "/translations/agentic-engineering-patterns/" >}}) · [下一篇：让智能体执行手动测试]({{< relref "/translations/agentic-engineering-patterns-agentic-manual-testing/" >}})
