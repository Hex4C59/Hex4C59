+++
title = "Rust 入门 08：拆分模块，为程序写测试"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-12T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "区分 package、crate 和 module，把代码拆到 lib.rs 与模块文件，编写单元测试、集成测试和文档测试。"
summary = "区分 package、crate 和 module，把代码拆到 lib.rs 与模块文件，编写单元测试、集成测试和文档测试。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 8
series_label = "模块与测试"
series_part = "写出可维护的程序"
series_number = 8
ShowToc = true
+++

当一个程序包含输入、计算和文件读写时，把所有内容放在 `main.rs` 会越来越难修改。本章将温度转换逻辑放到独立模块，并写测试固定它的行为。

## 先区分 package、crate 和 module

| 名称 | 本章中的意思 |
| --- | --- |
| package（包） | 由一个 `Cargo.toml` 管理的一组目标和配置 |
| crate | Rust 的编译单元，例如一个库或一个可执行程序 |
| module（模块） | crate 内组织名称、代码和可见性的边界 |
| workspace（工作区） | 由一个顶层清单统一管理的多个包 |

配套源码的顶层 `Cargo.toml` 是工作区。`basics` 和 `taskbook` 是两个包；`basics/src/lib.rs` 是库 crate 的入口；`math` 是库里的模块。

一个包可以同时有库和可执行程序。常见做法是把可复用、可测试的逻辑放进 `lib.rs`，`main.rs` 只负责接收输入和调用逻辑。最后两章会采用这个结构。

## 从三个文件开始

以下文件都相对于配套源码的 `basics` 目录。`Cargo.toml` 已把包命名为 `rust-basics`，因此 Rust 代码中引用库时使用 `rust_basics`。连字符与下划线的区别容易在第一次写 `use` 时造成困惑。

`src/lib.rs` 的完整内容：

```rust
pub mod math;
```

`pub mod math;` 声明一个公开模块，并让编译器从对应的 `math.rs` 或模块目录中读取代码。仅在硬盘上创建文件，不会自动让它成为模块。

`src/math.rs` 的完整内容：

```rust
/// 把摄氏温度转换为华氏温度。
///
/// ```
/// assert_eq!(rust_basics::math::celsius_to_fahrenheit(0.0), 32.0);
/// ```
pub fn celsius_to_fahrenheit(celsius: f64) -> f64 {
    celsius * 1.8 + 32.0
}

#[cfg(test)]
mod tests {
    use super::celsius_to_fahrenheit;

    #[test]
    fn freezing_point() {
        assert!((celsius_to_fahrenheit(0.0) - 32.0).abs() < 1e-10);
    }

    #[test]
    fn negative_temperature() {
        assert!((celsius_to_fahrenheit(-40.0) + 40.0).abs() < 1e-10);
    }
}
```

`pub fn` 允许模块外的调用方访问这个函数。Rust 默认限制很多条目的可见性；需要成为外部接口的条目再显式公开。`use` 用来把已有路径中的名称引入当前位置，不会自动加载一个未声明的模块。

运行调用它的示例：

```sh
cargo run -p rust-basics --example ch08_modules
```

`basics/examples/ch08_modules.rs` 的完整内容：

```rust
use rust_basics::math::celsius_to_fahrenheit;

fn main() {
    let fahrenheit = celsius_to_fahrenheit(25.0);
    println!("25 摄氏度 = {fahrenheit} 华氏度");
}
```

预期输出 `25 摄氏度 = 77 华氏度`。这个示例依赖上面的库模块，不能单独复制到一个没有 `rust_basics` 库的新项目后直接运行。

如果想从头创建自己的库，先在工作区之外运行 `cargo new temperature --lib --edition 2024`，再按相同方式创建模块。此时包名是 `temperature`，调用路径也需要换成 `temperature::math::...`。

## 单元测试：在模块附近检查行为

`#[test]` 标记测试函数。`cargo test` 会寻找并运行它们。`#[cfg(test)]` 表示这段代码只在构建测试时启用，因此 `tests` 模块不会作为正常业务接口发布。

`use super::celsius_to_fahrenheit` 从父模块引入待测函数。冻结点、负温度是不同的输入条件，能检查公式是否写对。

浮点数会有表示和运算误差。测试里用 `(actual - expected).abs() < 1e-10` 检查差值是否足够小，而不是对任意浮点运算都使用精确相等。这里的容差是为这些简单输入选择的测试标准，并非适合所有数值问题。

运行：

```sh
cargo test -p rust-basics --lib
```

应看到两个测试通过。试着把公式中的 `32.0` 改成 `30.0`，重新运行，确认测试失败，再改回来。测试失败说明检查发挥了作用。

## 集成测试：通过公开接口调用

`basics/tests/conversion.rs` 是完整的集成测试文件：

```rust
use rust_basics::math::celsius_to_fahrenheit;

#[test]
fn boiling_point_through_public_api() {
    assert!((celsius_to_fahrenheit(100.0) - 212.0).abs() < 1e-10);
}
```

它从库外部使用公开路径，不能依赖库的私有函数。运行 `cargo test -p rust-basics --test conversion`，应有一个测试通过。这类测试能发现公开接口无法使用或接线错误。

## 文档测试：让示例也参与检查

`///` 是文档注释，`math.rs` 中的 Rust 代码块也是一个可执行的使用示例。`cargo test -p rust-basics --doc` 会运行它。这样函数行为改变时，旧用法更容易被发现。

运行整个配套源码的验证命令：

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
cargo test --workspace --all-targets
```

`cargo fmt` 统一格式；`--check` 只检查是否已经符合格式。Clippy 检查常见问题；这里将警告当作失败。第一条 `cargo test` 包括库文档测试，第二条把示例等所有目标也纳入检查。构建一个示例不等于已经执行它的 `main`，观察输出仍需 `cargo run --example ...`。

## 外部依赖先知道放在哪里

第三方库通常记录在 `Cargo.toml` 的 `[dependencies]` 下，由 Cargo 下载、构建和连接。一个常见安装命令是 `cargo add 库名`，其中“库名”必须换成实际依赖名称；这不是本章需要执行的步骤。

本教材项目只使用标准库。能完成基础项目后，再按照需要引入命令行解析、序列化和网络库，并查阅对应版本的官方文档。可执行程序通常应保留 `Cargo.lock`，让依赖选择更容易复现。

## 练习：增加一个测试

在 `math.rs` 的测试模块里，检查 25 摄氏度等于 77 华氏度。先写测试，再把公式改错，确认测试能发现问题，最后恢复正确公式。

<details>
<summary>参考答案：先自己完成再展开</summary>

把下面这个完整测试函数放到已有的 `mod tests { ... }` 内：

```rust
#[test]
fn room_temperature() {
    let actual = celsius_to_fahrenheit(25.0);
    assert!((actual - 77.0).abs() < 1e-10);
}
```

运行 `cargo test -p rust-basics --lib`，新增后应有三个单元测试通过。如果是原始下载包，没有添加这个练习，库里仍是两个测试。

</details>

## 官方延伸阅读

- [包与 crate](https://doc.rust-lang.org/book/ch07-01-packages-and-crates.html)
- [测试的组织](https://doc.rust-lang.org/book/ch11-03-test-organization.html)
- [Cargo 工作区](https://doc.rust-lang.org/book/ch14-03-cargo-workspaces.html)

外部文档查阅日期：2026-10-12。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：输入与错误处理](/posts/rust-07-errors/) · [下一章：泛型、trait 与生命周期](/posts/rust-09-traits/)
