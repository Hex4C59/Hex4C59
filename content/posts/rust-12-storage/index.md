+++
title = "Rust 入门 12：保存数据，完成命令行工具"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-12T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "为待办工具设计文件格式，读写数据，连接命令行入口，测试跨进程持久化并构建可执行文件。"
summary = "为待办工具设计文件格式，读写数据，连接命令行入口，测试跨进程持久化并构建可执行文件。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 12
series_label = "实战：文件与完整程序"
series_part = "完成一个小项目"
series_number = 12
ShowToc = true
+++

这一章为待办工具加上文件存储和真正的命令行入口。完成后，每条命令都可以单独启动程序，之前写入的任务会重新读回来。

前置条件是上一章的 `src/lib.rs`。从头跟写时保留它和已有测试，再按本章添加两个文件、替换入口。配套下载包已经包含最终版本。

## 设计一个容易查看的文件格式

本项目采用制表符分隔的文本格式（Tab-Separated Values，TSV）。每行记录一条任务，依次保存编号、完成状态和标题。状态 `0` 表示未完成，`1` 表示已完成。

```text
1<TAB>0<TAB>学习 Rust
2<TAB>1<TAB>写练习
```

上面的 `<TAB>` 只是显示分隔位置的标记，实际文件使用制表符字节；你不需要手动创建初始文件。程序首次新增任务时会写出它。

空文件表示没有任务。标题禁止制表符、回车和换行，否则需要另外设计转义规则。UTF-8 文件可以保存中文。坏数据要返回错误，不能悄悄当成空列表再覆盖原文件。

## 添加 storage 模块

在 `src/lib.rs` 顶部增加一行：

```rust
pub mod storage;
```

这是模块声明片段。然后新建 `src/storage.rs`，完整内容如下：

```rust
use std::collections::HashSet;
use std::fs;
use std::io::ErrorKind;
use std::path::Path;

use crate::{Task, validate_title};

pub fn encode(tasks: &[Task]) -> Result<String, String> {
    let mut output = String::new();
    let mut ids = HashSet::new();
    for task in tasks {
        validate_title(&task.title)?;
        if task.id == 0 || !ids.insert(task.id) {
            return Err(format!("任务编号无效或重复：{}", task.id));
        }
        let done = if task.done { 1 } else { 0 };
        output.push_str(&format!("{}\t{done}\t{}\n", task.id, task.title));
    }
    Ok(output)
}

pub fn decode(input: &str) -> Result<Vec<Task>, String> {
    let mut tasks = Vec::new();
    let mut ids = HashSet::new();
    for (index, line) in input.lines().enumerate() {
        let line_number = index + 1;
        let invalid = || format!("第 {line_number} 行格式无效");
        let parts: Vec<&str> = line.splitn(3, '\t').collect();
        let [id, done, title] = parts.as_slice() else {
            return Err(invalid());
        };
        let id = id.parse::<u64>().map_err(|_| invalid())?;
        if id == 0 || !ids.insert(id) {
            return Err(format!("第 {line_number} 行编号为 0 或重复"));
        }
        let done = match *done {
            "0" => false,
            "1" => true,
            _ => return Err(invalid()),
        };
        validate_title(title).map_err(|message| format!("第 {line_number} 行：{message}"))?;
        tasks.push(Task {
            id,
            title: title.to_string(),
            done,
        });
    }
    Ok(tasks)
}

pub fn load(path: &Path) -> Result<Vec<Task>, String> {
    match fs::read_to_string(path) {
        Ok(content) => decode(&content),
        Err(error) if error.kind() == ErrorKind::NotFound => Ok(Vec::new()),
        Err(error) => Err(format!("无法读取 {}：{error}", path.display())),
    }
}

pub fn save(path: &Path, tasks: &[Task]) -> Result<(), String> {
    let content = encode(tasks)?;
    fs::write(path, content).map_err(|error| format!("无法写入 {}：{error}", path.display()))
}
```

`crate::{Task, validate_title}` 从当前库 crate 的根部引入类型和函数。`std::path::Path` 表示借用的文件系统路径；路径不是必须能转换成普通 UTF-8 字符串的文本，所以函数接收 `&Path`。

## 先编码和解析，再接触磁盘

`encode` 把任务列表转换成完整文本，`decode` 把文本转换成任务列表。它们不操作文件，便于单独验证格式。

`decode` 逐行处理，`.enumerate()` 给出从 0 开始的行索引，所以错误消息要加 1。`splitn(3, '\t')` 最多拆成三部分，第三部分保留标题的其余内容。如果里面还有制表符，`validate_title` 会拒绝它。

