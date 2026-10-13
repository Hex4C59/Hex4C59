+++
url = "/posts/rust-08-projects/"
title = "Rust 入门 08：拆分模块，为程序写测试"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "拆分模块并写测试，解释 crate、self、super 路径、可见性、use 别名、宏和属性。"
summary = "拆分模块并写测试，解释 crate、self、super 路径、可见性、use 别名、宏和属性。"
tags = ["Rust", "Cargo", "模块", "可见性"]
categories = ["programming"]
series = ["rust-from-zero"]
series_order = 8
series_label = "模块与测试"
series_part = "写出可维护的程序"
series_number = 8
ShowToc = true
source_kind = "original"
article_type = "tutorial"
series_role = "chapter"
+++

当一个程序包含输入、计算和文件读写时，把所有内容放在 `main.rs` 会越来越难修改。本章将温度转换逻辑放到独立模块，并写测试固定它的行为。

## 先确定本章的工作目录

本章的文件都属于下载包里的 `rust-course/basics`。在 `rust-course` 目录执行带 `-p rust-basics` 的命令；编辑文件时进入它的 `basics` 子目录。不要把两个目录的 `Cargo.toml` 混在一起：前者管理工作区，后者定义具体包。

我们会把温度换算函数放进库，让一个示例程序调用它，再分别写单元测试、集成测试和文档测试。学完后，你应该能从报错路径找到对应文件，并判断一段逻辑需要作为公开接口还是留在模块内部。

## 先区分 package、crate 和 module

| 名称 | 本章中的意思 |
| --- | --- |
| package（包） | 由一个 `Cargo.toml` 管理的一组目标和配置 |
| crate | Rust 的编译单元，例如一个库或一个可执行程序 |
| module（模块） | crate 内组织名称、代码和可见性的边界 |
| workspace（工作区） | 由一个顶层清单统一管理的多个包 |

配套源码的顶层 `Cargo.toml` 是工作区。`basics` 和 `taskbook` 是两个包；`basics/src/lib.rs` 是库 crate 的入口；`math` 是库里的模块。

一个包可以同时有库和可执行程序。常见做法是把可复用、可测试的逻辑放进 `lib.rs`，`main.rs` 只负责接收输入和调用逻辑。最后两章会采用这个结构。

### 看文件树，比记四个名词更直观

本章用到的部分结构是：

```text
rust-course/
├── Cargo.toml
└── basics/
    ├── Cargo.toml
    ├── src/
    │   ├── lib.rs
    │   └── math.rs
    ├── examples/
    │   └── ch08_modules.rs
    └── tests/
        └── conversion.rs
```

`math.rs` 是库的一部分。示例和集成测试则通过库的公开入口调用函数。Cargo 认识 `src/lib.rs`、`examples/`、`tests/` 这些约定的位置；普通模块文件怎样连到库里，还要由 `mod` 声明。

这一章不用建立很多目录。一个函数、一个模块、几个检查已经足够看清组织方式。等不同职责确实需要分开时，再拆新模块。

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

### 两个 pub 分别解决哪一层可见性

调用路径 `rust_basics::math::celsius_to_fahrenheit` 经过库、模块、函数三个位置。`pub mod math` 让外部看见模块；`pub fn celsius_to_fahrenheit` 让外部看见其中的函数。

可以在自己的练习副本里暂时去掉其中一个 `pub`，运行 `cargo check -p rust-basics --example ch08_modules`。去掉模块的 `pub` 会报告模块私有，去掉函数的 `pub` 会报告函数私有。然后恢复。这能帮助你区分“没有这个名字”和“有这个名字但我不能访问”。

`use` 只是缩短书写路径。若不写 `use`，示例仍能直接调用完整路径：

```rust
fn main() {
    let value = rust_basics::math::celsius_to_fahrenheit(25.0);
    println!("{value}");
}
```

这是替换 `basics/examples/ch08_modules.rs` 的完整版本，输出 `77`；它依赖本章的库，不能脱离这个包单独编译。

### 在下载包之外重建同样的结构

如果想检查自己是否真的会组织文件，在一个空的练习目录运行：

```sh
cargo new rust-basics --lib --edition 2024 --vcs none
cd rust-basics
mkdir examples tests
```

