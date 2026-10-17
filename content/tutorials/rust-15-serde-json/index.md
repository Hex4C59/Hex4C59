+++
url = "/posts/rust-15-serde-json/"
title = "Rust 入门 15：用 Serde 保存 JSON，并迁移旧任务"
date = 2026-10-13T09:00:00+08:00
lastmod = 2026-10-17
draft = false
author = "Hex4C59"
description = "引入 Serde 和 serde_json，验证任务文件的结构与业务规则，并把旧 TSV 数据迁移到不覆盖原文件的新 JSON。"
summary = "引入 Serde 和 serde_json，验证任务文件的结构与业务规则，并把旧 TSV 数据迁移到不覆盖原文件的新 JSON。"
tags = ["Rust", "Serde", "数据迁移"]
categories = ["programming"]
series = ["rust-from-zero"]
series_order = 15
series_label = "Serde 与 JSON 保存"
series_part = "继续完善项目"
series_number = 15
ShowToc = true
source_kind = "original"
article_type = "tutorial"
series_role = "chapter"
+++

本章把待办任务保存成 JSON（JavaScript Object Notation）文本，并提供一条迁移命令，把旧 TSV 数据转换到新文件。新增、完成、筛选和删除继续复用第十三章的逻辑，文件错误则采用第十四章的类型化处理方式。

你会第一次给业务项目引入第三方库。Serde 提供序列化和反序列化接口：序列化按字段读出 Rust 值，反序列化读取输入中的字段并构造 Rust 值；`serde_json` 负责把这些字段写成 JSON 文本，或从 JSON 文本中读出。本章完成后，你应该能添加依赖、理解派生实现、区分格式错误与业务错误，并检查迁移是否保留原数据。

## 先确定工作目录和依赖

本章使用下载包的 `rust-course/practice/taskbook-json`。所有 Cargo 命令在 `rust-course/practice` 工作区执行，第一步是：

```sh
cargo fetch --locked
cargo run -p taskbook-json --example serde_basics
```

首次获取第三方依赖需要网络。下载包包含 `practice/Cargo.lock`；`--locked` 要求按现有锁文件解析，不允许这个命令悄悄修改依赖选择。它不保证脱离当前工具链和系统后仍然能运行。

本章验证使用 Serde `1.0.229` 和 `serde_json` `1.0.154`，清单将它们固定为这两个版本。这样正文与配套源码使用相同接口，没有把所有未来版本的行为当作已验证结果。

`taskbook-json/Cargo.toml` 的完整内容：

```toml
[package]
name = "taskbook-json"
version = "0.1.0"
edition = "2024"
rust-version = "1.85"
publish = false

[dependencies]
taskbook = { path = "../../taskbook" }
taskbook-plus = { path = "../taskbook-plus" }
serde = { version = "=1.0.229", features = ["derive"] }
serde_json = "=1.0.154"
```

`features = ["derive"]` 启用 Serde 的派生宏，让 `#[derive(Serialize, Deserialize)]` 可以生成对应实现。派生 `Serialize` 时，生成的代码读取结构体字段并交给格式库；派生 `Deserialize` 时，生成的代码按字段名称和类型构造结构体。这些代码在编译时生成，真正转换文本时才由下面的 JSON 函数调用。

`serde_json` 实现具体格式。它们都不是 Rust 标准库的一部分，`use serde::...` 能工作，是因为这个包的清单已经声明了依赖。

如果以后自己创建另一个项目，通常可以用 `cargo add serde --features derive` 和 `cargo add serde_json` 添加依赖。Cargo 会选择当时可用的版本；这与复制本章固定版本的清单不同。学习本章时使用下载包或下面的清单即可。

## 用一个小对象做往返转换

配套文件 `taskbook-json/examples/serde_basics.rs` 的完整内容：

