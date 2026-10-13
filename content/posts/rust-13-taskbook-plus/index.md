+++
title = "Rust 入门 13：给待办工具增加筛选、搜索和删除"
date = 2026-10-13T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "复用已有库，返回任务的借用视图，按编号删除任务，并用测试固定查询与修改的边界。"
summary = "复用已有库，返回任务的借用视图，按编号删除任务，并用测试固定查询与修改的边界。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 13
series_label = "筛选、搜索与删除"
series_part = "继续完善项目"
series_number = 13
ShowToc = true
+++

第十二章的工具已经会保存任务。本章给它增加三个命令：`pending` 只看未完成项，`search "关键词"` 按标题搜索，`remove 编号` 删除任务。新增、完成和列出仍沿用原来的规则。

本章会继续用到切片、迭代器、生命周期和错误返回。学完后，你应该能把一个新功能拆成参数解析、核心函数、入口分支和测试，并看懂“返回任务的借用”与“复制一批新任务”的区别。

## 先到新的练习工作区

重新下载 [配套源码](/posts/rust-from-zero/course.zip)，解压得到 `rust-course`。第 1～12 章的文件仍在原位置；第 13～15 章放在它的 `practice` 子目录：

```text
rust-course/
├── Cargo.toml
├── basics/
├── taskbook/
└── practice/
    ├── Cargo.toml
    ├── taskbook-plus/
    ├── error-lab/
    ├── taskbook-json/
    └── test_support/
```

`practice/Cargo.toml` 是另一个工作区的入口。本章后续带 `-p taskbook-plus` 的命令都在这里执行：

```sh
cd rust-course/practice
cargo fetch --locked
cargo run -p taskbook-plus -- list
```

`cargo fetch --locked` 按下载包的锁文件获取练习工作区的依赖。其中第三方库由第十五章使用，首次获取需要网络；完成后可以给运行、测试命令加 `--offline`。本章的业务代码本身只使用标准库和本地的 `taskbook` 库。

如果已有 `tasks.tsv`，最后一条会显示它的任务；没有文件时则输出 `还没有任务`。下面的演示会指定新文件，不要求你的默认列表为空。

## 把新行为写清楚

| 命令 | 要求 |
| --- | --- |
| `pending` | 只显示未完成任务，保持原编号和原顺序 |
| `search "Rust"` | 在标题中查找这个连续文本，区分大小写，保持原顺序 |
| `search "   "` | 拒绝全是空白的关键词 |
| `remove 2` | 删除编号 2 的任务，其他任务的编号不变 |
| `remove 99` | 编号不存在时返回错误，不保存新文件内容 |

筛选和搜索没有匹配项时显示 `没有符合条件的任务`。搜索关键词先去掉两端空白；它不匹配编号，不做正则匹配，也不自动把 `rust` 当成 `Rust`。

删除引入了一条原项目没有遇到的情况：新增编号仍是“当前列表最大编号加 1”。若删除了最高编号，再新增任务，就可能复用刚删除的编号。本章允许这种行为；现存任务不会被重新编号。若要求删除过的编号永不复用，就要单独保存下一个编号，不能仅从现存列表推算。

## 用本地依赖复用前面的库

`practice/taskbook-plus/Cargo.toml` 的完整内容：

```toml
[package]
name = "taskbook-plus"
version = "0.1.0"
edition = "2024"
rust-version = "1.85"
publish = false

[dependencies]
taskbook = { path = "../../taskbook" }
```

`path` 相对于这个清单文件，而不是终端当前目录。`../../taskbook` 指向第十一、十二章的包。Cargo 构建新程序时会一起构建需要的库，代码里仍用 `taskbook::add_task` 这样的公开路径。

包名里的连字符在 Rust 路径中换成下划线，因此新库的代码路径是 `taskbook_plus::...`。这与第八章的 `rust-basics`、`rust_basics` 是同一规则。

