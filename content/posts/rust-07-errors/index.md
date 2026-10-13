+++
title = "Rust 入门 07：读取输入，处理可能失败的操作"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
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

前面几章的值大多写在代码里。从这一章开始，程序要接收人输入的内容。输入 `30` 时记录学习时长，输入 `abc` 时说明哪里不对，输入结束时也要有明确的处理方式。

读到一行文本和得到一个有效的分钟数，是两件事。我们会把它们分开：`main` 负责终端输入输出，`parse_minutes` 负责转换和检查。本章需要用到第五章的借用、第六章的 `match` 与枚举。学完后，你应该能写出一个返回 `Result` 的函数，并解释错误从哪里产生、最后由谁显示。

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

## 先用几种输入观察程序

把完整程序运行起来后，每次输入一行。它处理完这一行就结束；想试下一个输入，需要重新运行。

| 输入 | 应观察到的行为 |
| --- | --- |
| `30` | 输出 `已记录 30 分钟` |
| ` 30 ` | 首尾空白被去掉，仍记录 30 分钟 |
| `0` | 报告 `分钟数必须大于 0` |
| `abc` 或 `-1` | 报告数字解析失败 |
| `4294967296` | 超过 `u32` 的上限，解析失败 |
| 直接回车 | 读到了换行，但去掉空白后没有数字，解析失败 |

数字解析错误的后半段由标准库提供，具体措辞可能随工具链变化。先关注它进入了哪个分支。

在 macOS 或 Linux 的终端，可以把输入通过管道交给程序，这样不用每次手动敲字。在 `rust-course` 目录运行：

```sh
printf '30\n' | cargo run -p rust-basics --example ch07_errors
printf '0\n' | cargo run -p rust-basics --example ch07_errors
printf '' | cargo run -p rust-basics --example ch07_errors
```

最后一条没有提供任何字节，应报告 `输入已结束，没有读到数据`。空输入和按下回车不同：前者让 `read_line` 返回 `Ok(0)`，后者通常读到一个换行字节。Windows PowerShell 也可以用 `"30" | cargo run -p rust-basics --example ch07_errors` 试正常输入；上面的 `printf` 命令按 macOS、Linux 的 shell 写法给出。

## 从标准输入读取一行

`std::io` 是标准库的输入输出模块。`io::stdin()` 获取标准输入句柄，`read_line(&mut input)` 把读到的一行追加到 `String`，所以需要可变借用。

`String::new()` 创建空字符串。输入通常带末尾换行，`trim()` 让后续数字解析忽略首尾空白。

`read_line` 返回 `Result<usize, io::Error>`：成功时是读取的字节数，失败时是输入输出错误。`Ok(0)` 表示输入已经结束，没有读到数据，所以示例单独报告它。多次调用时要先清空旧字符串，否则新行会追加在后面。

### 为什么第二次读取前要 clear

`read_line` 追加文本，不会先替你清空字符串。下面是一个独立的完整程序，保存为自己的 `src/main.rs` 后运行。依次输入 `30` 和 `45`，每输入一次按回车：

```rust
use std::io;

fn main() {
    let mut input = String::new();
    for number in 1..=2 {
        input.clear();
        println!("第 {number} 次输入：");
        match io::stdin().read_line(&mut input) {
            Ok(0) => {
                println!("输入结束");
                break;
            }
            Ok(bytes) => println!("读到 {bytes} 字节，内容是 {:?}", input.trim()),
            Err(error) => {
                eprintln!("读取失败：{error}");
                break;
            }
        }
    }
}
```

用 `printf '30\n45\n' | cargo run` 提供输入时，两次分别读到 3 字节，内容分别是 `"30"` 和 `"45"`。这里字节数包含末尾的 `\n`；遇到不同的换行表示，字节数可能不同。输入中文时也不要把字节数当作文字个数。

暂时删掉 `input.clear()` 再运行。第二次字符串会包含两行，`trim()` 只去掉两端的空白，中间的换行仍在。`clear` 保留这个 `String` 的绑定和可用缓冲区，只把内容清空。

## Result 表示成功或失败

`Result<T, E>` 有两个变体：`Ok(T)` 保存成功结果，`Err(E)` 保存错误。上一章的 `Option<T>` 只区分有值和没值；这里还需要知道为什么失败。

`parse_minutes` 的返回类型 `Result<u32, String>` 表示：成功时交出分钟数，失败时交出错误消息。返回 `Ok(minutes)` 和 `Err(message)` 时，两种分支都满足这个返回类型。

`match` 把成功与失败分开处理。`println!` 输出正常内容，`eprintln!` 输出到标准错误流。标准输出和标准错误是两条独立的输出通道，命令行工具可以把正常结果交给其他程序，同时显示错误。

### 用一个小函数认清两个分支

下面是独立的完整程序。它不读终端，所以能专心观察 `Result`：

