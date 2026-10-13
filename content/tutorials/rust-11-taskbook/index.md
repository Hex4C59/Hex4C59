+++
url = "/posts/rust-11-taskbook/"
title = "Rust 入门 11：实现待办工具的核心逻辑"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
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

前面十章已经覆盖了这个项目要用的主要语法。这一章开始实现 `taskbook`：保存一组待办任务，新增任务，按编号标记完成，并把结果展示成文本。

我们先实现不接触终端和文件的核心函数。这样新增失败时有没有改变列表、完成任务时有没有改错对象，都能用测试直接检查。下一章再把同一组函数接到命令行和文件上。本章跟写结束后，你应该能运行内存版程序，并解释为什么不同函数分别接收 `&str`、`&[Task]`、`&mut [Task]` 或 `&mut Vec<Task>`。

## 先写下程序应该怎样工作

任务有固定编号、标题和完成状态。新任务默认未完成；完成任务时按编号查找，找不到要返回错误。空白标题不接受。列出任务时使用 `1 [ ] 标题` 或 `1 [x] 标题` 的形式。

命令有三种：`add "标题"`、`list`、`done 编号`。编号使用正整数。标题中不允许制表符或换行，因为下一章会用制表符分隔文件字段。

本项目只增加和完成任务，不删除。新编号取已有最大编号加 1，避免依赖列表当前位置；编号达到上限时返回错误。

### 把规则写成能检查的结果

| 操作或输入 | 预期结果 |
| --- | --- |
| 向空列表新增 `学习 Rust` | 得到编号 1，状态为未完成 |
| 再新增 `写练习` | 得到编号 2，第一条仍保留 |
| 完成编号 1 | 只把第一条标记为完成 |
| 再次完成编号 1 | 仍然成功，状态保持完成 |
| 完成不存在的编号 9 | 返回错误，已有任务不变 |
| 新增空文本或全是空白的标题 | 返回错误，不追加任务 |
| 列出空列表 | 返回 `还没有任务`，末尾有换行 |
| 已有最大编号是 `u64::MAX` | 拒绝新增，避免编号溢出 |

编号和列表下标不是一回事。即使列表中只有两条任务，它们的编号也可能是 7 和 12。查找任务要比较 `task.id`，不能用 `tasks[id - 1]` 猜测位置。

## 从头建立项目

你可以直接阅读配套源码，也可以在工作区之外新建自己的项目：

```sh
cargo new taskbook --edition 2024
cd taskbook
```

自行新建项目时，下面的文件路径都相对于这个 `taskbook` 目录，运行命令用 `cargo run` 和 `cargo test`。配套工作区中的对应命令则分别是 `cargo run -p taskbook ...` 和 `cargo test -p taskbook ...`。

项目现在只需要下面两个文件：

```text
taskbook/
├── Cargo.toml
└── src/
    ├── lib.rs
    └── main.rs
```

`lib.rs` 定义可测试的业务函数，`main.rs` 使用它们。读完整代码时，可以先只找 `Task`、`Command` 和五个函数名，确认每个函数的输入输出；随后按下面的说明逐段阅读，不需要一次背下全部代码。

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

### 沿着一次新增看函数怎样合作

调用 `add_task(&mut tasks, "  学习 Rust  ")` 时，程序先检查标题是否有效，再计算编号，最后才 `push` 新任务。保存的标题会去掉两端空白，成为 `学习 Rust`。

`validate_title` 返回 `Result<(), String>`。只有检查通过，`?` 才让后面的步骤继续。如果标题非法，函数在修改列表之前返回错误。

`render_tasks` 则把结果组织为一个 `String`，而不是直接打印。这样测试能准确比较输出，入口也可以选择打印、写日志或再加工。字符串中的 `\n` 是输出格式的一部分，`print!` 打印时不用再加一个换行。

