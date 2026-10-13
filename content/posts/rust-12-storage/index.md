+++
title = "Rust 入门 12：保存数据，完成命令行工具"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
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

## 本章从上一章的哪个状态开始

如果你一直自己跟写，项目现在有上一章的 `src/lib.rs` 和内存版 `src/main.rs`。保留库里的函数与测试，新建 `src/storage.rs`，在库入口声明它，再把 `main.rs` 替换为本章的命令行版本。

下载包则已经包含最终版本。你可以直接运行它，但仍建议逐段读一遍：先看文本怎样转换成任务，再看磁盘读取，最后看命令怎样把它们连起来。本章完成后，同一个工具退出再启动，任务应仍然存在；无效命令和损坏文件应得到错误消息。

## 设计一个容易查看的文件格式

本项目采用制表符分隔的文本格式（Tab-Separated Values，TSV）。每行记录一条任务，依次保存编号、完成状态和标题。状态 `0` 表示未完成，`1` 表示已完成。

```text
1<TAB>0<TAB>学习 Rust
2<TAB>1<TAB>写练习
```

上面的 `<TAB>` 只是显示分隔位置的标记，实际文件使用制表符字节；你不需要手动创建初始文件。程序首次新增任务时会写出它。

空文件表示没有任务。标题禁止制表符、回车和换行，否则需要另外设计转义规则。UTF-8 文件可以保存中文。坏数据要返回错误，不能悄悄当成空列表再覆盖原文件。

### 分隔符为什么会影响标题规则

每行固定三列：正整数编号、`0` 或 `1` 状态、标题。文件里存的是实际制表符，不是反斜杠和字母 `t` 两个字符。

标题可以包含普通空格和中文，但不能包含 `\t`、`\n`、`\r`，否则会破坏列或行的边界。上一章的 `validate_title` 已经检查这些字符；文件解码时也会复用它。

空文件表示没有任务。只有一个换行的文件则有一条空记录，缺少必要字段，应报错。也不要把终端展示用的 `1 [ ] 标题` 直接写进数据文件：展示格式和保存格式是两套明确的规则。

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

### 先认出 storage 里的四个函数

| 函数 | 输入 | 输出 |
| --- | --- | --- |
| `encode` | 任务切片 | 按文件格式组织的文本，或错误 |
| `decode` | 文件文本 | 任务列表，或错误 |
| `load` | 路径 | 从磁盘读出的任务列表，或错误 |
| `save` | 路径和任务切片 | 保存成功，或错误 |

前两个不访问磁盘，后两个负责磁盘边界。`save` 先调用 `encode`，确认内存数据符合格式后，才尝试写入文件。

这里的 `&Path` 是借用路径。主函数中的 `PathBuf` 拥有路径内容，关系类似 `&str` 和 `String`，不过路径需要处理操作系统自己的表示，不能简单把两者当成同一种文本类型。

## 先编码和解析，再接触磁盘

`encode` 把任务列表转换成完整文本，`decode` 把文本转换成任务列表。它们不操作文件，便于单独验证格式。

`decode` 逐行处理，`.enumerate()` 给出从 0 开始的行索引，所以错误消息要加 1。`splitn(3, '\t')` 最多拆成三部分，第三部分保留标题的其余内容。如果里面还有制表符，`validate_title` 会拒绝它。

`let [id, done, title] = parts.as_slice() else { ... };` 是 `let ... else`：匹配成功就继续使用绑定；失败就提前返回。它适合“没有满足结构，就无法继续”的流程。

`HashSet` 是只保存不重复值的集合。这里用它记录已出现的编号。`.insert(id)` 返回是否真的插入新值，因此可以发现重复编号。`encode` 也检查编号和标题，避免公开字段被手工设置成非法值后写入文件。

遇到任何坏行，解析整个文件失败；不会只保留能读懂的几条再写回去。

### 顺着 decode 的循环读一行

`input.lines()` 逐行提供文本，`enumerate()` 给出从 0 开始的下标。错误消息里用 `index + 1`，这样读者看到的行号从 1 开始。

`splitn(3, '\t')` 最多分成三段。最后一段包含剩余文本；若里面还有制表符，标题校验会拒绝它。`parts.as_slice()` 将收集到的列表借用为切片，再用模式拆出恰好三段。

代码中的 `let [id, done, title] = ... else { ... };` 是 `let...else`：形状匹配时，三个变量可以在后面继续使用；形状不匹配时，`else` 必须通过 `return` 等方式离开当前流程。本例直接返回格式错误。

`HashSet` 只负责记住出现过的编号。`insert(id)` 在新编号第一次出现时返回 `true`，重复插入时返回 `false`，因此 `!ids.insert(id)` 表示重复。它不决定任务顺序；顺序仍由 `Vec<Task>` 保留。

### 用内存文本检查一轮转换

