+++
title = "Rust 入门 09：读懂泛型、trait 和生命周期"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-12T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "通过 Pair、笔记摘要和字符串比较，学习类型参数、trait 约束和引用之间的生命周期关系。"
summary = "通过 Pair、笔记摘要和字符串比较，学习类型参数、trait 约束和引用之间的生命周期关系。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 9
series_label = "泛型、trait 与生命周期"
series_part = "写出可维护的程序"
series_number = 9
ShowToc = true
+++

你已经见过 `Vec<i32>`、`Option<&Task>` 和 `Result<u32, String>`。本章解释尖括号里的类型参数，再用一个小例子介绍 trait 和生命周期。目标是能读懂常见接口，并写出简单的复用函数。

在解压后的 `rust-course` 目录运行：

```sh
cargo run -p rust-basics --example ch09_traits
```

完整代码位于 `basics/examples/ch09_traits.rs`。也可以把下面的代码完整替换到自己项目的 `src/main.rs`，再运行 `cargo run`。

```rust
use std::fmt::Display;

struct Pair<T> {
    first: T,
    second: T,
}

trait Summary {
    fn summary(&self) -> String;
}

struct Note {
    title: String,
}

impl Summary for Note {
    fn summary(&self) -> String {
        format!("笔记：{}", self.title)
    }
}

fn print_summary(item: &impl Summary) {
    println!("{}", item.summary());
}

fn print_value<T: Display>(value: T) {
    println!("{value}");
}

fn longer<'a>(left: &'a str, right: &'a str) -> &'a str {
    if left.len() >= right.len() {
        left
    } else {
        right
    }
}

fn main() {
    let pair = Pair {
        first: 3,
        second: 8,
    };
    print_value(pair.first + pair.second);
    let note = Note {
        title: String::from("借用"),
    };
    print_summary(&note);
    let left = String::from("rust");
    let right = String::from("cargo");
    println!("字节更多的是：{}", longer(&left, &right));
}
```

输出：

```text
11
笔记：借用
字节更多的是：cargo
```

## 泛型为类型留下参数

`Pair<T>` 把具体类型留给使用方选择。`first` 和 `second` 都是 `T`，所以它们必须具有同一种类型。示例构造的 `Pair { first: 3, second: 8 }` 可以推断为 `Pair<i32>`。

你也可以写 `Pair { first: "早上", second: "晚上" }`，得到保存两个文本视图的类型。`T` 只是常用的参数名；也可以选择其他有意义的名称。

泛型自身并没有承诺“支持所有操作”。如果在泛型函数中直接把两个任意 `T` 相加，编译器需要知道 `T` 是否支持加法。这就需要通过 trait 约束说明能力。

## trait 约定一种能力

`trait Summary` 要求实现者提供 `summary(&self) -> String`。`Note` 实现它时，明确写出怎样把笔记变成摘要。

`print_summary(item: &impl Summary)` 接收一个借来的、实现了 `Summary` 的值。调用方只要满足这个能力要求，就能传进来。函数内部通过这个约定调用 `item.summary()`。

trait 与结构体的方法实现有关，但职责不同：`impl Note { ... }` 定义 `Note` 自己的关联函数和方法；`impl Summary for Note { ... }` 说明 `Note` 怎样满足名为 `Summary` 的能力约定。

本例使用的是泛型形式的 `impl Trait` 参数。它不能直接让一个 `Vec` 同时存放任意不同类型；那涉及枚举或 trait 对象等另外的设计，先不要混为一谈。

## trait 约束让泛型函数知道能做什么

`Display` 是标准库的 trait，表示类型支持面向用户的 `{}` 格式化。`print_value<T: Display>` 中，`T: Display` 就是约束。

这个函数对满足约束的多种类型都能工作。`Debug` 对应 `{:?}`，常用于查看内部结构；`Display` 对应 `{}`，更关注给用户看的内容。第六章的 `derive(Debug)` 就是在生成 trait 实现。