```rust
use serde::{Deserialize, Serialize};

#[derive(Debug, PartialEq, Serialize, Deserialize)]
struct Settings {
    name: String,
    active: bool,
}

fn main() -> Result<(), serde_json::Error> {
    let settings = Settings {
        name: String::from("Rust 练习"),
        active: true,
    };
    let json = serde_json::to_string(&settings)?;
    println!("{json}");
    let restored: Settings = serde_json::from_str(&json)?;
    assert_eq!(restored, settings);
    println!("读回：{}，启用：{}", restored.name, restored.active);
    Ok(())
}
```

运行后输出：

```text
{"name":"Rust 练习","active":true}
读回：Rust 练习，启用：true
```

`to_string` 把 Rust 值编码成文本，`from_str` 把文本解析成 Rust 值。后者需要知道目标类型；这里通过 `let restored: Settings` 提供类型信息，也可以写 `serde_json::from_str::<Settings>(&json)`。这次转换先从原对象读出名称和启用状态，生成 JSON 字符串，再从字符串构造一个拥有名称文本的新对象，两个对象各自保有自己的字段内容。

`active` 是 JSON 布尔值 `true`，没有引号；`"true"` 是字符串，无法直接作为这里的 `bool` 字段读入。结构体的派生实现帮助你检查字段类型，但它不会自动判断标题是否为空、任务编号是否重复。

双引号、反斜杠等字符由库按 JSON 规则编码。不要用 `format!` 手工把标题拼进 JSON，再逐个补转义规则。

## 给任务文件加一个版本字段

本章的文件形状是一个对象，包含 `version` 和 `tasks`：

```json
{
  "version": 1,
  "tasks": [
    {
      "id": 7,
      "title": "读 \"Rust\"",
      "done": true
    }
  ]
}
```

这是一份完整的示例 JSON，可以作为单独的练习数据文件。版本 1 是本教材定义的格式版本，不是 Rust、Serde 或应用程序的版本。

读取时只接受版本 1。未来若调整字段，程序需要明确决定怎样识别旧格式和迁移，不能假定增加了一个版本号就已经解决兼容问题。

空任务列表写成 `{"version":1,"tasks":[]}`。一个空的现有文件不是有效 JSON，会报错；文件完全不存在时，工具仍允许首次启动并返回空列表。这与第十二章“空 TSV 文件就是空列表”的规则不同。

## 单独定义用于保存的结构体

旧库的 `Task` 没有实现 Serde 的 trait，本章又希望保留第 1～12 章只用标准库的项目，所以不直接修改它。我们在新包里定义 `StoredTask`，保存相同的三个字段，再显式转换成原来的 `Task`。

这让文件结构和业务结构有各自的位置。当前转换确实只有三个字段，但它仍是一段需要检查的代码；如果漏掉完成状态，JSON 格式正确也可能把任务读错。

新建 `taskbook-json/src/lib.rs`，完整内容只有：

```rust
pub mod storage;
```

再新建 `src/storage.rs`，下面是完整业务代码。测试模块在后面追加：

