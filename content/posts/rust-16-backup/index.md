+++
title = "Rust 入门 16：备份任务数据，恢复到新文件"
date = 2026-10-13T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "复用 JSON 校验，在 Rust 中备份和恢复任务文件，学习 create_new、写入失败边界，以及如何用测试确认旧文件没有被覆盖。"
summary = "复用 JSON 校验，在 Rust 中备份和恢复任务文件，学习 create_new、写入失败边界，以及如何用测试确认旧文件没有被覆盖。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 16
series_number = 16
series_label = "备份与恢复"
series_part = "文件、命令行与网络"
ShowToc = true
+++

上一章的任务文件已经能读写 JSON。发生误删后，还需要一份此前保存的副本。这一章给工具增加手动备份，再把备份恢复到一个新文件里。

读完后，你应该能解释三个决定：为什么备份前仍要解析 JSON，为什么恢复时拒绝覆盖已有文件，以及为什么一次成功的复制不等于完整的故障恢复机制。你需要先完成第十二章的文件读写、第十四章的自定义错误和第十五章的 JSON 校验。

## 先约定备份和恢复的行为

本章使用新包 `taskbook-backup`，保留第十五章的代码。两个命令都接收源路径和新目标路径：

```text
taskbook-backup backup tasks.json backup.json
taskbook-backup restore backup.json restored.json
```

它们的文件操作相同：读取源文件，确认数据有效，再原样写入一个此前不存在的目标。命令名表达这次复制的用途。

| 情况 | 结果 |
| --- | --- |
| 源文件存在，JSON 和任务数据有效，目标不存在 | 创建目标，返回任务数量 |
| 源文件缺失、不是 UTF-8，或数据无效 | 报错，不创建目标 |
| 目标已经存在，包括源和目标是同一路径 | 报错，保留已有文件 |
| 目标创建后，写入发生错误 | 报错，新目标可能是不完整文件 |

这份备份没有时间戳、压缩和自动轮换。练习时，每次手动选择一个新文件名，例如 `backup-01.json`。先停止其他写入任务文件的程序，再复制；本项目没有协调并发读写。

## 把后续项目放到独立工作区

从[教材目录](/posts/rust-from-zero/)下载并解压源码。本章及后两章在 `rust-course/projects` 运行；第十三至十五章仍在 `practice`，前十二章仍在外层工作区。

```text
rust-course/
├── taskbook/
├── practice/
│   ├── taskbook-plus/
│   └── taskbook-json/
└── projects/
    ├── Cargo.toml
    ├── Cargo.lock
    ├── test_support/
    ├── taskbook-backup/
    ├── taskbook-cli/
    └── lesson-http/
```

下载包已经包含全部目录。如果你从空目录跟写，先建立 `projects/taskbook-backup/src`，在 `projects/Cargo.toml` 中只列出已经建立的包：

```toml
[workspace]
members = ["taskbook-backup"]
resolver = "3"
```

第十七、十八章再把对应包名加入 `members`。下载包的工作区已经列出三个成员，不必删改。下面三个文件就是本章工具的全部业务代码。

`taskbook-backup/Cargo.toml` 的完整内容：

```toml
[package]
name = "taskbook-backup"
version = "0.1.0"
edition = "2024"
rust-version = "1.85"
publish = false

[dependencies]
taskbook-json = { path = "../../practice/taskbook-json" }
```

这里的本地依赖路径相对于这个 `Cargo.toml`，所以 `../../practice/taskbook-json` 指向第十五章的包。复制本章目录时，要一起保留下载包中的上层目录，不能只搬走一个子目录。

在 `rust-course/projects` 中先运行 `cargo fetch --locked`。下载包共用的锁文件还包含后两章的 clap 和 reqwest 依赖，因此首次获取需要网络。已有缓存后，本文的 Cargo 命令可以加 `--offline`。

## 先验证，再创建新文件

`taskbook-backup/src/lib.rs` 的完整内容：

```rust
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;

use taskbook_json::storage::{self, StoreError};

pub fn copy_snapshot(source: &Path, destination: &Path) -> Result<usize, StoreError> {
    let content = fs::read_to_string(source)?;
    let tasks = storage::decode(&content)?;
    let mut output = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(destination)?;
    output.write_all(content.as_bytes())?;
    Ok(tasks.len())
}
```

