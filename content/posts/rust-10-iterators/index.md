+++
title = "Rust 入门 10：闭包和迭代器"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "从 for 循环改写出筛选、转换和汇总流程，读懂 iter、iter_mut、into_iter、filter、map 和 collect。"
summary = "从 for 循环改写出筛选、转换和汇总流程，读懂 iter、iter_mut、into_iter、filter、map 和 collect。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 10
series_label = "闭包与迭代器"
series_part = "写出可维护的程序"
series_number = 10
ShowToc = true
+++

假设要从学习记录中找出至少 30 分钟的项目，给每项加 5 分钟，再统计总计。你已经能用 `for` 完成，本章会把这些操作表达为迭代器流水线，并解释每一步究竟拿到了值还是引用。

在解压后的 `rust-course` 目录运行：

```sh
cargo run -p rust-basics --example ch10_iterators
```

完整代码位于 `basics/examples/ch10_iterators.rs`。也可以把下面的代码完整替换到自己项目的 `src/main.rs`，再运行 `cargo run`。

```rust
fn main() {
    let minutes = [10, 35, 50, 20];
    let threshold = 30;
    let selected: Vec<i32> = minutes
        .iter()
        .copied()
        .filter(|minutes| *minutes >= threshold)
        .map(|minutes| minutes + 5)
        .collect();
    println!("筛选后：{selected:?}");
    let total: i32 = selected.iter().sum();
    println!("合计：{total}");

    let titles = vec![String::from("读书"), String::from("写代码")];
    for (index, title) in titles.iter().enumerate() {
        println!("{}：{title}", index + 1);
    }
    println!("原列表仍可使用，共 {} 项", titles.len());

    let upper: Vec<String> = titles
        .into_iter()
        .map(|title| format!("任务：{title}"))
        .collect();
    println!("新列表：{upper:?}");
}
```

输出：

```text
筛选后：[40, 55]
合计：95
1：读书
2：写代码
原列表仍可使用，共 2 项
新列表：["任务：读书", "任务：写代码"]
```

## 先说清楚这条数据处理规则

本章的输入是 `[10, 35, 50, 20]`。我们先留下至少 30 的值，再分别加 5，得到 `[40, 55]`，最后相加得到 95。执行顺序会影响结果：先加 5 再筛选，是另一条规则。

闭包用来描述“每个元素怎样处理”，迭代器负责逐项提供元素。你已经会写 `for`、借用列表和使用 `Option`，本章要做的是把这些知识连在一起。先能说明每一步收到什么类型，再考虑把循环改成一条调用链。

## 闭包是可以放在表达式里的小函数

`|minutes| minutes + 5` 接收一个值，返回加 5 的结果。参数写在两条竖线之间，函数体很短时可以只写表达式；需要多行时使用 `{}`。

`|minutes| *minutes >= threshold` 使用了外面的 `threshold`。闭包可以捕获周围的变量，而普通 `fn` 定义不能直接捕获调用位置的局部变量。这里仅仅读取阈值，编译器会选择合适的捕获方式。

闭包的参数和返回类型通常由使用位置推断。第一次调用确定的类型不会让同一个闭包随后自动适用于任意其他类型。需要类型参数时，使用上一章学习的泛型函数。

### 单独调用一个闭包

这是独立的完整程序：

```rust
fn main() {
    let bonus = 5;
    let add_bonus = |minutes: i32| -> i32 { minutes + bonus };
    println!("{}", add_bonus(35));
    println!("bonus 仍是 {bonus}");
}
```

输出 `40` 和 `bonus 仍是 5`。这里把参数和返回类型都写出来了；在迭代器里，上下文通常已给出类型，可以省略。

闭包也可以修改捕获的变量。下面是另一个独立程序：

```rust
fn main() {
    let mut count = 0;
    {
        let mut record = || {
            count += 1;
            println!("已经记录 {count} 次");
        };
        record();
        record();
    }
    println!("最终计数：{count}");
}
```

输出的计数依次为 1、2，最后为 2。`||` 表示没有参数；`record` 要声明为 `mut`，因为调用它会改变捕获的状态。内层块结束后，这个闭包不再持有对 `count` 的借用，外面可以继续读取 `count`。

同一个闭包通常只对应一组确定的参数类型。下面是**故意不能编译的完整程序**：

```rust
fn main() {
    let identity = |value| value;
    let _number = identity(3);
    let _text = identity("Rust");
}
```

第一处调用使参数类型确定为整数，第二处不能再传字符串，会报告 `E0308`。若要同一个定义处理不同类型，可以写泛型函数 `fn identity<T>(value: T) -> T { value }`。

## 先写出循环版本

下面是完整的等价程序，输出同样的 `[40, 55]`：