```rust
use std::collections::HashSet;
use std::error::Error;
use std::fmt;
use std::fs::{self, OpenOptions};
use std::io::{self, Write};
use std::path::Path;

use serde::{Deserialize, Serialize};
use taskbook::{Task, validate_title};

#[derive(Debug)]
pub enum StoreError {
    Io(io::Error),
    Json(serde_json::Error),
    InvalidData(String),
}

impl fmt::Display for StoreError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(_) => write!(f, "文件操作失败"),
            Self::Json(_) => write!(f, "JSON 内容无法解析或生成"),
            Self::InvalidData(message) => write!(f, "{message}"),
        }
    }
}

impl Error for StoreError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Io(error) => Some(error),
            Self::Json(error) => Some(error),
            Self::InvalidData(_) => None,
        }
    }
}

impl From<io::Error> for StoreError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

impl From<serde_json::Error> for StoreError {
    fn from(error: serde_json::Error) -> Self {
        Self::Json(error)
    }
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Document {
    version: u32,
    tasks: Vec<StoredTask>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct StoredTask {
    id: u64,
    title: String,
    done: bool,
}

fn validate(tasks: &[Task]) -> Result<(), StoreError> {
    let mut ids = HashSet::new();
    for task in tasks {
        if task.id == 0 || !ids.insert(task.id) {
            return Err(StoreError::InvalidData(format!(
                "任务编号无效或重复：{}",
                task.id
            )));
        }
        validate_title(&task.title).map_err(StoreError::InvalidData)?;
    }
    Ok(())
}

pub fn encode(tasks: &[Task]) -> Result<String, StoreError> {
    validate(tasks)?;
    let document = Document {
        version: 1,
        tasks: tasks
            .iter()
            .map(|task| StoredTask {
                id: task.id,
                title: task.title.clone(),
                done: task.done,
            })
            .collect(),
    };
    Ok(serde_json::to_string_pretty(&document)?)
}

pub fn decode(input: &str) -> Result<Vec<Task>, StoreError> {
    let document: Document = serde_json::from_str(input)?;
    if document.version != 1 {
        return Err(StoreError::InvalidData(format!(
            "不支持文件格式版本 {}",
            document.version
        )));
    }
    let tasks: Vec<Task> = document
        .tasks
        .into_iter()
        .map(|task| Task {
            id: task.id,
            title: task.title,
            done: task.done,
        })
        .collect();
    validate(&tasks)?;
    Ok(tasks)
}

pub fn load(path: &Path) -> Result<Vec<Task>, StoreError> {
    match fs::read_to_string(path) {
        Ok(content) => decode(&content),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(Vec::new()),
        Err(error) => Err(StoreError::Io(error)),
    }
}

pub fn save(path: &Path, tasks: &[Task]) -> Result<(), StoreError> {
    let content = encode(tasks)?;
    fs::write(path, content)?;
    Ok(())
}

pub fn migrate(source: &Path, destination: &Path) -> Result<usize, StoreError> {
    let input = fs::read_to_string(source)?;
    let tasks = taskbook::storage::decode(&input).map_err(StoreError::InvalidData)?;
    let content = encode(&tasks)?;
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(destination)?;
    file.write_all(content.as_bytes())?;
    Ok(tasks.len())
}
```

### 编码和解码怎样分工

`encode` 先验证业务数据，再构建 `Document`，最后调用 `to_string_pretty`。这个接口增加缩进和换行，便于直接查看文件；它不会改变字段代表的业务含义。

编码接收 `&[Task]`，不能把借来的标题移出任务，所以构建 `StoredTask` 时明确克隆标题。解码得到的 `Document` 则拥有字段内容，转换时可以把 `String` 直接移进 `Task`，不需要再克隆。

`decode` 先解析结构和字段类型，再检查文件版本，最后检查正整数编号、重复编号与标题规则。任何一步失败，都不会生成可交给后续命令修改的成功列表。

### JSON 能解析，不代表任务有效

以下两种输入会在不同层次失败：

- `done` 写成 `"false"`：字段类型不对，返回 `StoreError::Json`。
- `id` 写成 `0`：它是能解析的整数，但不符合业务规则，返回 `StoreError::InvalidData`。

标题仍沿用前面项目的约束，不允许空白标题、制表符或换行。JSON 本身能表示这些字符，并不意味着我们已经决定改变业务规则。

`#[serde(deny_unknown_fields)]` 让 `Document` 和 `StoredTask` 拒绝未定义字段。例如把 `done` 拼成别的名字，应报告错误，不能假装这个字段已正确读入。这个选择也意味着未来新增字段时，旧程序可能拒绝它；格式演进需要单独设计。

这里既没有给必需字段设置默认值，也没有允许未知字段，所以缺少完成状态和多出一个拼错的状态字段都会失败，而不会悄悄补成未完成。

### 自定义错误与第三方错误怎么连起来

`StoreError::Json` 保存 `serde_json::Error`，`Io` 保存 `io::Error`；两者通过 `From` 接到 `?`，通过 `source` 提供底层原因。`InvalidData(String)` 保存业务检查消息，没有附加底层错误。

