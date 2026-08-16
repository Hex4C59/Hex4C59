+++
title = ""
date = {{ .Date }}
draft = true
author = "Hex4C59"
description = ""
summary = ""
tags = []
categories = ["Agent"]
series = []
series_order = 0
difficulty = ""
article_type = ""
topics = []
frameworks = []
ShowToc = true
+++

> 本文件只提供 Agent 文章的 front matter 和文章骨架，不是完整写作规范。通用技术写作要求见 `.agents/content/technical-writing.md`；Agent 专栏规则见 `.agents/content/agent-section.md`；DeepSeek Harness 系列另见 `.agents/content/deepseek-harness.md`。
>
> 新建文章后，先补全 front matter，再删除这段提示。`article_type` 使用 `concept`、`tutorial`、`practice`、`review` 或 `eval`；`difficulty` 使用 `beginner`、`intermediate` 或 `advanced`。只有属于某个系列时才填写 `series` 和 `series_order`。
>
> 如果文章介绍一个具体项目、框架或实验，请补充被测试的版本或 commit、运行环境、依赖、模型和关键配置，并把复现命令写进正文。

## 这篇文章要解决什么问题

> 用 2~4 句话说明目标读者、前置知识、核心问题、问题的重要性和文章范围。

## 先给结论

先写读者最需要知道的判断、结果或建议。不要让读者读完整篇文章后才知道你的结论。

## 正文结构

> 根据 `article_type` 选择下面一种结构，并删除不适用的提示。不要为了填满模板而保留无关章节。

### `concept`：概念或架构解释

> 问题与背景 → 核心概念或系统结构 → 证据和实例 → 常见误解 → 适用边界 → 总结。

### `tutorial`：操作教程

> 目标结果 → 前置条件 → 环境准备 → 分步实现 → 验证结果 → 常见失败与排查 → 清理和扩展。

### `practice`：工程实战

> 场景与约束 → 方案选择 → 系统设计 → 关键实现 → 测试与验证 → 工程权衡 → 失败模式 → 总结。

### `review`：方案或项目复盘

> 评审问题 → 背景与范围 → 观察到的事实 → 设计判断 → 替代方案 → 风险与限制 → 结论。

### `eval`：评测或实验

> 评测问题 → 实验环境 → 数据集或测试任务 → 指标定义 → 实验方法 → 结果 → 分析 → 局限与复现方法。

## 总结

用 3~5 条要点回收全文结论、主要代价、适用边界和可执行的下一步。若文章是教程，确认读者能从这里找到验证结果和后续扩展方向。

## 延伸阅读

- 
- 
- 
