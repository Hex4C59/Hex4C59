+++
title = "Rust 入门附录：从报错位置找到问题"
date = 2026-10-13T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "按工具、工作区、编译和运行阶段排查常见问题，重现移动、借用和生命周期错误，并检查依赖、文件路径及本机 HTTP 服务。"
summary = "按工具、工作区、编译和运行阶段排查常见问题，重现移动、借用和生命周期错误，并检查依赖、文件路径及本机 HTTP 服务。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
ShowToc = true
+++

遇到 Rust 报错时，先判断它发生在哪一步：终端没有找到工具，Cargo 没有找到项目，编译器拒绝代码，还是程序已经启动但操作失败。不同阶段需要检查的东西不同。

这篇指南供《Rust 从零开始》的读者查阅，不必一次读完。先按现象找到对应小节，保留第一条完整错误，再用一个最小例子确认原因。代码中的错误文字可能随编译器和操作系统变化，错误编号和指向的位置更适合定位。

## 找不到 rustc 或 cargo {#toolchain}

在终端分别运行：

```sh
rustc --version
cargo --version
```

如果终端说命令不存在，先确认 Rust 是否已经安装，再重新打开终端，查看安装器的 PATH 提示。PATH 是终端搜索程序的目录列表；在编辑器里打开项目，不等于终端能找到工具。

macOS / Linux 可运行 `command -v cargo` 查看命令路径；PowerShell 使用 `Get-Command cargo`。如果能显示版本，就先处理后面的实际错误，不必因为一个编译失败重新安装整套工具。

