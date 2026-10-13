+++
url = "/posts/rust-01-setup/"
title = "Rust 入门 01：安装工具，运行第一个程序"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "认识终端、Rust 编译器和 Cargo，创建项目，运行并修改第一个 Rust 程序。"
summary = "认识终端、Rust 编译器和 Cargo，创建项目，运行并修改第一个 Rust 程序。"
tags = ["Rust", "Cargo", "开发环境"]
categories = ["programming"]
series = ["rust-from-zero"]
series_order = 1
series_label = "安装与第一个程序"
series_part = "把程序写出来"
series_number = 1
ShowToc = true
source_kind = "original"
article_type = "tutorial"
series_role = "chapter"
+++

这一节会带你安装工具，创建一个能反复修改、检查和运行的 Rust 项目。你不需要会写代码，但要能打开终端、创建文件夹，用文本编辑器保存文件。后面两节继续用这个项目练习。

先让终端显示下面两行文字，再换成你自己想说的内容。

```text
你好，Rust！
我正在学习编程。
```

## 1.1 我们写的代码怎样变成程序

你写在 `.rs` 文件里的代码叫源代码。Rust 编译器先检查语法和类型，再把符合要求的代码编译成目标平台的程序。编译成功后，再运行程序，观察结果。

学习时要分清两类问题：代码没能通过编译，或程序能运行，结果却不符合预期。前者需要读编译器的错误提示，后者需要检查程序逻辑。后面会分别练习。

你会使用这三个工具：

| 工具 | 在学习中负责什么 |
| --- | --- |
| `rustup` | 安装和管理 Rust 工具链 |
| `rustc` | 编译 Rust 源代码 |
| `cargo` | 创建项目，组织构建、运行和测试等操作 |

工具链就是编译和构建程序所需的一组工具。平时大多数操作交给 `cargo` 即可，它会调用编译器，不必每次手动运行 `rustc`。

## 1.2 先检查工具是否已经安装

macOS 打开“终端”，Windows 可以打开 PowerShell，Linux 打开系统终端。先分别输入：

```sh
rustc --version
cargo --version
```

每输入一行，按一次回车。如果两条命令都能显示版本，就先跳过安装步骤。教材的配套项目使用 Rust 2024 edition，需要 Rust 1.85 或更新的工具链。edition 指语言兼容规则的版本，与编译器的发布版本是两个概念。

代码块左上角的 `sh` 表示终端命令，`rust` 表示 Rust 源代码，`text` 表示输出或目录示意。不要把 Rust 代码直接粘到终端里。终端自己显示的 `%`、`$` 或 `>` 提示符也不用输入。

如果终端提示 `command not found` 或“无法识别”，再安装工具。

### macOS 和 Linux

