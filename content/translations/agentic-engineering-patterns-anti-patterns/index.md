+++
title = "智能体工程模式 05：反模式——应该避免的做法"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison 解释为什么不应把未经自己审查的智能体生成代码交给协作者，并列出一个好的智能体工程 PR 应具备的条件。"
summary = "提交 PR 前，先亲自审查代码、确认它能正常工作，并核对说明文字。用便于审查的改动、清楚的背景和验证证据，尊重协作者投入的时间。"
tags = ["Agent", "智能体工程", "编程智能体", "代码审查", "团队协作"]
categories = ["engineering"]
topics = ["agents", "agentic-engineering", "coding-agents", "code-review"]
translation_category = "工程实践"
series = ["智能体工程模式"]
series_order = 6
series_label = "反模式——应该避免的做法"
series_part = "基本原则"
series_number = 5
original_title = "Anti-patterns: things to avoid"
original_url = "https://simonwillison.net/guides/agentic-engineering-patterns/anti-patterns/"
original_author = "Simon Willison"
original_date = ""
original_site = "Simon Willison’s Weblog"
ShowToc = true
source_kind = "translation"
lastmod = 2026-10-11T21:22:32+08:00
+++

> **译文信息**
>
> - 原文：[Anti-patterns: things to avoid](https://simonwillison.net/guides/agentic-engineering-patterns/anti-patterns/)
> - 作者：Simon Willison
> - 中文翻译与整理：Hex4C59（AI 辅助）
> - 翻译整理：2026-10-11
>
> 本文为非官方中文译文，依据提供的原文正文翻译。正文中的「我」及相关判断和建议均指原作者。

在智能体工程这个陌生而奇特的新世界里，有些行为属于反模式，也就是应该避免的做法。

## 把未经审查的代码丢给协作者 {#inflicting-unreviewed-code-on-collaborators}

这种反模式很常见，也非常令人恼火。

**不要提交包含你自己尚未审查过的代码的拉取请求（Pull Request，PR）。**

如果你提交的 PR 包含智能体生成的几百行甚至几千行代码，而你自己没有花功夫确认它能正常工作，你就是把真正需要做的工作推给了别人。

他们完全可以自己给智能体发提示词。那你到底提供了什么价值？

把代码交给别人审查之前，你需要有把握：这份代码已经准备好，值得别人花时间审查。第一轮审查是你的责任，不应该甩给其他人。

一个好的智能体工程 PR 应该具备以下特点：

- 代码能正常工作，而且你对此有把握。[你的工作是交付能够正常工作的代码](https://simonwillison.net/2025/Dec/18/code-proven-to-work/)。
- 改动足够小，审查者可以高效审查，不必承担过多额外的理解负担。几个小 PR 优于一个大 PR。有编程智能体帮你处理 Git 操作，把代码拆成几个独立提交也很容易。
- PR 提供了额外的背景，帮助别人理解改动。这项改动服务于什么更大的目标？附上相关问题（issue）或规格说明的链接，会很有帮助。
- 智能体会写出看起来很有说服力的 PR 说明，你也需要审查这些文字！让别人阅读你自己都没读过、没核实过的文字，是不尊重人的做法。

把未经审查的代码丢给别人实在太容易了，因此我建议附上一些证据，证明你自己已经做过这些额外的工作。手动测试的记录、对具体实现选择的说明，甚至功能运行时的截图和视频，都能*很有效地*让审查者相信：花时间深入了解这些细节，不会是白费功夫。
