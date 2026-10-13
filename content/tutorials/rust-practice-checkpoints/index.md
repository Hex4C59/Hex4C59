+++
url = "/posts/rust-practice-checkpoints/"
title = "Rust 入门附录：三个阶段的分级练习与项目验收"
date = 2026-10-13T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "在第六、十二、十八章后完成内存书单、文件记录器和批量本机 HTTP 客户端，按修改、补全和独立实现三档检查学习结果。"
summary = "在第六、十二、十八章后完成内存书单、文件记录器和批量本机 HTTP 客户端，按修改、补全和独立实现三档检查学习结果。"
tags = ["Rust", "练习", "项目验收"]
categories = ["programming"]
ShowToc = true
source_kind = "original"
article_type = "tutorial"
series = ["rust-from-zero"]
series_role = "exercise"
series_label = "分级练习与项目验收"
+++

这篇练习配合《Rust 从零开始》的第六、十二、十八章使用。每个阶段都有三档任务：修改现有程序、补全指定行为、根据需求从空文件实现一个小项目。

先试着完成当前阶段的练习，再展开答案。不必等到第十八章才开始；第六章后的书单只使用当时已经学过的数据类型、借用和分支。完成后记录自己在哪一步需要查正文，下一次重点重做那一步。

下载包的运行命令用于核对参考实现。自己练习时，用 `cargo new` 创建另一个项目，不要覆盖下载包里的旧答案或自己的任务文件。

## 第六章后：实现内存书单 {#after-ch06}

这一阶段检查能否组织结构体、枚举、列表和可变借用。程序只处理内存中的数据，不接终端输入，也不读写文件。

### 第一档：修改已有程序

从第六章的书籍练习开始，增加第三本书。只把第二本标记为已读，打印三本书的标题和状态，再给空列表调用同一个修改函数。

通过标准是：三本书都还在列表中，只有第二本已读，空列表不会 panic。先写下预计输出，再运行；如果直接用下标修改，想一想怎样先处理列表长度不足的情况。

### 第二档：按标题查找并修改

写 `finish_by_title(books: &mut [Book], title: &str) -> bool`。找到完全相同的标题就标记为已读并返回 `true`，没找到返回 `false`。对已经读完的同一本书再次调用，仍返回 `true`。

分别检查标题存在、标题不存在和列表为空这三种情况。这里只返回是否找到，不返回书籍引用，所以暂时不需要给两个参数标生命周期。

### 第三档：独立组织命令

从空 `main.rs` 实现一个书单程序。需求如下：

- `Book` 保存标题和是否已读。新增时去掉标题首尾空白；空标题和重复标题返回 `false`，列表不变。重复按去掉首尾空白后的文本判断，区分大小写。
- `Command` 有 `Add(String)`、`Finish(String)`、`List` 三种情况。完成命令按传入标题精确查找，不再自动去掉空白。
- 执行预先写好的命令列表：列出空书单，新增两本书，尝试重复新增，标记一本，再尝试标记不存在的书，最后列出全部。
- 新增和完成函数只借用列表；执行完命令后，调用方还能检查书籍数量和状态。

先让程序输出正确，再加入 `assert!` 检查失败操作没有增加书籍、没有把其他书标为已读。这里用布尔值报告结果；第七章学过 `Result` 后，可以再改为返回具体错误原因。

<details>
<summary>参考答案：内存书单</summary>

下面是可以放入自己项目 `src/main.rs` 的完整程序。下载包对应 `basics/examples/checkpoint06.rs`，还附有供第八章之后运行的单元测试。

