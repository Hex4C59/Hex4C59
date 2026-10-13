+++
title = "Rust 入门 04：所有权、移动和借用"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-12T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "用字符串修改和打印的具体例子解释 move、Copy、clone、共享借用和可变借用。"
summary = "用字符串修改和打印的具体例子解释 move、Copy、clone、共享借用和可变借用。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 4
series_label = "所有权与借用"
series_part = "理解数据如何使用"
series_number = 4
ShowToc = true
+++

本章要解决一个实际问题：一个函数只想打印文本，另一个函数需要修改文本。怎样让它们协作，同时保留调用方继续使用文本的能力？

先运行完整示例，再回来看 Rust 为什么要求这些 `&` 和 `mut`。

在解压后的 `rust-course` 目录运行：

```sh
cargo run -p rust-basics --example ch04_ownership
```

完整代码位于 `basics/examples/ch04_ownership.rs`。也可以把下面的代码完整替换到自己项目的 `src/main.rs`，再运行 `cargo run`。

```rust
fn show_title(title: &str) {
    println!("标题：{title}");
}

fn add_suffix(title: &mut String) {
    title.push_str("（已复习）");
}

fn main() {
    let original = String::from("学习 Rust");
    let mut title = original;
    show_title(&title);
    add_suffix(&mut title);
    show_title(&title);

    let backup = title.clone();
    title.push('！');
    println!("当前：{title}");
    println!("备份：{backup}");

    let count = 3;
    let copied = count;
    println!("两个整数：{count}、{copied}");
}
```

预期输出：

```text
标题：学习 Rust
标题：学习 Rust（已复习）
当前：学习 Rust（已复习）！
备份：学习 Rust（已复习）
两个整数：3、3
```

## String 拥有一段可以增长的文本

`String::from("学习 Rust")` 创建一个拥有文本内容的 `String`。它可以增长，例如通过 `push_str` 追加文字。为可增长内容分配的内存，需要在不再使用时清理。

Rust 用所有权规则决定谁负责这个值。先掌握与本例有关的几件事：一个值由其所有者负责；值可以转移给新的所有者；当拥有该值的变量离开作用域时，该值会被丢弃，所持资源按相应规则清理。

作用域常由花括号界定。函数内创建的局部变量，在函数返回时会离开该函数的作用域。所有权规则由编译器检查，很多不合法的使用在程序运行前就会被拒绝。

## 移动后，旧绑定不能继续使用

`let mut title = original;` 把这个 `String` 的所有权从 `original` 移到 `title`。它不会为文本自动做一份独立复制。之后继续访问 `original` 会报错。

`compile-fail/moved_value.rs` 是故意失败的完整例子：

```rust
fn main() {
    let first = String::from("Rust");
    let second = first;
    println!("{first} {second}");
}
```

运行 `rustc --edition 2024 compile-fail/moved_value.rs`，会得到 `E0382`，提示值已经被移动。你应当先确定意图：后面是否还要用原值？是否只是想读取它？是否确实需要独立副本？

按值传递参数也适用这个规则。如果函数参数是 `title: String`，调用 `consume(title)` 会把 `String` 移进去；除非函数返回所有权，否则调用方不能继续用原绑定。

## 借用允许临时访问

`show_title(title: &str)` 接收共享引用。引用让函数访问已有的数据，不取得这段文本的所有权。调用 `show_title(&title)` 后，`title` 仍属于调用方。

`&title` 创建共享借用。`String` 可以在这里转换为文本切片 `&str`，因此打印函数也能接受固定文本，不必限定输入必须是某个 `String`。共享引用提供只读访问；这里不能通过它追加文字。

`add_suffix(title: &mut String)` 接收可变引用。调用方写 `add_suffix(&mut title)`，允许函数修改同一个 `String`。调用方的绑定也必须是 `mut`。

| 参数形式 | 这次调用能做什么 | 调用后调用方是否还能使用原值 |
| --- | --- | --- |
| `String` | 取得所有权，可以自行保留或丢弃 | 原绑定已移动，除非重新取得所有权 |
| `&str` | 查看文本 | 可以 |
| `&mut String` | 修改借来的字符串 | 借用结束后可以 |

## 同一份数据不能一边被共享引用使用，一边被修改

下面也是故意无法编译的完整例子，文件为 `compile-fail/borrow_conflict.rs`：

```rust
fn main() {
    let mut text = String::from("Rust");
    let borrowed = &text;
    text.push('!');
    println!("{borrowed}");
}
```

最后一行仍使用 `borrowed`，说明共享借用需要跨过 `push` 这一行。Rust 拒绝在这个共享借用仍需使用时，对同一字符串创建可变借用。运行 `rustc --edition 2024 compile-fail/borrow_conflict.rs`，可以观察 `E0502`。

通常可以先用完共享引用，再修改原值。下面是完整的修复版本：

```rust
fn main() {
    let mut text = String::from("Rust");
    let borrowed = &text;
    println!("{borrowed}");
    text.push('!');
    println!("{text}");
}
```

编译器在这里能判断共享借用最后用在第一个 `println!`，后面的修改就合法。对本章的普通引用，可以记为：同一段数据在需要访问的期间，要么允许多个共享引用，要么允许一个独占的可变引用。借用何时结束，要结合引用实际使用的位置判断。

## Copy 与 clone

示例末尾的整数 `count` 在赋给 `copied` 后仍能使用。整数实现了 `Copy`，赋值时复制数值，不让原绑定失效。布尔值等一些简单类型也具有这个性质。`String` 没有 `Copy`。

`let backup = title.clone();` 显式创建一个独立字符串。随后修改 `title` 不影响 `backup`。复制 `String` 的内容通常需要分配和复制文本，所以只在需要独立数据时使用。为了打印一次文本，借用已经足够。

## 引用不能指向已经销毁的数据

`compile-fail/dangling.rs` 试图返回对局部 `String` 的引用。函数返回时字符串被清理，引用没有可以继续指向的有效文本，所以编译器报告 `E0515`。给它写上 `'static` 也不能使局部字符串活得更久。需要把新创建的文本交给调用方时，直接返回 `String`。

## 练习：追加一个感叹号

写 `append_mark`，参数是 `&mut String`，给文本追加 `！`。调用后在 `main` 中打印原变量，确保它仍能使用。

<details>
<summary>参考答案：先自己完成再展开</summary>

```rust
fn append_mark(text: &mut String) {
    text.push('！');
}

fn main() {
    let mut message = String::from("继续练习");
    append_mark(&mut message);
    println!("{message}");
    assert_eq!(message, "继续练习！");
}
```

运行 `cargo run -p rust-basics --example answer04`。再把参数改为 `String`，观察调用方继续使用变量时的报错；把它改回可变借用，解释两种函数签名表达的不同意图。

</details>

## 官方延伸阅读

- [所有权与移动](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html)
- [引用与借用](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html)

外部文档查阅日期：2026-10-12。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：函数与控制流程](/posts/rust-03-functions/) · [下一章：字符串与集合](/posts/rust-05-collections/)
