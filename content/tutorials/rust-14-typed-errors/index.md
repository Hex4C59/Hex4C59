+++
url = "/posts/rust-14-typed-errors/"
title = "Rust 入门 14：用自定义错误类型保留失败原因"
date = 2026-10-13T09:00:00+08:00
lastmod = 2026-10-17
draft = false
author = "Hex4C59"
description = "用枚举、Display、Error 和 From 区分输入与文件错误，通过问号传播，并在命令行显示原因链。"
summary = "用枚举、Display、Error 和 From 区分输入与文件错误，通过问号传播，并在命令行显示原因链。"
tags = ["Rust", "错误处理"]
categories = ["programming"]
series = ["rust-from-zero"]
series_order = 14
series_label = "自定义错误类型"
series_part = "继续完善项目"
series_number = 14
ShowToc = true
source_kind = "original"
article_type = "tutorial"
series_role = "chapter"
+++

第七章为了显示错误，把解析失败转换成了 `String`。第十三章继续沿用这个接口，也能把错误交给用户。但当调用方需要区分“文件打不开”“数字格式不对”“分钟数为 0”时，文本不便于让程序判断错误种类。

本章使用枚举保存错误种类和底层原因，再实现 `Display`、`Error` 和 `From`。你会用到第六章的枚举、第九章的 trait，以及第七章的 `?`。完整程序既可以接收一个分钟数，也可以从文件读取它；失败时给出类别、原因和失败退出状态。

## 先运行两个失败条件

本章命令都在下载包的 `rust-course/practice` 工作区执行。先按第十三章运行过 `cargo fetch --locked`，然后试：

```sh
cargo run -p error-lab -- 30
cargo run -p error-lab -- 0
cargo run -p error-lab -- abc
```

第一条输出 `已记录 30 分钟`。第二条失败，只输出：

```text
错误：分钟数必须大于 0
```

第三条也失败，但有两层信息：第一层是我们的分钟数错误，第二层是标准库整数解析器的原因。底层原因的具体措辞可能随工具链变化，不要让业务代码去匹配那段文本。

## 用枚举保留错误种类

本章项目位于 `practice/error-lab`。它的 `Cargo.toml` 没有第三方依赖，完整内容是：

```toml
[package]
name = "error-lab"
version = "0.1.0"
edition = "2024"
rust-version = "1.85"
publish = false
```

先写 `src/lib.rs`。下面是完整业务代码，测试会在后面追加：

```rust
use std::error::Error;
use std::fmt;
use std::fs;
use std::io;
use std::num::ParseIntError;
use std::path::Path;

#[derive(Debug)]
pub enum AppError {
    Io(io::Error),
    Number(ParseIntError),
    ZeroMinutes,
    Usage,
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(_) => write!(f, "无法读取分钟文件"),
            Self::Number(_) => write!(f, "分钟数不是有效的非负整数"),
            Self::ZeroMinutes => write!(f, "分钟数必须大于 0"),
            Self::Usage => write!(f, "用法：error-lab <分钟> | --file <文件路径>"),
        }
    }
}

impl Error for AppError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Io(error) => Some(error),
            Self::Number(error) => Some(error),
            Self::ZeroMinutes | Self::Usage => None,
        }
    }
}

impl From<io::Error> for AppError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

impl From<ParseIntError> for AppError {
    fn from(error: ParseIntError) -> Self {
        Self::Number(error)
    }
}

pub fn parse_minutes(input: &str) -> Result<u32, AppError> {
    let minutes = input.trim().parse::<u32>()?;
    if minutes == 0 {
        return Err(AppError::ZeroMinutes);
    }
    Ok(minutes)
}

pub fn read_minutes(path: &Path) -> Result<u32, AppError> {
    let content = fs::read_to_string(path)?;
    parse_minutes(&content)
}
```

`AppError::Number` 保存原来的 `ParseIntError`，`AppError::Io` 保存原来的 `io::Error`。调用方可以通过模式匹配分辨种类，也可以继续访问原错误。

`ZeroMinutes` 是业务校验失败：整数解析已经成功，但不满足“大于 0”的规则。它没有底层解析错误。`Usage` 则表示参数形式不符合这个演示程序的命令约定。

返回 `Result<u32, AppError>` 后，成功分支仍交出 `u32`，错误分支交出枚举。错误信息改用枚举组织，解析规则仍然相同。调用方可以直接匹配错误变体来决定下一步，无须从显示给人的句子里猜测失败原因；修改提示文字也不会改变错误属于哪一类。

## Display 决定给用户看的文本

`fmt::Display` 对应 `{}` 格式。`fmt` 方法收到格式化器，通过 `write!` 向它写入内容；这个过程不是直接写终端。

