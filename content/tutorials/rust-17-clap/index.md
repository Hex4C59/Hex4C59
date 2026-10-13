+++
url = "/posts/rust-17-clap/"
title = "Rust 入门 17：用 clap 整理命令行接口"
date = 2026-10-13T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "用 clap 的派生宏声明子命令、路径选项和参数类型，把参数错误与业务错误分开，并复用 JSON 存储和备份。"
summary = "用 clap 的派生宏声明子命令、路径选项和参数类型，把参数错误与业务错误分开，并复用 JSON 存储和备份。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 17
series_number = 17
series_label = "命令行与 clap"
series_part = "文件、命令行与网络"
ShowToc = true
+++

待办工具的命令越来越多了：新增、查询、删除，还有上一章的备份和恢复。手写解析需要逐项检查参数个数，并一起维护帮助信息与实际行为。

本章用 clap 声明命令行接口。完成后，你会得到一个支持 `--help`、`--version` 和 `--file` 的 `taskbook-cli`。任务规则、JSON 格式和备份行为继续复用旧包，主要改变参数进入程序的方式。

先完成第十三至十六章，再进入下载包的 `rust-course/projects`。本章固定使用 clap 4.6.7；首次执行 `cargo fetch --locked` 获取依赖，已有缓存后可加 `--offline`。这是教材选择的版本，不要求读者追随每次依赖发布。

## 把参数写成结构体和枚举

先看目标命令：

```sh
cargo run -p taskbook-cli -- --help
cargo run -p taskbook-cli -- add --help
cargo run -p taskbook-cli -- --version
cargo run -p taskbook-cli -- --file demo.json add "学习 Rust"
cargo run -p taskbook-cli -- list --file demo.json
```

Cargo 的 `--` 把后面的参数交给自己的程序。`--file` 既可以放在子命令前，也可以放在子命令后；代码会把它声明为全局选项。标题中有空格时要加引号，使 shell 把它作为一个参数传入。

`--file` 默认是当前工作目录里的 `tasks.json`。它取代这个新包的环境变量接口：`taskbook-cli` 不读取 `TASKBOOK_JSON_FILE`。第十五章原包仍保留原来的使用方式。

`taskbook-cli/Cargo.toml` 的完整内容：

```toml
[package]
name = "taskbook-cli"
version = "0.1.0"
edition = "2024"
rust-version = "1.85"
publish = false

[dependencies]
clap = { version = "=4.6.7", features = ["derive"] }
taskbook = { path = "../../taskbook" }
taskbook-plus = { path = "../../practice/taskbook-plus" }
taskbook-json = { path = "../../practice/taskbook-json" }
taskbook-backup = { path = "../taskbook-backup" }
```

如果从空目录跟写，把 `taskbook-cli` 加入 `projects/Cargo.toml` 的成员列表；`taskbook-backup` 也要保留，因为这个新包依赖上一章的库。

clap 的 `derive` 功能提供派生宏，可以根据结构体和枚举生成参数解析实现。宏在编译时展开，不是运行时才去分析 Rust 源码。

## 完整的参数定义与业务入口

`taskbook-cli/src/lib.rs` 的完整内容：

```rust
use std::path::PathBuf;

use clap::{Parser, Subcommand};
use taskbook_json::storage::{self, StoreError};

#[derive(Debug, Parser)]
#[command(name = "taskbook-cli", version, about = "管理本地 JSON 待办任务")]
pub struct Cli {
    #[arg(
        long,
        global = true,
        default_value = "tasks.json",
        help = "任务文件路径"
    )]
    pub file: PathBuf,
    #[command(subcommand)]
    pub command: Command,
}

#[derive(Debug, Subcommand)]
pub enum Command {
    #[command(about = "新增任务")]
    Add { title: String },
    #[command(about = "列出全部任务")]
    List,
    #[command(about = "标记任务完成")]
    Done {
        #[arg(value_parser = clap::value_parser!(u64).range(1..))]
        id: u64,
    },
    #[command(about = "列出未完成任务")]
    Pending,
    #[command(about = "按标题搜索")]
    Search { query: String },
    #[command(about = "删除任务")]
    Remove {
        #[arg(value_parser = clap::value_parser!(u64).range(1..))]
        id: u64,
    },
    #[command(about = "备份到一个新文件")]
    Backup { destination: PathBuf },
    #[command(about = "从备份恢复到 --file 指定的新文件")]
    Restore { source: PathBuf },
}

pub fn execute(cli: Cli) -> Result<String, StoreError> {
    match &cli.command {
        Command::Backup { destination } => {
            let count = taskbook_backup::copy_snapshot(&cli.file, destination)?;
            return Ok(format!(
                "已备份 {count} 个任务到 {}\n",
                destination.display()
            ));
        }
        Command::Restore { source } => {
            let count = taskbook_backup::copy_snapshot(source, &cli.file)?;
            return Ok(format!("已恢复 {count} 个任务到 {}\n", cli.file.display()));
        }
        _ => {}
    }
    let mut tasks = storage::load(&cli.file)?;
    let output = match cli.command {
        Command::Add { title } => {
            let id = taskbook::add_task(&mut tasks, &title).map_err(StoreError::InvalidData)?;
            storage::save(&cli.file, &tasks)?;
            format!("已添加任务 {id}\n")
        }
        Command::List => taskbook::render_tasks(&tasks),
        Command::Done { id } => {
            taskbook::mark_done(&mut tasks, id).map_err(StoreError::InvalidData)?;
            storage::save(&cli.file, &tasks)?;
            format!("已完成任务 {id}\n")
        }
        Command::Pending => taskbook_plus::render_selection(&taskbook_plus::pending(&tasks)),
        Command::Search { query } => {
            let found = taskbook_plus::search(&tasks, &query).map_err(StoreError::InvalidData)?;
            taskbook_plus::render_selection(&found)
        }
        Command::Remove { id } => {
            taskbook_plus::remove_task(&mut tasks, id).map_err(StoreError::InvalidData)?;
            storage::save(&cli.file, &tasks)?;
            format!("已删除任务 {id}\n")
        }
        Command::Backup { .. } | Command::Restore { .. } => unreachable!(),
    };
    Ok(output)
}
```

