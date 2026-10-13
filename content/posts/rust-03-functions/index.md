+++
title = "Rust 入门 03：函数、判断和循环"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "把重复计算写成函数，用 if、for、while 和 loop 表达程序的执行顺序。"
summary = "把重复计算写成函数，用 if、for、while 和 loop 表达程序的执行顺序。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 3
series_label = "函数与控制流程"
series_part = "把程序写出来"
series_number = 3
ShowToc = true
+++

前两节里，你已经运行过程序，也学会了保存数据和计算。本节会把重复的动作写成可以多次调用的函数，再让程序按条件选择分支、依次处理记录。

具体来说，用函数组织计算，用 `if` 作判断，用 `for`、`while` 和 `loop` 重复操作，最后完成一个三天学习统计程序。本节的函数只使用数字、布尔值和固定长度数组，借用与生命周期留到相应章节。

继续在 `hello-rust` 项目里练习。完整程序可以直接替换 `src/main.rs`，运行 `cargo run`；只有明确标注的替换行或局部片段需要放入已有代码。

## 3.1 从一个没有参数的函数开始

完整程序：

```rust
fn print_goal() {
    println!("今天的目标：练习函数。");
}

fn main() {
    print_goal();
    print_goal();
}
```

输出两次同样的目标。

`fn print_goal() { ... }` 定义函数，说明这个动作怎样完成。`print_goal();` 调用函数，执行里面的代码。`main` 先执行第一条调用，完成后再执行第二条。

定义一个函数不会自动运行它。在 `main` 中删掉两条调用，运行后就不会打印目标；编译器还可能提醒这个函数没有使用。

函数名通常也使用小写和下划线，例如 `total_minutes`。函数可以定义在 `main` 前面或后面。对这里的普通函数，执行顺序取决于调用位置，与定义在文件中的先后无关。

## 3.2 参数让同一段逻辑处理不同输入

刚才的函数每次打印相同的目标。要让它打印不同的分钟数，可以增加参数。完整程序：

```rust
fn print_minutes(minutes: u32) {
    println!("这次学习 {minutes} 分钟");
}

fn main() {
    print_minutes(20);
    print_minutes(45);
}
```

预期输出：

```text
这次学习 20 分钟
这次学习 45 分钟
```

函数定义中的 `minutes: u32` 是参数，表示函数接收一个 `u32` 值。调用 `print_minutes(20)` 时，20 就是这次调用的实际输入。

函数参数需要写明类型。函数内部的 `minutes` 只属于这次函数调用的局部范围；它不会自动改变 `main` 中的同名变量。

多个参数用逗号分隔，调用时按对应顺序提供值。参数名写清楚，可以减少把两个同类型数字传反的错误。

## 3.3 返回值把计算结果交回调用方

打印结果和返回结果是两件事。一个加法函数可以只负责算出和，调用方再决定打印、继续计算或作比较。

完整程序：

```rust
fn add(left: i32, right: i32) -> i32 {
    left + right
}

fn main() {
    let total = add(20, 30);
    let doubled = total * 2;
    println!("合计：{total}，两倍：{doubled}");
}
```

输出 `合计：50，两倍：100`。

拆开函数签名：

| 部分 | 含义 |
| --- | --- |
| `fn add` | 定义名为 `add` 的函数 |
| `(left: i32, right: i32)` | 接收两个 `i32` 参数 |
| `-> i32` | 返回一个 `i32` 值 |
| `left + right` | 计算并作为函数结果交回 |

调用时，20 和 30 传入函数，计算结果 50 通过 `let total = ...` 赋给变量。函数本身不打印，终端里的输出来自 `main`。

## 3.4 返回值后面为什么没有分号

Rust 中，表达式会计算出一个值，语句则用于执行动作。函数体最后的表达式可以成为返回值，因此刚才的 `left + right` 后面没有分号。

下面是故意无法编译的完整程序：

```rust
fn add(left: i32, right: i32) -> i32 {
    left + right;
}

fn main() {
    println!("{}", add(20, 30));
}
```

加上分号后，计算结果就不再作为函数体的值返回。函数体得到的是单元值 `()`，与声明的 `i32` 不匹配，编译器通常报告 `E0308`。