约束很多时，可以写在 `where` 子句中。以下是同一个函数的完整替代定义：

```rust
fn print_value<T>(value: T)
where
    T: std::fmt::Display,
{
    println!("{value}");
}
```

泛型约束描述类型能力；它并不保证业务条件。例如 `Display` 不保证数字大于 0，金额和编号仍需要各自检查。

## 生命周期描述引用之间的关系

第四章说明引用不能指向已被销毁的数据。生命周期是编译器用来检查引用在何时仍然有效的概念。大多数时候可以推断，不必手写。

当函数接收两个文本引用、并可能返回其中任意一个时，编译器需要知道返回值与输入的有效期有什么关系。示例的函数签名是：

```rust
fn longer<'a>(left: &'a str, right: &'a str) -> &'a str
```

这是签名片段，不是独立可运行的函数。`'a` 是生命周期参数，说明返回引用必须落在两个输入引用都能有效使用的那段范围内。它不要求两个原始字符串同时创建或销毁，也不会延长它们的存活时间。

函数内部比较的是 UTF-8 字节长度，所以本例叫“字节更多”。这不是对任意语言文字数量的比较。

如果删掉签名中的生命周期标注，`compile-fail/missing_lifetime.rs` 会报告 `E0106`，因为编译器无法从多个输入引用中自动确定返回引用的关系。

## 一个只有输入引用的函数通常不用标注

下面是完整定义，可以放进某个已有程序中使用：

```rust
fn first_word(text: &str) -> &str {
    text.split_whitespace().next().unwrap_or("")
}
```

它只有一个输入引用，返回的文本来自它，编译器可以按生命周期省略规则推断关系。`unwrap_or("")` 在没有词时返回默认空文本，不会像 `unwrap()` 那样在 `None` 时 panic。

对于 `fn label(&self) -> &str`，返回引用的生命周期通常关联到 `self`。这就是第六章里标题视图不能在原任务被销毁后继续使用的原因。

## 创建新文本时直接返回 String

如果函数内部新建 `String`，需要把它交给调用方使用，返回 `String`。它带着所有权离开函数。返回引用适用于指向仍由外部拥有的数据；不要用随意增加 `'static` 的方式试图保住局部变量。

初学时可以依次问：这个函数是在借用已有数据，还是创建新数据？返回引用指向谁？调用方使用这个引用时，原数据还存在吗？这些问题比先给每个引用加标注更容易找到错误。

## 练习：让书签提供标题

定义 `Label` trait，方法为 `label(&self) -> &str`。定义带 `String` 标题的 `Bookmark`，实现 `Label`，再写一个接受 `&impl Label` 的打印函数。这里不需要显式生命周期标注。

<details>
<summary>参考答案：先自己完成再展开</summary>

```rust
trait Label {
    fn label(&self) -> &str;
}

struct Bookmark {
    title: String,
}

impl Label for Bookmark {
    fn label(&self) -> &str {
        &self.title
    }
}

fn print_label(item: &impl Label) {
    println!("{}", item.label());
}

fn main() {
    let bookmark = Bookmark {
        title: String::from("Rust 官方文档"),
    };
    print_label(&bookmark);
    assert_eq!(bookmark.label(), "Rust 官方文档");
}
```

运行 `cargo run -p rust-basics --example answer09`。返回的是 `Bookmark` 内标题的借用，打印函数没有复制标题，也没有取得书签所有权。

</details>

## 官方延伸阅读

- [泛型数据类型](https://doc.rust-lang.org/book/ch10-01-syntax.html)
- [trait 与约束](https://doc.rust-lang.org/book/ch10-02-traits.html)
- [生命周期语法](https://doc.rust-lang.org/book/ch10-03-lifetime-syntax.html)

外部文档查阅日期：2026-10-12。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：模块与测试](/posts/rust-08-projects/) · [下一章：闭包与迭代器](/posts/rust-10-iterators/)