`Cli` 是解析后的参数，包含路径和一个子命令。`PathBuf` 拥有路径，适合放在这个结构体里；`Command` 表达这次需要执行哪一种操作。

`#[derive(Parser)]` 为结构体生成解析接口，`#[derive(Subcommand)]` 为枚举生成子命令接口。`#[command(subcommand)]` 把二者接起来。枚举变体 `Add` 对应命令 `add`，变体内的 `title` 是必需的位置参数。

这里的 `Parser` 是 clap 提供的 trait。下一段 `Cli::parse()` 能调用它生成的关联方法，也需要把这个 trait 引入作用域。这和第九章讨论的“类型实现某种行为”是同一个机制，只是实现由派生宏生成。

### 参数类型与业务规则各管一层

`Done` 和 `Remove` 的编号字段是 `u64`。`clap::value_parser!(u64).range(1..)` 先要求参数能解析成该类型，再要求编号至少为 1。因此 `done abc` 和 `done 0` 都是参数错误，不会进入文件读写。

但 `done 999` 能通过参数检查：它是一个合法的正整数。文件里是否存在编号 999，要等任务加载后才能判断，仍由 `mark_done` 处理。

标题和搜索词也有业务规则。只包含空白的标题不能新增，空白搜索词不能查询；这些规则继续放在旧库里，而不是只在新命令入口再写一次。其他调用者直接使用库函数时也能得到同样的检查。

### 为什么先处理备份和恢复

普通任务命令先加载 `--file` 指定的列表。备份和恢复的输入方式不同，所以函数先处理它们，再进入普通分支。

- `backup backup.json` 从 `--file` 读取，创建 `backup.json`；源文件必须存在。
- `restore backup.json` 从备份读取，创建 `--file` 指定的目标；目标必须不存在。

恢复直接读取备份，并要求目标是一个新文件。规则来自上一章的 `copy_snapshot`。

最后的 `unreachable!()` 对应已经在函数开头返回的两个变体。如果以后调整控制流程，要一起检查这项假设；它不是处理用户输入错误的方式。

## main 只组织输入、输出和退出码

`taskbook-cli/src/main.rs` 的完整内容：