```rust
struct Book {
    title: String,
    finished: bool,
}

enum Command {
    Add(String),
    Finish(String),
    List,
}

fn add_book(books: &mut Vec<Book>, title: &str) -> bool {
    let title = title.trim();
    if title.is_empty() {
        return false;
    }
    for book in books.iter() {
        if book.title == title {
            return false;
        }
    }
    books.push(Book {
        title: title.to_string(),
        finished: false,
    });
    true
}

fn finish_by_title(books: &mut [Book], title: &str) -> bool {
    for book in books {
        if book.title == title {
            book.finished = true;
            return true;
        }
    }
    false
}

fn apply(books: &mut Vec<Book>, command: &Command) {
    match command {
        Command::Add(title) => println!("新增成功：{}", add_book(books, title)),
        Command::Finish(title) => println!("标记成功：{}", finish_by_title(books, title)),
        Command::List => {
            if books.is_empty() {
                println!("还没有书");
            }
            for book in books {
                let state = if book.finished { "已读" } else { "未读" };
                println!("{}：{state}", book.title);
            }
        }
    }
}

fn main() {
    let mut books = Vec::new();
    let commands = [
        Command::List,
        Command::Add(String::from("Rust 入门")),
        Command::Add(String::from("写练习")),
        Command::Add(String::from("Rust 入门")),
        Command::Finish(String::from("Rust 入门")),
        Command::Finish(String::from("不存在")),
        Command::List,
    ];
    for command in &commands {
        apply(&mut books, command);
    }
    assert!(!add_book(&mut books, " "));
    assert_eq!(books.len(), 2);
    assert!(books[0].finished);
    assert!(!books[1].finished);
    assert!(!finish_by_title(&mut [], "Rust 入门"));
}
```

预期输出：

```text
还没有书
新增成功：true
新增成功：true
新增成功：false
标记成功：true
标记成功：false
Rust 入门：已读
写练习：未读
```

在下载包的 `rust-course` 目录运行：

```sh
cargo run -p rust-basics --example checkpoint06
```

`books.iter()` 临时共享借用列表，检查已有标题。循环结束后，函数才用 `push` 修改列表。`finish_by_title` 接收可变切片，可以改已有书籍的状态，但不能向切片增加书籍。

读完第八章后，再运行 `cargo test -p rust-basics --example checkpoint06`。三个测试检查新增拒绝条件、只修改目标书籍，以及空列表。

</details>

## 第十二章后：完成学习时长记录器 {#after-ch12}

这一阶段要把终端参数、`Result`、小函数和文件保存用到一起。换成学习时长这个数据模型，看看自己能否应用前十二章的知识。

### 第一档：确认当前程序在哪里读文件

先用第十二章的 `taskbook` 做一次练习：在两个独立目录分别运行同一个可执行程序，新增不同任务，再观察默认任务文件出现在哪里。

开始前写下预计路径。通过标准是能解释：项目清单在哪里、可执行文件在哪里、运行时的当前工作目录在哪里，以及相对数据路径以哪一个为起点。不要用修改别人的文件来验证路径。

### 第二档：先写文本转换函数

学习时长文件每行保存一个整数分钟数，例如 `25\n40\n`。写 `decode` 把文本转成列表，再写 `encode` 转回文本。

规则是每条记录在 1～1440 分钟之间；空文件表示零条记录，文件末尾的一次换行允许存在，中间空行无效。解析失败要指出行号。依次检查空文件、两条记录、0、1441、非数字和中间空行，先不要操作磁盘。

### 第三档：从参数到保存

从空项目完成下面的命令接口。示意中的路径要换成自己的练习文件：

```text
checkpoint12 minutes.txt add 25
checkpoint12 minutes.txt total
```

`add` 新增一条记录，`total` 打印累计分钟数。参数个数或分钟数无效时，在读取文件前报错。文件缺失视为空列表，但 `total` 不创建文件；已有文件损坏时，`add` 报错并保留原文件。

有效源文件必须是 UTF-8 文本。新增采用读取、解析、增加记录、重新编码、覆盖保存的顺序。本练习没有事务、文件锁和写入中断恢复；只能确认写入前拒绝的错误不会覆盖文件。

<details>
<summary>参考答案：学习时长记录器</summary>

下面是完整程序，可以放入自己项目的 `src/main.rs`。下载包对应 `basics/examples/checkpoint12.rs`，另附三个单元测试。

