+++
title = "智能体工程模式：系列目录"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison《Agentic Engineering Patterns》中文系列目录，涵盖基本原则、编程智能体协作、测试与质量保证、代码理解、提示词详解和常用提示词。"
summary = "按原指南顺序整理 6 个部分、16 篇文章及其小节的中文目录，并提供中文译文与英文原文入口。"
tags = ["Agent", "智能体工程", "编程智能体", "软件工程"]
categories = ["Translations"]
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
+++

> **系列信息**
>
> - 原指南：[Agentic Engineering Patterns](https://simonwillison.net/guides/agentic-engineering-patterns/)
> - 作者：Simon Willison
> - 中文目录翻译与整理：Hex4C59
> - 目录整理日期：2026-10-11
>
> 本页为指南目录的非官方中文翻译，保留原有章节顺序和小节层级。各章标题优先链接到中文译文，其余链接指向英文原文。

本指南介绍如何运用各种模式，让 Claude Code、OpenAI Codex 等编程智能体取得更好的结果。关于这个项目的更多信息，请参阅作者的[项目介绍](https://simonwillison.net/2026/Feb/23/agentic-engineering-patterns/)。

系列面向使用编程智能体开展软件开发的读者。以下目录分为 6 个部分，共 16 篇，覆盖基本原则、工具协作、测试、代码理解和具体案例。

## 系列序言

[写作计划]({{< relref "/translations/agentic-engineering-patterns-introduction/" >}})：作者介绍项目缘起、智能体工程与 Vibe Coding 的区别，以及指南与章节的组织方式。序言独立于下面的 16 篇主体章节。

## 第一部分：基本原则

### 01. [什么是智能体工程？]({{< relref "/translations/agentic-engineering-patterns-what-is-agentic-engineering/" >}})

- 智能体工程
- 这不就是 Vibe Coding 吗？
- 关于本指南

### 02. [如今，编写代码的成本已经很低]({{< relref "/translations/agentic-engineering-patterns-code-is-cheap/" >}})

- 好代码仍然有成本
- 我们需要养成新的习惯

### 03. [积累你已经掌握的实现方法]({{< relref "/translations/agentic-engineering-patterns-hoard-things-you-know-how-to-do/" >}})

- 重新组合已有积累
- 编程智能体让这种方法更加强大

### 04. [AI 应该帮助我们写出更好的代码]({{< relref "/translations/agentic-engineering-patterns-better-code/" >}})

- 避免引入技术债务
- 编程智能体可以替我们处理这些问题
- AI 工具让我们能够考虑更多方案
- 拥抱复利式工程循环（Compound Engineering Loop）

### 05. [反模式：应该避免的做法]({{< relref "/translations/agentic-engineering-patterns-anti-patterns/" >}})

- 把未经审查的代码丢给协作者

## 第二部分：与编程智能体协作

### 06. [编程智能体如何工作]({{< relref "/translations/agentic-engineering-patterns-how-coding-agents-work/" >}})

- 大语言模型（Large Language Models，LLM）
- 按聊天模板组织提示词
- Token 缓存
- 调用工具
- 系统提示词
- 推理
- 在循环中组合 LLM、系统提示词和工具

### 07. [与编程智能体协作时如何使用 Git]({{< relref "/translations/agentic-engineering-patterns-using-git-with-coding-agents/" >}})

- Git 基础知识
- 核心概念与提示词
- 重写历史

### 08. [子智能体]({{< relref "/translations/agentic-engineering-patterns-subagents/" >}})

- Claude Code 的 Explore 子智能体
- 并行子智能体
- 专家子智能体
- 官方文档

## 第三部分：测试与质量保证

### 09. [红灯／绿灯测试驱动开发（TDD）]({{< relref "/translations/agentic-engineering-patterns-red-green-tdd/" >}})

### 10. [先运行测试]({{< relref "/translations/agentic-engineering-patterns-first-run-the-tests/" >}})

### 11. [让智能体执行手动测试]({{< relref "/translations/agentic-engineering-patterns-agentic-manual-testing/" >}})

- 智能体执行手动测试的机制
- 使用浏览器自动化测试 Web 用户界面
- 让智能体使用 Showboat 记录过程

## 第四部分：理解代码

### 12. [按顺序讲解代码]({{< relref "/translations/agentic-engineering-patterns-linear-walkthroughs/" >}})

- 使用 Showboat 和 Present 的示例

### 13. [交互式讲解]({{< relref "/translations/agentic-engineering-patterns-interactive-explanations/" >}})

- 理解词云

## 第五部分：提示词详解

### 14. [使用 WebAssembly 和 Gifsicle 构建 GIF 优化工具]({{< relref "/translations/agentic-engineering-patterns-gif-optimization/" >}})

- 后续提示词

### 15. [为博客转邮件简报工具添加新的内容类型]({{< relref "/translations/agentic-engineering-patterns-adding-a-new-content-type/" >}})

## 第六部分：附录

### 16. [我使用的提示词]({{< relref "/translations/agentic-engineering-patterns-prompts/" >}})

- Artifacts（产物）
- 校对
- 替代文本（Alt Text）
- 播客亮点
