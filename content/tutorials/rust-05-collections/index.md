+++
url = "/posts/rust-05-collections/"
title = "Rust 入门 05：字符串、列表和字典"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-17
draft = false
author = "Hex4C59"
description = "处理中文字符串，使用 Vec、切片和 HashMap，理解索引、遍历和可变引用。"
summary = "处理中文字符串，使用 Vec、切片和 HashMap，理解索引、遍历和可变引用。"
tags = ["Rust", "字符串", "集合"]
categories = ["programming"]
series = ["rust-from-zero"]
series_order = 5
series_label = "字符串与集合"
series_part = "理解数据如何使用"
series_number = 5
ShowToc = true
source_kind = "original"
article_type = "tutorial"
series_role = "chapter"
+++

上一章已经能让函数读取和修改一个字符串。接下来处理更常见的情况：标题可能含中文，记录可能从三条增加到四条，还需要按名称统计次数。

本章学习 `String`、`Vec`、切片和 `HashMap`。学完后，你应该能修改一组学习记录，计算其中一部分的总和，并统计一句文本中各单词出现的次数。遇到空文本或不存在的位置时，也要知道应该怎样读取。

继续在自己的 `hello-rust` 项目里练习。完整程序可以替换整个 `src/main.rs`，保存后运行 `cargo run`。几个例子中的 `Some(...)` 和 `None` 暂时分别读作“有值”和“没有值”；本章先观察输出，第六章再学习怎样取出里面的数据。

## String 与 &str 的分工

`String` 拥有文本内容，可以修改并增长；`&str` 只读地访问一段已有的有效 UTF-8 文本，适合只读取文本的函数。UTF-8 是文本的字节编码方式，下一节会用中文说明它怎样影响长度。字符串字面量 `"你好"` 可以作为 `&str` 使用，`String::from("你好")` 则创建拥有内容的字符串。

先把上一章的追加操作再练一次。完整程序：

```rust
fn main() {
    let mut title = String::from("学习");
    title.push_str(" Rust");
    title.push('！');

    println!("{title}");
    println!("包含 Rust：{}", title.contains("Rust"));
}
```

预期输出：

```text
学习 Rust！
包含 Rust：true
```

这几个常用方法的结果不同：

| 方法 | 作用 | 是否修改原文本 |
| --- | --- | --- |
| `push('！')` | 追加一个 `char` | 是 |
| `push_str(" Rust")` | 追加一段文本 | 是 |
| `trim()` | 得到去掉首尾空白的文本视图 | 否 |
| `contains("Rust")` | 判断是否包含这段子串 | 否 |
| `to_string()` | 从文本视图创建拥有内容的 `String` | 否 |

`trim()` 不会把原字符串里的空格删除。完整程序：

```rust
fn main() {
    let input = String::from("  cargo  ");
    let cleaned = input.trim();
    let owned = cleaned.to_string();

    println!("原文：[{input}]");
    println!("处理后：[{cleaned}]");
    println!("独立字符串：[{owned}]");
}
```

预期输出：

```text
原文：[  cargo  ]
处理后：[cargo]
独立字符串：[cargo]
```

方括号只是为了看清首尾空格。`cleaned` 借用 `input` 中的文本，`owned` 则拥有独立内容。需要让处理后的文本脱离原字符串长期保存时，可以创建这样的 `String`。

这里还适用第四章的规则：共享视图后面仍要使用时，不能同时修改原字符串。`trim()` 得到视图，并没有让借用规则消失。

## 中文文本的长度该怎样计算

UTF-8 是一种把 Unicode 文本编码为字节的方式。“你”和“好”各占三个 UTF-8 字节，英文和空格各占一个，所以 `"你好 Rust"` 是 11 字节。

完整程序：

```rust
fn main() {
    let text = "你好 Rust";
    println!("字节数：{}", text.len());
    println!("标量值数：{}", text.chars().count());

    for ch in "你好".chars() {
        println!("逐项读取：{ch}");
    }
}
```

预期输出：

```text
字节数：11
标量值数：7
逐项读取：你
逐项读取：好
```

`len()` 对字符串返回字节数。`chars()` 按 Unicode 标量值遍历，`count()` 统计遍历得到的项目数。因此 `chars().count()` 在这里得到 7。这里把两个方法接着调用：先得到遍历对象，再统计项目数。第十章会进一步讲这种迭代器写法。

标量值也不一定等于人眼看到的一个完整字符。下面用字母加组合重音观察这个区别。完整程序：