这里把每种错误显示成简短的类别说明，底层错误留给下一节的 `source()`。所以 `Number` 显示“分钟数不是有效的非负整数”，不会在这一层重复拼上解析器消息。

`#[derive(Debug)]` 提供 `{:?}` 调试格式。标准库的 `Error` trait 要求实现类型也能以 `Debug` 和 `Display` 格式化，所以只有派生 `Debug` 还不够。

方法签名中的 `Formatter<'_>` 使用可推断的生命周期参数。你先按这个标准库接口实现即可，不需要给自己的业务函数都加一遍相同标注。

## source 提供底层原因，不会自动打印

`Error::source()` 返回一个可选的底层错误引用。`Io`、`Number` 有原错误，所以返回 `Some`；两个业务变体没有下层原因，返回 `None`。

签名里的 `dyn Error` 表示通过统一接口借用某种错误，不要求所有底层错误具有同一个具体类型。返回引用仍关联当前错误对象的借用。这里的 `+ 'static` 约束底层错误类型不携带短期借用，并不让返回引用可以在当前错误被销毁后继续使用。

实现 `source` 之后，运行时不会自动多打印一行。显示整个原因链的代码仍要写在入口里。调用方也可以选择只显示类别，或把完整原因用于排查。

## From 让问号完成错误转换

`parse::<u32>()` 原本返回 `Result<u32, ParseIntError>`，而 `parse_minutes` 要返回 `Result<u32, AppError>`。`impl From<ParseIntError> for AppError` 给出这两个错误类型之间的转换，`?` 就能在失败时使用它。例如输入为 `30` 时，问号取出成功的数字，让函数继续检查是否为 0；输入为 `abc` 时，它把解析错误包装成 `AppError::Number` 并立即返回，后面的业务检查不再执行。

`fs::read_to_string` 的错误是 `io::Error`，对应另一份 `From` 实现。这里取回的是拥有内容的原错误，没有先变成字符串再丢掉结构。

`From::from` 做的是错误包装，不会处理失败或重试操作。遇到错误时，当前函数仍然提前返回。如果转换需要附加当前文件路径等上下文，使用 `map_err` 构造更具体的变体会更合适；`From` 只拿到被转换的错误本身。

可以在自己的副本里暂时移除 `From<ParseIntError>` 的实现，再运行 `cargo check -p error-lab`。应看到 `E0277`：函数使用了 `?`，却没有可用的错误转换。恢复实现后再检查。

## 接到 main.rs，逐层显示原因

`src/main.rs` 的完整内容：

```rust
use std::env;
use std::error::Error;
use std::path::Path;
use std::process::ExitCode;

use error_lab::{AppError, parse_minutes, read_minutes};

fn run() -> Result<(), AppError> {
    let args: Vec<String> = env::args().skip(1).collect();
    let minutes = match args.as_slice() {
        [input] if input != "--file" => parse_minutes(input)?,
        [flag, path] if flag == "--file" => read_minutes(Path::new(path))?,
        _ => return Err(AppError::Usage),
    };
    println!("已记录 {minutes} 分钟");
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

数字形式要求恰好一项参数；文件形式要求 `--file` 和文件路径两项。没有参数、单独输入 `--file` 或多余参数会得到用法错误。

`while let Some(cause) = source` 读取当前原因并继续往下找，直到没有下一层。循环中的引用来自仍然存活的 `error`。例如数字解析失败时，先由入口显示应用定义的错误类别，再由循环显示保留的解析错误；分钟数为 0 时没有下一层原因，循环一次也不执行。这里使用 `eprintln!`，所以错误内容进入标准错误通道，正常分钟数进入标准输出。

入口返回 `ExitCode::FAILURE` 才让 shell 知道命令失败。仅打印一句错误、然后正常返回，并不能提供这个状态。

## 从专用文件读取分钟数

在 macOS / Linux 的 `practice` 工作区执行：

```sh
error_practice_dir=$(mktemp -d)
printf ' 45\n' > "$error_practice_dir/minutes.txt"
cargo run -p error-lab -- --file "$error_practice_dir/minutes.txt"
cargo run -p error-lab -- --file "$error_practice_dir/missing.txt"
```

第三条输出 `已记录 45 分钟`；第四条失败，显示 `错误：无法读取分钟文件` 和操作系统给出的底层原因。这里只读取文件，不会创建这个缺失路径。

如果文件存在但内容是 `abc`，错误种类会是 `Number`；如果内容是 `0`，错误种类会是 `ZeroMinutes`。文件读取成功和内容有效是两次独立检查。

## 调用方怎样判断错误

配套示例 `error-lab/examples/inspect.rs` 的完整内容：

```rust
use error_lab::{AppError, parse_minutes};
use std::error::Error;