自己跟写时，可以在 `practice` 目录下创建相同的 `taskbook-plus` 目录和三个文件：`Cargo.toml`、`src/lib.rs`、`src/main.rs`，并把包加入该工作区的 `members`。下面两份 Rust 代码可以完整写入对应文件。

## 在 lib.rs 中实现新行为

```rust
use taskbook::Task;

pub const USAGE: &str = "用法：taskbook-plus add <标题> | list | done <编号> | pending | search <关键词> | remove <编号>";

#[derive(Debug, PartialEq, Eq)]
pub enum Command {
    Base(taskbook::Command),
    Pending,
    Search(String),
    Remove(u64),
}

pub fn parse_args(args: &[String]) -> Result<Command, String> {
    match args {
        [command] if command == "pending" => Ok(Command::Pending),
        [command, query] if command == "search" => {
            let query = query.trim();
            if query.is_empty() {
                return Err(String::from("搜索关键词不能为空"));
            }
            Ok(Command::Search(query.to_string()))
        }
        [command, id] if command == "remove" => {
            let id = id
                .parse::<u64>()
                .map_err(|_| String::from("编号必须是正整数"))?;
            if id == 0 {
                return Err(String::from("编号必须大于 0"));
            }
            Ok(Command::Remove(id))
        }
        _ => taskbook::parse_args(args)
            .map(Command::Base)
            .map_err(|message| {
                if message == taskbook::USAGE {
                    USAGE.to_string()
                } else {
                    message
                }
            }),
    }
}

pub fn pending(tasks: &[Task]) -> Vec<&Task> {
    tasks.iter().filter(|task| !task.done).collect()
}

pub fn search<'a>(tasks: &'a [Task], query: &str) -> Result<Vec<&'a Task>, String> {
    let query = query.trim();
    if query.is_empty() {
        return Err(String::from("搜索关键词不能为空"));
    }
    Ok(tasks
        .iter()
        .filter(|task| task.title.contains(query))
        .collect())
}

pub fn render_selection(tasks: &[&Task]) -> String {
    if tasks.is_empty() {
        return String::from("没有符合条件的任务\n");
    }
    let mut output = String::new();
    for task in tasks {
        let mark = if task.done { "x" } else { " " };
        output.push_str(&format!("{} [{mark}] {}\n", task.id, task.title));
    }
    output
}

pub fn remove_task(tasks: &mut Vec<Task>, id: u64) -> Result<(), String> {
    let index = tasks
        .iter()
        .position(|task| task.id == id)
        .ok_or_else(|| format!("找不到任务 {id}"))?;
    tasks.remove(index);
    Ok(())
}
```

`Command::Base` 保存原库的命令，另外三个变体代表新命令。解析器先检查新增的形式，再把其余参数交回原解析器。只有原解析器给出用法时，才替换成扩展版用法；非法编号等具体错误仍保留。

`pending` 返回 `Vec<&Task>`。这个新列表拥有自己的容器，但元素只是指向原任务的引用。它不会复制标题，也不取得任务的所有权。收集完后，原列表必须在这些引用使用期间保持有效。

### search 的生命周期只关联任务

`search<'a>(tasks: &'a [Task], query: &str)` 返回 `Vec<&'a Task>`，结果借用的是任务，不是关键词。函数比较标题时会读取关键词，但结果里没有保存对关键词的引用。

因此，关键词在函数返回后可以离开作用域，只要原任务仍然存在，选中的任务就还能使用。反过来，原任务被销毁后，搜索结果不能继续使用。不要因为有两个输入引用，就把它们都标成相同的 `'a`。

### 为什么单独写 render_selection

原来的 `render_tasks` 接收 `&[Task]`，这里拿到的却是 `Vec<&Task>`。一个切片里是任务，一个切片里是任务引用，两种切片的元素类型不同。

`render_selection` 接收 `&[&Task]`，直接读被选中任务的字段并生成文本。访问字段时，Rust 可以自动解引用，所以不用把 `task.id` 写成一串星号。只有结果为空时，展示消息与原来的完整列表不同。

