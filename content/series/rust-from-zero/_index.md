---
title: "Rust 从零开始"
url: "/series/rust-from-zero/"
description: "已发布 18 章 Rust 入门教材与配套练习；后续以 Web Server 为综合项目，从 TCP 和 HTTP 逐步学习路由、静态文件、线程池与服务关闭。"
lastmod: 2026-10-15
series_start: "/tutorials/rust-00-learning-guide/"
series_status: "18 章已发布；后续 Web Server 项目已规划"
---

这套教材按知识依赖顺序编排，每章都有完整示例、练习和参考答案。先运行、再修改、再独立完成练习。第十一、十二章把基础知识组合成能够保存数据的待办工具，后续章节扩展查询、JSON、备份与命令行接口，并用本机服务学习 HTTP 请求。

[从学习指南开始](/posts/rust-00-learning-guide/) · [下载配套源码](/posts/rust-from-zero/course.zip)

后续综合项目是[Web Server](/posts/rust-from-zero/#webserver-project)：从接收本机连接开始，实现网页与 JSON 路由、静态文件、固定线程池和服务关闭。拟定第十九至二十五章围绕这个项目展开，逐项讲解所有权、字节与字符串、线程约束及资源释放；正文与源码待编写。

正式章节之外还提供[分级练习与项目验收](/posts/rust-practice-checkpoints/)和[常见错误排查](/posts/rust-troubleshooting/)。所有权与生命周期图解分别放在第四、九章中。

第二、三、四、六到十章提供[语法细读](/posts/rust-from-zero/#syntax-route)，用类型推导、对照写法和编译反例解释语言规则。