新结构体在当前包里定义，因此可以为它派生 Serde 的实现。这里只是把旧 `Task` 的字段映射到新结构，没有尝试给外部库的类型直接增加外部 trait 实现。

## 在入口选择 JSON 路径

`taskbook-json/src/main.rs` 的完整内容：

```rust
use std::env;
use std::error::Error;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use taskbook::{add_task, mark_done, render_tasks};
use taskbook_json::storage::{self, StoreError};
use taskbook_plus::{Command, parse_args, pending, remove_task, render_selection, search};

fn run() -> Result<(), StoreError> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.first().map(String::as_str) == Some("migrate") {
        let [_, source, destination] = args.as_slice() else {
            return Err(StoreError::InvalidData(String::from(
                "用法：taskbook-json migrate <TSV源文件> <JSON新文件>",
            )));
        };
        let count = storage::migrate(Path::new(source), Path::new(destination))?;
        println!("已迁移 {count} 条任务");
        return Ok(());
    }
    let command = parse_args(&args).map_err(|message| {
        let message = if message == taskbook_plus::USAGE {
            message.replace("taskbook-plus", "taskbook-json")
        } else {
            message
        };
        StoreError::InvalidData(message)
    })?;
    let path = env::var_os("TASKBOOK_JSON_FILE")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("tasks.json"));
    let mut tasks = storage::load(&path)?;
    match command {
        Command::Base(taskbook::Command::Add(title)) => {
            let id = add_task(&mut tasks, &title).map_err(StoreError::InvalidData)?;
            storage::save(&path, &tasks)?;
            println!("已添加任务 {id}");
        }
        Command::Base(taskbook::Command::List) => print!("{}", render_tasks(&tasks)),
        Command::Base(taskbook::Command::Done(id)) => {
            mark_done(&mut tasks, id).map_err(StoreError::InvalidData)?;
            storage::save(&path, &tasks)?;
            println!("已完成任务 {id}");
        }
        Command::Pending => print!("{}", render_selection(&pending(&tasks))),
        Command::Search(query) => {
            let selected = search(&tasks, &query).map_err(StoreError::InvalidData)?;
            print!("{}", render_selection(&selected));
        }
        Command::Remove(id) => {
            remove_task(&mut tasks, id).map_err(StoreError::InvalidData)?;
            storage::save(&path, &tasks)?;
            println!("已删除任务 {id}");
        }
    }
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("错误：{error}");
            let mut source = error.source();
            while let Some(cause) = source {
                eprintln!("原因：{cause}");
                source = cause.source();
            }
            ExitCode::FAILURE
        }
    }
}
```

普通命令使用 `TASKBOOK_JSON_FILE`，没有设置时使用当前工作目录下的 `tasks.json`。它与 TSV 工具的 `TASKBOOK_FILE` 是不同的环境变量，文件名也不同。

这里复用 `taskbook_plus::parse_args` 和筛选、删除函数，把它们返回的 `String` 错误包装成 `InvalidData`。原接口仍只返回文本；若以后调用方还需要区分“关键词为空”和“任务不存在”，相应核心接口也需要换成更具体的错误类型。

迁移命令单独接收源、目标两个路径。它不通过环境变量猜测路径，参数形式错误时直接给出迁移用法。迁移分支完成后立即返回，因此不会再加载普通命令的默认任务文件；迁移的数据只由这两个显式路径决定。

## 先运行新的 JSON 工具

在 macOS / Linux 的 `practice` 工作区执行：

```sh
json_practice_dir=$(mktemp -d)
TASKBOOK_JSON_FILE="$json_practice_dir/tasks.json" cargo run -p taskbook-json -- add '读 "Rust"'
TASKBOOK_JSON_FILE="$json_practice_dir/tasks.json" cargo run -p taskbook-json -- add "写练习"
TASKBOOK_JSON_FILE="$json_practice_dir/tasks.json" cargo run -p taskbook-json -- done 1
TASKBOOK_JSON_FILE="$json_practice_dir/tasks.json" cargo run -p taskbook-json -- list
cat "$json_practice_dir/tasks.json"
```

