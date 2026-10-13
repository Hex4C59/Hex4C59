+++
title = "Rust 入门 09：读懂泛型、trait 和生命周期"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
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

## 三个概念各回答一个问题

先不要把三个新名词揉在一起。泛型让调用方选择类型，trait 约定类型需要提供的能力，生命周期则描述引用之间的有效期关系。

本章建立在第四、五章的所有权和借用之上。开头的完整程序把三者放在一起供你运行，下面再拆开观察。你暂时不需要设计复杂的泛型库，先能读懂签名，并写出一个带约束的函数和一个返回借用的函数。

## 泛型为类型留下参数

`Pair<T>` 把具体类型留给使用方选择。`first` 和 `second` 都是 `T`，所以它们必须具有同一种类型。示例构造的 `Pair { first: 3, second: 8 }` 可以推断为 `Pair<i32>`。

你也可以写 `Pair { first: "早上", second: "晚上" }`，得到保存两个文本视图的类型。`T` 只是常用的参数名；也可以选择其他有意义的名称。

泛型自身并没有承诺“支持所有操作”。如果在泛型函数中直接把两个任意 `T` 相加，编译器需要知道 `T` 是否支持加法。这就需要通过 trait 约束说明能力。

### 两个字段为什么必须是同一类型

下面是独立的完整程序：

```rust
struct Pair<T> {
    first: T,
    second: T,
}

impl<T> Pair<T> {
    fn first(&self) -> &T {
        &self.first
    }
}

fn main() {
    let words = Pair {
        first: String::from("早上"),
        second: String::from("晚上"),
    };
    println!("{} / {}", words.first(), words.second);
}
```

输出 `早上 / 晚上`。`impl<T>` 先声明类型参数，再为 `Pair<T>` 实现方法。`first()` 返回 `&T`，因此调用它不会把第一个字段移出结构体。

`first()` 只借用字段，不复制文本。同样的结构定义既能保存整数，也能保存 `String`，但某一个 `Pair<T>` 中的两个字段共享同一个 `T`。

下面是**故意不能编译的完整程序**：

```rust
struct Pair<T> {
    first: T,
    second: T,
}

fn main() {
    let _pair = Pair {
        first: 3,
        second: "晚上",
    };
}
```

会得到类型不匹配的 `E0308`。若确实需要两个字段使用不同类型，可以定义 `Pair<A, B>`，分别让字段使用 `A`、`B`。泛型参数表达的限制是你设计接口的一部分。

## trait 约定一种能力

`trait Summary` 要求实现者提供 `summary(&self) -> String`。`Note` 实现它时，明确写出怎样把笔记变成摘要。

`print_summary(item: &impl Summary)` 接收一个借来的、实现了 `Summary` 的值。调用方只要满足这个能力要求，就能传进来。函数内部通过这个约定调用 `item.summary()`。

trait 与结构体的方法实现有关，但职责不同：`impl Note { ... }` 定义 `Note` 自己的关联函数和方法；`impl Summary for Note { ... }` 说明 `Note` 怎样满足名为 `Summary` 的能力约定。

本例使用的是泛型形式的 `impl Trait` 参数。它不能直接让一个 `Vec` 同时存放任意不同类型；那涉及枚举或 trait 对象等另外的设计，先不要混为一谈。

### 让两种类型使用同一个打印函数

这是独立的完整程序，包含 trait、两份实现和调用方：

```rust
trait Summary {
    fn summary(&self) -> String;
}

struct Note {
    title: String,
}

struct Course {
    name: String,
    lessons: u32,
}

impl Summary for Note {
    fn summary(&self) -> String {
        format!("笔记：{}", self.title)
    }
}

impl Summary for Course {
    fn summary(&self) -> String {
        format!("课程：{}，共 {} 章", self.name, self.lessons)
    }
}

fn print_summary(item: &impl Summary) {
    println!("{}", item.summary());
}

fn main() {
    let note = Note {
        title: String::from("借用"),
    };
    let course = Course {
        name: String::from("Rust 入门"),
        lessons: 12,
    };
    print_summary(&note);
    print_summary(&course);
    println!("原笔记标题仍在：{}", note.title);
}
```

输出：

```text
笔记：借用
课程：Rust 入门，共 12 章
原笔记标题仍在：借用
```

`print_summary` 不用识别传来的是笔记还是课程，只要求它能生成摘要。参数前的 `&` 则说明打印函数借用原值；实现 trait 不会自动改变所有权规则。

这里的每个 `summary` 都新建并返回一个 `String`。如果只是提供已有标题的视图，返回 `&str` 会更合适，本章的书签练习就采用这种接口。

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

### 类型参数没有自带格式化能力

下面是**故意不能编译的完整程序**：

```rust
fn print_value<T>(value: T) {
    println!("{value}");
}

fn main() {
    print_value(3);
}
```

编译器会报告 `E0277`，因为函数定义没有保证 `T` 实现 `Display`。即使这一次传入的是整数，也不能用调用方的偶然选择替代函数签名中的约束。

独立运行的修正版如下：

```rust
fn print_value<T: std::fmt::Display>(value: T) {
    println!("{value}");
}

fn main() {
    print_value(3);
    print_value("早上");
}
```

输出 `3` 和 `早上`。若想打印一个整数列表，可以用 `println!("{:?}", vec![3, 8])` 查看调试格式；这个列表没有因为元素能显示，就自动支持同一种 `{}` 显示接口。

## 生命周期描述引用之间的关系

第四章说明引用不能指向已被销毁的数据。生命周期是编译器用来检查引用在何时仍然有效的概念。大多数时候可以推断，不必手写。