### 删除的是编号对应的位置

`position` 返回第一个匹配元素的列表下标，是 `Option<usize>`。先把“找不到”转换成错误，得到下标后才调用 `Vec::remove`。

下标属于当前列表的位置，任务编号属于数据。删除中间一项后，后面的元素位置会前移，但它们的 `id` 不会变。这里返回的是普通整数下标，查找结束后不再持有元素借用，因此后面能够修改列表。

## 在 main.rs 中接上命令和保存

```rust
use std::env;
use std::path::PathBuf;
use std::process::ExitCode;

use taskbook::{add_task, mark_done, render_tasks, storage};
use taskbook_plus::{Command, parse_args, pending, remove_task, render_selection, search};

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().skip(1).collect();
    let command = parse_args(&args)?;
    let path = env::var_os("TASKBOOK_FILE")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("tasks.tsv"));
    let mut tasks = storage::load(&path)?;
    match command {
        Command::Base(taskbook::Command::Add(title)) => {
            let id = add_task(&mut tasks, &title)?;
            storage::save(&path, &tasks)?;
            println!("已添加任务 {id}");
        }
        Command::Base(taskbook::Command::List) => print!("{}", render_tasks(&tasks)),
        Command::Base(taskbook::Command::Done(id)) => {
            mark_done(&mut tasks, id)?;
            storage::save(&path, &tasks)?;
            println!("已完成任务 {id}");
        }
        Command::Pending => print!("{}", render_selection(&pending(&tasks))),
        Command::Search(query) => print!("{}", render_selection(&search(&tasks, &query)?)),
        Command::Remove(id) => {
            remove_task(&mut tasks, id)?;
            storage::save(&path, &tasks)?;
            println!("已删除任务 {id}");
        }
    }
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("错误：{message}");
            ExitCode::FAILURE
        }
    }
}
```

新增和完成继续调用原来的核心函数。筛选、搜索只生成展示文本；删除成功后才调用保存。无效参数、找不到的编号或加载失败都会通过 `?` 提前返回。

文件格式仍然是第十二章的 TSV。新工具可以读懂旧工具写出的有效数据，但两个工具都没有并发写入协调。本章演示按顺序运行命令。

## 用一份新文件运行

下面的命令适用于 macOS / Linux，在 `rust-course/practice` 执行：

```sh
plus_practice_dir=$(mktemp -d)
TASKBOOK_FILE="$plus_practice_dir/tasks.tsv" cargo run -p taskbook-plus -- add "学习 Rust"
TASKBOOK_FILE="$plus_practice_dir/tasks.tsv" cargo run -p taskbook-plus -- add "买水果"
TASKBOOK_FILE="$plus_practice_dir/tasks.tsv" cargo run -p taskbook-plus -- add "复习 Rust"
TASKBOOK_FILE="$plus_practice_dir/tasks.tsv" cargo run -p taskbook-plus -- done 1
TASKBOOK_FILE="$plus_practice_dir/tasks.tsv" cargo run -p taskbook-plus -- pending
TASKBOOK_FILE="$plus_practice_dir/tasks.tsv" cargo run -p taskbook-plus -- search "Rust"
TASKBOOK_FILE="$plus_practice_dir/tasks.tsv" cargo run -p taskbook-plus -- remove 2
TASKBOOK_FILE="$plus_practice_dir/tasks.tsv" cargo run -p taskbook-plus -- list
```

前三次新增分别得到编号 1、2、3。完成编号 1 后，`pending` 输出：

```text
2 [ ] 买水果
3 [ ] 复习 Rust
```

`search "Rust"` 输出：

```text
1 [x] 学习 Rust
3 [ ] 复习 Rust
```

删除编号 2 后，`list` 输出相同的两行。从只剩编号 1、3 的状态出发，直接新增会得到编号 4；若先删除编号 3 再新增，则可以重新得到编号 3。

