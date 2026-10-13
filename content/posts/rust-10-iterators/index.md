+++
title = "Rust 入门 10：闭包和迭代器"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-12T09:00:00+08:00
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

## 闭包是可以放在表达式里的小函数

`|minutes| minutes + 5` 接收一个值，返回加 5 的结果。参数写在两条竖线之间，函数体很短时可以只写表达式；需要多行时使用 `{}`。

`|minutes| *minutes >= threshold` 使用了外面的 `threshold`。闭包可以捕获周围的变量，而普通 `fn` 定义不能直接捕获调用位置的局部变量。这里仅仅读取阈值，编译器会选择合适的捕获方式。

闭包的参数和返回类型通常由使用位置推断。第一次调用确定的类型不会让同一个闭包随后自动适用于任意其他类型。需要类型参数时，使用上一章学习的泛型函数。

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

## collect 与 sum 为什么要写类型

`collect()` 可以收集成多种容器。`let selected: Vec<i32>` 给它提供了目标类型；也可以写 `.collect::<Vec<i32>>()`。

`sum()` 汇总元素，本例用 `let total: i32` 明确结果类型。类型推断依靠上下文，在可选结果很多时，补一个类型标注会比反复修改表达式更有效。

## 迭代器通常按需要执行

`map` 和 `filter` 创建适配后的迭代器，仅仅构造它们通常不会处理所有元素。`collect`、`sum` 或 `for` 驱动它们不断取值，实际操作才随之发生。这叫惰性执行。

因此只写 `.map(|value| println!("{value}"))` 而不消费结果，不能用来保证完成打印。若目的是对每个元素做动作，写 `for` 更直接。若目的是产生新数据，再用转换和收集。

`find` 可以在找到第一项后停止，`any` 可以在第一次条件成立后停止。迭代器不意味着每次必须遍历完整集合。

## iter、iter_mut 与 into_iter

对 `Vec<T>` 而言，`iter()` 借用元素，`iter_mut()` 可变借用元素，`into_iter()` 消耗这个列表并取得各个元素的所有权。

示例第一次遍历 `titles.iter()` 后还能打印 `titles.len()`。第二次使用 `titles.into_iter()` 把 `String` 元素移给闭包，原列表的绑定随后不能继续使用。`.enumerate()` 给每个元素附带从 0 开始的序号。

关于是否消耗原数据，要同时看调用的接收者和具体类型。这里的表述针对拥有元素的 `Vec<T>`，不要把它机械推广到所有引用和自定义容器。

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

## 官方延伸阅读

- [闭包](https://doc.rust-lang.org/book/ch13-01-closures.html)
- [迭代器](https://doc.rust-lang.org/book/ch13-02-iterators.html)

外部文档查阅日期：2026-10-12。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：泛型、trait 与生命周期](/posts/rust-09-traits/) · [下一章：实战：任务与命令](/posts/rust-11-taskbook/)
