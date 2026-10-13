+++
title = "{{ replace (replace .Name "_" " ") "-" " " | title }}"
date = {{ .Date }}
draft = true
author = "Hex4C59"
description = ""
summary = ""
tags = []
categories = ["programming"]
source_kind = "original"
ShowToc = true
math = false
+++

> 写作前按 `.agents/content/section-routing.md` 确定栏目，并阅读通用技术写作规范。发布前补全标题、描述和摘要，删除模板提示，再将 `draft` 改为 `false`。
>
> 连续课程的章节另加 `series = ["系列键"]`、`series_order = 1`；`series_number`、`series_label` 和 `series_part` 按课程需要填写。单篇教程和课程附录可以不加入正式系列。只有迁移旧文章、需要保留地址时才添加 `url`。

## 读完能学会什么

说明读者将理解的规则或能够完成的任务，以及需要先掌握的知识。操作教程列出环境和版本；原理文章说明讨论范围。

## 从一个例子开始

给出可以直接运行或逐步推导的例子。代码块标明语言，并解释输入、关键步骤和结果。

## 为什么这样写

解释规则和推导过程。用对照写法说明边界；编译反例应明确标注为不能通过的代码，并解释报错原因。

## 自己试一遍

给出具体练习、验收条件和参考答案。涉及文件写入或服务启动时，说明如何清理本次操作。

## 继续阅读

把下一步学习入口、参考资料或配套源码放在这里。