fn main() {
    for input in ["abc", "0"] {
        let error = parse_minutes(input).unwrap_err();
        let category = match &error {
            AppError::Number(_) => "数字格式错误",
            AppError::ZeroMinutes => "业务规则错误",
            _ => "其他错误",
        };
        println!(
            "{input}：{category}，有底层原因：{}",
            error.source().is_some()
        );
    }
}
```

运行：

```sh
cargo run -p error-lab --example inspect
```

输出：

```text
abc：数字格式错误，有底层原因：true
0：业务规则错误，有底层原因：false
```

示例中的 `unwrap_err()` 只用于检查两个确定应该失败的输入。如果函数意外返回成功，示例就会 panic，提醒你规则发生了变化。真实入口仍用 `match` 处理成功和失败。

`match &error` 借用错误，匹配之后还能访问同一个错误的 `source()`。判断错误时匹配变体，比把 `error.to_string()` 与某段中文做比较更可靠。

## 给错误路径写测试

把下面完整模块追加到 `src/lib.rs`，或查看下载包里的同一模块：

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_valid_minutes_and_distinguishes_failures() {
        assert!(matches!(parse_minutes(" 30 "), Ok(30)));
        assert!(matches!(parse_minutes("0"), Err(AppError::ZeroMinutes)));
        for input in ["abc", "-1", "4294967296", ""] {
            assert!(matches!(parse_minutes(input), Err(AppError::Number(_))));
        }
    }

    #[test]
    fn preserves_sources_for_lower_level_errors() {
        let number = parse_minutes("abc").unwrap_err();
        assert_eq!(number.to_string(), "分钟数不是有效的非负整数");
        assert!(number.source().is_some());
        assert!(parse_minutes("0").unwrap_err().source().is_none());
        let io = AppError::from(io::Error::from(io::ErrorKind::NotFound));
        assert!(matches!(io, AppError::Io(_)));
        assert!(io.source().is_some());
    }
}
```

在 `practice` 工作区运行：

```sh
cargo test -p error-lab --lib
cargo test -p error-lab --test cli
```

库测试检查 0、无效文本、负数、超范围数字和空文本，并确认底层原因是否保留。这里用 `matches!` 检查枚举种类，没有要求标准库的 I/O 错误实现内容相等比较。

CLI 测试则检查数字和文件入口、标准输出、标准错误与失败状态。它们使用自己的临时目录；不会依赖或改写你手动创建的分钟文件。

## 练习：给一天的分钟数设置上限

让 `parse_minutes` 拒绝超过 1440 的分钟数，新增 `TooLong(u32)` 变体。保留 0 的检查和底层数字错误。上限检查要放在数字解析成功之后：能表示为 `u32` 但超过一天的值属于新业务错误，连 `u32` 都容纳不了的数字仍属于原来的解析错误。

要求 `1440` 成功，`1441` 返回 `TooLong(1441)`，显示 `一天最多记录 1440 分钟，收到 1441`，并且没有底层原因。

<details>
<summary>参考答案：先自己完成再展开</summary>

需要修改四处。下面三个代码块是局部插入片段，不能单独运行。

先在 `AppError` 枚举中增加变体：

```rust
TooLong(u32),
```

在 `Display` 的匹配中增加一个分支：

```rust
Self::TooLong(value) => write!(f, "一天最多记录 1440 分钟，收到 {value}"),
```

在 `parse_minutes` 的 `Ok(minutes)` 之前增加检查：

```rust
if minutes > 1440 {
    return Err(AppError::TooLong(minutes));
}
```

第四处是 `source()`：将返回 `None` 的分支改为同时覆盖 `Self::ZeroMinutes | Self::Usage | Self::TooLong(_)`。枚举新增变体后，每个穷尽匹配都要检查，编译器会指出遗漏。

将下面完整测试函数加入已有的 `mod tests`：

```rust
#[test]
fn rejects_minutes_beyond_one_day() {
    assert!(matches!(parse_minutes("1440"), Ok(1440)));
    let error = parse_minutes("1441").unwrap_err();
    assert!(matches!(error, AppError::TooLong(1441)));
    assert_eq!(error.to_string(), "一天最多记录 1440 分钟，收到 1441");
    assert!(error.source().is_none());
}
```

下载包保留未加入上限的本章主版本。完成练习后，你自己的库应有 3 个测试。

</details>

## 官方延伸阅读

- [Error trait 和 source](https://doc.rust-lang.org/std/error/trait.Error.html)
- [Display](https://doc.rust-lang.org/std/fmt/trait.Display.html)
- [From](https://doc.rust-lang.org/std/convert/trait.From.html)
- [Result 和问号传播](https://doc.rust-lang.org/book/ch09-02-recoverable-errors-with-result.html)

外部文档查阅日期：2026-10-13。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：筛选、搜索与删除](/posts/rust-13-taskbook-plus/) · [下一章：Serde 与 JSON 保存](/posts/rust-15-serde-json/)