新建自己的 `examples/format.rs`，内容如下。在单包目录运行 `cargo run --example format`；下载包没有预置这个辅助目标，需要先添加文件。

```rust
use taskbook::{Task, storage};

fn main() -> Result<(), String> {
    let tasks = vec![Task {
        id: 1,
        title: String::from("学习 Rust"),
        done: false,
    }];
    let text = storage::encode(&tasks)?;
    println!("编码文本：{text:?}");
    assert_eq!(storage::decode(&text)?, tasks);
    assert!(storage::decode("1\t2\t学习 Rust\n").is_err());
    println!("来回转换与非法状态检查通过");
    Ok(())
}
```

第一行的调试格式应是 `编码文本："1\t0\t学习 Rust\n"`。这里为了让分隔符可见，使用了 `{:?}`；实际字符串包含制表符和换行。第二行说明正常文本能解码回原任务，而状态 `2` 被拒绝。

## 文件不存在和文件损坏是两种情况

`fs::read_to_string` 读取整个文件并按 UTF-8 解码。只有 `ErrorKind::NotFound` 被当成首次启动的空列表。权限问题、目录路径、无效 UTF-8 等错误会返回明确消息。

`save` 先完成编码，成功后再调用 `fs::write`。这会创建文件，或覆盖已有文件内容。如果父目录不存在，不会自动创建父目录，而是报告写入错误。

这是用于学习、单个进程顺序使用的小工具。`fs::write` 不是事务：写入中断可能留下不完整文件，同时运行两个写入进程也可能丢失更新。重要数据应额外设计备份、并发访问规则和可靠的替换流程，或使用数据库。教程的测试不能证明它具有这些能力。

### 缺失文件为什么单独处理

第一次使用工具时还没有数据文件，这是约定允许的情况，`load` 返回空列表。权限不足、路径指向目录、文件内容不是有效 UTF-8 或记录格式不对，都不能等同于“还没有任务”。

如果把所有读取失败都替换成 `Vec::new()`，下一次新增就可能在已有数据无法读取时，用新列表覆盖文件。所以这里仅对 `ErrorKind::NotFound` 使用空列表，其他读取错误和解码错误继续向外返回。

成功读取也不代表内容有效。`read_to_string` 负责读取 UTF-8 文本，`decode` 再检查字段数量、编号、状态和标题，两层失败都由入口处理。

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

### 入口按什么顺序执行

`env::args()` 提供命令行参数；第一项通常是程序名，因此 `.skip(1)` 跳过它，剩下的参数收集为 `Vec<String>`，交给 `parse_args`。

接下来确定文件路径，读取已有任务，再执行命令。`TASKBOOK_FILE` 若存在，就使用它提供的路径；否则使用当前工作目录下的 `tasks.tsv`。这个默认路径与可执行文件放在哪里无关。

新增和完成命令在成功保存之后才打印成功消息；列出命令只读文件，不保存。若文件原本不存在，首次执行 `list` 只会报告没有任务，不会创建一个空文件。

最外层的 `main` 把 `run()` 的结果转换成 `ExitCode`。正常完成返回成功状态；失败时用 `eprintln!` 输出带 `错误：` 前缀的消息，并返回失败状态。这样 shell 和其他调用程序也能判断失败，而不只是有人在屏幕上看到一句话。

`?` 仍没有“自动打印”功能。发生读取、解析或保存错误时，它逐层返回，直到 `main` 的 `Err` 分支决定怎样显示。

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

### 用一份新文件重演全部命令

下面的 macOS / Linux 命令在 `rust-course` 工作区执行，为练习新建临时目录。每条命令都指定同一个数据文件，不会读取工作区默认的 `tasks.tsv`：

```sh
practice_dir=$(mktemp -d)
TASKBOOK_FILE="$practice_dir/tasks.tsv" cargo run -p taskbook -- list
TASKBOOK_FILE="$practice_dir/tasks.tsv" cargo run -p taskbook -- add "学习 Rust"
TASKBOOK_FILE="$practice_dir/tasks.tsv" cargo run -p taskbook -- add "写练习"
TASKBOOK_FILE="$practice_dir/tasks.tsv" cargo run -p taskbook -- done 1
TASKBOOK_FILE="$practice_dir/tasks.tsv" cargo run -p taskbook -- list
cat "$practice_dir/tasks.tsv"
```

前五条工具命令的输出依次是：

```text
还没有任务
已添加任务 1
已添加任务 2
已完成任务 1
1 [x] 学习 Rust
2 [ ] 写练习
```

最后的 `cat` 显示数据文件：编号 1 的状态为 `1`，编号 2 的状态为 `0`，字段用实际制表符分隔。你可以拿它和 `list` 的输出对照。

再执行不存在编号的完成命令，并立即查看退出状态：

```sh
TASKBOOK_FILE="$practice_dir/tasks.tsv" cargo run -p taskbook -- done 99
printf '退出状态：%s\n' "$?"
TASKBOOK_FILE="$practice_dir/tasks.tsv" cargo run -p taskbook -- list
```

