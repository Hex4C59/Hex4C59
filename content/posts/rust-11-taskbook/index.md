+++
title = "Rust 入门 11：实现待办工具的核心逻辑"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-12T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "组合结构体、枚举、集合和错误处理，实现任务新增、完成、展示和命令参数解析。"
summary = "组合结构体、枚举、集合和错误处理，实现任务新增、完成、展示和命令参数解析。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 11
series_label = "实战：任务与命令"
series_part = "完成一个小项目"
series_number = 11
ShowToc = true
+++

这一章开始实现 `taskbook`。先把任务的新增、完成、展示和命令解析做好，下一章再连接文件与终端。这样你可以先确认数据逻辑正确，再处理外部输入输出。

## 先写下程序应该怎样工作

任务有固定编号、标题和完成状态。新任务默认未完成；完成任务时按编号查找，找不到要返回错误。空白标题不接受。列出任务时使用 `1 [ ] 标题` 或 `1 [x] 标题` 的形式。

命令有三种：`add "标题"`、`list`、`done 编号`。编号使用正整数。标题中不允许制表符或换行，因为下一章会用制表符分隔文件字段。

本项目只增加和完成任务，不删除。新编号取已有最大编号加 1，避免依赖列表当前位置；编号达到上限时返回错误。

## 从头建立项目

你可以直接阅读配套源码，也可以在工作区之外新建自己的项目：

```sh
cargo new taskbook --edition 2024
cd taskbook
```

自行新建项目时，下面的文件路径都相对于这个 `taskbook` 目录，运行命令用 `cargo run` 和 `cargo test`。配套工作区中的对应命令则分别是 `cargo run -p taskbook ...` 和 `cargo test -p taskbook ...`。

## 在 lib.rs 中实现核心逻辑

新建 `src/lib.rs`，完整内容如下。这是暂时不含存储模块的第一版；下一章只需要增加模块声明，不必重写这些函数。

```rust
pub const USAGE: &str = "用法：taskbook add <标题> | list | done <正整数编号>";

#[derive(Debug, PartialEq, Eq)]
pub struct Task {
    pub id: u64,
    pub title: String,
    pub done: bool,
}

#[derive(Debug, PartialEq, Eq)]
pub enum Command {
    Add(String),
    List,
    Done(u64),
}

pub fn parse_args(args: &[String]) -> Result<Command, String> {
    match args {
        [command, title] if command == "add" => Ok(Command::Add(title.clone())),
        [command] if command == "list" => Ok(Command::List),
        [command, id] if command == "done" => {
            let id = id
                .parse::<u64>()
                .map_err(|_| String::from("编号必须是正整数"))?;
            if id == 0 {
                return Err(String::from("编号必须大于 0"));
            }
            Ok(Command::Done(id))
        }
        _ => Err(USAGE.to_string()),
    }
}

pub fn validate_title(title: &str) -> Result<(), String> {
    if title.trim().is_empty() {
        return Err(String::from("标题不能为空"));
    }
    if title.contains(['\t', '\n', '\r']) {
        return Err(String::from("标题不能包含制表符或换行"));
    }
    Ok(())
}

pub fn add_task(tasks: &mut Vec<Task>, title: &str) -> Result<u64, String> {
    validate_title(title)?;
    let id = tasks
        .iter()
        .map(|task| task.id)
        .max()
        .unwrap_or(0)
        .checked_add(1)
        .ok_or_else(|| String::from("任务编号已用完"))?;
    tasks.push(Task {
        id,
        title: title.trim().to_string(),
        done: false,
    });
    Ok(id)
}

pub fn mark_done(tasks: &mut [Task], id: u64) -> Result<(), String> {
    let task = tasks
        .iter_mut()
        .find(|task| task.id == id)
        .ok_or_else(|| format!("找不到任务 {id}"))?;
    task.done = true;
    Ok(())
}

pub fn render_tasks(tasks: &[Task]) -> String {
    if tasks.is_empty() {
        return String::from("还没有任务\n");
    }
    let mut output = String::new();
    for task in tasks {
        let mark = if task.done { "x" } else { " " };
        output.push_str(&format!("{} [{mark}] {}\n", task.id, task.title));
    }
    output
}
```

这些函数没有读取终端或写入文件，所以相同输入可以得到可预测的结果，也很容易在测试里调用。

## 命令解析里有哪些新写法

`match args` 对切片进行模式匹配。`[command, title]` 要求恰好两个参数；`[command]` 要求恰好一个。后面的 `if command == "add"` 是匹配守卫，进一步检查第一个参数的内容。

`title` 来自借用的参数切片，因此是借来的 `String`。`Command::Add` 要保存拥有内容的标题，于是 `title.clone()` 创建副本。这是为命令对象保留数据所做的明确选择。

`parse_args` 负责检查命令形式和编号；`add_task` 负责检查标题。因此解析出 `Add("   ")` 后，实际新增时仍会被拒绝。保持这两个层次的职责明确，测试才容易定位问题。