```rust
fn half(value: u32) -> Result<u32, String> {
    if value % 2 != 0 {
        return Err(String::from("只能处理偶数"));
    }
    Ok(value / 2)
}

fn main() {
    for value in [8, 7] {
        match half(value) {
            Ok(answer) => println!("{value} 的一半是 {answer}"),
            Err(message) => println!("{value} 失败：{message}"),
        }
    }
}
```

输出：

```text
8 的一半是 4
7 失败：只能处理偶数
```

错误分支不会给出一个假答案。若约定“失败时返回 0”，调用方就无法区分失败和 `half(0)` 的正常结果。`Result` 把这两种情况放进不同的变体，调用方必须按返回类型使用它们。

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

### map_err 不会调用成功分支

这是独立的完整程序：

```rust
fn main() {
    let good: Result<u32, &str> = Ok(30);
    let bad: Result<u32, &str> = Err("不是数字");
    let good = good.map_err(|message| format!("输入有误：{message}"));
    let bad = bad.map_err(|message| format!("输入有误：{message}"));
    println!("{good:?}");
    println!("{bad:?}");
}
```

输出 `Ok(30)` 和 `Err("输入有误：不是数字")`。两个结果的成功类型仍是 `u32`，错误类型都从 `&str` 变成了 `String`。

这里先出现闭包，是因为我们需要告诉 `map_err`“拿到错误后怎样转换”。你可以先把 `|message| ...` 读成“参数是 message，返回右边的表达式”，不必在这一章掌握闭包的全部规则。

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

### 当前函数也要能返回错误

初学时容易把带 `?` 的表达式直接放进默认的 `main`。下面是**故意不能编译的完整程序**：

```rust
fn main() {
    let minutes = "30".parse::<u32>()?;
    println!("{minutes}");
}
```

默认的 `main` 返回 `()`，不能接收这里传播出来的解析错误。编译器会报告 `E0277`。不要为了消掉这个错误就把 `?` 全换成 `unwrap()`；应该先决定错误由哪一层接住。

一种做法是给读取和计算写一个返回 `Result` 的函数，再让 `main` 显示错误。下面是独立的完整程序：

```rust
fn record(input: &str) -> Result<(), String> {
    let minutes = input
        .trim()
        .parse::<u32>()
        .map_err(|_| String::from("请输入整数分钟"))?;
    println!("已记录 {minutes} 分钟");
    Ok(())
}

fn main() {
    match record("abc") {
        Ok(()) => println!("记录完成"),
        Err(message) => eprintln!("记录失败：{message}"),
    }
}
```

这个小例子只演示解析与错误传播，尚未加入本章开头的“大于 0”检查。运行时只输出错误消息，`?` 后面的两条正常输出都不会执行。

`Result<(), String>` 的 `()` 表示成功时没有额外的值要交出；`Ok(())` 仍然明确表示成功。它在写文件、修改任务这类函数中很常见。第十二章会进一步用退出状态表示命令成功还是失败；本章的输入演示只负责显示消息，错误分支执行完后仍正常返回。

## 什么时候不要 unwrap

`unwrap()` 从 `Some` 或 `Ok` 中取值，在 `None` 或 `Err` 时 panic。`expect("说明")` 也会 panic，只是能附加消息。它们适合某些确知不会失败的内部假设或测试断言；用户输入错误是预期情况，应该正常处理。

示例收到 `abc` 时返回 `Err`，让调用方显示原因。更大的程序中也常定义专门的错误类型，或者使用错误处理库；这套教材先用 `String`，让传播路径容易看清。

### 不要把无效输入悄悄变成有效数据

`unwrap_or(0)` 不会 panic，但它会把失败替换成默认值。如果你写 `input.parse::<u32>().unwrap_or(0)`，那么输入 `abc` 就变成了 0，错误原因也丢失了。只有业务明确允许这个默认值时才这样写。

可以先问自己：这次失败是用户需要修正的输入，还是程序内部假设被打破了？前者通常应该返回或显示可理解的错误。后者若使用 `expect`，至少应写明你依赖的假设，并用测试检查它。

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

### 再把解析函数接到终端

不展开答案，修改本章开头的完整程序：把提示改成输入年龄，把 `parse_minutes` 换成 `parse_age`，成功时打印年龄。依次试 `18`、`0`、`151`、空行和 `abc`。

还可以给 `parse_age` 写一个不用终端的 `main`，直接调用五次并检查结果。下一章会把这样的检查组织成 `cargo test` 能自动执行的测试。此时先确认：输入来自哪里，不应该影响解析函数的规则。

## 官方延伸阅读

- [Result 和错误传播](https://doc.rust-lang.org/book/ch09-02-recoverable-errors-with-result.html)
- [Stdin::read_line](https://doc.rust-lang.org/std/io/struct.Stdin.html#method.read_line)

外部文档查阅日期：2026-10-13。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：结构体与枚举](/posts/rust-06-modeling/) · [下一章：模块与测试](/posts/rust-08-projects/)