```rust
fn main() {
    let text = "e\u{301}";
    println!("显示：{text}");
    println!("字节数：{}", text.len());
    println!("标量值数：{}", text.chars().count());
}
```

预期输出：

```text
显示：é
字节数：3
标量值数：2
```

`\u{301}` 在字符串里写入一个组合重音标量值。它与前面的 `e` 通常一起显示为带重音的字母，但这段文本仍由两个标量值组成。某些 emoji 序列也会包含多个标量值。

处理文本时，先确定要数什么：文件占多少字节，用字节数；按标量值逐项处理，用 `chars()`。人眼字符数、字形分割和自然语言分词需要另外考虑，不能把 `chars().count()` 当成所有场景通用的“字数”。

## 为什么不能用 text[0]

`text[0]` 容易让人以为“取第一个字”，但整数 0 不能同时清楚表达字节位置、标量值位置和人眼字符位置。Rust 不支持用整数索引 `String` 得到一个字符。

下面是故意无法编译的完整程序：

```rust
fn main() {
    let text = String::from("你好");
    println!("{}", text[0]);
}
```

运行 `cargo check`，应得到 `E0277`。下载包的 `compile-fail/string_index.rs` 保存了这个例子，在 `rust-course` 目录也可以运行：

```sh
rustc --edition 2024 compile-fail/string_index.rs
```

要读取第一个 Unicode 标量值，可以使用 `chars().next()`。完整程序：

```rust
fn main() {
    let text = "你好 Rust";
    println!("第一项：{:?}", text.chars().next());
    println!("空文本：{:?}", "".chars().next());
}
```

预期输出：

```text
第一项：Some('你')
空文本：None
```

`next()` 请求下一项，字符串为空就没有可返回的字符。`{:?}` 使用调试格式，能把 `Some(...)` 和 `None` 显示出来；它还没有把 `Some` 里面的字符直接取出来。

字符串可以按字节范围取得切片，但范围边界必须落在 UTF-8 编码边界上。完整程序：

```rust
fn main() {
    let text = "你好 Rust";
    println!("完整的首字：{}", &text[..3]);
    println!("截断中文：{:?}", text.get(..1));
    println!("超过长度：{:?}", text.get(..100));
}
```

预期输出：

```text
完整的首字：你
截断中文：None
超过长度：None
```

这里确定“你”占三个字节，才直接写 `[..3]`。处理任意输入时，需要确认切分位置，不能猜一个数字就当作文字边界。`get(范围)` 在范围越界或边界无效时返回 `None`。

下面是故意在运行时失败的完整程序，请与正常例子分开运行：

```rust
fn main() {
    let text = "你好 Rust";
    println!("{}", &text[..1]);
}
```

它能编译，但运行时会 panic，因为范围把“你”截成了一个字节。panic 在这个例子中会使程序以失败状态结束。出现这类错误时，要检查索引和边界；正常处理可能无效的范围时，可以用上面的 `get`。

## Vec 是长度可以变化的列表

第二章学过的数组长度固定，例如 `[20, 30, 40]` 始终有三个元素。需要继续追加记录时，使用 `Vec`。`Vec<T>` 中的 `T` 表示元素类型，整个列表保存同一类型的元素。第九章会解释这种类型参数写法。

完整程序：

```rust
fn main() {
    let mut minutes: Vec<i32> = vec![20, 30, 40];
    minutes.push(10);
    println!("追加后：{minutes:?}");

    let removed = minutes.pop();
    println!("取出的末项：{removed:?}");
    println!("剩余：{minutes:?}，共 {} 条", minutes.len());

    let mut empty: Vec<i32> = Vec::new();
    println!("是否为空：{}", empty.is_empty());
    println!("空列表取末项：{:?}", empty.pop());
}
```

预期输出：

```text
追加后：[20, 30, 40, 10]
取出的末项：Some(10)
剩余：[20, 30, 40]，共 3 条
是否为空：true
空列表取末项：None
```

`vec![...]` 用现有元素创建列表，`Vec::new()` 创建空列表。空列表没有元素可帮助推断类型，所以这里明确写了 `Vec<i32>`。

`push` 向末尾追加元素；`pop` 从末尾移出并返回一项。因为列表可能为空，`pop` 返回的结果也要区分有值和没值。`len()` 返回元素个数，`is_empty()` 返回是否为空。读到长度时，要分清它是在数列表元素，还是字符串的字节。

## 读取元素时怎样处理不存在的位置