```rust
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

const USAGE: &str = "用法：checkpoint12 <文件> add <分钟数> | <文件> total";

enum Command {
    Add(u32),
    Total,
}

fn parse_minutes(input: &str) -> Result<u32, String> {
    let value = input
        .trim()
        .parse::<u32>()
        .map_err(|_| String::from("分钟数必须是整数"))?;
    validate_minutes(value)
}

fn validate_minutes(value: u32) -> Result<u32, String> {
    if !(1..=1440).contains(&value) {
        return Err(String::from("每条记录必须在 1～1440 分钟之间"));
    }
    Ok(value)
}

fn parse_args(args: &[String]) -> Result<(PathBuf, Command), String> {
    match args {
        [file, command, minutes] if command == "add" => {
            Ok((PathBuf::from(file), Command::Add(parse_minutes(minutes)?)))
        }
        [file, command] if command == "total" => Ok((PathBuf::from(file), Command::Total)),
        _ => Err(USAGE.to_string()),
    }
}

fn decode(input: &str) -> Result<Vec<u32>, String> {
    let mut records = Vec::new();
    for (index, line) in input.lines().enumerate() {
        let minutes =
            parse_minutes(line).map_err(|message| format!("第 {} 行：{message}", index + 1))?;
        records.push(minutes);
    }
    Ok(records)
}

fn encode(records: &[u32]) -> Result<String, String> {
    let mut output = String::new();
    for minutes in records {
        validate_minutes(*minutes)?;
        output.push_str(&format!("{minutes}\n"));
    }
    Ok(output)
}

fn load(path: &Path) -> Result<Vec<u32>, String> {
    match fs::read_to_string(path) {
        Ok(input) => decode(&input),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(Vec::new()),
        Err(error) => Err(format!("读取失败：{error}")),
    }
}

fn total(records: &[u32]) -> Result<u64, String> {
    let mut sum = 0_u64;
    for minutes in records {
        sum = sum
            .checked_add(u64::from(*minutes))
            .ok_or_else(|| String::from("总时长超出范围"))?;
    }
    Ok(sum)
}

fn run() -> Result<(), String> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let (path, command) = parse_args(&args)?;
    let mut records = load(&path)?;
    match command {
        Command::Add(minutes) => {
            records.push(minutes);
            let content = encode(&records)?;
            fs::write(&path, content).map_err(|error| format!("保存失败：{error}"))?;
            println!("已记录 {minutes} 分钟");
        }
        Command::Total => println!("累计 {} 分钟", total(&records)?),
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

`parse_args` 只接受两种完整参数形状，`parse_minutes` 和 `validate_minutes` 分别检查文本能否转成整数，以及整数是否在业务范围内。编码时也检查范围，防止调用者直接传入无效数字。

下面的演示在下载包 `rust-course` 中运行，适用于 macOS / Linux shell。使用一个此前不存在的练习目录：

```sh
mkdir checkpoint12-demo
cargo run -p rust-basics --example checkpoint12 -- checkpoint12-demo/minutes.txt total
cargo run -p rust-basics --example checkpoint12 -- checkpoint12-demo/minutes.txt add 25
cargo run -p rust-basics --example checkpoint12 -- checkpoint12-demo/minutes.txt add 40
cargo run -p rust-basics --example checkpoint12 -- checkpoint12-demo/minutes.txt total
```

忽略 Cargo 日志，输出：

```text
累计 0 分钟
已记录 25 分钟
已记录 40 分钟
累计 65 分钟
```

再制造一份专用的损坏数据，并比较运行前后的字节。以下命令只写刚才建立的练习目录：

```sh
printf '25\nbad\n' > checkpoint12-demo/broken.txt
cp checkpoint12-demo/broken.txt checkpoint12-demo/before.txt
cargo run -p rust-basics --example checkpoint12 -- checkpoint12-demo/broken.txt add 20
cmp checkpoint12-demo/before.txt checkpoint12-demo/broken.txt
```

新增命令应该失败，提示第二行无效；最后的 `cmp` 成功时没有输出。如果在自动脚本中启用了遇错退出，要为这条预期失败的命令单独处理退出码。

PowerShell 读者可以用文本编辑器在专用目录里建立同样的 UTF-8 文件，再运行 Cargo 命令；这里没有把 shell 的 `printf`、`cp`、`cmp` 写法当作 PowerShell 命令。

运行 `cargo test -p rust-basics --example checkpoint12`，检查文本往返、边界值、行号和参数形状。文件跨进程保存与损坏文件保留还需要运行上面的命令演示，不能仅凭内存转换测试下结论。

</details>

## 第十八章后：顺序读取多个本机服务 {#after-ch18}

这一阶段把参数解析和错误处理组合起来，不引入异步或线程。你需要会启动第十八章的一次性本机服务。

### 第一档：修改服务响应

把练习 JSON 的分钟数从 30 改成 45，重新运行服务，再用它新显示的端口请求一次。随后改成 0，检查 HTTP 200 为什么仍会触发数据错误。练习结束后恢复原来的响应文件。

通过标准是能指出：服务返回的状态码、JSON 字段类型和业务范围分别由哪一段代码检查。不要把响应格式变化归因于客户端是否连上服务器。

### 第二档：接到失败后继续处理

写一个循环，依次处理两份 `Result`：第一份失败，第二份成功。失败时记录错误，成功时打印数据，最后分别统计数量。

这一档先用手工构造的 `Result`，不需要网络。比较 `match` 和在循环里直接用 `?` 的控制流程；这次需求要求处理下一项，因此一次失败不能让整个函数提前返回。

### 第三档：批量客户端

从空示例文件实现 `checkpoint18`：接收 1～3 个本机端口，顺序调用已有的 `lesson_http::fetch`。不接受任意网址，也不使用公网服务。

每个成功响应打印端口、课程标题和分钟数；每个失败响应打印端口及原因。继续处理后面的端口，最后打印成功和失败数量。全部成功返回退出码 0，任一请求失败返回 1；参数无效由 clap 返回 2。

复用 `fetch` 时仍保留它的状态码、大小和数据检查。顺序请求没有引入整个批次的绝对截止时间；第十八章说明的阻塞读取超时边界也仍然适用。

<details>
<summary>参考答案：批量本机客户端</summary>

下面是 `projects/lesson-http/examples/checkpoint18.rs` 的完整内容。它依赖第十八章的库，不能只复制这个文件到没有依赖的新项目后直接编译。

```rust
use std::error::Error;
use std::process::ExitCode;

