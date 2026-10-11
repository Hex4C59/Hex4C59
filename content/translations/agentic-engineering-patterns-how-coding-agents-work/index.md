+++
title = "智能体工程模式 06：编程智能体如何工作"
date = 2026-10-11T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "Simon Willison 解释编程智能体的运行机制，涵盖大语言模型、聊天模板、Token 缓存、工具调用、系统提示词和推理。"
summary = "编程智能体用运行框架组织 LLM、系统提示词和工具。本文通过对话与天气查询示例，说明框架如何维护历史、执行工具并把结果反馈给模型。"
tags = ["Agent", "智能体工程", "编程智能体", "LLM", "工具调用", "提示词"]
categories = ["Translations"]
topics = ["agents", "agentic-engineering", "coding-agents", "tool-use", "prompting"]
translation_category = "工程实践"
series = ["智能体工程模式"]
series_order = 7
series_label = "编程智能体如何工作"
series_part = "与编程智能体协作"
series_number = 6
original_title = "How coding agents work"
original_url = "https://simonwillison.net/guides/agentic-engineering-patterns/how-coding-agents-work/"
original_author = "Simon Willison"
original_date = ""
original_site = "Simon Willison’s Weblog"
ShowToc = true
+++

> **译文信息**
>
> - 原文：[How coding agents work](https://simonwillison.net/guides/agentic-engineering-patterns/how-coding-agents-work/)
> - 作者：Simon Willison
> - 中文翻译与整理：Hex4C59（AI 辅助）
> - 翻译整理：2026-10-11
>
> 本文为非官方中文译文，依据提供的原文正文翻译，并按系列目录补入小节标题。正文中的「我」及相关判断均指原作者。模型名称、Token 编号和示例保留原文记录；对话与工具调用片段用于说明机制，不是完整的可运行程序。Codex 系统提示词链接指向原文引用的固定版本，不代表当前版本。

和使用任何工具一样，理解[编程智能体](https://simonwillison.net/guides/agentic-engineering-patterns/what-is-agentic-engineering/)内部如何工作，可以帮助你更好地判断该怎样使用它们。

编程智能体是一种软件，充当大语言模型的运行框架（harness）。它通过用户看不到的提示词和可调用的工具，为模型扩展额外的能力。

## 大语言模型 {#large-language-models}

任何编程智能体的核心，都是一个大语言模型（Large Language Model，LLM）。它们的名字可能是 GPT-5.4、Claude Opus 4.6、Gemini 3.1 Pro 或 Qwen3.5-35B-A3B。

LLM 是一种能够补全文本句子的机器学习模型。给模型输入「the cat sat on the 」，它几乎肯定会建议用「mat」作为句子的下一个词。

随着模型规模增大、训练数据增加，它们可以补全更复杂的句子，比如「a python function to download a file from a URL is def download_file(url): 」。

LLM 实际上并不直接处理单词，而是处理 Token，也就是文本编码后得到的单位。一段文本会转换成一串整数形式的 Token，因此「the cat sat on the 」会变成 `[3086, 9059, 10139, 402, 290, 220]`。理解这一点很有用，因为 LLM 提供商按处理的 Token 数量收费，而且模型一次能处理的 Token 数量也有上限。

你可以在 [platform.openai.com/tokenizer](https://platform.openai.com/tokenizer) 上试用 OpenAI 的分词器，看看这个过程如何工作。

输入 LLM 的内容称为提示词（prompt）。LLM 返回的文本称为补全结果（completion），有时也称为响应（response）。

如今，许多模型是多模态的，也就是说，它们接受的输入不只有文本。视觉大语言模型（Vision LLMs，vLLMs）可以把图像作为输入的一部分，因此你可以向它们提供草图、照片或截图。一种常见的误解是，这些图像会先经过独立的光学字符识别（OCR）或图像分析流程。实际上，这些输入也会转换为整数形式的 Token，并以与文本相同的方式处理。

## 按聊天模板组织提示词 {#chat-templated-prompts}

最早的 LLM 是补全引擎。用户需要提供一段提示词，让模型接着补全，就像前面的两个例子那样。

这种方式不太方便用户使用，因此大多数模型后来转而使用聊天模板，把与模型的交流组织成一段模拟对话。

它实际上仍是一种补全提示词，只是采用了特殊的格式，大致如下：

```
user: write a python function to download a file from a URL
assistant:

```

这段提示词最自然的补全，就是让由 LLM 扮演的助手用一段 Python 代码回答用户的问题。

LLM 是无状态的：每次处理提示词时，它都从同样的空白状态开始。

为了维持对话的效果，与模型交互的软件需要自行保存状态。每当用户输入新的聊天提示词，它都要把已有的完整对话重新传给模型：

```
user: write a python function to download a file from a URL
assistant: def download_url(url):
    return urllib.request.urlopen(url).read()
user: use the requests library instead
assistant:

```

由于提供商对输入和输出的 Token 都收费，对话越长，每次提示的费用就越高，因为输入 Token 的数量会不断增加。

## Token 缓存 {#token-caching}

大多数模型提供商会为缓存的输入 Token 提供更低的费率，在一定程度上缓解这个问题。如果一段相同的 Token 前缀在较短时间内已经处理过，底层设施就可以缓存并复用处理它时所需的大量昂贵计算，因此再次处理时能够收取较低的费用。

编程智能体在设计时会考虑这种优化。它们尽量不修改早先的对话内容，以便充分利用缓存。

## 调用工具 {#calling-tools}

LLM 智能体的决定性特征，是能够调用工具。那么，什么是工具？

工具就是智能体运行框架提供给 LLM 调用的函数。

在提示词层面，它大致是这样的：

```
system: If you need to access the weather, end your turn with <tool>get_weather(city_name)</tool>
user: what's the weather in San Francisco?
assistant:

```

这里，助手可能会返回以下文本：

```
<tool>get_weather("San Francisco")</tool>

```

随后，模型运行框架会从响应中提取这个函数调用请求，可能是通过正则表达式来提取，然后执行工具。

接着，它会构造一段大致如下的提示词，把结果返回给模型：

```
system: If you need to access the weather, end your turn with <tool>get_weather(city_name)</tool>
user: what's the weather in San Francisco?
assistant: <tool>get_weather("San Francisco")</tool>
user: <tool-result>61°, Partly cloudy</tool-result>
assistant:

```

现在，LLM 就能利用工具结果来回答用户的问题。

大多数编程智能体会定义十几个甚至更多工具，供智能体调用。其中最强大的工具能够执行代码，例如执行终端命令的 `Bash()` 工具，或者运行 Python 代码的 `Python()` 工具。

## 系统提示词 {#the-system-prompt}

在前面的例子中，我加入了一条标记为 `system` 的初始消息，告诉 LLM 有哪些工具可用，以及如何调用它们。

编程智能体通常会在每次对话开始时加入这样的系统提示词。用户看不到它，但它会通过指令告诉模型应该如何行动。

这些系统提示词可能长达数百行。这是截至 2026 年 3 月的 [OpenAI Codex 系统提示词](https://github.com/openai/codex/blob/rust-v0.114.0/codex-rs/core/templates/model_instructions/gpt-5.2-codex_instructions_template.md)。它清楚地展示了驱动这些编程智能体工作的指令是什么样的，是一个很有参考价值的例子。

## 推理 {#reasoning}

2025 年的一项重大进展，是前沿模型系列引入了推理能力。

推理（reasoning）有时在界面中显示为「思考」（thinking），指的是模型在向用户给出回复之前，先花额外的时间生成文本，逐步分析问题及其可能的解决方案。

这看起来有点像一个人把思考过程说出来，效果也类似。关键在于，它让模型能够花更多时间、消耗更多 Token 来处理问题，以期得到更好的结果。

推理对调试代码尤其有用。它让模型有机会梳理更复杂的代码路径，在其中穿插工具调用，并在推理阶段沿着函数调用追溯问题可能的来源。

许多编程智能体可以调高或调低推理强度，让模型在较难的问题上花更多时间思考。

## 在循环中组合 LLM、系统提示词和工具 {#llm-system-prompt-tools-in-a-loop}

信不信由你，构建一个编程智能体所需的主要机制，大部分就是这些！

如果想更深入地理解它们如何工作，可以尝试从零构建自己的智能体。在现有 LLM API，也就是模型服务的调用接口之上，只用几十行代码就能实现一个简单的工具调用循环。

要把工具循环做得好，还需要投入多得多的工作，但它的基本机制出乎意料地简单。

---

[上一篇原文：反模式——应该避免的做法](https://simonwillison.net/guides/agentic-engineering-patterns/anti-patterns/) · [下一篇原文：与编程智能体协作时如何使用 Git](https://simonwillison.net/guides/agentic-engineering-patterns/using-git-with-coding-agents/)
