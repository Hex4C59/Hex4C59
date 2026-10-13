+++
title = "Rust 入门 05：字符串、列表和字典"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-12T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "处理中文字符串，使用 Vec、切片和 HashMap，理解索引、遍历和可变引用。"
summary = "处理中文字符串，使用 Vec、切片和 HashMap，理解索引、遍历和可变引用。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 5
series_label = "字符串与集合"
series_part = "理解数据如何使用"
series_number = 5
ShowToc = true
+++

任务标题是文本，多条任务需要列表，按名称统计次数需要字典。本章学习这几种数据容器，并解释为什么字符串不能直接用 `text[0]` 取出“第一个字”。

在解压后的 `rust-course` 目录运行：

```sh
cargo run -p rust-basics --example ch05_collections
```

完整代码位于 `basics/examples/ch05_collections.rs`。也可以把下面的代码完整替换到自己项目的 `src/main.rs`，再运行 `cargo run`。

```rust
use std::collections::HashMap;

fn total(numbers: &[i32]) -> i32 {
    let mut sum = 0;
    for number in numbers {
        sum += number;
    }
    sum
}

fn main() {
    let text = String::from("你好 Rust");
    println!("字节数：{}，标量值数：{}", text.len(), text.chars().count());
    println!("第一个标量值：{:?}", text.chars().next());

    let mut minutes = vec![20, 30, 40];
    minutes.push(10);
    for value in &mut minutes {
        *value += 5;
    }
    println!("记录：{minutes:?}");
    println!("前两天合计：{}", total(&minutes[..2]));
    println!("第十条记录：{:?}", minutes.get(9));

    let mut counts = HashMap::new();
    for word in "rust cargo rust".split_whitespace() {
        let count = counts.entry(word).or_insert(0);
        *count += 1;
    }
    println!("rust 出现 {} 次", counts["rust"]);
}
```

预期输出：

```text
字节数：11，标量值数：7
第一个标量值：Some('你')
记录：[25, 35, 45, 15]
前两天合计：60
第十条记录：None
rust 出现 2 次
```

`Some` 与 `None` 表示有值和没值，下一章会正式讲它们。

## String 与 &str 的分工

`String` 拥有文本，可以修改并增长。`&str` 是对有效 UTF-8 文本的借用视图，适合只读的函数参数。字符串字面量 `"你好"` 可以作为 `&str` 使用；`String::from("你好")` 则创建拥有内容的字符串。

常用方法有 `push('！')` 追加一个 `char`，`push_str(" Rust")` 追加文本，`trim()` 获取去掉首尾空白的视图，`contains("Rust")` 检查子串。`.to_string()` 可以从文本视图创建拥有内容的 `String`。

UTF-8 是一种把 Unicode 文本编码为字节的方式。示例中的“你”和“好”各占三个 UTF-8 字节，英文和空格各占一个，所以 `"你好 Rust"` 是 11 字节。

`len()` 对字符串返回字节数。`chars().count()` 返回 Unicode 标量值的个数，本例是 7。组合字符和某些 emoji 序列可能包含多个标量值，因此这个计数不等于所有情况下的人眼字符数。

## 为什么不能用 text[0]

索引 0 对字节序列和对文字含义不同。Rust 不支持用整数索引 `String` 得到一个字符。`compile-fail/string_index.rs` 用来观察这个错误：

```sh
rustc --edition 2024 compile-fail/string_index.rs
```

`text.chars().next()` 获取第一个 Unicode 标量值。因为字符串可能为空，返回值需要表达“没有第一项”，所以示例输出 `Some('你')`。

字符串可以按字节范围切片，但边界必须恰好落在 UTF-8 编码边界。`&text[0..1]` 对中文“你”的第一个字节进行截断，会在运行时 panic。处理任意用户文本时，优先按 `chars()` 遍历，或用 `get(范围)` 处理可能无效的边界。按标量值遍历仍不等于完整的自然语言分词或字形分割。