本章使用 `derive(Debug, PartialEq, Eq)`。`Debug` 帮助观察值，`PartialEq` 与 `Eq` 让任务和命令能按内容比较；它们不会替我们检查标题或编号的业务规则。

## 命令解析里有哪些新写法

`match args` 对切片进行模式匹配。`[command, title]` 要求恰好两个参数；`[command]` 要求恰好一个。后面的 `if command == "add"` 是匹配守卫，进一步检查第一个参数的内容。

`title` 来自借用的参数切片，因此是借来的 `String`。`Command::Add` 要保存拥有内容的标题，于是 `title.clone()` 创建副本。这是为命令对象保留数据所做的明确选择。

`parse_args` 负责检查命令形式和编号；`add_task` 负责检查标题。因此解析出 `Add("   ")` 后，实际新增时仍会被拒绝。保持这两个层次的职责明确，测试才容易定位问题。

### shell 会先把命令拆成参数

在下一章运行 `taskbook add "学习 Rust"` 时，程序接收的命令参数是 `"add"` 和 `"学习 Rust"` 两项。引号帮助 shell 把含空格的标题当成一项；引号本身不成为标题内容。

如果写成 `taskbook add 学习 Rust`，参数就会有三项，无法匹配 `[command, title]`，程序会给出用法。这是我们有意选择的命令规则：标题必须是一个参数，而不是自动拼接所有剩余词。

先不等下一章，直接调用解析器看看结果。创建自己的 `examples/parse.rs`，完整内容如下，随后在单包目录执行 `cargo run --example parse`。这份辅助示例需要你按本文新建，不是下载包中的既有目标。

```rust
use taskbook::parse_args;

fn main() {
    let inputs = [
        vec!["add", "学习 Rust"],
        vec!["list"],
        vec!["done", "2"],
        vec!["add", "学习", "Rust"],
    ];
    for input in inputs {
        let args: Vec<String> = input.iter().map(|value| value.to_string()).collect();
        println!("{:?}", parse_args(&args));
    }
}
```

前面三行分别是 `Ok(Add("学习 Rust"))`、`Ok(List)`、`Ok(Done(2))`，第四行是包含用法的 `Err`。`parse_args` 不知道这些字符串来自 shell、测试还是别的地方，它只按同一套规则检查。

`Done` 的编号还要经过数字解析和大于 0 的检查。参数数量正确，并不意味着内容有效；同理，成功得到一个 `Add` 命令，也不代表标题已经通过新增函数的校验。

## Option 可以转换成 Result

`max()` 对空列表返回 `None`，`unwrap_or(0)` 提供初始编号 0。它不会在 `None` 时 panic。

`checked_add(1)` 在加法溢出时返回 `None`。`.ok_or_else(|| String::from("任务编号已用完"))` 把缺失情况转换成 `Err`，接下来的 `?` 就能把错误传出去。

`find` 同样返回 `Option`。`mark_done` 用 `iter_mut()` 找到可修改的任务，再通过 `ok_or_else` 把“找不到”转换成带编号的错误消息。

### 不要为了短一点省去溢出检查

编号代码可读成四步：取得每条任务的编号，找最大值，空列表时从 0 开始，尝试加 1。下面是独立的完整程序，只观察最后两步：

```rust
fn main() {
    let empty: Vec<u64> = Vec::new();
    let ids = vec![7_u64, 2];
    let exhausted = vec![u64::MAX];
    println!("{:?}", empty.iter().copied().max().unwrap_or(0).checked_add(1));
    println!("{:?}", ids.iter().copied().max().unwrap_or(0).checked_add(1));
    println!("{:?}", exhausted.iter().copied().max().unwrap_or(0).checked_add(1));
}
```

输出 `Some(1)`、`Some(8)`、`None`。业务函数接着把最后一种情况转换成 `Err("任务编号已用完")`。这条失败路径应该在测试中保留，不能只换成普通的 `+ 1` 后假定编号永远不会到上限。

