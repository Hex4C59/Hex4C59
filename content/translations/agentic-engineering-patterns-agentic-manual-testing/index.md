+++
title = "智能体工程模式 11：让智能体执行手动测试"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison 介绍如何让编程智能体通过命令行和浏览器试验代码，并使用 Rodney 与 Showboat 记录测试过程和结果。"
summary = "自动化测试通过后，仍需确认功能在实际使用中正常工作。本文介绍 Python、curl 和浏览器自动化的试验方式，以及把发现的问题补入测试、把验证过程写成文档的方法。"
tags = ["Agent", "智能体工程", "编程智能体", "自动化测试", "Playwright", "Showboat"]
categories = ["engineering"]
topics = ["agents", "agentic-engineering", "coding-agents", "testing", "browser-automation"]
translation_category = "工程实践"
series = ["智能体工程模式"]
series_order = 12
series_label = "让智能体执行手动测试"
series_part = "测试与质量保证"
series_number = 11
original_title = "Agentic manual testing"
original_url = "https://simonwillison.net/guides/agentic-engineering-patterns/agentic-manual-testing/"
original_author = "Simon Willison"
original_date = ""
original_site = "Simon Willison’s Weblog"
ShowToc = true
source_kind = "translation"
lastmod = 2026-10-11T21:22:32+08:00
+++