缺少链接器时，错误通常出现在构建阶段，而不是找不到 Cargo。这种情况回到[第一章的安装说明](/posts/rust-01-setup/#12-先检查工具是否已经安装)，按当前系统准备构建工具。本文不替读者修改全局 PATH 或重新执行安装步骤。

## Cargo 找不到项目，或者找不到包 {#working-directory}

看到 `could not find Cargo.toml`，先检查当前工作目录。macOS / Linux 用 `pwd`，PowerShell 用 `Get-Location`。确认终端进入了包含清单的项目或其子目录。

看到包名没有匹配，检查自己在哪一个工作区。下载包目前有三个独立工作区：

| 目录 | 主要包 | 对应章节 |
| --- | --- | --- |
| `rust-course` | `rust-basics`、`taskbook` | 第 1～12 章及前两个阶段练习 |
| `rust-course/practice` | `taskbook-plus`、`error-lab`、`taskbook-json` | 第 13～15 章 |
| `rust-course/projects` | `taskbook-backup`、`taskbook-cli`、`lesson-http` | 第 16～18 章及 HTTP 阶段练习 |

`-p` 从选中的工作区找包，不会因为下载包里有一个同名目录就自动切换过去。先进入正确目录，也可以显式选择清单。在 `rust-course` 中运行：

```sh
cargo run --manifest-path projects/Cargo.toml -p taskbook-cli -- --help
```

`--manifest-path` 选择清单，不会把运行时的当前工作目录改成清单所在目录。上面的命令只显示帮助；运行数据命令时，相对文件路径仍以启动命令的目录为起点。

## 修改了代码，输出却没变 {#unchanged-output}

依次检查文件是否保存、编辑器和终端是否指向同一个项目，以及实际运行的是哪个目标。教材下载包使用 `--example` 选择示例，自己的新项目通常运行 `src/main.rs`。

例如在下载包外层运行 `cargo run -p rust-basics --example ch01_hello`，不会执行你另一个 `hello-rust` 项目的 `main.rs`。命令中写错包或示例，比构建缓存异常更值得先检查。

阅读 Cargo 输出里的目标名称，必要时在自己的程序中临时增加一句容易辨认的文本，再运行确认。定位完成后移除这句调试输出。不要先用清理整个工作区或覆盖源文件来猜问题。

## E0382：移动后又使用旧绑定 {#moved-value}

下面是故意不能编译的完整程序，下载包中保存为 `compile-fail/support-move.rs`：

```rust
fn main() {
    let title = String::from("学习 Rust");
    let moved = title;
    println!("{title} / {moved}");
}
```

`String` 从 `title` 移动给 `moved` 后，旧绑定不能再用于打印。先明确程序是否需要保留两份独立文本。如果只需要打印转移后的文本，使用现在拥有它的变量即可：

```rust
fn main() {
    let title = String::from("学习 Rust");
    let moved = title;
    println!("{moved}");
}
```

输出 `学习 Rust`。如果函数只需要读取标题，可以改为借用；如果确实需要独立副本，才考虑 `clone`。先检查数据之后由谁使用，不要在每个报错位置都加一次复制。完整解释见[第四章](/posts/rust-04-ownership/)。

## E0502：共享借用之后还要使用，却先修改了原值 {#borrow-conflict}

故意不能编译的完整程序，对应 `compile-fail/support-borrow.rs`：

```rust
fn main() {
    let mut title = String::from("学习 Rust");
    let view = &title;
    title.push('!');
    println!("{view}");
}
```

`view` 后面还要用于打印，这时先修改同一字符串会发生借用冲突。如果只是想先打印原内容，再追加感叹号，可以调整操作顺序：

```rust
fn main() {
    let mut title = String::from("学习 Rust");
    let view = &title;
    println!("{view}");
    title.push('!');
    println!("{title}");
}
```

输出依次是 `学习 Rust` 和 `学习 Rust!`。这里 `view` 最后一次使用在修改之前，编译器能结束相关借用检查；不要求为了这个例子手动调用 `drop`。

调整顺序只适合行为允许的情况。若确实要同时保留修改前的独立内容，需要另行创建副本，并说明复制的用途。

## E0597：引用指向的值不再有效 {#lifetime}

故意不能编译的完整程序，对应 `compile-fail/support-lifetime.rs`：

```rust
fn main() {
    let view;
    {
        let title = String::from("学习 Rust");
        view = title.as_str();
    }
    println!("{view}");
}
```

`title` 在内层作用域结束时被销毁，外层仍想通过 `view` 打印它。生命周期标注无法延长这个局部值的存活时间。

如果外层需要借用这份文本，就把所有者放到足够长的作用域：

```rust
fn main() {
    let title = String::from("学习 Rust");
    let view;
    {
        view = title.as_str();
    }
    println!("{view}");
}
```

输出 `学习 Rust`。如果文本在函数里创建，并需要交给调用方持有，通常应返回拥有文本的 `String`。第九章用[生命周期图解](/posts/rust-09-traits/#生命周期描述引用之间的关系)解释引用与输入的关系。

## 类型、trait 和问号相关错误 {#types-and-traits}

遇到这类错误，先对照编译器指出的期望类型和实际类型，再检查函数签名。

| 现象 | 优先检查 | 回到哪一章 |
| --- | --- | --- |
| E0308，类型不匹配 | 返回值是否多了分号，是否把文本当作数字，两个分支是否返回兼容类型 | 第 2、3 章 |
| E0106，缺少生命周期说明 | 多个输入引用与返回引用是什么关系；是否其实应该返回拥有的数据 | 第 9 章 |
| E0277，缺少某个 trait 实现 | 用了哪个操作，它要求什么能力，泛型约束或错误转换是否齐全 | 第 9、14 章 |
| 使用 `?` 后无法编译 | 当前函数能否返回对应结果，底层错误能否转换成返回的错误类型 | 第 7、14 章 |

`?` 不会把任意错误自动变成任意类型。先确定调用表达式的错误类型，再检查外层 `Result` 的错误类型；需要时使用 `map_err` 或适当的 `From` 实现。具体写法见[第十四章](/posts/rust-14-typed-errors/#from-让问号完成错误转换)。

在 `rust-course` 中可以单独运行这些诊断命令。前三条编译命令应该失败：

```sh
rustc --edition 2024 --emit=metadata compile-fail/support-move.rs
rustc --edition 2024 --emit=metadata compile-fail/support-borrow.rs
rustc --edition 2024 --emit=metadata compile-fail/support-lifetime.rs
rustc --explain E0382
rustc --explain E0502
rustc --explain E0597
```

这些文件没有加入 Cargo 的正常目标。不要为了让工作区构建通过而删除它们，也不要把故意失败的代码搬进正常入口后忘记恢复。

## 依赖无法获取，或者离线构建缺少包 {#dependencies}

第一次运行第三方依赖项目，Cargo 需要取得依赖。先在正文指定的工作区运行 `cargo fetch --locked`；获取完成后，再使用 `--offline`。

如果离线模式提示找不到某个包，先检查这个工作区的依赖是否已经获取。基础工作区只使用标准库和本地包，后两个工作区包含 Serde、clap 或 reqwest；在外层测试成功不代表另一个工作区的依赖也已经就绪。

网络、代理或镜像错误要根据实际错误和自己的环境检查。不要为了消除下载提示随意删除 `Cargo.lock` 或改变依赖版本，那会让教材固定的依赖选择发生变化。

## 程序启动后，文件或 HTTP 操作失败 {#runtime}

先看程序自己的标准错误，再判断文件路径、数据内容和服务状态。

- 任务突然像是空的：确认当前目录和实际文件选项。`taskbook`、`taskbook-plus` 使用 TSV，`taskbook-json` 使用 `TASKBOOK_JSON_FILE`，`taskbook-cli` 使用 `--file`，不要混用路径接口。
- JSON 无法读取：检查文件是否完整、版本和字段类型是否正确。保留原文件，再在新的练习副本中检查；空文件不等于有效的空任务 JSON。
- 备份或恢复报告目标已存在：这是第十六章的拒绝覆盖行为。先检查目标内容，再选择新路径；不要为了让命令成功直接删除原数据。
- 本机 HTTP 连接失败：确认服务和客户端在同一台机器上，使用的是服务刚打印的端口。一次性服务响应后会退出，下次请求前需要重新启动。
- 收到 404、JSON 错误或数据错误：分别检查请求资源、响应结构和业务字段。收到 HTTP 200 后仍需解析与校验，见[第十八章](/posts/rust-18-http/#把失败条件逐项试出来)。

成功信息通常写到标准输出，失败信息写到标准错误。需要检查退出码时，macOS / Linux shell 在程序结束后立即运行 `echo $?`，PowerShell 查看 `$LASTEXITCODE`；在执行另一条程序命令之后再看，可能已经不是上一次的结果。

## 把问题缩小后再继续 {#minimal-example}

记录运行目录、完整命令、第一条错误和相关的最小代码。确认程序输入和失败位置后，一次只改一个条件：修正路径、补齐类型，或者调整借用的使用顺序。每次修改都重新检查。

可以用 `cargo check` 检查编译，再用正文命令运行程序；检查通过不表示输出和文件行为已经正确。需要自查项目行为时，使用[分级练习](/posts/rust-practice-checkpoints/)列出的成功与失败条件。

本文的三个故意编译失败案例与三个修正版于 2026-10-13 在 macOS arm64、rustc 1.99.0 上验证。工具安装、最低 Rust 版本和其他系统没有在本轮重新验证。

## 官方延伸阅读

- [Rust 错误编号索引](https://doc.rust-lang.org/error_codes/error-index.html)
- [所有权](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html)
- [引用与借用](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html)
- [生命周期](https://doc.rust-lang.org/book/ch10-03-lifetime-syntax.html)
- [Cargo run 的工作目录说明](https://doc.rust-lang.org/cargo/commands/cargo-run.html#description)
- [Cargo fetch 与锁文件选项](https://doc.rust-lang.org/cargo/commands/cargo-fetch.html)

外部文档查阅日期：2026-10-13。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [学习指南](/posts/rust-00-learning-guide/) · [分级练习](/posts/rust-practice-checkpoints/)