use clap::Parser;

#[derive(Parser)]
#[command(about = "顺序读取最多三个本机课程服务")]
struct Args {
    #[arg(long = "port", required = true, num_args = 1..=3,
        value_parser = clap::value_parser!(u16).range(1..))]
    ports: Vec<u16>,
}

fn main() -> ExitCode {
    let args = Args::parse();
    let mut succeeded = 0;
    let mut failed = 0;
    for port in args.ports {
        match lesson_http::fetch(port) {
            Ok(lesson) => {
                println!("端口 {port}：{}，{} 分钟", lesson.title, lesson.minutes);
                succeeded += 1;
            }
            Err(error) => {
                eprintln!("端口 {port} 请求失败：{error}");
                let mut cause = error.source();
                while let Some(source) = cause {
                    eprintln!("原因：{source}");
                    cause = source.source();
                }
                failed += 1;
            }
        }
    }
    println!("成功 {succeeded} 项，失败 {failed} 项");
    if failed == 0 {
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}
```

在同一台机器上打开三个终端，都进入 `rust-course/projects`。终端 A 启动 `cargo run -p lesson-http --example serve -- missing`，终端 B 启动 `cargo run -p lesson-http --example serve`。分别记下它们显示的实际端口。

终端 C 运行下面的命令，将两个示意数字换成 A 和 B 的端口，先传失败服务，再传成功服务：

```sh
cargo run -p lesson-http --example checkpoint18 -- --port 54321 54322
```

失败信息写到标准错误，成功信息和统计写到标准输出。成功的课程仍应该被打印，最后一行是：

```text
成功 1 项，失败 1 项
```

程序退出码为 1。两种输出流在终端上的显示顺序不应作为断言，测试应分别检查内容。

每个服务只接受一次连接，重试前要重新启动。再检查全部成功、全部失败、端口 0、缺少端口和超过三个端口的情况；参数错误不应发出请求。

</details>

## 怎样判断自己已经完成

先对照需求逐项检查，再回看答案。每次练习都保留自己写的源码、实际运行的输入，以及成功和失败的结果。结果不一致时，用[排错指南](/posts/rust-troubleshooting/)缩小问题范围。

如果某一档做不出来，回到对应章节重做最小例子，再回来继续。可以先完成第六章的内存书单，过几天换一个名称和数据重新实现；能解释每个参数的所有权，比记住答案的行数更有用。

这三份参考实现于 2026-10-13 在 macOS arm64、rustc 1.99.0、cargo 1.99.0 上验证。具体执行范围见[学习指南](/posts/rust-00-learning-guide/#版本与验证范围)，最低工具链和其他系统没有在本轮实测。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [学习指南](/posts/rust-00-learning-guide/) · [常见错误排查](/posts/rust-troubleshooting/)
