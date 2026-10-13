+++
title = "智能体工程模式 12：按顺序讲解代码"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison 以 SwiftUI 演示应用 Present 为例，介绍如何让编程智能体使用 Showboat 生成有组织的代码讲解，帮助读者理解实现。"
summary = "让智能体阅读源码、规划讲解顺序，再通过 Showboat 记录说明和直接读取的代码片段。作者借此理解了一个通过 Vibe Coding 构建的 SwiftUI 应用。"
tags = ["智能体工程", "代码理解", "Showboat"]
categories = ["engineering"]
topics = ["agents", "agentic-engineering", "coding-agents", "code-understanding", "swiftui"]
translation_category = "工程实践"
series = ["智能体工程模式"]
series_order = 13
series_label = "按顺序讲解代码"
series_part = "理解代码"
series_number = 12
original_title = "Linear walkthroughs"
original_url = "https://simonwillison.net/guides/agentic-engineering-patterns/linear-walkthroughs/"
original_author = "Simon Willison"
original_date = ""
original_site = "Simon Willison’s Weblog"
ShowToc = true
source_kind = "translation"
lastmod = 2026-10-11T21:22:32+08:00
+++

> **译文信息**
>
> - 原文：[Linear walkthroughs](https://simonwillison.net/guides/agentic-engineering-patterns/linear-walkthroughs/)
> - 作者：Simon Willison
> - 中文翻译与整理：Hex4C59（AI 辅助）
> - 翻译整理：2026-10-11
>
> 本文为非官方中文译文，依据提供的原文正文翻译。正文中的「我」、项目经历和学习效果均指原作者；工具和模型名称保留原文记录。译者未执行示例命令或运行 Present 应用。

有时，让编程智能体有条理地讲解一个代码库，会很有帮助。

你可能需要尽快熟悉一份已有代码，也可能忘记了自己写过的代码的细节，或者整个项目都是通过 Vibe Coding 做出来的，现在需要弄明白它到底如何工作。

配合合适的智能体运行框架（harness），前沿模型能够生成详细的讲解，帮助你理解代码的工作方式。

## 使用 Showboat 和 Present 的示例 {#an-example-using-showboat-and-present}

最近，我在 Mac 上使用 Claude Code 和 Opus 4.6，通过 [Vibe Coding 做了一个 SwiftUI 幻灯片演示应用](https://simonwillison.net/2026/Feb/25/present/)。

当时，我要做一场演讲，介绍 2025 年 11 月至 2026 年 2 月间前沿模型的进展。我喜欢在演讲里至少安排一个小花样，也就是一个 [STAR 时刻](https://simonwillison.net/2019/Dec/10/better-presentations/)——Something They'll Always Remember，让听众一直记得的瞬间。这一次，我决定在演讲结束时揭晓：播放这些幻灯片的应用本身，就是 Vibe Coding 能做到什么的一个例子。

我把代码发布到 [GitHub](https://github.com/simonw/present)，随后才意识到，自己根本不知道它实际上是怎样工作的。整个应用都是我靠提示词做出来的，这里有[部分会话记录](https://gisthost.github.io/?bfbc338977ceb71e298e4d4d5ac7d63c)，而我完全没有关注它写出的代码。

于是，我启动了一个新的网页版 Claude Code 实例，让它访问我的仓库，并输入以下提示词：

> 阅读源码，然后规划一份按顺序展开的代码讲解，详细解释整个应用如何工作。
>
> 接着运行「`uvx showboat –help`」来了解 Showboat。使用 Showboat 在仓库中创建一个 `walkthrough.md` 文件，并在其中完成讲解。用 `showboat note` 添加说明；用 `showboat exec` 配合 `sed`、`grep`、`cat` 或任何你需要的工具，加入正在讲解的代码片段。

> **译者注：** 提示词中的 `–help` 保留了原文的长横线排印。复制运行时，应使用两个半角连字符，即 `uvx showboat --help`。

[Showboat](https://github.com/simonw/showboat) 是我开发的一个工具，用来帮助编程智能体撰写能够展示其工作过程的文档。这里可以查看 [showboat --help 的输出](https://github.com/simonw/showboat/blob/main/help.txt)。这份帮助信息经过专门设计，包含模型使用工具所需了解的全部内容。

`showboat note` 命令向文档添加 Markdown 内容。`showboat exec` 接收一条 shell 命令，执行它，然后把命令和输出一起加入文档。

我让它使用「`sed`、`grep`、`cat` 或任何你需要的工具，加入正在讲解的代码片段」，是为了确保 Claude Code 不会手动把代码片段复制到文档中，因为手动复制可能引入幻觉或错误。

这种做法效果非常好。这是 [Claude Code 使用 Showboat 生成的文档](https://github.com/simonw/present/blob/main/walkthrough.md)。它详细讲解了全部六个 `.swift` 文件，清楚地解释了代码如何工作，也提供了能够据此开展工作的具体说明。

仅仅阅读这份文档，我就学到了很多 SwiftUI 应用的组织方式，也掌握了一些 Swift 语言本身的具体知识。

如果你担心 LLM 会拖慢你学习新技能的速度，我强烈建议采用这样的做法。即便是一个花了大约 40 分钟、通过 Vibe Coding 做出来的玩具项目，也能成为探索新技术生态、学到有趣新技巧的机会。

---

[上一篇原文：让智能体执行手动测试](https://simonwillison.net/guides/agentic-engineering-patterns/agentic-manual-testing/) · [下一篇原文：交互式讲解](https://simonwillison.net/guides/agentic-engineering-patterns/interactive-explanations/)
