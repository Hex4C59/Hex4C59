+++
title = "智能体工程模式：系列目录"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison《Agentic Engineering Patterns》中文系列目录，涵盖基本原则、编程智能体协作、测试与质量保证、代码理解、提示词详解和常用提示词。"
summary = "按原指南顺序整理 6 个部分、16 篇文章及其小节的中文目录，并提供中文译文与英文原文入口。"
tags = ["智能体工程", "编程智能体", "软件工程"]
categories = ["engineering"]
topics = ["agents", "agentic-engineering", "coding-agents", "testing"]
translation_category = "工程实践"
series = ["智能体工程模式"]
series_order = 0
layout = "series"
series_index = true
series_title = "智能体工程模式"
series_status = "本轮翻译已完成"
series_intro = "从基本原则到编程智能体协作、测试和代码理解，按原指南的顺序阅读这组工程实践。"
original_title = "Agentic Engineering Patterns"
original_url = "https://simonwillison.net/guides/agentic-engineering-patterns/"
original_author = "Simon Willison"
original_date = ""
original_site = "Simon Willison’s Weblog"
ShowToc = true
source_kind = "translation"
series_kind = "translation"
lastmod = 2026-10-14T00:43:37+08:00
+++

> **系列信息**
>
> - 原指南：[Agentic Engineering Patterns](https://simonwillison.net/guides/agentic-engineering-patterns/)
> - 作者：Simon Willison
> - 中文目录翻译与整理：Hex4C59
> - 目录整理日期：2026-10-11
> - 原站核对日期：2026-10-14
>
> 本页为指南目录的非官方中文翻译，保留原有章节顺序和小节层级。章节和小节标题链接到中文译文，来源链接指向英文原文。

本指南介绍如何运用各种模式，让 Claude Code、OpenAI Codex 等编程智能体取得更好的结果。关于这个项目的更多信息，请参阅作者的[项目介绍](https://simonwillison.net/2026/Feb/23/agentic-engineering-patterns/)。

系列面向使用编程智能体开展软件开发的读者。以下目录分为 6 个部分，共 16 篇，覆盖基本原则、工具协作、测试、代码理解和具体案例。

## 系列序言

[写作计划]({{< relref "/translations/agentic-engineering-patterns-introduction/" >}})：作者介绍项目缘起、智能体工程与 Vibe Coding 的区别，以及指南与章节的组织方式。序言独立于下面的 16 篇主体章节。

## 第一部分：基本原则

### 01. [什么是智能体工程？]({{< relref "/translations/agentic-engineering-patterns-what-is-agentic-engineering/" >}})

- [智能体工程]({{< relref "/translations/agentic-engineering-patterns-what-is-agentic-engineering/" >}}#智能体工程)
- [这不就是 Vibe Coding 吗？]({{< relref "/translations/agentic-engineering-patterns-what-is-agentic-engineering/" >}}#这不就是-vibe-coding-吗)
- [关于本指南]({{< relref "/translations/agentic-engineering-patterns-what-is-agentic-engineering/" >}}#关于本指南)

### 02. [如今，编写代码的成本已经很低]({{< relref "/translations/agentic-engineering-patterns-code-is-cheap/" >}})

- [好代码仍然有成本]({{< relref "/translations/agentic-engineering-patterns-code-is-cheap/" >}}#好代码仍然有成本)
- [我们需要养成新的习惯]({{< relref "/translations/agentic-engineering-patterns-code-is-cheap/" >}}#我们需要养成新的习惯)

### 03. [积累你已经掌握的实现方法]({{< relref "/translations/agentic-engineering-patterns-hoard-things-you-know-how-to-do/" >}})

- [重新组合已有积累]({{< relref "/translations/agentic-engineering-patterns-hoard-things-you-know-how-to-do/" >}}#重新组合已有积累)
- [编程智能体让这种方法更加强大]({{< relref "/translations/agentic-engineering-patterns-hoard-things-you-know-how-to-do/" >}}#编程智能体让这种方法更加强大)

### 04. [AI 应该帮助我们写出更好的代码]({{< relref "/translations/agentic-engineering-patterns-better-code/" >}})

- [避免引入技术债务]({{< relref "/translations/agentic-engineering-patterns-better-code/" >}}#avoiding-taking-on-technical-debt)
- [编程智能体可以替我们处理这些问题]({{< relref "/translations/agentic-engineering-patterns-better-code/" >}}#coding-agents-can-handle-these-for-us)
- [AI 工具让我们能够考虑更多方案]({{< relref "/translations/agentic-engineering-patterns-better-code/" >}}#ai-tools-let-us-consider-more-options)
- [拥抱复利式工程循环（Compound Engineering Loop）]({{< relref "/translations/agentic-engineering-patterns-better-code/" >}}#embrace-the-compound-engineering-loop)

### 05. [反模式：应该避免的做法]({{< relref "/translations/agentic-engineering-patterns-anti-patterns/" >}})

- [把未经审查的代码丢给协作者]({{< relref "/translations/agentic-engineering-patterns-anti-patterns/" >}}#inflicting-unreviewed-code-on-collaborators)

## 第二部分：与编程智能体协作

### 06. [编程智能体如何工作]({{< relref "/translations/agentic-engineering-patterns-how-coding-agents-work/" >}})

- [大语言模型（Large Language Models，LLM）]({{< relref "/translations/agentic-engineering-patterns-how-coding-agents-work/" >}}#large-language-models)
- [按聊天模板组织提示词]({{< relref "/translations/agentic-engineering-patterns-how-coding-agents-work/" >}}#chat-templated-prompts)
- [Token 缓存]({{< relref "/translations/agentic-engineering-patterns-how-coding-agents-work/" >}}#token-caching)
- [调用工具]({{< relref "/translations/agentic-engineering-patterns-how-coding-agents-work/" >}}#calling-tools)
- [系统提示词]({{< relref "/translations/agentic-engineering-patterns-how-coding-agents-work/" >}}#the-system-prompt)
- [推理]({{< relref "/translations/agentic-engineering-patterns-how-coding-agents-work/" >}}#reasoning)
- [在循环中组合 LLM、系统提示词和工具]({{< relref "/translations/agentic-engineering-patterns-how-coding-agents-work/" >}}#llm-system-prompt-tools-in-a-loop)

### 07. [与编程智能体协作时如何使用 Git]({{< relref "/translations/agentic-engineering-patterns-using-git-with-coding-agents/" >}})

- [Git 基础知识]({{< relref "/translations/agentic-engineering-patterns-using-git-with-coding-agents/" >}}#git-essentials)
- [核心概念与提示词]({{< relref "/translations/agentic-engineering-patterns-using-git-with-coding-agents/" >}}#core-concepts-and-prompts)
- [重写历史]({{< relref "/translations/agentic-engineering-patterns-using-git-with-coding-agents/" >}}#rewriting-history)

### 08. [子智能体]({{< relref "/translations/agentic-engineering-patterns-subagents/" >}})

- [Claude Code 的 Explore 子智能体]({{< relref "/translations/agentic-engineering-patterns-subagents/" >}}#claude-codes-explore-subagent)
- [并行子智能体]({{< relref "/translations/agentic-engineering-patterns-subagents/" >}}#parallel-subagents)
- [专家子智能体]({{< relref "/translations/agentic-engineering-patterns-subagents/" >}}#specialist-subagents)
- [官方文档]({{< relref "/translations/agentic-engineering-patterns-subagents/" >}}#official-documentation)

## 第三部分：测试与质量保证

### 09. [红灯／绿灯测试驱动开发（TDD）]({{< relref "/translations/agentic-engineering-patterns-red-green-tdd/" >}})

### 10. [先运行测试]({{< relref "/translations/agentic-engineering-patterns-first-run-the-tests/" >}})

### 11. [让智能体执行手动测试]({{< relref "/translations/agentic-engineering-patterns-agentic-manual-testing/" >}})

- [智能体执行手动测试的机制]({{< relref "/translations/agentic-engineering-patterns-agentic-manual-testing/" >}}#mechanisms-for-agentic-manual-testing)
- [使用浏览器自动化测试 Web 用户界面]({{< relref "/translations/agentic-engineering-patterns-agentic-manual-testing/" >}}#using-browser-automation-for-web-uis)
- [让智能体使用 Showboat 记录过程]({{< relref "/translations/agentic-engineering-patterns-agentic-manual-testing/" >}}#have-them-take-notes-with-showboat)

## 第四部分：理解代码

### 12. [按顺序讲解代码]({{< relref "/translations/agentic-engineering-patterns-linear-walkthroughs/" >}})

- [使用 Showboat 和 Present 的示例]({{< relref "/translations/agentic-engineering-patterns-linear-walkthroughs/" >}}#an-example-using-showboat-and-present)

### 13. [交互式讲解]({{< relref "/translations/agentic-engineering-patterns-interactive-explanations/" >}})

- [理解词云]({{< relref "/translations/agentic-engineering-patterns-interactive-explanations/" >}}#understanding-word-clouds)

## 第五部分：提示词详解

### 14. [使用 WebAssembly 和 Gifsicle 构建 GIF 优化工具]({{< relref "/translations/agentic-engineering-patterns-gif-optimization/" >}})

- [后续提示词]({{< relref "/translations/agentic-engineering-patterns-gif-optimization/" >}}#the-follow-up-prompts)

### 15. [为博客转邮件简报工具添加新的内容类型]({{< relref "/translations/agentic-engineering-patterns-adding-a-new-content-type/" >}})

## 第六部分：附录

### 16. [我使用的提示词]({{< relref "/translations/agentic-engineering-patterns-prompts/" >}})

- [Artifacts（产物）]({{< relref "/translations/agentic-engineering-patterns-prompts/" >}}#artifacts)
- [校对]({{< relref "/translations/agentic-engineering-patterns-prompts/" >}}#proofreader)
- [替代文本（Alt Text）]({{< relref "/translations/agentic-engineering-patterns-prompts/" >}}#alt-text)
- [播客亮点]({{< relref "/translations/agentic-engineering-patterns-prompts/" >}}#podcast-highlights)