```rust
use std::error::Error;
use std::process::ExitCode;

use clap::Parser;
use taskbook_cli::{Cli, execute};

fn main() -> ExitCode {
    let cli = Cli::parse();
    match execute(cli) {
        Ok(output) => {
            print!("{output}");
            ExitCode::SUCCESS
        }
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

`Cli::parse()` 负责帮助、版本和参数检查。帮助与版本成功时，clap 打印内容并以退出码 0 结束；参数无效时，打印错误并以退出码 2 结束。它们都在 `execute` 前完成。

`execute` 处理数据规则和文件操作。失败时 `main` 打印业务错误及原始原因，返回退出码 1。三种结果因而可以区分：

| 操作 | 退出码 | 是否执行任务读写 |
| --- | --- | --- |
| `--help` 或 `--version` | 0 | 否 |
| `done abc`、`done 0`、缺少参数或多余参数 | 2 | 否 |
| 参数有效，但任务缺失或文件无效 | 1 | 执行相关读取；校验失败不保存 |
| 正常操作完成 | 0 | 由具体命令决定 |

clap 的帮助信息中仍有 `Usage`、`Commands` 等英文标签；命令用途和文件选项的说明来自我们写的中文文本。这里没有配置完整的中文帮助模板。

## 完整地使用新接口

在 `rust-course/projects` 运行。新建一个未使用过的目录，以下命令对应空的初始任务列表：

```sh
mkdir cli-demo
cargo run -p taskbook-cli -- --file cli-demo/tasks.json add "学习 Rust"
cargo run -p taskbook-cli -- --file cli-demo/tasks.json add "写练习"
cargo run -p taskbook-cli -- --file cli-demo/tasks.json done 1
cargo run -p taskbook-cli -- --file cli-demo/tasks.json pending
cargo run -p taskbook-cli -- --file cli-demo/tasks.json search Rust
cargo run -p taskbook-cli -- --file cli-demo/tasks.json backup cli-demo/backup.json
cargo run -p taskbook-cli -- --file cli-demo/restored.json restore cli-demo/backup.json
cargo run -p taskbook-cli -- --file cli-demo/restored.json list
```

忽略 Cargo 日志，输出：

```text
已添加任务 1
已添加任务 2
已完成任务 1
2 [ ] 写练习
1 [x] 学习 Rust
已备份 2 个任务到 cli-demo/backup.json
已恢复 2 个任务到 cli-demo/restored.json
1 [x] 学习 Rust
2 [ ] 写练习
```

`list`、`pending` 和 `search` 只读取任务，不写回文件。`add`、`done` 和 `remove` 仍覆盖保存整个 JSON 文件；引入参数库并没有改变第十五章的写入限制，也没有加入文件锁。

再观察两种失败：

```sh
cargo run -p taskbook-cli -- --file cli-demo/tasks.json done 0
cargo run -p taskbook-cli -- --file cli-demo/tasks.json done 999
```

两条命令都应该失败。第一条是 clap 的范围检查，退出码 2；第二条到达任务库，报告编号不存在，退出码 1。macOS / Linux shell 可以在每条命令后运行 `echo $?`，PowerShell 使用 `$LASTEXITCODE`；两种环境都要在下一条程序命令前查看。

## 测试命令，而不只测试解析函数

下载包中的 `tests/cli.rs` 直接启动编译好的二进制。运行：

```sh
cargo test -p taskbook-cli --test cli
```

4 个测试检查选定路径、全局选项的位置、查询不保存、帮助与版本不加载损坏文件、参数错误和业务错误的退出码，以及备份和恢复的拒绝覆盖行为。

例如，帮助测试先在默认路径写入 `broken`，再执行 `--help`。如果程序错误地先加载任务，JSON 校验会失败；当前测试要求帮助成功，且文件仍是 `broken`。这个检查对应一个实际使用场景：数据损坏时，读者仍然能查看使用说明。

## 练习：增加 stats 子命令

增加只读命令 `stats`，输出任务总数和待完成数量。不要因为统计而保存文件，也不要要求它额外接收参数。

<details>
<summary>参考答案：先自己完成再展开</summary>

先在 `Command` 枚举中增加下面的变体。这是需要插入原文件的片段：

```rust
#[command(about = "统计任务数量")]
Stats,
```

再在 `execute` 的第二个 `match` 中、最后的 `Backup | Restore` 分支之前，增加下面的分支：

```rust
Command::Stats => {
    let pending = tasks.iter().filter(|task| !task.done).count();
    format!("共 {} 个任务，待完成 {pending} 个\n", tasks.len())
}
```

第一个 `match` 的 `_ => {}` 已经让普通命令继续往下执行，不需要修改那里。第二个 `match` 需要显式处理新变体，否则编译器会报告匹配不完整。

完成前面的演示后，运行 `cargo run -p taskbook-cli -- --file cli-demo/tasks.json stats`，应输出：

```text
共 2 个任务，待完成 1 个
```

空列表则输出 `共 0 个任务，待完成 0 个`。配套主版本没有预先加入这个命令，便于你自己修改。验证时既要检查输出，也要比较运行前后的文件字节，确认统计没有保存文件。

</details>

## 官方延伸阅读

- [clap 4.6.7 的 derive 教程](https://docs.rs/clap/4.6.7/clap/_derive/_tutorial/index.html)
- [Parser::parse 与 try_parse](https://docs.rs/clap/4.6.7/clap/trait.Parser.html)
- [RangedU64ValueParser 的范围检查](https://docs.rs/clap/4.6.7/clap/builder/struct.RangedU64ValueParser.html)

外部文档查阅日期：2026-10-13。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：备份与恢复](/posts/rust-16-backup/) · [下一章：请求本机 HTTP 服务](/posts/rust-18-http/)
