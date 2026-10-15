---
title: "软件设计的取舍：抽象、契约与复杂度"
description: "用可运行的案例比较抽象、契约与模块边界，沿需求变化检查软件设计的收益和代价。"
lastmod: 2026-10-15
series_start: "/articles/software-design-00-reading-guide/"
series_status: "连载中"
---

从[系列目录](/articles/software-design/)查看阅读路线。先读[导读](/articles/software-design-00-reading-guide/)，再进入[第 01 篇：抽象的收益与代价](/articles/software-design-01-abstraction/)。

目前完成导读和前六篇：[第 02 篇](/articles/software-design-02-contracts/)以完成待办任务为主线，讨论输入、结果、失败与数据变化的约定，并比较需求变化后的选择。[第 03 篇](/articles/software-design-03-indirection/)继续解释按操作名称选择函数的过程，比较条件分支与处理器表的收益、依赖和阅读成本。[第 04 篇](/articles/software-design-04-module-boundaries/)比较按操作拆分与集中维护任务表示，沿内部容器变化解释模块边界和信息隐藏。[第 05 篇](/articles/software-design-05-state-effects/)解释状态与副作用，沿保存顺序、失败和重试检查内存及外部数据的变化。[第 06 篇](/articles/software-design-06-async-errors/)继续讨论 Promise、等待与错误传播，处理同一所有者等待期间的新修改。后续将讨论可测试性与设计演化。各篇使用合成数据，并记录对应代码的运行环境和验证范围。