函数返回 `Result<usize, StoreError>`：成功值是复制的任务数量，失败沿用第十五章的错误类型。调用者能继续查看 I/O 或 JSON 错误的原始原因，校验规则也由旧库统一处理。

留意操作顺序。`fs::read_to_string` 读取源文件，`storage::decode` 检查 JSON、版本和任务字段；只有两步都成功，才创建目标。

第十五章的 `storage::load` 把不存在的文件当作空任务列表，适合首次使用待办工具。备份却必须有真实源文件，所以这里直接调用 `read_to_string`：文件不存在就是错误，不能误报“成功备份了 0 个任务”。

`decode` 得到的任务只用于校验和计数，写入目标的仍是原始 `content`。文件里的缩进、换行和字段顺序因此会保留。如果先解码，再用 `encode` 生成 JSON，任务可以相同，文件字节却未必相同。

### 为什么用 create_new

`OpenOptions` 用来设置打开文件的方式。这里启用写入，再调用 `create_new(true)`，要求目标此前不存在。已有文件会使 `open` 失败。

不要先写 `if !destination.exists()`，再用会覆盖文件的 `fs::write`。检查结束和实际写入之间，另一个程序仍可能创建目标。`create_new` 把“必须是新文件”交给创建操作来判断。这个性质只保护目标的创建，不能让源文件读取和整个备份过程都成为原子操作。

`write_all` 会尝试写完传入的字节；它返回成功时，本次调用已经完成写入。它没有承诺磁盘断电后仍能恢复文件，也没有把“创建目标”和“写完内容”合成一个不会中断的步骤。

如果 `write_all` 报错，代码保留这个新目标，没有自动删除或再次覆盖。检查目标后，用另一个新名字重试。要实现自动清理、临时文件替换或断电恢复，需要另立行为约定和测试，这一章没有实现这些功能。

## 在命令行展示结果和原因

`taskbook-backup/src/main.rs` 的完整内容：

```rust
use std::error::Error;
use std::path::Path;
use std::process::ExitCode;

use taskbook_json::storage::StoreError;

fn run() -> Result<(), StoreError> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.as_slice() {
        [command, source, destination] if command == "backup" || command == "restore" => {
            let count = taskbook_backup::copy_snapshot(Path::new(source), Path::new(destination))?;
            let action = if command == "backup" {
                "备份"
            } else {
                "恢复"
            };
            println!("已{action} {count} 个任务到 {destination}");
            Ok(())
        }
        _ => Err(StoreError::InvalidData(String::from(
            "用法：taskbook-backup backup <源文件> <新备份> | restore <备份> <新文件>",
        ))),
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("错误：{error}");
            let mut cause = error.source();
            while let Some(source) = cause {
                eprintln!("原因：{source}");
                cause = source.source();
            }
            ExitCode::FAILURE
        }
    }
}
```

`backup` 和 `restore` 共用复制函数。恢复到 `restored.json` 后，先用旧工具读取它，确认内容，再决定以后使用哪个路径。原先的 `tasks.json` 保留，便于检查误操作前后的差别。

`Path::new` 在这里借用参数中的路径文本；路径的实际文件操作发生在库函数里。成功消息写到标准输出，错误及原因链写到标准错误，退出码分别是 0 和 1。

本章仍沿用手写参数解析。下一章会把这部分交给 clap，增加 `--help`、子命令和显式文件选项。

## 从一次备份到一次恢复

以下命令适用于 macOS / Linux 的 shell，在 `rust-course/projects` 中运行。先建一个新的练习目录，避免和自己的任务文件混用；不要删除已有数据来迁就示例。

```sh
mkdir backup-demo
TASKBOOK_JSON_FILE=backup-demo/tasks.json cargo run --manifest-path ../practice/Cargo.toml -p taskbook-json -- add "学习 Rust"
cargo run -p taskbook-backup -- backup backup-demo/tasks.json backup-demo/backup.json
TASKBOOK_JSON_FILE=backup-demo/tasks.json cargo run --manifest-path ../practice/Cargo.toml -p taskbook-json -- remove 1
cargo run -p taskbook-backup -- restore backup-demo/backup.json backup-demo/restored.json
TASKBOOK_JSON_FILE=backup-demo/restored.json cargo run --manifest-path ../practice/Cargo.toml -p taskbook-json -- list
```