## Vec 是长度可以变化的列表

`vec![20, 30, 40]` 创建 `Vec<i32>`。`Vec<T>` 中的 `T` 表示元素类型，整个列表的元素具有同一类型。第九章会解释这种写法。

`push` 向末尾追加元素，`pop` 从末尾取出一项；列表可能为空，因此 `pop` 返回的值也需要表示是否存在。

`minutes[0]` 可以直接取得有效位置的元素，但越界会 panic。`minutes.get(9)` 返回 `None`，允许我们正常处理不存在的第十条记录。

## 遍历时借用还是移动

| 写法 | 每轮拿到的值 | 循环后原列表 |
| --- | --- | --- |
| `for value in &list` | `&T`，共享引用 | 仍可使用 |
| `for value in &mut list` | `&mut T`，可变引用 | 仍可使用 |
| `for value in list` | `T`，取得元素所有权 | `Vec` 被消耗，原绑定不能继续使用 |

示例用 `for value in &mut minutes` 修改列表中的数值。`value` 是引用，`*value` 访问它指向的位置；`*value += 5` 将 5 加到原元素上。这里的 `*` 叫解引用，不是乘号。

遍历 `&Vec<i32>` 时，即使元素是 `Copy`，循环默认仍提供引用。是否复制，要看使用它的表达式或显式的 `.copied()`。

## 切片提供列表的一部分

`&minutes[..2]` 是前两项的只读切片，范围的右边界 2 不包含在内。它没有创建新的元素列表。

`fn total(numbers: &[i32])` 能查看数组的一段，也能查看 `Vec` 的一段。函数只需要读取元素时，接收切片通常比限定为 `&Vec<i32>` 更方便。切片不能通过这个共享引用增长原列表。

## HashMap 按键保存值

`HashMap` 是字典，把键映射到值。例子将英文单词映射到出现次数。`use std::collections::HashMap` 把标准库中的名称引入当前文件，后面就能直接写 `HashMap`。

`split_whitespace()` 按空白分开文本，依次得到单词。`counts.entry(word).or_insert(0)` 的意思是：找到这个词的计数；如果还没有，先放入 0；返回可修改的计数引用。再通过 `*count += 1` 更新原值。

本例用的键 `&str` 借自程序中的固定文本。需要保留来自短暂输入的键时，常用拥有内容的 `String`。遍历 `HashMap` 的顺序没有固定保证，所以输出完整词频表时，若需要稳定顺序，应先排序。

## 练习：修改记录，检查不存在的位置

创建 `[10, 20, 30]` 对应的 `Vec`，把每个数字乘 2，再确认第十项不存在。最后比较 `"中文"` 的字节数和标量值数。要求不通过越界索引制造 panic。

<details>
<summary>参考答案：先自己完成再展开</summary>

```rust
fn main() {
    let mut records = vec![10, 20, 30];
    for record in &mut records {
        *record *= 2;
    }
    assert_eq!(records, [20, 40, 60]);
    assert_eq!(records.get(9), None);
    let text = "中文";
    assert_eq!(text.len(), 6);
    assert_eq!(text.chars().count(), 2);
    println!("{records:?}，中文：6 字节、2 个标量值");
}
```

运行 `cargo run -p rust-basics --example answer05`。再试 `""` 的 `chars().next()`，应得到 `None`。

</details>

## 官方延伸阅读

- [UTF-8 字符串](https://doc.rust-lang.org/book/ch08-02-strings.html)
- [Vec 的使用](https://doc.rust-lang.org/book/ch08-01-vectors.html)
- [HashMap 的使用](https://doc.rust-lang.org/book/ch08-03-hash-maps.html)

外部文档查阅日期：2026-10-12。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：所有权与借用](/posts/rust-04-ownership/) · [下一章：结构体与枚举](/posts/rust-06-modeling/)