Windows PowerShell 可以先给 `$env:TASKBOOK_FILE` 设置一个专用练习文件路径，再执行相同的 Cargo 命令。`mktemp` 和单次命令前设置环境变量的写法属于这里给出的 macOS / Linux 演示。

## 看一次借用视图怎样结束

配套源码的 `taskbook-plus/examples/selection.rs` 是完整程序：

```rust
use taskbook::{add_task, mark_done, render_tasks};
use taskbook_plus::{pending, render_selection};

fn main() -> Result<(), String> {
    let mut tasks = Vec::new();
    add_task(&mut tasks, "学习 Rust")?;
    let selected = pending(&tasks);
    print!("{}", render_selection(&selected));
    mark_done(&mut tasks, 1)?;
    print!("{}", render_tasks(&tasks));
    Ok(())
}
```

运行 `cargo run -p taskbook-plus --example selection`，输出：

```text
1 [ ] 学习 Rust
1 [x] 学习 Rust
```

程序先使用筛选结果，随后才修改任务。虽然 `selected` 的绑定还在作用域里，它后面不再被使用，对任务的共享借用就可以结束。

在自己的副本中试着把修改放在第一次打印之前，再运行 `cargo check`。如果修改之后还需要使用原筛选结果，共享借用与可变借用发生冲突。修复时先整理使用顺序，不必把所有标题复制一遍。

## 为筛选和删除写测试