`list` 应输出：

```text
1 [x] 读 "Rust"
2 [ ] 写练习
```

查看文件时，标题中的双引号会以 JSON 转义形式保存。重新读入后，标题仍包含原来的双引号。`pending`、`search` 和 `remove` 也可以用同一个文件继续运行。

文件损坏时，程序会在加载阶段报错，不会把它当成空列表再保存。保存仍使用覆盖写入，没有事务、文件锁或写入中断恢复；本章只检查读取和校验失败不会触发后续保存。

## 把旧 TSV 迁移到新文件

`migrate` 的顺序是：读取源文件，按旧规则解码，按新规则验证并编码，最后创建目标文件并写入。源文件只被读取。

`create_new(true)` 要求目标此前不存在；如果已经存在，打开就失败。不要先用 `exists()` 检查，再用普通覆盖写入，那两个操作之间目标仍可能被其他程序创建。

在前面新建的练习目录中，写一份专用旧数据，再迁移：

```sh
printf '7\t1\t读 "Rust"\n12\t0\t写练习\n' > "$json_practice_dir/source.tsv"
cargo run -p taskbook-json -- migrate "$json_practice_dir/source.tsv" "$json_practice_dir/migrated.json"
TASKBOOK_JSON_FILE="$json_practice_dir/migrated.json" cargo run -p taskbook-json -- list
cat "$json_practice_dir/source.tsv"
```

应看到 `已迁移 2 条任务`，随后列表仍为：

```text
7 [x] 读 "Rust"
12 [ ] 写练习
```

编号、顺序、标题和状态都保留，源文件仍是原 TSV 文本。再对同一目标运行迁移，应失败并保留已存在的 JSON 文件。源与目标写成同一个已有路径时，同样不能覆盖源文件。

坏格式或缺失的源文件在创建目标之前就失败，不会新建目标。写入途中若失败，已创建的新目标可能留下不完整内容；本例没有自动清理或恢复流程。看到失败时先检查这份新文件，不能把它当作成功迁移的结果。

## 测试格式、业务规则和迁移

把下面完整测试模块追加到 `src/storage.rs`，或查看下载包里的同一模块：

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trips_unicode_quotes_and_completion() {
        let tasks = vec![Task {
            id: 7,
            title: String::from("读 \"Rust\"，再练习 🦀"),
            done: true,
        }];
        let text = encode(&tasks).unwrap();
        assert_eq!(decode(&text).unwrap(), tasks);
        assert!(text.contains("\\\"Rust\\\""));
        assert_eq!(decode(&encode(&[]).unwrap()).unwrap(), []);
    }

    #[test]
    fn distinguishes_json_syntax_from_business_validation() {
        assert!(matches!(decode("not-json"), Err(StoreError::Json(_))));
        for input in [
            r#"{"version":2,"tasks":[]}"#,
            r#"{"version":1,"tasks":[{"id":0,"title":"Rust","done":false}]}"#,
            r#"{"version":1,"tasks":[{"id":1,"title":" ","done":false}]}"#,
            r#"{"version":1,"tasks":[{"id":1,"title":"Rust","done":false},{"id":1,"title":"重复","done":true}]}"#,
        ] {
            assert!(
                matches!(decode(input), Err(StoreError::InvalidData(_))),
                "{input}"
            );
        }
        for input in [
            r#"{"version":1,"tasks":[{"id":1,"title":"Rust","done":"false"}]}"#,
            r#"{"version":1,"tasks":[{"id":1,"title":"Rust"}]}"#,
            r#"{"version":1,"tasks":[],"typo":true}"#,
            r#"{"version":1,"tasks":[{"id":1,"title":"Rust","done":false,"typo":true}]}"#,
        ] {
            assert!(matches!(decode(input), Err(StoreError::Json(_))), "{input}");
        }
    }

    #[test]
    fn encoding_also_rejects_invalid_task_fields() {
        for task in [
            Task {
                id: 0,
                title: String::from("Rust"),
                done: false,
            },
            Task {
                id: 1,
                title: String::from("bad\ttitle"),
                done: false,
            },
        ] {
            assert!(matches!(encode(&[task]), Err(StoreError::InvalidData(_))));
        }
        let task = || Task {
            id: 1,
            title: String::from("Rust"),
            done: false,
        };
        assert!(encode(&[task(), task()]).is_err());
    }
}
```

在 `practice` 工作区运行：

```sh
cargo test -p taskbook-json --lib
cargo test -p taskbook-json --test cli
```

库里的 3 个测试检查编码和解码，包括中文、引号、空列表、类型错误、未知字段、无效版本和重复编号。CLI 测试另检查重启后数据仍在、查询没有修改文件、损坏数据不会被保存成新列表，以及迁移保留源文件并拒绝已有目标。

测试里的“旧数据保持不变”对应明确的读取、校验失败和目标已存在条件，没有覆盖磁盘写入中断的恢复保证。

## 练习：缺少字段时提供默认值

另写一个 `Note` 结构体，包含 `title: String` 和 `tags: Vec<String>`。旧 JSON 只有标题时，让标签默认为空列表；标签字段存在但类型错误时，仍要失败。这个练习独立于任务文件，不修改它的版本或业务规则。

<details>
<summary>参考答案：先自己完成再展开</summary>

下面是配套示例 `taskbook-json/examples/answer15.rs` 的完整内容：

```rust
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Note {
    title: String,
    #[serde(default)]
    tags: Vec<String>,
}