> **译文信息**
>
> - 原文：[Agentic manual testing](https://simonwillison.net/guides/agentic-engineering-patterns/agentic-manual-testing/)
> - 作者：Simon Willison
> - 中文翻译与整理：Hex4C59（AI 辅助）
> - 翻译整理：2026-10-11
>
> 本文为非官方中文译文，依据提供的原文正文翻译，并按系列目录补入小节标题。正文中的「我」、工具能力和实践效果均为原作者的表述。示例命令和测试流程未由译者执行。

编程智能体的决定性特征，是能够执行自己编写的代码。正是这一点，让它们比那些只会输出代码、却没有办法验证代码的大语言模型（LLM）有用得多。

在 LLM 生成的代码真正执行过之前，绝不要假定它能够正常工作。

编程智能体能够确认自己产出的代码是否符合预期；如果不符合，就继续迭代，直到符合为止。

让智能体[编写单元测试](https://simonwillison.net/guides/agentic-engineering-patterns/red-green-tdd/)，尤其是采用测试先行的测试驱动开发（Test Driven Development，TDD），是确保它实际运行并检验所写代码的一种有效方法。

不过，值得采用的方法并不只有这一种。

代码通过测试，不代表它就能按预期工作。任何做过自动化测试的人，都见过测试全部通过、代码却明显出问题的情况：服务器可能一启动就崩溃，某个关键界面元素可能没有显示，或者某个细节根本没有被测试覆盖。

自动化测试不能代替手动测试。在把功能纳入发布版本之前，我喜欢亲眼看到它正常工作。

我发现，让智能体对代码进行手动测试同样很有价值，常常能发现自动化测试没有捕捉到的问题。

## 智能体执行手动测试的机制 {#mechanisms-for-agentic-manual-testing}

智能体应该怎样「手动」测试代码，取决于代码的类型。

对于 Python 库，一种实用的做法是使用 `python -c "... code ..."`。你可以把一段字符串或多行字符串形式的 Python 代码直接传给 Python 解释器，其中也可以包含导入其他模块的代码。

编程智能体都熟悉这个技巧，有时不用提醒就会采用。不过，提醒它们用 `python -c` 测试，往往也很有效：

> 使用 `python -c`，针对一些边界情况试运行那个新函数。

其他语言可能也有类似机制。即使没有，智能体也能很快写一个演示文件，再编译并运行。我有时会让它把文件放在 `/tmp`，只是为了避免这些文件后来被意外提交到仓库。

> 在 `/tmp` 中编写代码，试验那个函数的边界情况，然后编译并运行。

我的许多项目都是带有 JSON API 的 Web 应用。对于这类应用，我会让智能体用 `curl` 实际调用接口：

> 启动开发服务器，用 `curl` 探索那个新的 JSON API。

让智能体「探索」，往往会促使它尝试新 API 的多个方面，很快覆盖许多情况。

如果智能体通过手动测试发现了问题，我喜欢让它用红灯／绿灯 TDD 来修复。这样，新发现的情况就会被纳入长期保留的自动化测试。

## 使用浏览器自动化测试 Web 用户界面 {#using-browser-automation-for-web-uis}

如果项目包含交互式 Web 界面，有一套手动测试流程就更有价值。

过去，这类界面很难通过代码测试。但在过去十年里，真实浏览器自动化系统有了显著进步。用真正的 Chrome、Firefox 或 Safari 浏览器访问应用，可以在真实的使用环境中发现各种问题。

编程智能体非常熟悉这些工具的用法。

如今，其中最强大的工具是微软开发的开源库 [Playwright](https://playwright.dev/)。它提供功能完整的 API，支持通过多种常见编程语言调用，也能够自动化操作各种常见浏览器引擎。

只要告诉智能体「用 Playwright 测试一下」，可能就够了。它随后会选择最合适的语言接口，或者使用 Playwright 的 [playwright-cli](https://github.com/microsoft/playwright-cli) 工具。

编程智能体也很适合使用专门的命令行界面（Command-Line Interface，CLI）工具。Vercel 的 [agent-browser](https://github.com/vercel-labs/agent-browser) 是一个功能全面的 Playwright 命令行封装，专门为编程智能体设计。

我自己的项目 [Rodney](https://github.com/simonw/rodney) 也有类似用途，不过它通过 Chrome DevTools Protocol，也就是 Chrome 开发者工具协议，直接控制一个 Chrome 实例。

下面是我使用 Rodney 进行测试时的一条示例提示词：

> 启动开发服务器，然后使用 `uvx rodney --help` 测试新的首页，查看截图，确认菜单位于正确的位置。

这条提示词里有三个技巧：

- 「使用 `uvx rodney --help`」会让智能体通过 [uvx](https://docs.astral.sh/uv/guides/tools/) 包管理工具运行 `rodney --help`。首次调用时，它会自动安装 Rodney。
- `rodney --help` 的帮助信息经过专门设计，包含智能体理解和使用工具所需的全部信息。这是[帮助文本](https://github.com/simonw/rodney/blob/main/help.txt)。
- 「查看截图」提示智能体使用 `rodney screenshot` 命令，也提醒它可以利用自己的视觉能力分析生成的图像文件，评估页面的外观。

一条简短的提示词，就包含了这么多手动测试操作！

Rodney 及类似工具提供了许多能力，包括在已加载的网站上运行 JavaScript、滚动、点击、输入文字，甚至读取页面的无障碍树。这棵树描述了界面元素及其关系，供辅助技术理解页面。

与其他手动测试方式一样，通过浏览器自动化发现并修复的问题，也可以加入长期保留的自动化测试。

过去，许多开发者不愿编写太多浏览器自动化测试，因为这类测试以不稳定著称：页面 HTML 中极小的调整，都可能引发一连串令人烦恼的测试失败。

让编程智能体持续维护这些测试，可以大幅减少 Web 界面设计变化时，同步更新测试所需的工作。

## 让智能体使用 Showboat 记录过程 {#have-them-take-notes-with-showboat}

让智能体手动测试代码，既能发现更多问题，也能产出一些材料，用来说明代码，以及展示它经过了怎样的测试。

我对「让智能体展示自己的工作过程」这个问题很感兴趣。能够看到演示或有记录的实验，是确认智能体已经完整解决所交任务的一种有效方式。

我开发了 [Showboat](https://github.com/simonw/showboat)，让记录智能体手动测试流程的文档更容易生成。

下面是我经常使用的一条提示词：

> 运行 `uvx showboat --help`，然后创建一个 `notes/api-demo.md` Showboat 文档，用它测试并记录那个新 API。

与前面的 Rodney 一样，`showboat --help` 会教智能体理解 Showboat 是什么、该怎样使用。这是[完整的帮助文本](https://github.com/simonw/showboat/blob/main/help.txt)。

Showboat 的三个关键命令是 `note`、`exec` 和 `image`。

`note` 向 Showboat 文档追加一段 Markdown 笔记。`exec` 记录一条命令，随后执行它，并记录输出。`image` 向文档添加一张图像，适合加入使用 Rodney 拍摄的 Web 应用截图。

其中最重要的是 `exec`，因为它会同时记录命令及其实际输出。这样，你就能看到智能体做了什么、结果是什么。这种设计旨在减少智能体作弊、把自己希望发生的事情写进文档的情况。

我发现，Showboat 这种方式很适合记录智能体会话中完成的工作。我希望看到更多工具采用类似的做法。

---

[上一篇原文：先运行测试](https://simonwillison.net/guides/agentic-engineering-patterns/first-run-the-tests/) · [下一篇原文：按顺序讲解代码](https://simonwillison.net/guides/agentic-engineering-patterns/linear-walkthroughs/)
