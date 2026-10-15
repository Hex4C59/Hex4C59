+++
url = "/posts/rust-from-zero/"
title = "Rust 从零开始：教材目录与配套源码"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-15
draft = false
author = "Hex4C59"
description = "面向第一次学习 Rust 的中文教材。已发布 18 章基础讲解、练习和配套源码；后续以 Web Server 为综合项目，逐步学习 TCP、HTTP、路由、静态文件、线程池与服务关闭。"
summary = "从基础语法、所有权与错误处理入门，先用命令行工具和 HTTP 客户端练习，再以 Web Server 为后续综合项目，把连接、请求处理、并发与资源管理串起来。"
tags = ["Rust", "学习路线", "项目实践"]
categories = ["programming"]
series = ["rust-from-zero"]
series_order = 0
layout = "series"
series_index = true
series_title = "Rust 从零开始"
series_status = "18 章已发布；后续 Web Server 项目已规划"
series_intro = "从第一个程序开始学习 Rust，用命令行与 HTTP 客户端练习基础，再逐步完成一个支持静态文件、JSON 路由和线程池的 Web Server。"
ShowToc = true
source_kind = "original"
article_type = "tutorial"
series_kind = "course"
+++

[开始阅读：学习指南](/posts/rust-00-learning-guide/) · [下载配套源码](course.zip)

## 已发布章节 {#全部章节}

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
- [Rust 入门 16：备份任务数据，恢复到新文件](/posts/rust-16-backup/)
- [Rust 入门 17：用 clap 整理命令行接口](/posts/rust-17-clap/)
- [Rust 入门 18：请求本机 HTTP 服务，读取 JSON 响应](/posts/rust-18-http/)

## 后续综合项目：Web Server {#webserver-project}

前十八章打好语法、文件操作和 HTTP 客户端的基础，接下来的综合项目是从空 Cargo 项目实现一个 Web Server（Web 服务器）：接收浏览器或客户端的 HTTP 请求，再返回网页、文件或 JSON。命令行待办工具作为前置练习，后续项目围绕服务器展开。

目标程序暂定名为 `rust-webserver`，默认只监听本机地址 `127.0.0.1`。完成后应能访问首页 `/`、健康检查 `/health`、课程数据 `/lesson.json` 和静态资源 `/static/`；第十八章的客户端可以请求其中的课程数据，检查服务器是否返回了正确的响应。

下面是后续章节的写作安排，正文和项目源码尚未发布。先用标准库讲清连接、协议和并发；异步 Rust、Tokio 与 Web 框架作为完成这个项目后的扩展。

| 拟定章节 | 项目推进 | 要讲透的 Rust 规则与问题 |
| --- | --- | --- |
| 19：接收第一个 TCP 连接 | 监听本机端口，接收连接并读写字节 | `TcpListener`、`TcpStream`、`Read`、`Write`；谁拥有连接，离开作用域后由谁释放 |
| 20：解析请求，构造响应 | 定义请求与响应类型，处理完整请求头和字节长度 | `&[u8]`、`&str` 与 `String` 的边界；借用何时结束，`Result` 如何保留解析错误 |
| 21：路由与 JSON 接口 | 实现首页、健康检查和课程数据路由 | 用枚举和 `match` 分派请求；函数、闭包与处理器的参数和返回值 |
| 22：提供静态文件 | 读取文档目录中的文件，处理不存在和越界路径 | `Path` 与 `PathBuf`、所有权与文件句柄；把 I/O 错误转换为明确响应 |
| 23：让多个连接同时工作 | 从单线程处理过渡到多线程，观察慢请求的影响 | `move` 闭包、`Send` 与 `'static` 约束；为何借用局部数据的任务不能直接交给工作线程 |
| 24：实现固定线程池 | 用工作线程和有界队列分配连接，定义队列满时的行为 | channel、`Arc`、`Mutex`、`Box<dyn FnOnce() + Send + 'static>`；锁保护什么，何时释放 |
| 25：关闭服务并完成验收 | 配置地址与目录，限制请求大小和等待时间，停止接收后回收线程 | `Drop`、`Option::take`、资源释放顺序与 `JoinHandle`；单元测试和本机集成测试 |

首版按教学用的 HTTP/1.1 子集实现：支持 `GET` 和 `HEAD`，每条连接只处理一个请求，响应声明 `Connection: close`。请求头必须有大小和时间限制，静态文件只能来自配置的文档目录。请求体、长连接、TLS 和公网部署留在扩展范围中；具体拒绝规则会随协议章节和测试一起写清。

项目验收包含以下行为：