```rust
fn main() {
    let minutes = [10, 35, 50, 20];
    let threshold = 30;
    let mut selected = Vec::new();
    for value in &minutes {
        if *value >= threshold {
            selected.push(*value + 5);
        }
    }
    println!("{selected:?}");
}
```

迭代器版本没有改变筛选条件或计算公式，只是把遍历、筛选、转换和收集分别交给几个方法表达。某段链式调用不好读时，拆成命名变量或普通循环完全可以。

## 每一步的元素类型

| 步骤 | 向下一步提供什么 |
| --- | --- |
| `minutes.iter()` | `&i32`，借用数组元素 |
| `.copied()` | `i32`，复制简单整数 |
| `.filter(...)` | 只留下符合条件的 `i32` |
| `.map(...)` | 转换后的 `i32` |
| `.collect()` | 将值收集到 `Vec<i32>` |

`filter` 判断条件时，会借用当前元素，所以即使当前元素类型是 `i32`，闭包参数仍是 `&i32`，需要 `*minutes`。`map` 接收当前元素本身；经过 `copied()` 后就是 `i32`，所以直接相加。

如果省去 `copied()`，传到这些方法中的引用层级会不同。这正是读迭代器代码时常出现多个 `&` 或 `*` 的原因。先确定每一步的元素类型，再判断闭包收到什么。

### 不写 copied 时，filter 收到的是两层引用

下面是独立的完整程序，与开头采用相同规则：

```rust
fn main() {
    let minutes = [10, 35, 50, 20];
    let selected: Vec<i32> = minutes
        .iter()
        .filter(|minutes| **minutes >= 30)
        .map(|minutes| *minutes + 5)
        .collect();
    println!("{selected:?}");
}
```

仍输出 `[40, 55]`。`iter()` 的元素是 `&i32`，而 `filter` 再借用当前元素，参数就成了 `&&i32`；`map` 收到当前元素本身，即 `&i32`。因此这里分别写两个和一个 `*`。

并不是看见引用就要加 `copied()`。它要求元素可以按 `Copy` 复制，`String` 不满足。处理字符串时，可以继续使用引用，或明确克隆、取得所有权。

## collect 与 sum 为什么要写类型

`collect()` 可以收集成多种容器。`let selected: Vec<i32>` 给它提供了目标类型；也可以写 `.collect::<Vec<i32>>()`。

`sum()` 汇总元素，本例用 `let total: i32` 明确结果类型。类型推断依靠上下文，在可选结果很多时，补一个类型标注会比反复修改表达式更有效。

### 收集成什么类型，是调用方的选择

这是独立的完整程序，演示两种等价的类型标注位置：

```rust
fn main() {
    let first: Vec<i32> = (1..=3).map(|value| value * 2).collect();
    let second = (1..=3).map(|value| value * 2).collect::<Vec<i32>>();
    assert_eq!(first, second);
    println!("{first:?}");
    let total = first.iter().sum::<i32>();
    println!("合计：{total}");
    let empty: Vec<i32> = Vec::new();
    assert_eq!(empty.iter().sum::<i32>(), 0);
}
```

输出 `[2, 4, 6]` 和 `合计：12`。不要把推断失败理解成链条一定写错了；当结果可以有多种类型时，告诉编译器你希望得到哪一种。

## 迭代器通常按需要执行

`map` 和 `filter` 创建适配后的迭代器，仅仅构造它们通常不会处理所有元素。`collect`、`sum` 或 `for` 驱动它们不断取值，实际操作才随之发生。这叫惰性执行。

因此只写 `.map(|value| println!("{value}"))` 而不消费结果，不能用来保证完成打印。若目的是对每个元素做动作，写 `for` 更直接。若目的是产生新数据，再用转换和收集。

`find` 可以在找到第一项后停止，`any` 可以在第一次条件成立后停止。迭代器不意味着每次必须遍历完整集合。

### 一次 next，只让链条前进一步

下面是独立的完整程序：

```rust
fn main() {
    let mut doubled = [1, 2, 3].into_iter().map(|value| {
        println!("处理 {value}");
        value * 2
    });
    println!("迭代器已创建");
    println!("第一项：{:?}", doubled.next());
    let rest: Vec<i32> = doubled.collect();
    println!("剩下：{rest:?}");
}
```

输出：

```text
迭代器已创建
处理 1
第一项：Some(2)
处理 2
处理 3
剩下：[4, 6]
```

创建链条时闭包还没有执行。第一次 `next()` 消耗一个元素，随后 `collect()` 从当前位置继续，不会重新回到第一项。取完后，后续 `next()` 会得到 `None`。因为 `next` 改变迭代器的推进状态，绑定要写成 `mut`。