列表使用从 0 开始的索引。确定位置存在时，可以直接索引；位置可能不存在时，使用 `get`。完整程序：

```rust
fn main() {
    let minutes = vec![20, 30, 40];
    println!("第一项：{}", minutes[0]);
    println!("第二项：{:?}", minutes.get(1));
    println!("第十项：{:?}", minutes.get(9));
}
```

预期输出：

```text
第一项：20
第二项：Some(30)
第十项：None
```

`minutes[9]` 会越界并在运行时 panic。`minutes.get(9)` 返回 `None`，让程序可以继续判断该怎样处理。第六章会用 `match` 分别处理有值和没值的情况。

当列表保存 `String` 时，读取元素还要考虑第四章的所有权。完整程序：

```rust
fn main() {
    let titles = vec![String::from("学习 Rust"), String::from("写练习")];
    let first = &titles[0];

    println!("第一项：{first}");
    println!("列表仍有 {} 项", titles.len());
}
```

预期输出：

```text
第一项：学习 Rust
列表仍有 2 项
```

`&titles[0]` 借用第一项，字符串仍由列表拥有。如果直接写成 `let first = titles[0];`，编译器会拒绝：它既不会自动复制整个字符串，也不允许这样从索引位置移走字符串，留下一个没有值的列表元素。整数可以复制，列表中的 `String` 则仍要按第四章的规则处理；这里只读第一项，所以保留借用即可。

## 遍历时借用还是移动

对 `Vec`，这三种写法有不同含义：

| 写法 | 每轮拿到的值 | 循环后原列表 |
| --- | --- | --- |
| `for value in &list` | `&T`，共享引用 | 仍可使用 |
| `for value in &mut list` | `&mut T`，可变引用 | 仍可使用 |
| `for value in list` | `T`，取得元素所有权 | `Vec` 被消耗，原绑定不能继续使用 |

只读取标题时，共享借用列表即可。完整程序：

```rust
fn main() {
    let titles = vec![String::from("读一节"), String::from("写一遍")];

    for title in &titles {
        println!("待办：{title}");
    }

    println!("总数：{}", titles.len());
}
```

预期输出：

```text
待办：读一节
待办：写一遍
总数：2
```

如果去掉循环中的 `&`，循环就取得整个 `Vec` 的所有权。下面是故意无法编译的完整程序：

```rust
fn main() {
    let titles = vec![String::from("读一节"), String::from("写一遍")];

    for title in titles {
        println!("待办：{title}");
    }

    println!("总数：{}", titles.len());
}
```

应得到 `E0382`。这里遍历的是 `Vec`；第三章按值遍历固定长度整数数组时，数组能够复制，不能把那一例的行为套到所有容器上。

修改现有元素时，可以可变借用列表。完整程序：

```rust
fn main() {
    let mut minutes = vec![20, 30, 40];

    for value in &mut minutes {
        *value += 5;
    }

    println!("{minutes:?}");
}
```

预期输出：

```text
[25, 35, 45]
```

`value` 是一个 `&mut i32`，指向当前元素。`*value` 访问它指向的位置，`*value += 5` 修改原元素。这里的 `*` 叫解引用，不是乘号。共享遍历得到的也是引用；需要取出可复制的整数值时，可以写 `*value`。

## 遍历期间不能随意改变列表长度

向 `Vec` 追加元素可能需要重新分配存储空间，原先借出的元素引用就不能假定继续有效。下面是故意无法编译的完整程序：

```rust
fn main() {
    let mut minutes = vec![20, 30, 40];

    for value in &minutes {
        println!("{value}");
        minutes.push(10);
    }
}
```

应得到 `E0502`。循环仍在共享借用列表，却又要通过 `push` 修改它。

如果新增记录与遍历过程无关，可以先 `push`，再遍历。如果只是要修改已有记录，使用上一节的 `&mut minutes` 循环，不在循环中改变列表长度。需要根据旧记录生成新记录时，可以先用另一份列表收集结果，等原列表的遍历结束后再合并。

## 切片提供列表的一部分

第三章的统计函数接收 `[u32; 3]`，只能处理三个元素。现在让函数接收切片，就能查看数组或列表中不同长度的一段数据。

完整程序：