按照 [Rust 官方安装页](https://rust-lang.org/tools/install/) 的说明安装 rustup。官方提供的命令是：

```sh
curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | sh
```

它从官方地址下载脚本并执行，需要联网。可以先在浏览器查看脚本内容，再按安装器的提示操作。安装后重新打开终端，检查前面的两条版本命令。

生成可执行程序还需要链接器，它把编译产物组合成最终程序。macOS 通常由 Xcode 或 Command Line Tools 提供；如果缺少开发工具，可以运行：

```sh
xcode-select --install
```

Linux 按发行版的说明准备 GCC 或 Clang；Ubuntu 常用 `build-essential`。已经安装的工具不需要重复安装。

### Windows

从同一个官方安装页下载 Windows 安装器，按提示安装。安装过程中可能需要 Visual Studio C++ 构建工具，它提供链接器和相关库。完成后重新打开 PowerShell，检查 `rustc --version` 和 `cargo --version`。

安装后仍找不到命令，就先检查安装器给出的 PATH 提示。PATH 是终端查找程序时搜索的目录列表，暂时不必为此大幅修改系统配置。

## 1.3 创建项目，确认自己在哪个目录

终端执行命令时有一个“当前工作目录”。命令通常从这里开始寻找文件，所以运行前要确认自己在哪个目录。

在你准备存放练习的目录中，依次运行：

```sh
cargo new hello-rust --edition 2024
cd hello-rust
cargo run
```

每一行的意思是：

1. 创建名为 `hello-rust` 的新项目目录，并采用 2024 edition。
2. 通过 `cd` 进入这个目录。
3. 构建并运行这个项目。

如果第一条提示同名目录已存在，可以进入之前创建的练习项目，也可以换一个项目名称。不要把其他项目的目录当成空目录覆盖。

运行成功后，终端会显示一些构建信息，程序本身输出：

```text
Hello, world!
```

`Compiling`、`Finished` 和 `Running` 等提示来自 Cargo；`Hello, world!` 来自你的程序。第二次运行时，如果代码没有变化，Cargo 通常会复用已有构建结果。

如果看到 `could not find Cargo.toml`，说明 Cargo 没在当前目录及其父目录中找到项目清单。先检查是否执行过 `cd hello-rust`。macOS / Linux 用 `pwd` 查看当前目录，PowerShell 用 `Get-Location`。

## 1.4 认识项目里的几个文件

初始项目的关键文件如下：

```text
hello-rust/
├── Cargo.toml
└── src/
    └── main.rs
```

`Cargo.toml` 是项目清单，记录项目名称、版本、edition 和依赖。新建项目通常会有类似内容：

```toml
[package]
name = "hello-rust"
version = "0.1.0"
edition = "2024"

[dependencies]
```

这里的 `[dependencies]` 是空的，尚未声明第三方依赖。这三节只使用 Rust 标准库和基本语言功能。

`src/main.rs` 是这个可执行程序的入口源码。用编辑器打开整个 `hello-rust` 文件夹，再找到它。不要把代码保存成 `main.rs.txt`，也不要用带字体、颜色等格式的富文本文件代替源代码。

首次构建后还会有：

- `Cargo.lock`：记录依赖解析结果，通常交给 Cargo 管理。
- `target/`：存放构建产物，不是你日常编辑的源码目录。

现在主要修改 `src/main.rs` 即可。

## 1.5 修改第一个程序

把 `src/main.rs` 完整替换成：

```rust
fn main() {
    println!("你好，Rust！");
    println!("我正在学习编程。");
}
```

保存文件，再在 `hello-rust` 目录运行：

```sh
cargo run
```

预期输出：

```text
你好，Rust！
我正在学习编程。
```

如果仍然显示 `Hello, world!`，先检查是否保存了文件，再确认编辑器和终端指向的是同一个项目。如果运行的是另一个项目，重装工具也解决不了问题。

这段代码中，各个符号的含义如下：

| 写法 | 作用 |
| --- | --- |
| `fn` | 声明一个函数 |
| `main` | 这个可执行程序的入口函数名 |
| `()` | 函数参数的位置，这里没有参数 |
| `{ ... }` | 函数体，包含它要执行的代码 |
| `println!(...)` | 打印内容，并在末尾换行 |
| `"你好，Rust！"` | 用双引号写出的字符串文本 |
| `;` | 结束当前这条语句 |

末尾带 `!` 的 `println!` 是一个宏。宏可以在编译时展开成代码；目前先学会调用它，不需要自己写宏。

程序从 `main` 的第一条语句开始依次执行，因此两行文字按代码中的顺序打印。缩进通常使用四个空格，方便阅读；函数体的范围由花括号界定。

## 1.6 亲手做三个小实验

这几个实验只改已有代码，不需要新语法。

把第一条 `println!` 中的文本换成一句问候，运行后确认变化。再交换两条语句的位置，观察输出顺序。最后增加第三条 `println!`，打印今天的学习目标。

你还可以加入注释。下面是可以直接替换 `main.rs` 的完整程序：

```rust
fn main() {
    // 这一行是注释，不会打印到终端。
    println!("今天开始学习 Rust。");
    println!("目标：独立修改并运行一个程序。");
}
```

`//` 后面直到本行结束的内容是注释，用来向读代码的人解释意图，不会打印到终端。

代码语法使用英文引号、括号和分号。字符串内部可以使用中文文字和标点；字符串外的 `（`、`；` 不能代替代码中的 `(`、`;`。

## 1.7 让编译器指出一次错误

在一条打印语句中，暂时删除字符串末尾的双引号，保存并运行 `cargo check`。编译器应报告字符串或相关语法有误。再补回引号，重新检查。

通过这次实验，练习“改动 → 检查 → 根据位置修复”的过程。报错通常包含：

- `error` 和原因说明。
- 文件路径、行号、列号。
- 用下划线或箭头标出的相关代码。
- 有时还会给出 `help` 建议。

先修复第一条错误，再重新检查。缺失的引号可能让编译器误读后面的多行代码，不必一次处理所有后续报错。`warning` 是警告，通常不阻止构建，读懂原因后也应处理。

## 1.8 记住四个常用命令

以下命令在自己的 `hello-rust` 项目目录运行：

| 命令 | 何时使用 |
| --- | --- |
| `cargo check` | 修改后先检查代码，不生成最终可执行文件 |
| `cargo run` | 想运行程序、观察结果时 |
| `cargo fmt` | 整理 Rust 代码格式时 |
| `cargo build --release` | 后面需要生成 release 构建时 |

`cargo build` 只构建，不运行。现阶段主要按“修改、保存、`cargo run`”的顺序练习；代码复杂一些后，可以先用 `cargo check` 检查。

如果使用教材下载包，在解压后的 `rust-course` 目录运行这个示例：

```sh
cargo run -p rust-basics --example ch01_hello
```

`-p rust-basics` 选择包，`--example ch01_hello` 选择示例。这是下载包的运行方式，与自己的 `hello-rust` 项目不同；后面默认继续在自己的项目中替换 `main.rs`。

## 1.9 练习：写一个自我介绍程序

独立写出三条打印语句，依次介绍一个虚构姓名、正在学习的语言和今天的目标。给其中一条语句加上注释，再运行确认输出。

<details>
<summary>参考答案：先自己完成再展开</summary>

```rust
fn main() {
    println!("我叫小林。");
    println!("我正在学习 Rust。");
    // 把今天要完成的动作写具体。
    println!("今天的目标：修改代码，保存文件，再运行一次。");
}
```

应看到三行文字，注释内容不会出现。把三条语句换一个顺序后，输出也应该跟着改变。

</details>

## 1.10 进入下一节前检查

关掉示例，自己完成一次：打开项目，找到 `src/main.rs`，修改文字，保存并运行，再指出终端里哪些内容由程序打印。

还应能回答：`Cargo.toml` 与 `main.rs` 分别做什么？`cargo check` 和 `cargo run` 有什么区别？为什么命令需要在项目目录里运行？

完成这些操作后，下一节就可以给程序加入变量和计算。

## 官方延伸阅读与验证

- [Rust 官方安装说明](https://doc.rust-lang.org/book/ch01-01-installation.html)
- [使用 Cargo 创建项目](https://doc.rust-lang.org/book/ch01-03-hello-cargo.html)

文档查阅与示例复核日期：2026-10-13。正文完整程序在 macOS arm64、Rust 1.99.0、Cargo 1.99.0 上运行验证；本次没有在全新机器上重新执行安装流程。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：学习指南](/posts/rust-00-learning-guide/) · [下一章：变量与类型](/posts/rust-02-variables/)