可以去掉这个分号，也可以明确写 `return`。下面是后一种写法的完整程序：

```rust
fn add(left: i32, right: i32) -> i32 {
    return left + right;
}

fn main() {
    println!("{}", add(20, 30));
}
```

`return` 会立即结束当前函数并返回结果。通常把返回结果的表达式直接放在函数末尾，需要提前结束时再用 `return`。是否加分号，要看这段代码是否需要产生值，不能每行都加。

没有声明 `-> ...` 的普通函数默认返回 `()`。`print_minutes` 只执行打印动作，就属于这种情况。

## 3.5 用 if 选择执行路径

完整程序：

```rust
fn main() {
    let minutes = 35;

    if minutes >= 60 {
        println!("学习时间充足");
    } else if minutes >= 30 {
        println!("已经完成一轮练习");
    } else {
        println!("再安排一小段时间");
    }
}
```

35 不满足第一个条件，但满足第二个，所以只输出 `已经完成一轮练习`。

`if` 按顺序检查条件。一旦选中一个分支，就跳过同一组的其他分支。这里如果先判断 `minutes >= 30`，再判断 `minutes >= 60`，60 以上也会先进入第一个分支；分支顺序会影响结果。

条件必须产生 `bool`。`if minutes >= 60` 合法，因为比较返回真或假；`if minutes` 不合法，Rust 不会把非零整数自动当成真。

把 `minutes` 依次改成 29、30、59、60，预测输出，再运行。边界值能帮助你检查应该使用 `>` 还是 `>=`。

## 3.6 if 也可以计算出一个值

完整程序：

```rust
fn main() {
    let minutes = 35;
    let target = 30;
    let message = if minutes >= target {
        "已达标"
    } else {
        "未达标"
    };

    println!("学习了 {minutes} 分钟：{message}");
}
```

被选中的分支产生的文本会赋给 `message`。分支末尾没有分号，因为这里需要它们的值；整个 `let message = ...;` 最后有分号，表示变量声明结束。

两个分支必须产生兼容类型的值。如果一个产生文本，另一个产生整数，就不能赋给这里的同一个变量。

只需要执行动作时，可以像上一小节那样在分支中打印；后面还要使用选择结果时，就让 `if` 产生值。

## 3.7 用 for 依次处理数组元素

沿用第二节的数组写法，用 `[20, 30, 40]` 保存三天记录。如果要把每项相加，不必手写三个索引，可以用 `for`。

完整程序：

```rust
fn main() {
    let days = [20, 30, 40];
    let mut total = 0;

    for minutes in days {
        total += minutes;
        println!("刚加入 {minutes} 分钟，目前合计 {total}");
    }

    println!("最终合计：{total} 分钟");
}
```

预期输出：

```text
刚加入 20 分钟，目前合计 20
刚加入 30 分钟，目前合计 50
刚加入 40 分钟，目前合计 90
最终合计：90 分钟
```

`for minutes in days` 每次把下一个元素交给本轮的 `minutes`。循环执行三轮，分别处理 20、30、40；没有下一个元素时退出。

在循环外初始化 `total`，并声明为 `mut`，才能让每一轮接着上一次的结果累加。如果把 `let mut total = 0;` 放进循环，每轮都会重新从 0 开始，得不到整组数据的总和。

先用 `for` 遍历数据本身，可以减少手写索引和长度判断。第四、五节再讨论遍历时怎样借用或移动数据；这里使用简单整数数组。

## 3.8 用范围生成连续整数

完整程序：

```rust
fn main() {
    for day in 1..=3 {
        println!("第 {day} 天");
    }

    for number in 1..3 {
        println!("不包含右边界：{number}");
    }
}
```

第一段输出第 1、2、3 天；第二段只输出 1、2。

| 范围 | 生成的整数 |
| --- | --- |
| `0..3` | 0、1、2 |
| `1..3` | 1、2 |
| `1..=3` | 1、2、3 |

`..` 不包含右边界，`..=` 包含右边界。不能直接把范围的上界当成执行次数，还要看起点。