应看到 `错误：找不到任务 99`，退出状态为 1，随后列出的任务保持原来的状态。`$?` 读取上一条命令的退出状态，所以中间不要插入别的命令。

这里新建的临时目录只用于自己的练习。阅读完后可以按实际路径检查并清理它；工具不会自动把临时数据迁移到默认文件。

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

### 为什么只测试 encode 与 decode 还不够

往返转换测试可以确认文本格式，但不能确认入口是否真的调用了保存，也不能确认下一次进程启动时是否读到了同一文件。CLI（Command-Line Interface，命令行接口）测试因此会启动编译出的 `taskbook`，逐次执行新增、完成和列出。

配套测试同时检查标准输出、标准错误和退出状态。正常命令应提供预期结果；错误命令应失败，且原文件字节保持不变。这样能发现“屏幕说失败，但文件已经改了”或“屏幕说成功，下次启动却丢了任务”的接线问题。

文件测试中的临时目录与正式数据文件分开，每次测试使用独立路径。不要为了省代码让多个测试共用仓库里的 `tasks.tsv`，否则它们可能互相影响，也会改变你的练习记录。

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

### 这份保存实现的边界

`fs::write` 会把指定文件的全部内容替换成新文本；它不是追加操作。本项目适合一人在本机顺序执行命令。

读取失败、解码失败或业务校验失败时，程序会在写入之前返回，这些情况由测试检查。写入本身若中途失败，则没有事务或恢复机制保证旧文件完整；两个进程同时读写也没有文件锁来协调。不要把“损坏输入没有被覆盖”的测试结果扩大成所有写入失败都能保住旧数据。

如果以后要存重要数据，可以另做一节，设计临时文件、替换、备份与并发策略，并为对应失败条件写测试。本章先完成一条清楚可验证的读取、处理、保存路径。

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

### 加上字节比较，避免只凭目测

在上面的专用练习目录中，还可以先执行 `cp practice-corrupt.tsv practice-corrupt.before.tsv`，再运行新增命令。运行后用 `cmp practice-corrupt.before.tsv practice-corrupt.tsv` 比较两份文件。`cmp` 没有输出且退出状态为 0，表示字节完全一致。

这是对你自己新建的坏数据文件做检查。不要通过故意破坏已有任务文件来测试错误路径。配套 CLI 测试则会自动创建坏格式和无效 UTF-8 文件，检查错误状态以及文件内容不变。

想换一个数据模型检查自己是否会用这些知识，可以完成[第十二章后的学习时长记录器](/posts/rust-practice-checkpoints/#after-ch12)。它要求处理参数、文本格式、跨进程保存和损坏数据，沿用本章的覆盖写入边界。

## 不看答案，重新完成一次

新建一个空项目，只看需求重新实现新增、完成、列出和保存。遇到编译错误时先读错误消息，查本教材对应章节，再查官方文档。完成后逐项验证：

- 标题有空格和中文时能够保存，重启后内容不变。
- 空白标题、非法编号、找不到的任务都有清楚的错误。
- 修改一条任务不改变其他任务的状态。
- 文件不存在可以首次启动，文件损坏会报错并保留原内容。
- 测试可以检查正常路径和上述失败条件。

如果你能从空项目完成这些行为，并解释主要函数的参数为什么采用值、共享引用或可变引用，就达到了这套教材的入门目标。

接下来可以给项目增加“只列出未完成任务”或“按关键词搜索”，先为新行为写测试，再修改代码。之后按自己的用途选择网络请求、数据序列化或并发主题。遇到异步和 `unsafe` 时，再单独学习它们的约束。


### 给下一个功能留一份具体需求

若选择“只列出未完成任务”，可以先要求：保留原编号、保持原顺序、不修改完成状态；没有未完成任务时显示明确消息。分别用空列表、全完成、部分完成三组输入写测试，再决定新增一个命令，还是给列表函数增加一个参数。

若选择“按关键词搜索”，先确定是否区分大小写、空关键词怎样处理、只匹配标题还是也匹配编号。需求确定以后，`iter`、`filter` 和已有的渲染函数才有清楚的工作范围。能把一个模糊功能拆成输入、结果和失败条件，是后续继续使用 Rust 时需要反复练习的能力。

## 官方延伸阅读

- [文件读取](https://doc.rust-lang.org/std/fs/fn.read_to_string.html)
- [文件写入](https://doc.rust-lang.org/std/fs/fn.write.html)
- [命令行参数](https://doc.rust-lang.org/std/env/fn.args.html)
- [ExitCode](https://doc.rust-lang.org/std/process/struct.ExitCode.html)

外部文档查阅日期：2026-10-13。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：实战：任务与命令](/posts/rust-11-taskbook/) · [下一章：筛选、搜索与删除](/posts/rust-13-taskbook-plus/)
