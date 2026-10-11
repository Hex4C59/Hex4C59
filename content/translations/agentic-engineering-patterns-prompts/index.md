+++
title = "智能体工程模式 16：我使用的提示词"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison 分享用于 HTML 原型、文章校对、图片替代文本和播客摘录的四组提示词，并说明自己的使用方式和修改原则。"
summary = "附录收录作者使用的 Claude 项目自定义指令：用原生 HTML 构建工具、检查文章问题、起草图片替代文本，以及从播客转录稿中挑选精彩引文。"
tags = ["Agent", "智能体工程", "提示词", "Claude", "无障碍", "校对"]
categories = ["Translations"]
topics = ["agents", "agentic-engineering", "prompting", "accessibility", "proofreading"]
translation_category = "工程实践"
series = ["智能体工程模式"]
series_order = 17
series_label = "我使用的提示词"
series_part = "附录"
series_number = 16
original_title = "Prompts I use"
original_url = "https://simonwillison.net/guides/agentic-engineering-patterns/prompts/"
original_author = "Simon Willison"
original_date = ""
original_site = "Simon Willison’s Weblog"
ShowToc = true
+++

> **译文信息**
>
> - 原文：[Prompts I use](https://simonwillison.net/guides/agentic-engineering-patterns/prompts/)
> - 作者：Simon Willison
> - 中文翻译与整理：Hex4C59（AI 辅助）
> - 翻译整理：2026-10-11
>
> 本文为非官方中文译文。正文中的「我」、写作原则、产品功能和使用体验均为原作者的表述。提示词已译为中文，两个代码片段逐字保留，它们仅展示开头格式，不是完整程序；译者未执行这些提示词。

指南的这一部分会持续更新，收录我自己使用的提示词。其他章节会在合适的地方链接到这里。

## Artifacts（产物） {#artifacts}

我经常使用 Claude 的 Artifacts 功能制作原型和小型 HTML 工具。Artifacts 指的是普通 Claude 对话用 HTML 和 JavaScript 构建应用，并直接在 Claude 的聊天界面中展示。OpenAI 和 Gemini 也提供类似的功能，两者都称之为 Canvas。

模型很喜欢用 React 来构建这些应用。我不喜欢 React 需要额外的构建步骤，因为这会妨碍我直接把代码从 Artifact 中复制出来，粘贴到其他静态托管服务。因此，我会在一个设置了以下自定义指令的 Claude 项目中创建 Artifacts：

> 在 Artifacts 中绝不要使用 React。始终使用普通 HTML、原生 JavaScript 和 CSS，并尽量减少依赖。
>
> CSS 使用两个空格缩进，开头应采用以下格式：

```xml
<style>
* {
  box-sizing: border-box;
}

```

> 输入框和文本区域的字号应为 16px。字体始终优先使用 Helvetica。
>
> JavaScript 使用两个空格缩进，开头应采用以下格式：

```xml
<script type="module">
// code in here should not be indented at the first level

```

> 标题优先使用句首大写（Sentence case）的形式。

## 校对 {#proofreader}

我不会让大语言模型（Large Language Models，LLM）为博客撰写正文。我的底线是：任何表达观点或使用第一人称「我」的文字，都必须由我自己写。我允许 LLM 更新代码文档，但如果一段文字带着我的名字和个人风格，就由我亲自撰写。

我会使用 LLM 校对准备发布的文字。下面是我目前的校对提示词，作为 Claude 项目中的自定义指令使用：

> 你负责校对即将发布的文章。
>
> 1. 找出拼写错误和笔误。
> 2. 找出语法错误。
> 3. 留意重复的用词，比如「X 很有趣，Y 也很有趣」。
> 4. 找出逻辑错误或事实错误。
> 5. 标出薄弱、可以进一步加强的论证。
> 6. 确保没有空链接或占位链接。

## 替代文本（Alt Text） {#alt-text}

我会把下面这条提示词与图片一起使用，帮助起草供无障碍访问使用的替代文本。替代文本用于向无法直接查看图片的读者传达图片内容。

> 为用户粘贴的任何图片编写替代文本。始终把替代文本放在围栏代码块中，方便复制粘贴。始终只用一行呈现，以便直接用于 Markdown 图片。图片中的所有文字，例如截图上的文字，都必须原样完整包含。开头应先简短说明这是什么类型的图片。

我通常用 Claude Opus 来完成这项任务，因为我发现它在替代文本方面很有判断力。它经常会自行做出编辑取舍，比如只突出图表中最有意思的数字。

这些取舍未必总是正确。替代文本应该传达图片想表达的核心含义。我经常亲自修改这条提示词生成的文字，或者继续发出提示，让它展开某些描述，或删掉多余的信息。

有时，我会在使用这条提示词的同一段对话中提供多张图片。这样，模型就能在描述后续图片时，参考第一张图片已经传达的信息。

## 播客亮点 {#podcast-highlights}

[作为嘉宾参加播客](https://simonwillison.net/tags/podcast-appearances/)后，我喜欢写一篇博客文章，引用对话中的一些精彩片段。我会先把播客转录稿粘贴到一个 Claude 项目中，并使用以下自定义指令：

> 你会收到一期播客的转录稿。找出其中最有意思的引文：最能体现整体主题的片段，以及提出出人意料的想法，或表达得特别清楚、引人入胜、有火花的片段。回答只包含这些引文，较长的引文也可以。

这里是我粘贴与 Lenny Rachitsky 对谈的[《AI 现状综述：我们已跨过拐点，无人化工厂即将到来，以及自动化的时间表》](https://www.lennysnewsletter.com/p/an-ai-state-of-the-union)转录稿后，得到的[示例输出](https://claude.ai/share/713e7c9a-66cb-4c24-a9e2-028ad96ec23b)。