## Option 可以转换成 Result

`max()` 对空列表返回 `None`，`unwrap_or(0)` 提供初始编号 0。它不会在 `None` 时 panic。

`checked_add(1)` 在加法溢出时返回 `None`。`.ok_or_else(|| String::from("任务编号已用完"))` 把缺失情况转换成 `Err`，接下来的 `?` 就能把错误传出去。

`find` 同样返回 `Option`。`mark_done` 用 `iter_mut()` 找到可修改的任务，再通过 `ok_or_else` 把“找不到”转换成带编号的错误消息。

## Vec 和切片各用在哪里

`add_task` 需要向列表追加元素，因此接收 `&mut Vec<Task>`。`mark_done` 只修改已有元素，接收 `&mut [Task]` 已经足够。`render_tasks` 只读取任务，接收 `&[Task]`。

函数签名直接说明了它需要的权限。调用方在查看这些签名时，也能判断哪些函数可能修改数据、哪些会改变列表长度。

`Task` 的字段暂时公开，方便在教材里查看和构造测试数据。实际库可以把字段设为私有，通过构造函数和方法维护约束。下一章的编码函数还会检查非法字段，防止手工构造的数据直接写入文件。

## 写一个内存中的 main.rs

在自己创建的项目中，将 `src/main.rs` 完整替换为下面的内容，再运行 `cargo run`：

```rust
use taskbook::{add_task, mark_done, render_tasks};

fn main() -> Result<(), String> {
    let mut tasks = Vec::new();
    add_task(&mut tasks, "学习 Rust")?;
    add_task(&mut tasks, "写练习")?;
    mark_done(&mut tasks, 1)?;
    print!("{}", render_tasks(&tasks));
    Ok(())
}
```

预期输出：

```text
1 [x] 学习 Rust
2 [ ] 写练习
```

`main` 返回 `Result<(), String>`，允许函数体中使用 `?`。`()` 表示成功时没有额外数据。若返回 `Err`，Rust 的默认入口处理会报告失败。下一章会改成显式处理错误，给用户更清楚的消息和退出状态。

在下载的配套源码中，这个内存版本保存为示例，而 `src/main.rs` 已是下一章的完整版本，所以运行方式是：

```sh
cargo run -p taskbook --example memory
```

内存版每次运行都创建新列表；退出后没有保存。这一章只是先检验核心函数。

## 为行为写测试

将以下完整测试模块追加到自己项目的 `src/lib.rs` 末尾，然后运行 `cargo test`：

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn add_and_complete_task() {
        let mut tasks = Vec::new();
        assert_eq!(add_task(&mut tasks, "学习 Rust"), Ok(1));
        assert_eq!(add_task(&mut tasks, "写练习"), Ok(2));
        assert_eq!(mark_done(&mut tasks, 1), Ok(()));
        assert_eq!(render_tasks(&tasks), "1 [x] 学习 Rust\n2 [ ] 写练习\n");
    }

    #[test]
    fn rejects_blank_titles_and_unknown_ids() {
        let mut tasks = Vec::new();
        assert!(add_task(&mut tasks, "   ").is_err());
        assert!(tasks.is_empty());
        assert!(mark_done(&mut tasks, 9).is_err());
    }
}
```

配套源码还有命令参数、标题非法字符、编号溢出和空列表的测试。运行 `cargo test -p taskbook --lib` 可以查看它们。测试直接调用核心逻辑，不需要每次手动在终端重演所有输入。

## 练习：统计未完成任务

写 `remaining(tasks: &[Task]) -> usize`，统计 `done` 为 `false` 的项。新增两条任务、完成其中一条后，结果应为 1；空列表应为 0。为它写一个测试。

<details>
<summary>参考答案：先自己完成再展开</summary>

将下面的完整函数放在 `lib.rs` 的测试模块外：

```rust
pub fn remaining(tasks: &[Task]) -> usize {
    tasks.iter().filter(|task| !task.done).count()
}
```

将下面的完整测试函数放在已有的 `mod tests` 内：

```rust
#[test]
fn counts_only_unfinished_tasks() {
    let mut tasks = Vec::new();
    assert_eq!(remaining(&tasks), 0);
    add_task(&mut tasks, "第一条").unwrap();
    add_task(&mut tasks, "第二条").unwrap();
    mark_done(&mut tasks, 1).unwrap();
    assert_eq!(remaining(&tasks), 1);
}
```

这里在测试中使用 `unwrap`：这些调用若意外失败，测试就应该立即失败。处理真实用户输入时仍返回错误。

</details>

## 官方延伸阅读

- [模式语法：切片与匹配守卫](https://doc.rust-lang.org/book/ch19-03-pattern-syntax.html)
- [Option::ok_or_else](https://doc.rust-lang.org/std/option/enum.Option.html#method.ok_or_else)

外部文档查阅日期：2026-10-12。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：闭包与迭代器](/posts/rust-10-iterators/) · [下一章：实战：文件与完整程序](/posts/rust-12-storage/)