`let [id, done, title] = parts.as_slice() else { ... };` 是 `let ... else`：匹配成功就继续使用绑定；失败就提前返回。它适合“没有满足结构，就无法继续”的流程。

`HashSet` 是只保存不重复值的集合。这里用它记录已出现的编号。`.insert(id)` 返回是否真的插入新值，因此可以发现重复编号。`encode` 也检查编号和标题，避免公开字段被手工设置成非法值后写入文件。

遇到任何坏行，解析整个文件失败；不会只保留能读懂的几条再写回去。

## 文件不存在和文件损坏是两种情况

`fs::read_to_string` 读取整个文件并按 UTF-8 解码。只有 `ErrorKind::NotFound` 被当成首次启动的空列表。权限问题、目录路径、无效 UTF-8 等错误会返回明确消息。

`save` 先完成编码，成功后再调用 `fs::write`。这会创建文件，或覆盖已有文件内容。如果父目录不存在，不会自动创建父目录，而是报告写入错误。

这是用于学习、单个进程顺序使用的小工具。`fs::write` 不是事务：写入中断可能留下不完整文件，同时运行两个写入进程也可能丢失更新。重要数据应额外设计备份、并发访问规则和可靠的替换流程，或使用数据库。教程的测试不能证明它具有这些能力。

## 把命令行接进 main.rs

将 `src/main.rs` 完整替换为：

```rust
use std::env;
use std::path::PathBuf;
use std::process::ExitCode;

use taskbook::{Command, add_task, mark_done, parse_args, render_tasks, storage};

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().skip(1).collect();
    let command = parse_args(&args)?;
    let path = env::var_os("TASKBOOK_FILE")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("tasks.tsv"));
    let mut tasks = storage::load(&path)?;

    match command {
        Command::Add(title) => {
            let id = add_task(&mut tasks, &title)?;
            storage::save(&path, &tasks)?;
            println!("已添加任务 {id}");
        }
        Command::List => print!("{}", render_tasks(&tasks)),
        Command::Done(id) => {
            mark_done(&mut tasks, id)?;
            storage::save(&path, &tasks)?;
            println!("已完成任务 {id}");
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

`env::args()` 获取进程参数，第一项通常是程序自身路径，所以 `.skip(1)` 跳过它。`.collect()` 收集剩余参数，由 `parse_args` 检查。

终端里的引号帮助把带空格的标题作为一个参数传递。`add "学习 Rust"` 提供两个业务参数；不加引号的 `add 学习 Rust` 提供三个，会被拒绝。引号本身不会作为标题内容传进去。

本入口要求参数能表示为有效 Unicode，符合教材中的 UTF-8 文本使用场景。需要支持 Unix 上任意字节参数时，应使用 `args_os` 并明确转换规则。

`PathBuf` 拥有路径内容，类似 `String` 与 `&str` 的关系。环境变量 `TASKBOOK_FILE` 可以选择文件位置；没有设置时使用当前工作目录中的 `tasks.tsv`。这里的当前工作目录是你启动命令时所在的目录，和源码文件位置不一定相同。

`run` 先解析命令，再读取数据，然后执行操作。新增或完成任务时，保存成功后才打印成功消息。读取失败会通过 `?` 提前返回，因此不会覆盖损坏的原文件。

最外层 `main` 用 `ExitCode` 明确返回成功或失败，并通过 `eprintln!` 显示错误。其他脚本可以据此判断命令是否完成。

## 实际运行完整工具

在解压后的 `rust-course` 目录运行。以下操作使用默认 `tasks.tsv`，先确认你是在新解压的练习目录中，且没有之前留下的同名数据文件：

```sh
cargo run -p taskbook -- list
cargo run -p taskbook -- add "学习 Rust"
cargo run -p taskbook -- add "写练习"
cargo run -p taskbook -- done 1
cargo run -p taskbook -- list
```

首次列出时显示 `还没有任务`，两次新增分别返回编号 1 和 2。最后应输出：

```text
1 [x] 学习 Rust
2 [ ] 写练习
```

命令中的 `--` 把 Cargo 参数与程序参数分开。省去它容易让 Cargo 把你的命令解释成构建参数。

再次运行 `list`，任务仍在。试试 `done 99`、`done abc`、`add "   "`，应收到错误，原文件内容不因这些失败而改变。

你也可以在 macOS / Linux / zsh 中指定另一份练习文件：

```sh
TASKBOOK_FILE=practice-tasks.tsv cargo run -p taskbook -- add "另一份列表"
TASKBOOK_FILE=practice-tasks.tsv cargo run -p taskbook -- list
```

这两条是 shell 的单次环境变量写法。Windows PowerShell 请先执行 `$env:TASKBOOK_FILE = "practice-tasks.tsv"`，再运行对应 Cargo 命令；练习后用 `Remove-Item Env:TASKBOOK_FILE` 移除这个环境变量设置。没有设置时，前面默认的 Cargo 命令不需要这个系统差异步骤。

## 测试文件格式与跨进程行为

从头跟写时，可以把下面的完整测试模块追加到 `storage.rs` 末尾：

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip_and_reject_bad_data() {
        let tasks = vec![Task {
            id: 1,
            title: String::from("学习 Rust 🦀"),
            done: false,
        }];
        assert_eq!(decode(&encode(&tasks).unwrap()), Ok(tasks));
        assert!(decode("1\t2\t非法状态\n").is_err());
        assert!(decode("1\t0\ta\n1\t1\tb\n").is_err());
    }
}
```