这里用第十五章的工具生成源文件、删除任务和读取恢复结果。`--manifest-path` 选择相邻的 `practice` 工作区，临时环境变量则为这一次调用指定任务文件。

上面完整演示对应的新目录输出如下，Cargo 的构建日志略去：

```text
已添加任务 1
已备份 1 个任务到 backup-demo/backup.json
已删除任务 1
已恢复 1 个任务到 backup-demo/restored.json
1 [ ] 学习 Rust
```

再恢复到同一个 `restored.json`，命令会失败。文件错误的底层文本由操作系统提供，措辞可能不同；应观察到错误原因、失败退出码，以及目标内容保持不变。

PowerShell 读者先用 `$env:TASKBOOK_JSON_FILE = "backup-demo/tasks.json"` 设定路径，再执行对应的 Cargo 命令；读取恢复文件时把值改为 `backup-demo/restored.json`，结束后运行 `Remove-Item Env:TASKBOOK_JSON_FILE`。备份和恢复命令本身不读取这个变量。

## 用测试确认会保留哪些文件

配套包的 `tests/snapshot.rs` 有 4 个测试，使用独立临时目录。运行：

```sh
cargo test -p taskbook-backup --test snapshot
```

它们检查实际的文件和命令入口：备份与恢复保留字节和任务数据；已有目标、相同路径会被拒绝；缺失、损坏及无效版本的源文件不会创建目标；命令会报告结果和失败原因。

例如，测试先写入有效源文件，再备份，随后把原文件改成 `damaged`。恢复时读取备份，创建一个新文件，最后确认新文件仍包含原任务，而原文件仍是 `damaged`。这能确认恢复使用了哪个输入，也能防止把“恢复成功”误写成“覆盖修好了原文件”。

这些测试覆盖的是代码中明确列出的条件，没有模拟断电、磁盘写满、权限变化或其他进程同时修改数据。正式数据还需要独立保存的备份；在同一目录增加一个文件，无法应对整个目录被删除或磁盘损坏。

## 练习：相同任务是否意味着相同文件

写一个函数，接收两段 JSON 文本，先分别调用 `decode`，再比较任务列表。有效文本返回 `Ok(true)` 或 `Ok(false)`；任一文本无效时返回错误。用缩进不同、任务相同的两段 JSON 检查结果。

<details>
<summary>参考答案：先自己完成再展开</summary>

`taskbook-backup/examples/answer16.rs` 的完整内容：

```rust
use taskbook_json::storage;

fn same_tasks(left: &str, right: &str) -> Result<bool, storage::StoreError> {
    Ok(storage::decode(left)? == storage::decode(right)?)
}

fn main() -> Result<(), storage::StoreError> {
    let compact = r#"{"version":1,"tasks":[]}"#;
    let spaced = "{ \"version\": 1, \"tasks\": [] }";
    println!("任务相同：{}", same_tasks(compact, spaced)?);
    println!("字节相同：{}", compact.as_bytes() == spaced.as_bytes());
    assert!(same_tasks(compact, "broken").is_err());
    Ok(())
}
```

运行 `cargo run -p taskbook-backup --example answer16`，输出：

```text
任务相同：true
字节相同：false
```

这里复用了 `Task` 已有的 `PartialEq` 实现，比较编号、标题和完成状态。列表顺序也参与比较，交换两项的位置会影响结果。损坏 JSON 返回错误，不会被当作“两个列表不相同”。

</details>

## 官方延伸阅读

- [OpenOptions::create_new：仅创建新文件](https://doc.rust-lang.org/std/fs/struct.OpenOptions.html#method.create_new)
- [Write::write_all：写入全部缓冲内容](https://doc.rust-lang.org/std/io/trait.Write.html#method.write_all)
- [File::sync_all：请求同步文件内容与元数据](https://doc.rust-lang.org/std/fs/struct.File.html#method.sync_all)

外部文档查阅日期：2026-10-13。本文示例没有调用 `sync_all`，阅读它的说明不等于本项目已具备断电恢复能力。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：Serde 与 JSON](/posts/rust-15-serde-json/) · [下一章：用 clap 整理命令行接口](/posts/rust-17-clap/)