例如要打印 1～5，就写 `1..=5`。遍历数组时，本节优先使用 `for value in array`，不用为了练习范围再改成索引。

## 3.9 while 每轮先检查条件

完整程序：

```rust
fn main() {
    let mut remaining = 3;

    while remaining > 0 {
        println!("倒计时：{remaining}");
        remaining -= 1;
    }

    println!("结束时：{remaining}");
}
```

输出倒计时 3、2、1，最后是 `结束时：0`。

每轮先检查 `remaining > 0`，为真才执行循环体，然后再检查条件：

| 检查时的值 | 条件是否成立 | 本轮动作 |
| --- | --- | --- |
| 3 | 是 | 打印 3，减成 2 |
| 2 | 是 | 打印 2，减成 1 |
| 1 | 是 | 打印 1，减成 0 |
| 0 | 否 | 跳出循环 |

如果一开始就是 0，循环体一次也不会执行。如果删掉 `remaining -= 1`，条件就会一直成立，程序不停打印。遇到这种情况，可以在终端按 `Ctrl+C` 中断，再检查循环条件或变量更新。

## 3.10 loop 持续执行，直到 break

完整程序：

```rust
fn main() {
    let mut attempts = 0;

    loop {
        attempts += 1;
        println!("第 {attempts} 次尝试");
        if attempts == 3 {
            break;
        }
    }

    println!("已经退出循环");
}
```

程序输出第 1、2、3 次尝试后退出循环。`loop` 没有自带条件，需要通过 `break` 或其他控制流结束。本例把条件写在循环体里。

`break` 只退出当前循环，不等于退出整个函数；所以最后一行还会打印。普通 `return` 则结束当前函数。

`loop` 还可以在退出时交出值。完整程序：

```rust
fn main() {
    let mut attempts = 0;
    let result = loop {
        attempts += 1;
        if attempts == 2 {
            break attempts * 10;
        }
    };

    println!("循环结果：{result}");
}
```

这里用 `break attempts * 10` 在退出时提供值 20，赋给外面的 `result`。退出时带值的写法适用于 `loop`，不能直接照搬成普通 `for` 或 `while` 的 `break 值`。

入门时按需求选择即可：逐项处理集合用 `for`，每轮先判断条件用 `while`，在循环内部决定何时退出用 `loop`。

## 3.11 continue 跳过本轮余下的动作

完整程序：

```rust
fn main() {
    for score in [50, 60, 85, 100, 90] {
        if score < 60 {
            continue;
        }
        println!("及格成绩：{score}");
        if score == 100 {
            break;
        }
    }
}
```

输出 60、85、100。

处理 50 时执行 `continue`，直接进入下一轮，不会打印。打印 100 后执行 `break`，整个循环结束，后面的 90 也不会打印。

`continue` 是“本轮剩下的不做了”，`break` 是“这个循环后面的轮次都不做了”。在普通筛选中，一个 `if` 往往已经足够；本例用来观察这两个关键字的不同效果。

## 3.12 完成三天学习统计程序

把函数、数组、循环、判断和输出放在一起，就能完成这个统计程序。下面的完整代码可以替换自己的 `src/main.rs`：

```rust
fn total_minutes(days: [u32; 3]) -> u32 {
    let mut total = 0;
    for minutes in days {
        total += minutes;
    }
    total
}

fn reached_target(total: u32, target: u32) -> bool {
    total >= target
}

fn main() {
    let days: [u32; 3] = [20, 30, 40];
    let target: u32 = 90;
    let total = total_minutes(days);
    let message = if reached_target(total, target) {
        "已达标"
    } else {
        "未达标"
    };

    println!("三天总计：{total} 分钟");
    println!("目标：{target} 分钟，{message}");

    for minutes in days {
        println!("单日记录：{minutes} 分钟");
    }
}
```

预期输出：

```text
三天总计：90 分钟
目标：90 分钟，已达标
单日记录：20 分钟
单日记录：30 分钟
单日记录：40 分钟
```

`total_minutes(days: [u32; 3]) -> u32` 明确要求输入三个 `u32`。`reached_target(total: u32, target: u32) -> bool` 负责比较，输出展示由 `main` 决定。