fn main() -> Result<(), serde_json::Error> {
    let note: Note = serde_json::from_str(r#"{"title":"Rust 练习"}"#)?;
    assert!(note.tags.is_empty());
    println!("{}", serde_json::to_string(&note)?);
    assert!(serde_json::from_str::<Note>(r#"{"title":"Rust","tags":"学习"}"#).is_err());
    Ok(())
}
```

运行 `cargo run -p taskbook-json --example answer15`，输出：

```text
{"title":"Rust 练习","tags":[]}
```

`#[serde(default)]` 在字段缺失时使用该类型的默认值，`Vec<String>` 的默认值就是空列表。它不会把一个现有的字符串自动当作标签列表；字段已经提供却类型不对时，仍是输入错误。再次序列化时，这个空列表也会作为标签字段写进 JSON，而不是继续省略。

为旧文件提供默认值是一种兼容选择，不应随便用于必需字段。任务编号或格式版本缺失时若悄悄补 0，反而会隐藏数据问题。本章的任务格式仍要求这些字段存在。

</details>

## 完成后再选择下一项改动

到这里，你已经使用过本地库、第三方依赖、借用视图、类型化错误、序列化和迁移。可以先不看答案重做其中一项，例如新增筛选命令，或把一个 `String` 错误接口改成枚举，再用测试确认原行为。

后面三章会继续完成具体项目：第十六章先做手动备份并恢复到新文件，第十七章用 clap 整理命令行接口，第十八章用本机 HTTP 服务练习请求和 JSON 响应。临时文件替换、异步和并发则需要再分别确定行为和测试。

## 官方延伸阅读

- [Serde 的派生实现](https://serde.rs/derive.html)
- [Serde 容器属性](https://serde.rs/container-attrs.html)
- [Serde 字段属性与默认值](https://serde.rs/field-attrs.html)
- [serde_json 文档](https://docs.rs/serde_json/1.0.154/serde_json/)
- [Cargo.lock](https://doc.rust-lang.org/cargo/guide/cargo-toml-vs-cargo-lock.html)
- [OpenOptions::create_new](https://doc.rust-lang.org/std/fs/struct.OpenOptions.html#method.create_new)

外部文档查阅日期：2026-10-13。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：自定义错误类型](/posts/rust-14-typed-errors/) · [下一章：备份与恢复](/posts/rust-16-backup/)