这里数组的 `into_iter()` 在 Rust 2024 中按值提供整数。下一节会专门观察拥有 `String` 元素的 `Vec`，避免把不同接收者的所有权行为混在一起。

### find 为什么可能没有检查所有元素

这是独立的完整程序：

```rust
fn main() {
    let values = [10, 35, 50, 20];
    let found = values.iter().copied().find(|value| {
        println!("检查 {value}");
        *value >= 30
    });
    println!("找到：{found:?}");
}
```

输出 `检查 10`、`检查 35`、`找到：Some(35)`。后面的 50 和 20 不再检查。最后两章会用 `find` 查找一条待办任务；它返回 `Option`，因为目标可能不存在。

## iter、iter_mut 与 into_iter

对 `Vec<T>` 而言，`iter()` 借用元素，`iter_mut()` 可变借用元素，`into_iter()` 消耗这个列表并取得各个元素的所有权。

示例第一次遍历 `titles.iter()` 后还能打印 `titles.len()`。第二次使用 `titles.into_iter()` 把 `String` 元素移给闭包，原列表的绑定随后不能继续使用。`.enumerate()` 给每个元素附带从 0 开始的序号。

关于是否消耗原数据，要同时看调用的接收者和具体类型。这里的表述针对拥有元素的 `Vec<T>`，不要把它机械推广到所有引用和自定义容器。

### 修改列表里的元素

这是独立的完整程序：

```rust
fn main() {
    let mut minutes = vec![10, 20];
    for value in minutes.iter_mut() {
        *value += 5;
    }
    println!("{minutes:?}");
}
```

输出 `[15, 25]`。循环变量是 `&mut i32`，`*value` 找到被借用的整数，修改会留在原列表中。

### 取得 String 的所有权后，原列表不能再用

下面是**故意不能编译的完整程序**：

```rust
fn main() {
    let titles = vec![String::from("读书"), String::from("写代码")];
    for title in titles.into_iter() {
        println!("{title}");
    }
    println!("还有 {} 项", titles.len());
}
```

会报告 `E0382`。`into_iter()` 消耗了这个 `Vec`；最后一行还在访问已经移动的值。如果遍历后仍需要原列表，改成 `titles.iter()` 或 `for title in &titles`。

还可以在保留原列表的同时收集借用视图。下面是独立的完整程序：

```rust
fn main() {
    let titles = vec![String::from("读书"), String::from("写代码")];
    let selected: Vec<&str> = titles
        .iter()
        .filter(|title| title.contains("读"))
        .map(|title| title.as_str())
        .collect();
    println!("{selected:?}");
    println!("原列表共 {} 项", titles.len());
}
```

输出 `["读书"]` 和 `原列表共 2 项`。`selected` 拥有自己的列表容器，但里面的 `&str` 仍借用 `titles` 中的文本；这些借用不能在原文本销毁后继续使用。

## 练习：筛选及格成绩

从 `[50, 60, 85, 40, 100]` 选出至少 60 的成绩，收集成 `Vec<i32>`，再计算及格成绩的总和。预期列表为 `[60, 85, 100]`，总和为 245。

<details>
<summary>参考答案：先自己完成再展开</summary>

```rust
fn main() {
    let scores = [50, 60, 85, 40, 100];
    let passed: Vec<i32> = scores
        .iter()
        .copied()
        .filter(|score| *score >= 60)
        .collect();
    let total: i32 = passed.iter().sum();
    assert_eq!(passed, [60, 85, 100]);
    assert_eq!(total, 245);
    println!("及格成绩：{passed:?}，合计：{total}");
}
```

运行 `cargo run -p rust-basics --example answer10`。再写一个循环版本，对照两个实现的输入、条件和输出。

</details>

### 把练习迁移到任务标题

创建 `Vec<String>`，内容为 `"学习 Rust"`、`"买水果"`、`"复习 Rust"`。筛选包含 `"Rust"` 的标题，再产生带 `"待办："` 前缀的新字符串，收集为 `Vec<String>`。

要求原列表还能使用。先写循环版本，再写迭代器版本。你需要借用原列表，并通过 `format!` 为结果创建新文本；不必克隆整个原列表。预期新列表是 `["待办：学习 Rust", "待办：复习 Rust"]`。

进入下一章前，尝试说出一条调用链里 `iter`、`filter`、`map`、`collect` 各自提供或接收什么。链条变长后不好解释时，拆开即可。

## 官方延伸阅读

- [闭包](https://doc.rust-lang.org/book/ch13-01-closures.html)
- [迭代器](https://doc.rust-lang.org/book/ch13-02-iterators.html)

外部文档查阅日期：2026-10-13。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：泛型、trait 与生命周期](/posts/rust-09-traits/) · [下一章：实战：任务与命令](/posts/rust-11-taskbook/)