这里固定为三天，函数签名就只需使用第二节学过的数组类型。第五节会改用切片，接收任意长度的记录，现在先不用处理那部分语法。

最后的循环直接打印每条记录。函数内的 `total`、参数 `total` 和 `main` 中的 `total` 各有自己的局部范围。名称相同，也不能把它们当成同一个变量跨函数直接修改。

下载包中对应 `basics/examples/ch03_flow.rs`。在解压后的 `rust-course` 目录运行：

```sh
cargo run -p rust-basics --example ch03_flow
```

先把目标改成 100，确认总计不变而判断变成“未达标”。再修改 `days` 中的一天，观察总计与明细一起变化。

本例的固定长度整数数组可以复制，因此传给 `total_minutes` 后，`main` 仍能遍历原来的 `days`。第四节会解释这类值的复制规则，以及为什么不能把它套用到所有类型。

## 3.13 练习一：温度转换函数

写 `celsius_to_fahrenheit(celsius: f64) -> f64`，公式是 `华氏温度 = 摄氏温度 × 1.8 + 32.0`。在 `main` 中调用三次，输入 0、100、-40，分别输出 32、212、-40。

<details>
<summary>参考答案：先自己完成再展开</summary>

```rust
fn celsius_to_fahrenheit(celsius: f64) -> f64 {
    celsius * 1.8 + 32.0
}

fn main() {
    println!("{}", celsius_to_fahrenheit(0.0));
    println!("{}", celsius_to_fahrenheit(100.0));
    println!("{}", celsius_to_fahrenheit(-40.0));
}
```

函数只负责转换，调用方用三个 `println!` 展示结果。第八节还会用这个公式学习模块和测试。

</details>

## 3.14 练习二：统计及格人数

写 `count_passed(scores: [u32; 3]) -> u32`。接收三个成绩，达到 60 算及格，返回及格人数。使用循环和 `if`，不需要调用还没有学过的方法。

至少检查三个输入：`[59, 60, 90]` 得到 2，`[0, 59, 58]` 得到 0，`[60, 60, 60]` 得到 3。

<details>
<summary>参考答案：先自己完成再展开</summary>

```rust
fn count_passed(scores: [u32; 3]) -> u32 {
    let mut passed = 0;
    for score in scores {
        if score >= 60 {
            passed += 1;
        }
    }
    passed
}

fn main() {
    assert_eq!(count_passed([59, 60, 90]), 2);
    assert_eq!(count_passed([0, 59, 58]), 0);
    assert_eq!(count_passed([60, 60, 60]), 3);
    println!("练习通过");
}
```

`assert_eq!` 检查左右两项是否相等，不相等时程序会失败。这里用它检查三个输入的结果，第八节再把这样的检查写成正式测试。

在下载包中运行 `cargo run -p rust-basics --example answer03`，应输出 `练习通过`。把判断错误地改成 `score > 60` 再运行，至少一个断言应失败；确认之后改回来。

</details>

## 3.15 进入第四节前检查

合上参考答案，从空白 `main.rs` 写一个程序：函数接收三个学习分钟数，返回总和；调用方判断是否达到目标，再用循环打印 1～3 天的序号。试着修改目标，预测输出，再运行核对。能做到这些，就完成了前三节的主要目标。

同时确认自己能回答：函数定义和调用有什么区别？返回表达式后面加分号为什么会报错？`1..3` 与 `1..=3` 相差什么？什么时候使用 `break`，什么时候使用 `continue`？

第四节将用可以增长的字符串和列表，说明函数之间怎样传递和借用数据。

## 官方延伸阅读与验证

- [函数与返回值](https://doc.rust-lang.org/book/ch03-03-how-functions-work.html)
- [分支和循环](https://doc.rust-lang.org/book/ch03-05-control-flow.html)

文档查阅与示例复核日期：2026-10-13。正文完整程序使用 macOS arm64、Rust 1.99.0、Cargo 1.99.0 验证；故意增加返回表达式分号的例子按 `E0308` 检查。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：变量与类型](/posts/rust-02-variables/) · [下一章：所有权与借用](/posts/rust-04-ownership/)