当函数接收两个文本引用、并可能返回其中任意一个时，编译器需要知道返回值与输入的有效期有什么关系。示例的函数签名是：

```rust
fn longer<'a>(left: &'a str, right: &'a str) -> &'a str
```

这是签名片段，不是独立可运行的函数。`'a` 是生命周期参数，说明返回引用必须落在两个输入引用都能有效使用的那段范围内。它不要求两个原始字符串同时创建或销毁，也不会延长它们的存活时间。

函数内部比较的是 UTF-8 字节长度，所以本例叫“字节更多”。这不是对任意语言文字数量的比较。

如果删掉签名中的生命周期标注，`compile-fail/missing_lifetime.rs` 会报告 `E0106`，因为编译器无法从多个输入引用中自动确定返回引用的关系。

### 运行结果选中了长字符串，也不能跳过引用检查

下面是**故意不能编译的完整程序**，保留正确的生命周期签名，仍然会失败：

```rust
fn longer<'a>(left: &'a str, right: &'a str) -> &'a str {
    if left.len() >= right.len() {
        left
    } else {
        right
    }
}

fn main() {
    let left = String::from("a much longer title");
    let result;
    {
        let right = String::from("rust");
        result = longer(&left, &right);
    }
    println!("{result}");
}
```

编译器会报告 `E0597`，指出 `right` 存活得不够久。它在内层块结束时销毁，而 `result` 在块外仍被使用。函数签名允许返回任意一个输入，调用方不能根据这次输入的文本长度假定它一定来自 `left`。

最直接的修复，是让使用返回引用的位置也留在内层块里。下面是替换上面 `main` 的完整定义，仍与原来的 `longer` 一起使用：

```rust
fn main() {
    let left = String::from("a much longer title");
    {
        let right = String::from("rust");
        let result = longer(&left, &right);
        println!("{result}");
    }
}
```

输出 `a much longer title`。若结果确实需要留到块外，就在引用仍有效时调用 `.to_string()` 得到自己拥有的字符串。这会复制文本；它是改变数据归属的选择，不是给引用延长寿命。

读生命周期报错时，先标出原数据在哪里创建、在哪里销毁，返回引用在哪里使用。标注本身不会使已经销毁的数据重新有效。

## 一个只有输入引用的函数通常不用标注

下面是完整定义，可以放进某个已有程序中使用：

```rust
fn first_word(text: &str) -> &str {
    text.split_whitespace().next().unwrap_or("")
}
```

它只有一个输入引用，返回的文本来自它，编译器可以按生命周期省略规则推断关系。`unwrap_or("")` 在没有词时返回默认空文本，不会像 `unwrap()` 那样在 `None` 时 panic。

对于 `fn label(&self) -> &str`，返回引用的生命周期通常关联到 `self`。这就是第六章里标题视图不能在原任务被销毁后继续使用的原因。

### 把省略规则放回真实调用

这是独立的完整程序：

```rust
fn first_word(text: &str) -> &str {
    text.split_whitespace().next().unwrap_or("")
}

fn main() {
    let title = String::from("Rust ownership");
    let word = first_word(&title);
    println!("第一个词：{word}");
    assert_eq!(first_word("   "), "");
}
```

输出 `第一个词：Rust`。没有手写生命周期参数，并不意味着返回的引用脱离了 `title`。若要使用 `word`，它所借用的内容就必须仍然有效。

`split_whitespace` 返回分词迭代器，`next` 取第一项，结果为 `Option<&str>`。这一行同时用到了借用和 `Option`；下一章会继续拆开迭代器的调用。

## 创建新文本时直接返回 String

如果函数内部新建 `String`，需要把它交给调用方使用，返回 `String`。它带着所有权离开函数。返回引用适用于指向仍由外部拥有的数据；不要用随意增加 `'static` 的方式试图保住局部变量。

初学时可以依次问：这个函数是在借用已有数据，还是创建新数据？返回引用指向谁？调用方使用这个引用时，原数据还存在吗？这些问题比先给每个引用加标注更容易找到错误。

下面是独立的完整程序，函数创建的字符串能够在函数返回后继续使用：

```rust
fn make_title(topic: &str) -> String {
    format!("学习：{topic}")
}

fn main() {
    let title = make_title("生命周期");
    println!("{title}");
}
```

输出 `学习：生命周期`。返回值拥有新文本，调用方接过了它的所有权。

若改成在函数里创建 `String`，再返回对它的引用，增加 `'a` 或 `'static` 都不能解决“局部值将在返回时销毁”的问题。应该返回拥有的数据，或让调用方提供仍然存活的数据供你借用。

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

### 多做一次，判断返回值归谁

给 `Label` 再写一个实现，例如保存标题的 `Video`，用同一个 `print_label` 打印两者。接着写 `owned_label(item: &impl Label) -> String`，让它返回 `item.label().to_string()`。

比较两个函数：一个在调用时借用标题，一个返回新的字符串。尝试在书签离开作用域后使用返回值，观察哪种写法能通过检查，并解释原因。这道练习不需要增加生命周期标注。

## 官方延伸阅读

- [泛型数据类型](https://doc.rust-lang.org/book/ch10-01-syntax.html)
- [trait 与约束](https://doc.rust-lang.org/book/ch10-02-traits.html)
- [生命周期语法](https://doc.rust-lang.org/book/ch10-03-lifetime-syntax.html)

外部文档查阅日期：2026-10-13。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：模块与测试](/posts/rust-08-projects/) · [下一章：闭包与迭代器](/posts/rust-10-iterators/)
