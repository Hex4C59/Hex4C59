+++
title = "Rust 从零开始：教材目录与配套源码"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "面向第一次学习 Rust 的中文教材。15 章讲解、完整代码、练习和参考答案，从基础语法到待办工具，再学习功能扩展、自定义错误与 JSON 数据迁移。"
summary = "从安装和基础语法开始，学习所有权、集合、错误处理、测试、泛型和迭代器，再完成文件存储、功能扩展和 JSON 迁移项目。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 0
layout = "series"
series_index = true
series_title = "Rust 从零开始"
series_status = "15 章教材与配套项目已完成"
series_intro = "从第一个能运行的程序开始，通过练习学会使用 Rust，做出能保存数据的命令行工具，再学习依赖管理和数据迁移。"
ShowToc = true
+++

[开始阅读：学习指南](/posts/rust-00-learning-guide/) · [下载配套源码](course.zip)

## 全部章节

- [Rust 从零开始：怎么使用这套教材](/posts/rust-00-learning-guide/)
- [Rust 入门 01：安装工具，运行第一个程序](/posts/rust-01-setup/)
- [Rust 入门 02：用变量和类型表示数据](/posts/rust-02-variables/)
- [Rust 入门 03：函数、判断和循环](/posts/rust-03-functions/)
- [Rust 入门 04：所有权、移动和借用](/posts/rust-04-ownership/)
- [Rust 入门 05：字符串、列表和字典](/posts/rust-05-collections/)
- [Rust 入门 06：结构体、枚举和 Option](/posts/rust-06-modeling/)
- [Rust 入门 07：读取输入，处理可能失败的操作](/posts/rust-07-errors/)
- [Rust 入门 08：拆分模块，为程序写测试](/posts/rust-08-projects/)
- [Rust 入门 09：读懂泛型、trait 和生命周期](/posts/rust-09-traits/)
- [Rust 入门 10：闭包和迭代器](/posts/rust-10-iterators/)
- [Rust 入门 11：实现待办工具的核心逻辑](/posts/rust-11-taskbook/)
- [Rust 入门 12：保存数据，完成命令行工具](/posts/rust-12-storage/)
- [Rust 入门 13：给待办工具增加筛选、搜索和删除](/posts/rust-13-taskbook-plus/)
- [Rust 入门 14：用自定义错误类型保留失败原因](/posts/rust-14-typed-errors/)
- [Rust 入门 15：用 Serde 保存 JSON，并迁移旧任务](/posts/rust-15-serde-json/)

## 源码与运行方式

解压下载包，进入 `rust-course` 目录。安装好 Rust 工具链后运行：

```sh
cargo run -p rust-basics --example ch01_hello
cargo run -p taskbook -- add "学习 Rust"
cargo run -p taskbook -- list
cargo test --workspace
```

第 1～12 章使用基础工作区；第 13～15 章在 `practice` 工作区运行，第十五章使用 Serde 和 serde_json。更多命令、目录说明和验证范围见下载包中的 `README.md`。

```sh
cd practice
cargo fetch --locked
cargo run -p taskbook-plus -- pending
cargo run -p error-lab -- 30
cargo run -p taskbook-json --example serde_basics
```