将下文展示的 `src/lib.rs`、`src/math.rs`、`examples/ch08_modules.rs` 和 `tests/conversion.rs` 分别写到相应位置。`cargo new` 生成的默认 `lib.rs` 要由本文版本替换。这次包名也叫 `rust-basics`，因此代码里的 `rust_basics` 路径不用改。

在这个单包目录，可以省略 `-p rust-basics`：

```sh
cargo run --example ch08_modules
cargo test
```

应输出 25 摄氏度等于 77 华氏度，并通过两个单元测试、一个集成测试、一个文档测试。若按照前文建立的是 `temperature` 包，则文档注释、示例、集成测试中的 `rust_basics::` 都需要一起换成 `temperature::`。

## 单元测试：在模块附近检查行为

`#[test]` 标记测试函数。`cargo test` 会寻找并运行它们。`#[cfg(test)]` 表示这段代码只在构建测试时启用，因此 `tests` 模块不会作为正常业务接口发布。

`use super::celsius_to_fahrenheit` 从父模块引入待测函数。冻结点、负温度是不同的输入条件，能检查公式是否写对。

浮点数会有表示和运算误差。测试里用 `(actual - expected).abs() < 1e-10` 检查差值是否足够小，而不是对任意浮点运算都使用精确相等。这里的容差是为这些简单输入选择的测试标准，并非适合所有数值问题。

运行：

```sh
cargo test -p rust-basics --lib
```

应看到两个测试通过。试着把公式中的 `32.0` 改成 `30.0`，重新运行，确认测试失败，再改回来。测试失败说明检查发挥了作用。

### 测试函数怎么报告失败

测试函数里的 `assert!(条件)` 要求条件为真；`assert_eq!(实际值, 预期值)` 要求两者相等。断言不成立会触发 panic，测试框架会把这个测试记为失败，再给出位置和相关信息。

测试名称应该让你在失败列表中能认出检查的行为。`freezing_point` 比 `test1` 更容易定位“冰点换算错了”。

只运行一个测试，可以在命令后加名称过滤：

```sh
cargo test -p rust-basics freezing_point
```

这是名称过滤，不是文件路径。输出可能还列出别的测试目标，并显示其中没有匹配的测试。观察实际执行和通过的数量，不能只看命令没有报错。

修复测试时，先判断公式还是预期值有错。若正确结果应为 32，就不能为了让错误公式通过，把断言的 32 也改成 30。测试的目的，是保住你要求的行为。

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

### 两类测试该放在哪里

单元测试通常放在被测模块里，可以访问同一模块的私有实现；集成测试位于 `tests/`，作为外部使用方检查公开接口。它们观察的边界不同，不必为每个函数机械地写两份相同测试。

例如，温度公式可以就近检查不同输入；公开调用路径是否可用，则由这里的集成测试确认。到了待办工具，还会通过启动一个真正的可执行程序，检查两次运行之间的数据是否保留。

普通测试可能并行运行。不要让两个测试共同依赖一个会被修改的全局文件。第十二章的文件测试会给每次运行准备独立的临时目录。

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

### 从测试失败信息回到代码

遇到失败时，按下面的顺序处理：先找失败的测试名，再找断言所在行，最后比较实际输入和预期值。编译失败时测试尚未开始，应该先修语法、类型或可见性问题。

可以用 `cargo test -p rust-basics --lib -- --nocapture` 显示测试中的普通输出。第一个 `--` 把后面的参数交给测试程序；它和 `cargo run ... -- ...` 的分隔作用相似。这是排查时的工具，断言仍应负责判断行为。

## 外部依赖先知道放在哪里

第三方库通常记录在 `Cargo.toml` 的 `[dependencies]` 下，由 Cargo 下载、构建和连接。一个常见安装命令是 `cargo add 库名`，其中“库名”必须换成实际依赖名称；这不是本章需要执行的步骤。

本教材项目只使用标准库。能完成基础项目后，再按照需要引入命令行解析、序列化和网络库，并查阅对应版本的官方文档。可执行程序通常应保留 `Cargo.lock`，让依赖选择更容易复现。

## 语法细读：路径、可见性、宏和属性 {#syntax-depth}


本章语法细读里的每个 Rust 程序可以分别替换自己项目的 `src/main.rs`：正常例子运行 `cargo run`，故意失败的例子运行 `cargo check`。下载包另保存为独立文件，直接编译的方法见下载包里的 `syntax/README.md`。各个程序相互独立。

