+++
title = "智能体工程模式 08：子智能体"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison 介绍子智能体如何节省主智能体的上下文，以 Claude Code 的 Explore 子智能体为例，讨论并行任务和专家分工。"
summary = "子智能体用独立上下文处理探索、测试和调试等任务，再向主智能体返回所需信息。本文结合一次 Django 差异视图修改，说明这种协作方式的用途。"
tags = ["智能体工程", "子智能体", "上下文管理"]
categories = ["engineering"]
topics = ["agents", "agentic-engineering", "coding-agents", "subagents", "context"]
translation_category = "工程实践"
series = ["智能体工程模式"]
series_order = 9
series_label = "子智能体"
series_part = "与编程智能体协作"
series_number = 8
original_title = "Subagents"
original_url = "https://simonwillison.net/guides/agentic-engineering-patterns/subagents/"
original_author = "Simon Willison"
original_date = ""
original_site = "Simon Willison’s Weblog"
ShowToc = true
source_kind = "translation"
lastmod = 2026-10-14T00:43:37+08:00
+++

> **译文信息**
>
> - 原文：[Subagents](https://simonwillison.net/guides/agentic-engineering-patterns/subagents/)
> - 作者：Simon Willison
> - 中文翻译与整理：Hex4C59（AI 辅助）
> - 翻译整理：2026-10-11
>
> 本文为非官方中文译文，依据提供的原文正文翻译，并按系列目录补入小节标题。正文中的「我」及实践经历均指原作者。上下文容量、基准测试和性能方面的表述保留原文记录，译者未做独立测量。并行提示词原文保留在文本块中，下方附中文翻译。

大语言模型（Large Language Models，LLM）受到上下文上限的限制，也就是在任一时刻，它们的工作记忆能容纳多少 Token。过去两年，虽然 LLM 的能力有了显著提升，这个上限却没有增长太多。它们通常最多能容纳约 1,000,000 个 Token，而基准测试经常发现，在低于 200,000 个 Token 时，结果质量更好。

仔细管理上下文，让它保持在这些限制之内，是获得良好结果的关键。

子智能体（subagent）提供了一种简单而有效的方法：在不大量消耗编程智能体宝贵的顶层上下文的情况下，处理更大的任务。

当编程智能体使用子智能体时，实际上相当于派出一个全新的自身副本，让它完成指定目标。这个副本有独立的上下文窗口，并从一条新的提示词开始工作。

## Claude Code 的 Explore 子智能体 {#claude-codes-explore-subagent}

Claude Code 在日常工作流程中大量使用子智能体。我们就用它来举例。

每当你针对一个现有仓库开始新任务，Claude Code 都需要先探索仓库，了解它的大体结构，并找到完成任务所需的相关信息。

为此，它会构造一条提示词，派出一个子智能体进行探索，并让它返回所发现内容的说明。

我向 Claude Code 提供了一张[指南中某个页面](https://simonwillison.net/guides/agentic-engineering-patterns/linear-walkthroughs/changes/)的截图，并用下面这条提示词开始了一次会话：

> 让章节差异视图也能显示具体哪些字符发生了变化：对于一行文本中发生变化的片段，使用更深的红色或绿色标记。

这是这次会话的[完整记录](https://gisthost.github.io/?effbdc564939b88fe5c6299387e217da/index.html)。

Claude Code 一开始就运行了一个 Explore 子智能体，并向它提供以下初始提示词：

> 找到这个 Django 博客中实现「章节」差异视图的代码。我需要找到：
>
> 1. 渲染差异的模板：查找与差异有关、带红色或绿色背景的 HTML/CSS。
> 2. 生成差异的 Python 代码：查找 `difflib` 或类似工具的使用。
> 3. 与差异渲染有关的 JavaScript。
> 4. 差异视图的 CSS 样式：红色或绿色的行背景。
>
> 仔细搜索，检查 `templates/`、`static/` 和 `blog/` 目录。查找「diff」「chapter」「revision」「history」「compare」等关键词。

子智能体的调用方式与其他工具类似：主智能体（父智能体）像调用其他工具一样派出它们，然后等待响应。看模型这样给自己写提示词很有意思，它们通常很会选择提示策略。

Explore 子智能体忙了几秒钟，返回的响应以下面这些内容开头：

> 太好了！现在让我把所有发现整理成一份完整的总结：
>
> ### 摘要：章节差异视图实现 {#summary-chapter-diff-view-implementation}
>
> 我已经找到这个 Django 博客中章节差异视图的完整实现。以下是关键组件：
>
> #### 1. Python 代码：差异生成（`/home/user/simonwillisonblog/guides/views.py`，第 139—202 行） {#1-python-code-diff-generation-homeusersimonwillisonblogguidesviewspy-lines-139-202}
>
> `chapter_changes()` 视图函数使用 Python 内置的 `difflib.unified_diff()` 生成差异：［……］

子智能体的完整响应，包含了主智能体开始编辑代码、满足我最初需求所需的全部细节。

## 并行子智能体 {#parallel-subagents}

Explore 子智能体展示了最简单的一种协作方式：子智能体运行时，主智能体暂停等待。这类子智能体的主要优势，是能够使用全新的上下文开展工作，避免消耗主智能体可用的上下文 Token 配额。

主智能体也可以同时运行多个子智能体，显著提升处理速度。还可以使用 Claude Haiku 等更快、更便宜的模型，加速这些任务。

支持子智能体的编程智能体，可以根据你的指令使用它们。试试这样的提示词：

```
Use subagents to find and update all of the templates that are affected by this change.

```

> 使用子智能体，找出并更新所有受这次改动影响的模板。

对于需要编辑多个文件、而这些文件彼此没有依赖的任务，这种方式可以显著加快速度。

## 专家子智能体 {#specialist-subagents}

有些编程智能体允许对子智能体做进一步定制，通常是提供自定义系统提示词、自定义工具，或同时定制两者，让子智能体承担不同的角色。

这些角色可以涵盖多种有用的专长：

- 代码审查智能体可以审查代码，找出缺陷、功能缺失或设计上的薄弱之处。
- 测试执行智能体可以运行测试。如果测试套件很大、输出很多，这尤其有用：子智能体可以不把完整测试输出传给主智能体，只报告失败的具体情况。
- 调试智能体可以专门排查问题，把自己的 Token 配额用于分析代码库，并运行代码片段，帮助确定复现步骤和缺陷的根本原因。

把任务拆给几十个不同的专家子智能体，可能很有吸引力。但要记住，子智能体的主要价值，是保护宝贵的主智能体上下文，并承接消耗大量 Token 的操作。只要还有足够的 Token，主智能体完全有能力调试或审查自己的输出。

## 官方文档 {#official-documentation}

一些常见的编程智能体支持子智能体，并各自提供了使用文档：

- [OpenAI Codex 子智能体](https://developers.openai.com/codex/subagents/)
- [Claude 子智能体](https://code.claude.com/docs/en/sub-agents)
- [Gemini CLI 子智能体](https://geminicli.com/docs/core/subagents/)
- [Mistral Vibe 子智能体](https://docs.mistral.ai/mistral-vibe/agents-skills#agent-selection)
- [OpenCode 智能体](https://opencode.ai/docs/agents/)
- [Visual Studio Code 中的子智能体](https://code.visualstudio.com/docs/copilot/agents/subagents)
- [Cursor 子智能体](https://cursor.com/docs/subagents)

---

[上一篇原文：与编程智能体协作时如何使用 Git](https://simonwillison.net/guides/agentic-engineering-patterns/using-git-with-coding-agents/) · [下一篇原文：红灯／绿灯测试驱动开发](https://simonwillison.net/guides/agentic-engineering-patterns/red-green-tdd/)
