+++
title = "智能体工程模式·序言：写作计划"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison 介绍《Agentic Engineering Patterns》的写作计划，解释智能体工程与 Vibe Coding 的区别，以及持续更新的指南与章节形式。"
summary = "作为《智能体工程模式》的序言，本文介绍项目缘起、最初两篇文章、作者的写作原则，以及适合持续修订的指南与章节组织方式。"
tags = ["Agent", "智能体工程", "编程智能体", "软件工程"]
categories = ["Translations"]
topics = ["agents", "agentic-engineering", "coding-agents", "vibe-coding"]
translation_category = "工程实践"
series = ["智能体工程模式"]
series_order = 1
original_title = "Writing about Agentic Engineering Patterns"
original_url = "https://simonwillison.net/2026/Feb/23/agentic-engineering-patterns/"
original_author = "Simon Willison"
original_date = "2026-02-23"
original_site = "Simon Willison’s Weblog"
ShowToc = true
+++

> **译文信息**
>
> - 原文：[Writing about Agentic Engineering Patterns](https://simonwillison.net/2026/Feb/23/agentic-engineering-patterns/)
> - 作者：Simon Willison
> - 原文发布：2026-02-23
> - 中文翻译与整理：Hex4C59（AI 辅助）
> - 翻译整理：2026-10-11
>
> 本文为非官方中文译文。正文中的「我」、写作原则和计划均指原作者；「今天」指原文发表的 2026 年 2 月 23 日。文章数量、工具和模型名称保留原文记录。

我启动了一个新项目，用来收集和记录[**智能体工程模式（Agentic Engineering Patterns）**](https://simonwillison.net/guides/agentic-engineering-patterns/)——我们正在进入一个由编程智能体参与开发的新时代，这些编程实践与模式旨在帮助我们在这个时代取得更好的结果。

我用**智能体工程（Agentic Engineering）**来指借助编程智能体构建软件。这类工具包括 Claude Code 和 OpenAI Codex，其决定性特征是既能生成代码，也能*执行*代码。因此，它们能够测试代码并持续迭代，而不必每一步都等待人类监督者的指导。

我对 **Vibe Coding** 的理解沿用它的[原始定义](https://simonwillison.net/2025/Mar/19/vibe-coding/)：在编程过程中完全不关注代码本身。如今，这通常与非程序员使用大语言模型（Large Language Model，LLM）编写代码联系在一起。

智能体工程则位于这条光谱的另一端：专业软件工程师借助编程智能体放大已有的专业能力，从而改进工作并提高效率。

这门新领域有太多值得学习和探索的内容！我已经在 [ai-assisted-programming 标签下](https://simonwillison.net/tags/ai-assisted-programming/)发表了大量文章（已有 345 篇，还在增加），但这些内容相对零散。我的新目标是把相关内容集中起来，回答一个问题：「怎样才能用这些工具取得好的结果？」

我会在自己的博客上持续建设这个项目，把各种模式写成一篇篇章节。组织形式大致受到 1994 年出版的[《设计模式：可复用面向对象软件的基础》](https://en.wikipedia.org/wiki/Design_Patterns)所推广的模式写法启发。

今天，我发布了最初的两篇：

- [**如今，编写代码的成本已经很低**](https://simonwillison.net/guides/agentic-engineering-patterns/code-is-cheap/)讨论了智能体工程的核心挑战：快速产出初步可运行代码的成本已经降到几乎为零，这会怎样影响我们对个人和团队工作方式的既有直觉？
- [**红灯／绿灯测试驱动开发（TDD）**](https://simonwillison.net/guides/agentic-engineering-patterns/red-green-tdd/)介绍了先写测试的开发方式，如何只需很少的额外提示，就能帮助智能体写出更简洁、更可靠的代码。

我希望以每周 1～2 篇的速度增加新章节。我也不知道什么时候会停下来，毕竟还有很多内容值得讨论！

## 由我执笔，而非 LLM

我有一条坚定的个人原则：不以自己的名义发布 AI 生成的文章。《智能体工程模式》也会遵守这条原则。我会使用 LLM 来校对文字、完善示例代码，以及处理各种其他辅助任务，但你在这里读到的文字都会由我亲自撰写。

## 章节与指南

《智能体工程模式》不完全是*一本书*，但它的形态有点像书。我会在网站上用一种新的内容形式来发布它，我把这种形式叫作*指南（guide）*。一份指南由多个章节组成，每一章本质上都是一篇淡化发布日期的博客文章。它们从一开始就被设计成可以持续更新，而不会停留在首次发表时的版本。

如何在博客上发布能够长期保持价值的「常青」内容？指南与章节就是我的答案。我一直在尝试寻找合适的方法，而这种形式让我觉得有望长期沿用。

如果你对具体实现感兴趣，可以查看 [Guide](https://github.com/simonw/simonwillisonblog/blob/b9cd41a0ac4a232b2a6c90ca3fff9ae465263b02/blog/models.py#L262-L280)、[Chapter](https://github.com/simonw/simonwillisonblog/blob/b9cd41a0ac4a232b2a6c90ca3fff9ae465263b02/blog/models.py#L349-L405) 和 [ChapterChange](https://github.com/simonw/simonwillisonblog/blob/b9cd41a0ac4a232b2a6c90ca3fff9ae465263b02/blog/models.py#L408-L423) 模型，以及[相关的 Django 视图](https://github.com/simonw/simonwillisonblog/blob/b9cd41a0ac4a232b2a6c90ca3fff9ae465263b02/blog/views.py#L775-L923)中的代码。这些代码几乎全部由 Claude Opus 4.6 编写：我通过 iPhone 访问网页版 Claude Code，让它完成了这些工作。

---

原文发表于 [2026 年 2 月 23 日](https://simonwillison.net/2026/Feb/23/) 17:43。你可以在 [Mastodon](https://fedi.simonwillison.net/@simon)、[Bluesky](https://bsky.app/profile/simonwillison.net) 或 [Twitter](https://twitter.com/simonw) 上关注我，也可以[订阅我的邮件简报](https://simonwillison.net/about/#subscribe)。

## 原页面附带的近期文章

以下为页面附带的文章推荐，不属于《智能体工程模式》的章节。

- [用语音为我的博客构建一项新功能](https://simonwillison.net/2026/Oct/9/built-using-my-voice/)——2026 年 10 月 9 日
- [Claude Haiku 5.5](https://simonwillison.net/2026/Oct/7/claude-haiku-5-5/)——2026 年 10 月 7 日
- [我们几乎需要为所有东西默认设置不可突破的预算上限](https://simonwillison.net/2026/Oct/3/default-hard-budget-caps/)——2026 年 10 月 3 日
- [OpenAI DevDay 2026 实时记录](https://simonwillison.net/2026/Sep/29/openai-devday-2026-live-blog/)——2026 年 9 月 29 日

---

[返回《智能体工程模式》系列目录]({{< relref "/translations/agentic-engineering-patterns/" >}})