`ok_or_else` 后面的 `|| ...` 是无参数闭包，只有遇到 `None` 才需要生成错误值。`Option` 自身只有“有或没有”，这一层转换给“没有”加上了调用方能理解的原因。

## Vec 和切片各用在哪里

`add_task` 需要向列表追加元素，因此接收 `&mut Vec<Task>`。`mark_done` 只修改已有元素，接收 `&mut [Task]` 已经足够。`render_tasks` 只读取任务，接收 `&[Task]`。

函数签名直接说明了它需要的权限。调用方在查看这些签名时，也能判断哪些函数可能修改数据、哪些会改变列表长度。

`Task` 的字段暂时公开，方便在教材里查看和构造测试数据。实际库可以把字段设为私有，通过构造函数和方法维护约束。下一章的编码函数还会检查非法字段，防止手工构造的数据直接写入文件。

### 从权限反推参数类型

| 函数 | 参数里的集合类型 | 需要做什么 |
| --- | --- | --- |
| `add_task` | `&mut Vec<Task>` | 修改列表并增加长度 |
| `mark_done` | `&mut [Task]` | 修改已有元素，保持长度 |
| `render_tasks` | `&[Task]` | 读取已有元素 |

当你把 `&mut tasks` 传给 `mark_done` 时，Rust 可以把对 `Vec<Task>` 的借用转换成元素切片的借用。函数不需要知道列表的容量或怎样追加元素。

`add_task` 接收 `&str` 标题，再创建任务拥有的 `String`。调用方的输入即使之后被清空，已经加入的任务标题也仍然存在。与之相对，`render_tasks` 只是读任务，不会把它们移走。

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

### 再检查失败时列表是否保持原状

将下面的完整测试函数加入自己项目中已有的 `mod tests`：

```rust
#[test]
fn invalid_changes_leave_existing_task_unchanged() {
    let mut tasks = Vec::new();
    add_task(&mut tasks, "保留这条").unwrap();
    let before = render_tasks(&tasks);
    assert!(add_task(&mut tasks, "\t").is_err());
    assert!(mark_done(&mut tasks, 99).is_err());
    assert_eq!(render_tasks(&tasks), before);
    assert_eq!(tasks.len(), 1);
}
```

这里不仅检查“返回了错误”，还检查已有任务的内容和数量。若后来有人把 `push` 提前到验证之前，这个测试就有机会发现错误路径改变了数据。

再加入下面的解析测试，确认多余参数和非法编号都被拒绝：

```rust
#[test]
fn rejects_bad_command_arguments() {
    for parts in [
        vec!["list", "extra"],
        vec!["add"],
        vec!["done", "0"],
        vec!["done", "abc"],
    ] {
        let args: Vec<String> = parts.iter().map(|part| part.to_string()).collect();
        assert!(parse_args(&args).is_err());
    }
}
```

这两个测试是跟写时新增的检查；下载包中已经有覆盖相近规则的测试。不要根据两份项目的测试数量是否相同来判断行为是否正确，应该看具体检查了什么。

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

### 进入文件操作之前先确认三件事

运行内存示例，结果应只有编号 1 被标记为完成。运行自己的测试，合法操作和失败条件都应符合规则。最后找出每个函数修改数据的位置，确认它前面需要通过哪些检查。

下一章继续使用这些函数。如果文件读取失败，入口应提前返回错误；如果读取成功，才允许新增或完成任务。这样你不需要在每个业务函数里重复处理磁盘路径。

## 官方延伸阅读

- [模式语法：切片与匹配守卫](https://doc.rust-lang.org/book/ch19-03-pattern-syntax.html)
- [Option::ok_or_else](https://doc.rust-lang.org/std/option/enum.Option.html#method.ok_or_else)

外部文档查阅日期：2026-10-13。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：闭包与迭代器](/posts/rust-10-iterators/) · [下一章：实战：文件与完整程序](/posts/rust-12-storage/)