模块本身也是语言规则。文件放在哪个目录、名字通过哪条路径可见、以及哪段代码会参与编译，需要分别判断。

### use 引入名字，不复制代码也不放宽访问限制

完整程序，下载包中为 `syntax/syntax08-paths.rs`：

```rust
mod tools {
    pub(super) fn twice(value: i32) -> i32 {
        self::inner::add(value, value)
    }
    mod inner {
        pub(super) fn add(left: i32, right: i32) -> i32 {
            left + right
        }
    }
}
use crate::tools::twice as double;
fn main() {
    println!("{}", double(6));
}
```

预期输出：

```text
12
```

`crate::` 从当前 crate 根开始，`self::` 从当前模块开始，`super::` 从父模块开始。根部的 `use ... as double` 把一个可访问的函数用别名引入当前作用域；它不执行函数，也不把实现复制到这里。

`pub(super)` 表示向父模块范围开放。因此 `tools` 的父模块能调用 `twice`，`tools` 也能调用其子模块的 `add`。`pub(crate)` 把可见范围限制在当前 crate，普通 `pub` 则允许按所在模块路径继续向外公开。

以下完整程序故意无法编译，下载包中为 `compile-fail/syntax08-private-child.rs`：

```rust
mod tools {
    pub mod inner {
        fn hidden() {}
    }
}
fn main() {
    tools::inner::hidden();
}
```

预期诊断包含 `E0603`。

子模块公开，不会使里面的所有函数自动公开。路径的各层与目标项都要允许这次访问；`use` 别名也不能让这次私有调用变合法。前面用文件组织模块的写法与这里的内联 `mod { ... }` 遵守同一套规则。

### 感叹号调用宏，属性作用在后面的项上

完整程序，下载包中为 `syntax/syntax08-attributes-macros.rs`：

```rust
#[derive(Debug)]
struct Point {
    x: i32,
}
fn main() {
    let point = Point { x: 3 };
    let numbers = vec![point.x, 4];
    assert_eq!(numbers.len(), 2);
    println!("{point:?} / {numbers:?}");
}
```

预期输出：

```text
Point { x: 3 } / [3, 4]
```

`println!`、`vec!`、`assert_eq!` 是宏调用；括号或方括号中的内容会按该宏的规则处理，不能仅因为写法像调用就认为它是普通函数。宏可以展开成表达式或其他代码结构，也不是“程序运行时再拼接一段源代码”。

`#[derive(Debug)]` 是外层属性，作用于后面的结构体定义，要求生成相应的 trait 实现。`#[cfg(test)]` 用条件控制后面的项是否参与编译，`#[test]` 标记测试函数；它们不是放在函数前的一行注释，也不是每次调用函数都会执行的普通表达式。

阅读一个陌生片段时，先区分路径 `::`、方法访问 `.`、宏调用 `!` 和属性 `#[...]`，再去找名字的定义和作用范围。

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

### 自查：三个常见接线问题

- 创建了 `math.rs`，但 `lib.rs` 没写 `mod math`：模块还没有进入编译树。
- 模块已声明，示例却无法访问函数：检查路径经过的模块和函数是否公开。
- `cargo test --all-targets` 通过，就认为文档代码也验证了：文档测试需要普通的 `cargo test` 或 `cargo test --doc`。

试着不看答案重建四个文件。能从库外调用函数、能让错误公式触发测试失败、恢复后测试通过，本章的组织方式就已经用起来了。

## 官方延伸阅读

- [Rust Reference：模块路径](https://doc.rust-lang.org/reference/paths.html)
- [Rust Reference：可见性](https://doc.rust-lang.org/reference/visibility-and-privacy.html)
- [Rust Reference：属性](https://doc.rust-lang.org/reference/attributes.html)

- [包与 crate](https://doc.rust-lang.org/book/ch07-01-packages-and-crates.html)
- [测试的组织](https://doc.rust-lang.org/book/ch11-03-test-organization.html)
- [Cargo 工作区](https://doc.rust-lang.org/book/ch14-03-cargo-workspaces.html)

外部文档查阅日期：2026-10-13。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：输入与错误处理](/posts/rust-07-errors/) · [下一章：泛型、trait 与生命周期](/posts/rust-09-traits/)