把下面完整测试模块追加到 `src/lib.rs`，或直接查看下载包中的同一模块：

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use taskbook::{add_task, mark_done};

    #[test]
    fn filters_without_changing_tasks() {
        let mut tasks = Vec::new();
        add_task(&mut tasks, "学习 Rust").unwrap();
        add_task(&mut tasks, "买水果").unwrap();
        add_task(&mut tasks, "复习 Rust").unwrap();
        mark_done(&mut tasks, 1).unwrap();
        let before = taskbook::render_tasks(&tasks);
        assert_eq!(
            render_selection(&pending(&tasks)),
            "2 [ ] 买水果\n3 [ ] 复习 Rust\n"
        );
        assert_eq!(
            render_selection(&search(&tasks, "Rust").unwrap()),
            "1 [x] 学习 Rust\n3 [ ] 复习 Rust\n"
        );
        assert!(search(&tasks, "rust").unwrap().is_empty());
        assert!(search(&tasks, " \t ").is_err());
        assert_eq!(taskbook::render_tasks(&tasks), before);
    }

    #[test]
    fn search_result_borrows_tasks_without_borrowing_query() {
        let mut tasks = Vec::new();
        add_task(&mut tasks, "学习 Rust").unwrap();
        let selected;
        {
            let query = String::from("Rust");
            selected = search(&tasks, &query).unwrap();
        }
        assert_eq!(selected[0].title, "学习 Rust");
    }

    #[test]
    fn empty_selection_has_a_message() {
        assert_eq!(render_selection(&pending(&[])), "没有符合条件的任务\n");
        let mut tasks = Vec::new();
        add_task(&mut tasks, "学习 Rust").unwrap();
        mark_done(&mut tasks, 1).unwrap();
        assert!(pending(&tasks).is_empty());
    }

    #[test]
    fn removal_keeps_other_ids_and_reports_missing_id() {
        let mut tasks = Vec::new();
        for title in ["第一条", "第二条", "第三条"] {
            add_task(&mut tasks, title).unwrap();
        }
        remove_task(&mut tasks, 2).unwrap();
        assert_eq!(tasks.iter().map(|task| task.id).collect::<Vec<_>>(), [1, 3]);
        let before = taskbook::render_tasks(&tasks);
        assert!(remove_task(&mut tasks, 99).is_err());
        assert_eq!(taskbook::render_tasks(&tasks), before);
        assert_eq!(add_task(&mut tasks, "第四条"), Ok(4));
    }

    #[test]
    fn deleting_highest_id_can_reuse_it_on_the_next_add() {
        let mut tasks = Vec::new();
        add_task(&mut tasks, "第一条").unwrap();
        add_task(&mut tasks, "第二条").unwrap();
        remove_task(&mut tasks, 2).unwrap();
        assert_eq!(add_task(&mut tasks, "新第二条"), Ok(2));
    }

    #[test]
    fn parses_extended_commands_and_rejects_invalid_forms() {
        let args = |parts: &[&str]| {
            parts
                .iter()
                .map(|part| part.to_string())
                .collect::<Vec<_>>()
        };
        assert_eq!(parse_args(&args(&["pending"])), Ok(Command::Pending));
        assert_eq!(
            parse_args(&args(&["search", " Rust "])),
            Ok(Command::Search(String::from("Rust")))
        );
        assert_eq!(parse_args(&args(&["remove", "2"])), Ok(Command::Remove(2)));
        assert_eq!(
            parse_args(&args(&["list"])),
            Ok(Command::Base(taskbook::Command::List))
        );
        for parts in [
            vec!["pending", "extra"],
            vec!["search"],
            vec!["search", " "],
            vec!["remove", "0"],
            vec!["remove", "-1"],
            vec!["remove", "18446744073709551616"],
        ] {
            assert!(parse_args(&args(&parts)).is_err());
        }
    }
}
```

在 `practice` 工作区执行：

```sh
cargo test -p taskbook-plus --lib
cargo test -p taskbook-plus --test cli
```

库里有 6 个测试，检查筛选结果、关键词的作用域、空结果、删除、编号复用和参数形式。CLI 测试另外启动真实程序，检查重启后的删除结果，以及查询和失败命令没有改变文件字节。

## 练习：一次清除所有完成项

写 `remove_completed(tasks: &mut Vec<Task>) -> usize`，删除所有已完成任务，返回实际删除的数量。要求未完成任务的编号和顺序不变；空列表返回 0。先只实现函数和测试，不急着增加命令。

<details>
<summary>参考答案：先自己完成再展开</summary>

把下面的完整函数放在 `lib.rs` 的测试模块外：

```rust
pub fn remove_completed(tasks: &mut Vec<taskbook::Task>) -> usize {
    let before = tasks.len();
    tasks.retain(|task| !task.done);
    before - tasks.len()
}
```

`retain` 保留闭包返回 `true` 的元素，其他元素被移除。它保持保留元素的原顺序。这里保留 `done == false` 的任务。

将下面完整测试函数加入已有的 `mod tests`：

```rust
#[test]
fn clears_completed_without_renumbering_pending_tasks() {
    let mut tasks = Vec::new();
    assert_eq!(remove_completed(&mut tasks), 0);
    for title in ["第一条", "第二条", "第三条"] {
        add_task(&mut tasks, title).unwrap();
    }
    mark_done(&mut tasks, 1).unwrap();
    mark_done(&mut tasks, 3).unwrap();
    assert_eq!(remove_completed(&mut tasks), 2);
    assert_eq!(tasks.len(), 1);
    assert_eq!(tasks[0].id, 2);
    assert_eq!(remove_completed(&mut tasks), 0);
}
```

新增练习后再运行 `cargo test -p taskbook-plus --lib`，应有 7 个测试通过。下载包没有预先加入这道练习函数。

</details>

## 官方延伸阅读

- [Iterator::position](https://doc.rust-lang.org/std/iter/trait.Iterator.html#method.position)
- [Vec::remove 与 Vec::retain](https://doc.rust-lang.org/std/vec/struct.Vec.html)
- [Cargo 的本地依赖](https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#specifying-path-dependencies)

外部文档查阅日期：2026-10-13。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：文件与完整程序](/posts/rust-12-storage/) · [下一章：自定义错误类型](/posts/rust-14-typed-errors/)
