+++
title = "Rust 入门 06：结构体、枚举和 Option"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-12T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "为任务定义数据和方法，用枚举表示命令，用 Option 和 match 处理可能缺失的值。"
summary = "为任务定义数据和方法，用枚举表示命令，用 Option 和 match 处理可能缺失的值。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 6
series_label = "结构体与枚举"
series_part = "理解数据如何使用"
series_number = 6
ShowToc = true
+++

如果每条任务都需要标题和完成状态，可以用结构体把它们放在一起。如果程序只接受“新增、完成、列出”这几种命令，可以用枚举明确列出可能情况。本章把真实需求翻译为 Rust 类型。

在解压后的 `rust-course` 目录运行：

```sh
cargo run -p rust-basics --example ch06_modeling
```

完整代码位于 `basics/examples/ch06_modeling.rs`。也可以把下面的代码完整替换到自己项目的 `src/main.rs`，再运行 `cargo run`。

```rust
#[derive(Debug)]
struct Task {
    title: String,
    done: bool,
}

impl Task {
    fn new(title: &str) -> Self {
        Self {
            title: title.to_string(),
            done: false,
        }
    }

    fn complete(&mut self) {
        self.done = true;
    }

    fn label(&self) -> &str {
        &self.title
    }
}

enum Command {
    Add(String),
    Done(u64),
    List,
}

fn describe(command: &Command) {
    match command {
        Command::Add(title) => println!("新增：{title}"),
        Command::Done(id) => println!("完成编号：{id}"),
        Command::List => println!("列出全部任务"),
    }
}

fn first_task(tasks: &[Task]) -> Option<&Task> {
    tasks.first()
}

fn main() {
    let mut task = Task::new("学习枚举");
    task.complete();
    println!("{}：{}", task.label(), task.done);
    let tasks = vec![task];
    match first_task(&tasks) {
        Some(task) => println!("第一项：{}", task.label()),
        None => println!("还没有任务"),
    }
    if let Some(task) = first_task(&tasks) {
        println!("找到：{}", task.label());
    }
    describe(&Command::Add(String::from("写练习")));
    describe(&Command::Done(1));
    describe(&Command::List);
}
```

输出依次说明任务已完成、列表中找到了任务，并描述三种命令。`Task` 和 `Command` 是我们自己定义的类型。

## struct 为数据命名

`struct Task` 定义一种结构体，字段 `title: String` 保存标题，`done: bool` 保存完成状态。创建一个 `Task` 时，需要为这些字段提供值。

使用 `task.title` 访问字段，比记住某个元组的第 0 项是标题更容易读懂。包含 `String` 的 `Task` 默认不具备 `Copy`；把它移动到 `vec![task]` 后，就通过列表访问它。

`#[derive(Debug)]` 请编译器为类型生成调试输出所需的实现，之后可以用 `println!("{task:?}")` 查看字段。`{:?}` 适合检查数据，面向用户的输出通常另写格式。

## impl 把相关行为放在类型旁边

`impl Task` 内的函数与 `Task` 相关。`Task::new("学习枚举")` 没有 `self` 参数，称为关联函数，常用于创建值。`Self` 在这里代表 `Task`。

带 `self` 参数的函数称为方法。参数告诉你方法怎样使用当前对象：

| 参数 | 方法的权限 |
| --- | --- |
| `&self` | 借用当前对象，读取它 |
| `&mut self` | 独占地借用当前对象，允许修改它 |
| `self` | 取得当前对象所有权 |

`task.complete()` 需要 `&mut self`，所以 `task` 声明为 `mut`。`task.label()` 返回借用的标题视图，没有复制整个字符串。这个视图依赖原任务继续存在。

## enum 表示几种互斥情况

结构体把字段组合到一起；枚举表示一个值属于列出的哪一种情况。`Command` 有三种变体：

- `Add(String)` 携带一个拥有内容的标题。
- `Done(u64)` 携带要完成的任务编号。
- `List` 不需要额外数据。

一个命令在某一时刻只有一个变体。这样定义以后，不会出现“既是新增又是列出”的命令状态。

`describe` 接收 `&Command`，所以可以读取命令携带的数据而不拿走它。`match` 根据当前变体执行相应分支，还把变体里的数据绑定给 `title` 或 `id`。

## match 要覆盖所有可能

`match` 要求处理所有可能情况。给 `Command` 加一个新变体后，原来的 `match` 会指出哪个情况还没处理。这样增加功能时，就能发现需要一并更新的逻辑。

`_` 可以匹配剩下的情况；当每种情况都有明确含义时，逐一列出更容易发现遗漏。`match` 也可以产生值，所有可能返回结果的分支需要得到兼容的类型。

## Option 表示可能没有值

`Option<T>` 是标准库定义的枚举，可能是 `Some(value)` 或 `None`。`T` 是它包住的值的类型。

`first_task(tasks: &[Task]) -> Option<&Task>` 返回“可能存在的、借来的第一条任务”。有任务时得到 `Some(&Task)`，空列表时得到 `None`。访问其中的任务前，需要处理这两种情况。

`if let Some(task) = first_task(&tasks)` 用于只关心有值的分支。没有值时直接跳过代码块。如果两种情况都需要给用户反馈，使用 `match` 更清楚。

`Option` 在这里无需手工 `use`。它和常见的 `String`、`Vec` 等名称由 Rust 的预导入机制提供；这不意味着所有标准库类型都自动可见，`HashMap` 仍需要引入。

## 练习：定义一本书

定义 `Book`，保存标题 `String` 和是否读完 `bool`。写 `new` 和 `finish`，创建一个书籍列表，用 `first_mut()` 取得第一本书并标记读完。列表可能为空，要用 `if let` 或 `match` 处理。

<details>
<summary>参考答案：先自己完成再展开</summary>

```rust
struct Book {
    title: String,
    finished: bool,
}

impl Book {
    fn new(title: &str) -> Self {
        Self {
            title: title.to_string(),
            finished: false,
        }
    }

    fn finish(&mut self) {
        self.finished = true;
    }
}

fn main() {
    let mut books = [Book::new("Rust 入门")];
    if let Some(book) = books.first_mut() {
        book.finish();
        println!("{}：{}", book.title, book.finished);
    }
    assert!(books[0].finished);
}
```

运行 `cargo run -p rust-basics --example answer06`。`first_mut()` 返回 `Option<&mut Book>`，所以拿到 `Some(book)` 后能修改原书籍。将列表改为空时，分支应跳过；参考答案最后的断言也需要去掉或改成空列表检查，不能继续索引第 0 项。

</details>

## 官方延伸阅读

- [结构体与方法](https://doc.rust-lang.org/book/ch05-03-method-syntax.html)
- [枚举与 Option](https://doc.rust-lang.org/book/ch06-01-defining-an-enum.html)
- [match](https://doc.rust-lang.org/book/ch06-02-match.html)

外部文档查阅日期：2026-10-12。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：字符串与集合](/posts/rust-05-collections/) · [下一章：输入与错误处理](/posts/rust-07-errors/)