```rust
fn total(numbers: &[i32]) -> i32 {
    let mut sum = 0;
    for number in numbers {
        sum += *number;
    }
    sum
}

fn main() {
    let array = [20, 30, 25];
    let list = vec![10, 20, 30, 40];

    println!("数组合计：{}", total(&array));
    println!("列表合计：{}", total(&list));
    println!("前两项：{}", total(&list[..2]));
    println!("从第三项开始：{}", total(&list[2..]));
    println!("空切片：{}", total(&[]));
}
```

预期输出：

```text
数组合计：75
列表合计：100
前两项：30
从第三项开始：70
空切片：0
```

`&[i32]` 表示借来的整数切片，让函数查看一段连续的整数及其长度，元素仍由原数组或列表拥有。这里的 `&array` 和 `&list` 可以转换成函数需要的切片，不需要复制出一份新列表。循环中的 `number` 是共享引用，`*number` 取得这里可复制的整数值。

以 `[10, 20, 30, 40]` 为例：

| 写法 | 切片中的元素 |
| --- | --- |
| `&list[..]` | 10、20、30、40 |
| `&list[..2]` | 10、20 |
| `&list[2..]` | 30、40 |
| `&list[1..3]` | 20、30 |

范围右边界不包含在内。列表切片的索引按元素计数，字符串切片的范围按字节计数；两者都需要有效边界，不能超过各自的长度。

只读函数接收 `&[i32]`，通常比限定为 `&Vec<i32>` 更方便，因为数组也能传入。共享切片不允许修改元素，也不能通过它向原列表追加元素。

可变切片 `&mut [i32]` 则允许修改这一段中的元素。完整程序：

```rust
fn add_bonus(records: &mut [i32]) {
    for record in records {
        *record += 5;
    }
}

fn main() {
    let mut records = vec![10, 20, 30];
    add_bonus(&mut records[..2]);
    println!("{records:?}");
}
```

预期输出：

```text
[15, 25, 30]
```

只有前两项被修改。函数借到的是原列表的一段，并没有新建两个独立元素。切片长度在这次访问中已经确定，函数不能像操作 `Vec` 那样调用 `push`。

## HashMap 按键保存值

列表按位置找数据，字典按键找数据。例如用 `"周一"` 找到当天的学习分钟数。Rust 标准库中的 `HashMap` 可以保存这种对应关系。

完整程序：

```rust
use std::collections::HashMap;

fn main() {
    let mut minutes: HashMap<String, u32> = HashMap::new();
    minutes.insert(String::from("周一"), 20);
    minutes.insert(String::from("周二"), 30);
    minutes.insert(String::from("周一"), 25);

    println!("周一：{:?}", minutes.get("周一"));
    println!("周三：{:?}", minutes.get("周三"));
    println!("记录数：{}", minutes.len());
}
```

预期输出：

```text
周一：Some(25)
周三：None
记录数：2
```

`use std::collections::HashMap` 把这个标准库名称引入当前文件，后面就能直接写 `HashMap`。`HashMap<String, u32>` 表示键是拥有内容的字符串，值是非负整数。

对已有的键再次 `insert`，会替换原值，因此“周一”最终是 25，字典仍有两条记录。键中的 `String` 会移进字典；以后使用输入文本做键时，也要留意第四章的所有权规则。

这里可以用 `"周一"` 这样的 `&str` 查询 `String` 键，不必为一次查询重新创建字符串。查不到时，`get` 返回 `None`。直接写 `minutes["周三"]` 则会因键不存在而 panic。

遍历 `HashMap` 的顺序没有固定保证。需要稳定的展示顺序时，可以按明确的键顺序查询，或先排序。本章的预期输出都避免依赖字典的遍历顺序。

## 词频统计中的 entry 链

统计单词次数时，每遇到一个词，要么把已有计数加一，要么先创建计数。`entry` 可以把这两种情况接起来。完整程序：

```rust
use std::collections::HashMap;

fn main() {
    let mut counts: HashMap<&str, u32> = HashMap::new();

    for word in "rust cargo rust".split_whitespace() {
        let count = counts.entry(word).or_insert(0);
        *count += 1;
    }

    println!("rust：{:?}", counts.get("rust"));
    println!("cargo：{:?}", counts.get("cargo"));
}
```

预期输出：

```text
rust：Some(2)
cargo：Some(1)
```

`split_whitespace()` 按空白分开文本，循环依次得到 `rust`、`cargo`、`rust`。它按原有大小写保留单词，不做中文分词；本例只统计按空白分开的英文单词。