- 浏览器能打开首页；客户端能解析课程 JSON；`HEAD` 返回与对应 `GET` 一致的响应元信息，但不发送响应体。
- 不存在的资源、非法请求、不支持的方法和目录越界都有明确处理；对应行为有自动测试。
- 工作线程数量和等待队列有上限，慢连接不会无限占用资源；测试覆盖队列满、超时和客户端中途断开的情况。
- 关闭过程能停止接收新连接，处理或明确取消已接收的任务并回收工作线程。能够解释连接、任务和共享状态的所有权，以及释放它们的先后顺序。

每章仍会配最小语法例子、预期编译失败的对照和独立练习。项目完成与否同时检查运行行为和对语言规则的解释。

参考资料：[《Rust 程序设计语言》的多线程 Web Server 项目](https://doc.rust-lang.org/book/ch21-00-final-project-a-web-server.html)、[标准库 `TcpListener` 文档](https://doc.rust-lang.org/std/net/struct.TcpListener.html)。资料核对日期：2026-10-15。

## 语法规则阅读路线 {#syntax-route}

第二、三、四、六到十章增加了语法细读。每一节用最小程序拆开规则，再用故意失败的反例说明边界。按章节顺序读；已经做完项目的读者，可以用下表回查具体写法。

| 位置 | 讨论的语法 | 阅读时要回答的问题 |
| --- | --- | --- |
| [第二章](/posts/rust-02-variables/#syntax-depth) | 绑定、类型推断、数字后缀与转换 | 推断受哪些位置约束；为什么窄化可能改变数值 |
| [第三章](/posts/rust-03-functions/#syntax-depth) | 块、分号、单元值与控制流类型 | 一段代码产生什么值；哪个分支会结束函数 |
| [第四章](/posts/rust-04-ownership/#syntax-depth) | mut、引用、解引用与再借用 | 正在修改绑定还是所指的数据；权限是否仍被借用 |
| [第六章](/posts/rust-06-modeling/#syntax-depth) | 模式、守卫、ref、通配符与 let ... else | 模式建立了什么名字；内部字段会移动还是借用 |
| [第七章](/posts/rust-07-errors/#syntax-depth) | Result 与 Option 上的问号 | 成功留下什么值；失败返回到哪一层 |
| [第八章](/posts/rust-08-projects/#syntax-depth) | 路径、可见性、宏与属性 | 名字从哪里解析；访问和编译条件是否允许 |
| [第九章](/posts/rust-09-traits/#syntax-depth) | 泛型参数、impl Trait 与生命周期关系 | 哪些位置必须相同；签名增加了哪些约束 |
| [第十章](/posts/rust-10-iterators/#syntax-depth) | 闭包捕获与调用能力 | 捕获怎样发生；调用是否读取、修改或交出数据 |

源码下载包的 `syntax/` 保存 22 个正常程序，`compile-fail/syntax*.rs` 保存 20 个预期失败的程序。它们逐个运行，不并入正常 Cargo 构建。不要只记录“能编译”：还要写出值的类型、名字的作用域和失败发生在哪条规则上。

## 练习与查阅附录

- [三个阶段的分级练习与项目验收](/posts/rust-practice-checkpoints/)：第六、十二、十八章后的独立练习和可运行答案。
- [从报错位置找到问题](/posts/rust-troubleshooting/)：工具、工作区、所有权、依赖和运行错误的检查顺序。

附录供练习和查阅，不计入十八章的顺序。第四、九章另有所有权和生命周期图解。

## 源码与运行方式

解压下载包，进入 `rust-course` 目录。安装好 Rust 工具链后运行：

```sh
cargo run -p rust-basics --example ch01_hello
cargo run -p taskbook -- add "学习 Rust"
cargo run -p taskbook -- list
cargo test --workspace
```

第 1～12 章使用基础工作区；第 13～15 章在 `practice` 工作区运行；第 16～18 章在 `projects` 工作区运行。JSON 项目使用 Serde，后续命令行和 HTTP 项目分别使用 clap 与 reqwest。更多命令、目录说明和验证范围见下载包中的 `README.md`。

```sh
cd practice
cargo fetch --locked
cargo run -p taskbook-plus -- pending
cargo run -p error-lab -- 30
cargo run -p taskbook-json --example serde_basics
```

第 16～18 章的命令从 `rust-course/projects` 运行，首次获取依赖需要网络。HTTP 示例只连接同机启动的练习服务：

```sh
cd ../projects
cargo fetch --locked
cargo run -p taskbook-cli -- --help
cargo run -p lesson-http --example serve
```

服务打印端口后，在另一个进入 `projects` 的终端运行客户端。完整步骤、预期输出和失败条件见第十八章。
