+++
title = "智能体工程模式 15：为博客转邮件简报工具添加新的内容类型"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison 分析一条简短提示词，展示如何让编程智能体参考博客源码，为邮件简报工具加入 beats 内容，并用浏览器验证结果。"
summary = "把参考代码库、目标文件、已有筛选逻辑和验证方式写进提示词，就能让智能体理解需求。本文保留了最终修改中的 SQL 查询和类型名称映射。"
tags = ["Agent", "智能体工程", "编程智能体", "提示词", "代码复用", "邮件简报"]
categories = ["Translations"]
topics = ["agents", "agentic-engineering", "coding-agents", "prompting", "code-reuse"]
translation_category = "工程实践"
series = ["智能体工程模式"]
series_order = 16
series_label = "为博客转邮件简报工具添加新的内容类型"
series_part = "提示词详解"
series_number = 15
original_title = "Adding a new content type to my blog-to-newsletter tool"
original_url = "https://simonwillison.net/guides/agentic-engineering-patterns/adding-a-new-content-type/"
original_author = "Simon Willison"
original_date = ""
original_site = "Simon Willison’s Weblog"
ShowToc = false
+++

> **译文信息**
>
> - 原文：[Adding a new content type to my blog-to-newsletter tool](https://simonwillison.net/guides/agentic-engineering-patterns/adding-a-new-content-type/)
> - 作者：Simon Willison
> - 中文翻译与整理：Hex4C59（AI 辅助）
> - 翻译整理：2026-10-11
>
> 本文为非官方中文译文，依据提供的原文正文翻译。正文中的「我」、项目状态和结果判断均指原作者。示例代码逐字保留，均为原文片段，不是完整的可运行程序；译者未执行提示词、SQL 或浏览器测试。

下面这个例子中，一条看起来短得有些出乎意料的提示词，一次就完成了相当多的工作。

先介绍一点背景。我大约每周发送一期[免费的 Substack 邮件简报](https://simonw.substack.com/)，内容从博客复制粘贴而来。实际上，我把 Substack 当作一种轻量的方式，让读者通过邮件订阅我的博客。

我使用自己的 [blog-to-newsletter](https://tools.simonwillison.net/blog-to-newsletter) 工具生成简报。这是一个用 HTML 和 JavaScript 编写的应用，会从[这个 Datasette 实例](https://datasette.simonwillison.net/)获取最新内容，把它整理成富文本 HTML。随后，我可以把结果复制到剪贴板，再粘贴进 Substack 编辑器。这里有一篇[详细介绍其工作方式的文章](https://simonwillison.net/2023/Apr/4/substack-observable/)。

最近，我给博客[添加了一种新的内容类型](https://simonwillison.net/2026/Feb/20/beats/)，用来收集我在其他地方发布的内容。我把它叫作「beats」。这类条目包括开源项目的新版本、我构建的新工具、我参观过的博物馆——来自 [niche-museums.com](https://www.niche-museums.com/)——以及其他外部内容。

我想把这些内容也加入生成的邮件简报。下面是我通过[网页版 Claude Code](https://code.claude.com/docs/en/claude-code-on-the-web)，针对存放 blog-to-newsletter 工具的 [simonw/tools](https://github.com/simonw/tools) 仓库发出的提示词：

> 从 GitHub 把 simonw/simonwillisonblog 克隆到 `/tmp`，作为参考。
>
> 更新 `blog-to-newsletter.html`，加入有描述的 beats，做法类似博客的 Atom everything 订阅源。
>
> 用 `python -m http.server` 启动它，再使用 `uvx rodney --help` 进行测试。比较邮件简报中显示的内容与 [https://simonwillison.net](https://simonwillison.net/) 首页上的内容。

这让我得到了[完全符合需求的解决方案](https://github.com/simonw/tools/pull/268)。下面拆开分析这条提示词。

> 从 GitHub 把 simonw/simonwillisonblog 克隆到 `/tmp`，作为参考。

我经常使用这种做法。编程智能体可以从 GitHub 克隆代码，而解释问题最好的方式，往往就是让它们查看相关代码。指定克隆到 `/tmp`，是为了避免它们后来不小心把这些参考代码也加入自己的提交。

[simonw/simonwillisonblog](https://github.com/simonw/simonwillisonblog) 仓库包含我的 Django 博客 [simonwillison.net](https://simonwillison.net/) 的源码，其中也有新功能「beats」的逻辑和数据库结构。

> 更新 `blog-to-newsletter.html`，加入有描述的 beats，做法类似博客的 Atom everything 订阅源。

只要提到 `blog-to-newsletter.html`，就足以告诉 Claude：在 simonw/tools 仓库的 200 多个 HTML 应用中，应该修改哪一个。

Beats 会自动从多个来源导入。很多条目并没有太大意思，比如我某个小型开源项目的一次修复缺陷的小版本发布。

我的博客允许我为任何一条 beat 添加额外的描述。它既能提供补充说明，也能标记这条 beat 比那些我没有添加说明的条目更值得关注。

我已经用这个区别来决定哪些 beats 应该进入网站的 [Atom 订阅源](https://simonwillison.net/about/#atom)。让 Claude 仿照现有做法，就不必再额外详细描述筛选逻辑。

> 用 `python -m http.server` 启动它，再使用 `uvx rodney --help` 进行测试。比较邮件简报中显示的内容与 https://simonwillison.net 首页上的内容。

当编程智能体有某种验证机制，能够测试自己的工作时，它们的表现总是最好。

这一次，我希望 Claude Code 主动检查：它对工具的修改，是否确实能够正确获取并显示最新数据。

我提醒它用 `python -m http.server` 作为静态服务器，是因为过去遇到过这样的情况：应用需要获取数据，直接从磁盘打开文件时会出问题，通过 localhost 服务器访问则不会。在这次任务中，这一步可能并不必要，但如今 `python -m http.server` 已经成了我写提示词时的习惯！

我在[让智能体执行手动测试一章](https://simonwillison.net/guides/agentic-engineering-patterns/agentic-manual-testing/#using-browser-automation-for-web-uis)中介绍过 `uvx rodney --help` 这个技巧。Rodney 是可以通过 `uvx` 安装的浏览器自动化软件。它的 `--help` 输出经过专门设计，能教会智能体使用工具所需了解的一切。

我认为，让 Claude 把简报结果与博客首页的内容进行比较，就足以让它有把握地验证新改动是否正确，因为我最近已经发布了符合新要求的内容。

你可以查看[完整会话](https://claude.ai/code/session_01BibYBuvJi2qNUyCYGaY3Ss)。如果打不开，我也保存了[另一份会话记录](https://gisthost.github.io/?e906e938100ab42f4d6a932505219324/page-001.html#msg-2026-04-18T00-13-57-081Z)，展示了每一次工具调用。

[最终的 PR](https://github.com/simonw/tools/pull/268) 做出了完全正确的修改。它为获取博客内容的 SQL 查询增加了一段 `UNION` 子句，排除了草稿 beats，以及 `note` 列没有内容的 beats：

```
...
union all
select
  id,
  'beat' as type,
  title,
  created,
  slug,
  'No HTML' as html,
  json_object(
    'created', date(created),
    'beat_type', beat_type,
    'title', title,
    'url', url,
    'commentary', commentary,
    'note', note
  ) as json,
  url as external_url
from blog_beat
where coalesce(note, '') != '' and is_draft = 0
union all
...

```

它还整理出了 beat 类型与正式名称的映射，推测是从探索参考代码库时读到的 [Django 对象关系映射（ORM）定义](https://github.com/simonw/simonwillisonblog/blob/2e9d7ebe64da799b3927e61b4f85d98f7e9bc9aa/blog/models.py#L545-L551)中得出的：

```
const beatTypeDisplay = {
  release: 'Release',
  til: 'TIL',
  til_update: 'TIL updated',
  research: 'Research',
  tool: 'Tool',
  museum: 'Museum'
};

```

让智能体参考另一个代码库，是传达复杂概念的一条有效捷径。提示词只需补充很少的信息，就能让它理解需求。

---

[上一篇原文：使用 WebAssembly 和 Gifsicle 构建 GIF 优化工具](https://simonwillison.net/guides/agentic-engineering-patterns/gif-optimization/) · [下一篇原文：我使用的提示词](https://simonwillison.net/guides/agentic-engineering-patterns/prompts/)