`counts.entry(word).or_insert(0)` 先检查这个键是否已有值；有就使用已有计数，没有就插入 0，最后返回计数的可变引用。`count` 在这里是 `&mut u32`，`*count += 1` 更新字典里的原值，没有把计数复制到字典外再修改。本轮用完引用后，这次可变借用结束，下一轮才继续查找并更新下一个词。

| 读到的单词 | 加一前的计数 | 加一后的计数 |
| --- | --- | --- |
| 第一次 `rust` | 新建为 0 | 1 |
| `cargo` | 新建为 0 | 1 |
| 第二次 `rust` | 已有 1 | 2 |

键的类型是 `&str`，借自程序中的固定文本。如果键来自短暂存在的输入，却需要让字典继续保存它，通常应创建拥有内容的 `String`。引用仍依赖原文本有效，不会延长原文本的存活时间。

## 把文本、列表和字典组合起来

下面的完整程序对应下载包的 `basics/examples/ch05_collections.rs`：

```rust
use std::collections::HashMap;

fn total(numbers: &[i32]) -> i32 {
    let mut sum = 0;
    for number in numbers {
        sum += *number;
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

在解压后的 `rust-course` 目录运行：

```sh
cargo run -p rust-basics --example ch05_collections
```

这里直接索引 `counts["rust"]`，是因为循环中已经处理过 `rust`，确定这个键存在。如果输入可以任意修改，查询时应改用 `get` 处理键缺失的情况。

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

预期输出：

```text
[20, 40, 60]，中文：6 字节、2 个标量值
```

运行 `cargo run -p rust-basics --example answer05`。再把列表改成 `let mut records: Vec<i32> = Vec::new();`，循环应执行零次，列表仍为空，第十项仍不存在；对应断言也要检查空列表。

再试 `"".chars().next()`，应得到 `None`。空文本的字节数和标量值数都应是 0。

</details>

## 练习：统计三个单词的出现次数

统计 `"rust cargo rust borrow cargo"`。按 `rust`、`cargo`、`borrow` 的顺序显示结果，不依赖字典内部的遍历顺序。先预测每个词出现几次，再运行核对。

<details>
<summary>参考答案：先自己完成再展开</summary>

```rust
use std::collections::HashMap;

fn main() {
    let mut counts: HashMap<&str, u32> = HashMap::new();
    for word in "rust cargo rust borrow cargo".split_whitespace() {
        let count = counts.entry(word).or_insert(0);
        *count += 1;
    }

    for word in ["rust", "cargo", "borrow"] {
        println!("{word}：{:?}", counts.get(word));
    }

    assert_eq!(counts.get("rust"), Some(&2));
    assert_eq!(counts.get("cargo"), Some(&2));
    assert_eq!(counts.get("borrow"), Some(&1));
}
```

预期输出：

```text
rust：Some(2)
cargo：Some(2)
borrow：Some(1)
```

这份答案在正文中给出，可以替换自己项目的 `src/main.rs` 运行。`get` 返回借来的计数，所以断言中的预期值写成 `Some(&2)`；`{:?}` 打印引用时仍显示数值。

把输入改为空字符串时，循环不执行，字典保持为空，三个查询都应得到 `None`。先修改断言的预期，再运行验证。

</details>

## 进入下一章前检查

从空白文件写一个程序：创建可增长的学习记录列表，追加一项，通过可变借用给每项加上固定分钟数，再用切片函数计算前两项的总和。随后读取一个可能不存在的位置，用调试格式观察结果。

你还应能说明：字符串的 `len()` 数什么？为什么 `String` 不能用整数取“第一个字”？`for value in list` 与 `for value in &list` 怎样影响后续访问？`HashMap` 中同一个键插入两次，会发生什么？

下一章会给任务定义自己的数据类型，并正式处理本章出现的 `Some` 和 `None`。到那时，程序就能根据是否找到记录，显示不同的提示。

## 官方延伸阅读

- [UTF-8 字符串](https://doc.rust-lang.org/book/ch08-02-strings.html)
- [Vec 的使用](https://doc.rust-lang.org/book/ch08-01-vectors.html)
- [HashMap 的使用](https://doc.rust-lang.org/book/ch08-03-hash-maps.html)
- [切片类型](https://doc.rust-lang.org/book/ch04-03-slices.html)

外部文档查阅日期：2026-10-13。代码验证使用 Rust 2024 edition；工具链版本和实际验证范围见[学习指南](/posts/rust-00-learning-guide/#版本与验证范围)。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：所有权与借用](/posts/rust-04-ownership/) · [下一章：结构体与枚举](/posts/rust-06-modeling/)
