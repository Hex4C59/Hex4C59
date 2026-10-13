+++
title = "Rust 入门 07：读取输入，处理可能失败的操作"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-12T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "把终端输入转换为数字，用 Result、match、map_err 和问号操作符报告与传播错误。"
summary = "把终端输入转换为数字，用 Result、match、map_err 和问号操作符报告与传播错误。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 7
series_label = "输入与错误处理"
series_part = "写出可维护的程序"
series_number = 7
ShowToc = true
+++

用户可能输入文字而不是数字，文件可能不存在，读取操作也可能失败。本章会读取终端输入，把失败原因作为返回值传递，并让调用方决定如何显示。

在解压后的 `rust-course` 目录运行：

```sh
cargo run -p rust-basics --example ch07_errors
```

完整代码位于 `basics/examples/ch07_errors.rs`。也可以把下面的代码完整替换到自己项目的 `src/main.rs`，再运行 `cargo run`。

```rust
use std::io;

fn parse_minutes(input: &str) -> Result<u32, String> {
    let minutes = input
        .trim()
        .parse::<u32>()
        .map_err(|error| format!("请输入非负整数：{error}"))?;
    if minutes == 0 {
        return Err(String::from("分钟数必须大于 0"));
    }
    Ok(minutes)
}

fn main() {
    println!("请输入今天学习的分钟数：");
    let mut input = String::new();
    match io::stdin().read_line(&mut input) {
        Ok(0) => eprintln!("输入已结束，没有读到数据"),
        Ok(_) => match parse_minutes(&input) {
            Ok(minutes) => println!("已记录 {minutes} 分钟"),
            Err(message) => eprintln!("输入有误：{message}"),
        },
        Err(error) => eprintln!("读取输入失败：{error}"),
    }
}
```

程序会等待一行输入。输入 `30` 并回车，应看到 `已记录 30 分钟`。输入 `abc`、`0` 或 `-1` 时，应看到解释原因的错误消息，程序正常走完自己的错误处理分支。

## 从标准输入读取一行

`std::io` 是标准库的输入输出模块。`io::stdin()` 获取标准输入句柄，`read_line(&mut input)` 把读到的一行追加到 `String`，所以需要可变借用。

`String::new()` 创建空字符串。输入通常带末尾换行，`trim()` 让后续数字解析忽略首尾空白。

`read_line` 返回 `Result<usize, io::Error>`：成功时是读取的字节数，失败时是输入输出错误。`Ok(0)` 表示输入已经结束，没有读到数据，所以示例单独报告它。多次调用时要先清空旧字符串，否则新行会追加在后面。

## Result 表示成功或失败

`Result<T, E>` 有两个变体：`Ok(T)` 保存成功结果，`Err(E)` 保存错误。上一章的 `Option<T>` 只区分有值和没值；这里还需要知道为什么失败。

`parse_minutes` 的返回类型 `Result<u32, String>` 表示：成功时交出分钟数，失败时交出错误消息。返回 `Ok(minutes)` 和 `Err(message)` 时，两种分支都满足这个返回类型。

`match` 把成功与失败分开处理。`println!` 输出正常内容，`eprintln!` 输出到标准错误流。标准输出和标准错误是两条独立的输出通道，命令行工具可以把正常结果交给其他程序，同时显示错误。

## 从文本转换为数字

`parse::<u32>()` 尝试把文本解析成 `u32`。`::<u32>` 明确指定目标类型；这种类型参数写法有时被称为 turbofish，先能认出来即可。

解析也会失败，例如负数、不是数字的文本、超过 `u32` 范围的数字。`parse` 已经替我们检查这些条件，所以不用先自己逐个字符判断。

能被解析并不代表满足业务规则。`0` 是合法的 `u32`，但本函数要求记录的时长大于 0，所以还要显式检查 `minutes == 0`。

## map_err 只转换错误

示例中的局部表达式是：

```rust
.map_err(|error| format!("请输入非负整数：{error}"))?
```

它接在 `parse` 返回的 `Result` 后面。`map_err` 保留成功值，只把错误转换为另一种形式。解析器原本的错误类型不是 `String`，我们用它生成更适合展示的字符串。

`|error| ...` 是闭包，一种可以就地写的小函数。竖线里的 `error` 是参数，后面的表达式是结果。`format!` 和 `println!` 使用类似的格式规则，但它返回 `String`，不会直接打印。第十章会更多地使用闭包。

## 问号把错误交给调用方

对于本章的 `Result`，`?` 的行为是：如果为 `Ok(value)`，取出 `value` 继续执行；如果为 `Err(error)`，立即从当前函数返回错误，并在需要时进行兼容的错误转换。

因此这里的 `?` 不会从整个程序退出，也不会自动打印消息。它返回到调用 `parse_minutes` 的地方，外层 `match` 再决定打印什么。

下面是和示例行为一致的 `parse_minutes` 完整替代实现，展示不用 `?` 时的写法：

```rust
fn parse_minutes(input: &str) -> Result<u32, String> {
    let minutes = match input.trim().parse::<u32>() {
        Ok(value) => value,
        Err(error) => return Err(format!("请输入非负整数：{error}")),
    };
    if minutes == 0 {
        return Err(String::from("分钟数必须大于 0"));
    }
    Ok(minutes)
}
```

你能解释这两段代码为什么行为相同，就已经掌握了这次入门所需的错误传播。

## 什么时候不要 unwrap

`unwrap()` 从 `Some` 或 `Ok` 中取值，在 `None` 或 `Err` 时 panic。`expect("说明")` 也会 panic，只是能附加消息。它们适合某些确知不会失败的内部假设或测试断言；用户输入错误是预期情况，应该正常处理。

示例收到 `abc` 时返回 `Err`，让调用方显示原因。更大的程序中也常定义专门的错误类型，或者使用错误处理库；这套教材先用 `String`，让传播路径容易看清。

## 练习：解析年龄

写 `parse_age(input: &str) -> Result<u8, String>`。要求忽略首尾空白，只接受 0～150 的整数，并说明失败原因。验证 `18`、`0` 成功，`151`、`256`、`-1`、`abc` 和空文本失败。

<details>
<summary>参考答案：先自己完成再展开</summary>

```rust
fn parse_age(input: &str) -> Result<u8, String> {
    let age = input
        .trim()
        .parse::<u8>()
        .map_err(|_| String::from("年龄必须是整数"))?;
    if age > 150 {
        return Err(String::from("年龄不能超过 150"));
    }
    Ok(age)
}

fn main() {
    assert_eq!(parse_age(" 18 "), Ok(18));
    assert_eq!(parse_age("0"), Ok(0));
    for input in ["151", "256", "-1", "abc", ""] {
        assert!(parse_age(input).is_err());
    }
    println!("年龄校验通过");
}
```

运行 `cargo run -p rust-basics --example answer07`。`u8` 本身只允许 0～255，`256` 会在解析时失败；`151` 需要通过额外的范围检查拒绝。

</details>

## 官方延伸阅读

- [Result 和错误传播](https://doc.rust-lang.org/book/ch09-02-recoverable-errors-with-result.html)
- [Stdin::read_line](https://doc.rust-lang.org/std/io/struct.Stdin.html#method.read_line)

外部文档查阅日期：2026-10-12。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：结构体与枚举](/posts/rust-06-modeling/) · [下一章：模块与测试](/posts/rust-08-projects/)