`Task` 已派生 `PartialEq` 和 `Eq`，所以能直接比较解码后的列表是否等于原列表。只检查“能写文件”还不够，读回的标题、编号和状态都应该保持一致。

配套源码的 `taskbook/tests/cli.rs` 还会启动真正的可执行文件，在独立临时目录中多次运行命令，确认跨进程保存、失败时不覆盖旧数据、无效 UTF-8 和无法写入的路径得到处理。临时目录只用于测试，不会修改你的练习文件。

在工作区运行：

```sh
cargo test -p taskbook
cargo test -p taskbook --test cli
```

第一条已包含 CLI 集成测试；第二条用于你修改入口后单独复查它。自行跟写时若没有创建 `tests/cli.rs`，第二条自然没有可运行的目标，可以先阅读配套文件再补上。

## 构建可以直接运行的文件

在工作区运行：

```sh
cargo build -p taskbook --release
```

默认情况下，macOS / Linux 的可执行文件位于 `target/release/taskbook`，Windows 对应 `target/release/taskbook.exe`。如果设置了 `CARGO_TARGET_DIR`，构建产物会放在指定目录。macOS / Linux 可以这样运行：

```sh
./target/release/taskbook list
```

PowerShell 对应 `./target/release/taskbook.exe list`。运行时仍按当前工作目录寻找默认数据文件。构建产物针对当前目标平台，不是一个可以直接复制到所有系统上执行的通用文件。

## 练习：检查损坏数据有没有被覆盖

在自己独立的练习目录中，准备一份专用的 `practice-corrupt.tsv`，内容为 `bad-data`。不要使用你已经记录任务的文件。通过 `TASKBOOK_FILE` 让工具使用这份文件，再执行新增任务。

预期：程序失败并指出第 1 行格式无效，文件仍为 `bad-data`。这个练习验证的是错误传播是否阻止了后续保存。

<details>
<summary>参考答案：先自己完成再展开</summary>

macOS / Linux 可在专用练习目录运行：

```sh
printf 'bad-data\n' > practice-corrupt.tsv
TASKBOOK_FILE=practice-corrupt.tsv cargo run -p taskbook -- add "不应写入"
cat practice-corrupt.tsv
```

`>` 会覆盖指定文件，因此只对这份新建的练习文件执行。应看到 `错误：第 1 行格式无效`，最后仍输出 `bad-data`。

原因是 `storage::load(&path)?` 返回错误后，`run` 已经提前结束，没有执行 `add_task` 和 `storage::save`。配套集成测试自动检查了同样的条件。

</details>

## 不看答案，重新完成一次

新建一个空项目，只看需求重新实现新增、完成、列出和保存。遇到编译错误时先读错误消息，查本教材对应章节，再查官方文档。完成后逐项验证：

- 标题有空格和中文时能够保存，重启后内容不变。
- 空白标题、非法编号、找不到的任务都有清楚的错误。
- 修改一条任务不改变其他任务的状态。
- 文件不存在可以首次启动，文件损坏会报错并保留原内容。
- 测试可以检查正常路径和上述失败条件。

如果你能从空项目完成这些行为，并解释主要函数的参数为什么采用值、共享引用或可变引用，就达到了这套教材的入门目标。

接下来可以给项目增加“只列出未完成任务”或“按关键词搜索”，先为新行为写测试，再修改代码。之后按自己的用途选择网络请求、数据序列化或并发主题。遇到异步和 `unsafe` 时，再单独学习它们的约束。


## 官方延伸阅读

- [文件读取](https://doc.rust-lang.org/std/fs/fn.read_to_string.html)
- [文件写入](https://doc.rust-lang.org/std/fs/fn.write.html)
- [命令行参数](https://doc.rust-lang.org/std/env/fn.args.html)
- [ExitCode](https://doc.rust-lang.org/std/process/struct.ExitCode.html)

外部文档查阅日期：2026-10-12。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：实战：任务与命令](/posts/rust-11-taskbook/)
