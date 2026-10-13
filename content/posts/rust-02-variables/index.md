+++
title = "Rust 入门 02：用变量和类型表示数据"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "学习变量、可变性和常用数据类型，拆解 let 绑定、类型推断、数字后缀和显式转换的规则。"
summary = "学习变量、可变性和常用数据类型，拆解 let 绑定、类型推断、数字后缀和显式转换的规则。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 2
series_label = "变量与类型"
series_part = "把程序写出来"
series_number = 2
ShowToc = true
+++

上一节的程序只能打印固定文字。这一节用变量保存姓名和学习时长，计算还差多少分钟，再输出结果。学完后，你应该能写一个简单的费用或时长计算程序，并解释每个变量保存了什么。

继续使用第一节创建的 `hello-rust` 项目。标为“完整程序”的 Rust 代码块都可以替换整个 `src/main.rs`，保存后在项目目录运行 `cargo run`。各个示例相互独立，不要把几个 `fn main` 写在同一个文件里。

## 2.1 用 let 给数据起名字

先运行这个完整程序：

```rust
fn main() {
    let name = "小林";
    let minutes = 20;

    println!("{name} 今天学习了 {minutes} 分钟");
}
```

输出：

```text
小林 今天学习了 20 分钟
```

`let name = "小林";` 建立一个名为 `name` 的变量绑定，之后可以通过这个名字使用对应的值。`let minutes = 20;` 保存一个整数。等号右边是要保存的值，左边是变量名称。

这里的 `=` 表示赋值或初始化，不表示“比较是否相等”。比较相等使用 `==`，稍后会用到。

变量名通常采用英文小写字母和下划线，例如 `total_minutes`。名字区分大小写，`minutes` 和 `Minutes` 是两个名称。选择能说明用途的名字，比全部写成 `a`、`b` 更容易检查代码。

把 `minutes` 改成 35，再运行，确认输出的变化。只需修改变量的值，不必到每条输出中查找数字 20。

## 2.2 把变量和计算结果放进输出

`println!("{minutes}")` 使用当前可访问的 `minutes`，打印它的值。花括号必须写在字符串里。

完整程序：

```rust
fn main() {
    let today = 20;
    let yesterday = 30;
    let total = today + yesterday;

    println!("今天：{today} 分钟");
    println!("昨天：{yesterday} 分钟");
    println!("两天合计：{total} 分钟");
    println!("直接计算也可以：{} 分钟", today + yesterday);
}
```

合计输出为 50。最后一行的 `{}` 对应后面的表达式，Rust 先计算 `today + yesterday`，再把结果填进去。如果写了多个 `{}`，后面的参数就按顺序填入。

`"total"` 是五个字母组成的固定文本，`"{total}"` 才会把变量的值填进去。第一次打印变量时，这个区别容易漏掉。

## 2.3 默认不能重新赋值，需要修改时加 mut

下面的完整程序故意无法编译：

```rust
fn main() {
    let minutes = 20;
    minutes = 30;
    println!("{minutes}");
}
```

Rust 默认不允许给这个绑定重新赋值，通常报告 `E0384`。确实需要修改时，在声明中加 `mut`：

```rust
fn main() {
    let mut minutes = 20;
    println!("修改前：{minutes}");
    minutes = 30;
    minutes += 10;
    println!("修改后：{minutes}");
}
```

修复后的程序先输出 `修改前：20`，再输出 `修改后：40`。`mut` 表示允许修改，`minutes += 10` 等价于 `minutes = minutes + 10`。`-=`、`*=`、`/=` 也有类似含义。

不需要给所有变量都加 `mut`。变量不需要重新赋值时，就保留默认写法，让读代码的人也能看出这一点。编译器提示某个 `mut` 多余时，可以去掉它。

前面的错误例子也保存在下载包的 `compile-fail/immutable.rs`。在 `rust-course` 目录可运行：

```sh
rustc --edition 2024 compile-fail/immutable.rs
rustc --explain E0384
```

第一条预期失败，第二条查看这种错误的解释。

## 2.4 类型说明一个值能怎样使用

每个值有类型。整数可以参与加减乘除，布尔值表示真或假，文本用来保存文字。编译器会检查操作是否适用于这些类型。

完整程序：

```rust
fn main() {
    let temperature: i32 = -5;
    let minutes: u32 = 30;
    let average: f64 = 22.5;
    let finished: bool = false;
    let initial: char = '林';
    let name: &str = "小林";

    println!("温度：{temperature}，分钟数：{minutes}");
    println!("平均值：{average}，完成了吗：{finished}");
    println!("姓名：{name}，姓氏：{initial}");
}
```

冒号后的名称是类型标注。先掌握这些常用类型：

| 类型 | 表示什么 | 本节怎样选 |
| --- | --- | --- |
| `i32` | 32 位有符号整数，可以为负 | 温度、整数练习；无其他约束的整数常推断为它 |
| `u32` | 32 位无符号整数，只能是非负值 | 分钟数、普通计数 |
| `usize` | 与目标平台地址宽度对应的无符号整数 | 数组长度和索引 |
| `f64` | 双精度浮点数，用于近似小数 | 平均值、比例 |
| `bool` | 真或假 | `true` 或 `false` |
| `char` | 一个 Unicode 标量值 | 单引号里的 `'林'`、`'A'` |
| `&str` | 对一段文本的借用视图 | 本节用于双引号里的固定文本 |

`&str` 中的 `&` 涉及第四节的借用，现在只需要会写固定文本。`char` 使用单引号，字符串使用双引号，`'林'` 与 `"林"` 是不同类型。

Unicode 是用于表示文字和符号的标准。`char` 表示其中的一个标量值，不一定等于一个人眼看到的完整字符；组合文字和某些表情的细节放到第五节。

不必为每个变量都写类型标注。像 `let minutes = 20;` 这样的声明，编译器往往能根据上下文推断类型。如果整数没有其他类型约束，通常采用 `i32`；带小数点的数值通常采用 `f64`。刚开始时，可以给需要明确范围的数字加上标注，方便检查。

`mut` 也不会让同一个绑定随意改变类型。把一个文本变量重新赋为整数，会得到类型不匹配错误。下载包中的 `compile-fail/mismatched_types.rs` 演示了这种情况。

## 2.5 算术运算与整数除法

常见运算符是 `+`、`-`、`*`、`/` 和 `%`，分别表示加、减、乘、除和取余数。

完整程序：

```rust
fn main() {
    let total_minutes = 125;
    let hours = total_minutes / 60;
    let minutes = total_minutes % 60;

    println!("125 分钟 = {hours} 小时 {minutes} 分钟");
    println!("整数除法：{}", 5 / 2);
    println!("浮点除法：{}", 5.0 / 2.0);
    println!("先加再乘：{}", (2 + 3) * 4);
}
```

预期输出：

```text
125 分钟 = 2 小时 5 分钟
整数除法：2
浮点除法：2.5
先加再乘：20
```

整数除法向零截断，所以 `5 / 2` 得到整数 2。事后把结果转成小数，也补不回已经截掉的小数部分。需要小数结果时，参与除法的数值就应使用适当的浮点类型。

Rust 不会自动让任意两种数值类型混算。例如 `u32` 分钟数与 `f64` 目标比例参与同一运算时，需要明确转换。下面是完整程序：

```rust
fn main() {
    let minutes: u32 = 30;
    let target: u32 = 45;
    let progress = f64::from(minutes) / f64::from(target) * 100.0;

    println!("学习进度：{progress:.1}%");
}
```

`f64::from(minutes)` 把这里的 `u32` 转成 `f64`，再进行浮点除法。输出为 `学习进度：66.7%`。`:.1` 表示输出时保留一位小数，不会改变原变量保存的值。

浮点数表示近似值，不能假定任意十进制小数的运算都精确无误。后面的金额练习会用整数“分”，暂时避开小数金额的舍入问题。

## 2.6 比较得到布尔值

完整程序：

```rust
fn main() {
    let minutes = 30;
    let target = 45;
    let reached_target = minutes >= target;
    let has_record = minutes > 0;
    let needs_more = has_record && !reached_target;

    println!("已达标：{reached_target}");
    println!("有学习记录：{has_record}");
    println!("有记录并且还需继续：{needs_more}");
}
```

输出依次为 `false`、`true`、`true`。

`==` 比较相等，`!=` 比较不相等，`>`、`>=`、`<`、`<=` 比较大小。这些表达式的结果都是 `bool`。

`&&` 要求左右都为真，`||` 要求至少一边为真，`!` 把真假反转。下一节会把这些条件交给 `if`，决定执行哪段代码。

## 2.7 同名的新绑定叫遮蔽

再次用 `let` 声明同名变量，会建立一个新绑定，称为遮蔽（shadowing）。完整程序：

```rust
fn main() {
    let minutes = 20;
    let minutes = minutes + 10;
    println!("{minutes}");

    let input = " 42 ";
    let input = input.trim();
    println!("去掉首尾空白：{input}");
}
```

第二条 `let minutes` 先用旧值算出 30，再建立同名的新绑定，供后面的代码使用。第一个绑定不需要加 `mut`。

`input.trim()` 调用一个方法，取得去掉首尾空白的文本视图。这里沿用原来的名称表示处理后的输入，后面解析输入时还会用到这种写法。

遮蔽也允许新绑定采用不同类型，因为这是重新声明。给已有的 `mut` 绑定赋值则必须保持兼容类型。两者的区别是有没有重新写 `let`。

不用为了练习遮蔽，把所有中间结果都起成同一个名字。用 `total_minutes`、`remaining_minutes` 分别表达不同含义，通常更便于检查计算。

## 2.8 花括号界定可以使用名字的范围

作用域就是可以使用这个变量名的代码范围。完整程序：

```rust
fn main() {
    let minutes = 20;
    {
        let minutes = 30;
        println!("里面：{minutes}");
    }
    println!("外面：{minutes}");
}
```

程序先输出 30，再输出 20。内层的同名绑定只在内层起作用；离开那对花括号后，使用的仍是值为 20 的外层绑定。

如果一个变量只在内层声明，外层就不能直接使用它。后续写函数和分支时，也要留意声明位置。

## 2.9 用元组和数组放在一起

元组可以把几个不同类型的值放在一起。完整程序：

```rust
fn main() {
    let record = ("小林", 30, true);
    println!("姓名：{}，分钟：{}，已登记：{}", record.0, record.1, record.2);

    let (name, minutes, registered) = record;
    println!("{name}，{minutes}，{registered}");
}
```

`.0`、`.1`、`.2` 按位置访问元组。`let (name, minutes, registered) = record;` 把各项分别绑定到名字，称为解构。

数组保存同一类型、固定数量的元素。完整程序：

```rust
fn main() {
    let days: [u32; 3] = [20, 30, 25];
    println!("第一天：{} 分钟", days[0]);
    println!("第三天：{} 分钟", days[2]);
    println!("一共记录了 {} 天", days.len());
}
```

`[u32; 3]` 表示三个 `u32` 元素。这里方括号里的分号分隔元素类型和长度，不是语句结尾。`days[0]` 访问第一项，索引从 0 开始，所以第三项是 `days[2]`。

访问索引前要确认范围。运行时越界索引会 panic，停止正常执行；编译器能直接确定越界时，也可能提前拒绝编译。第五节会学习用 `get` 处理“不存在这一项”的情况。

## 语法细读：绑定、推断和数值转换 {#syntax-depth}


本章语法细读里的每个 Rust 程序可以分别替换自己项目的 `src/main.rs`：正常例子运行 `cargo run`，故意失败的例子运行 `cargo check`。下载包另保存为独立文件，直接编译的方法见下载包里的 `syntax/README.md`。各个程序相互独立。

前面的例子能运行，还需要解释每个位置为什么能这样写。下面按绑定的结构、类型约束和数值转换继续拆开。

### let 的左边是模式，不一定只有一个名字

这是语法示意，方括号表示可以省略的部分，不是要输入的 Rust 字符：

```text
let 模式 [: 类型] [= 初始化表达式];
```

`let minutes: u32 = 20;` 中，`minutes` 是最简单的名字模式，冒号后约束整个绑定的类型，等号右边产生初始值，分号结束这条声明。`let (hours, minutes) = (2, 5);` 的左边是元组模式，一次建立两个名字；模式的详细规则放到第六章。

初始化表达式可以省略，但变量在每一条实际会读取它的路径上都必须已经初始化。`let`、初始化和之后的赋值不是一回事：首次初始化不可变绑定不需要 `mut`，重新赋值才需要。暂时优先在声明处初始化，避免把“某个分支没有赋值”带进简单程序。

`const NAME: Type = expression;` 声明常量，需要显式类型和可以在编译期求值的初始化表达式。常量不能加 `mut`，也不是省略 `mut` 的普通局部变量。本章只用整数常量；`static` 涉及固定存储位置，是另一个概念。

### 类型推断会看使用位置，不能只盯住等号右边

完整程序，下载包中为 `syntax/syntax02-inference.rs`：

```rust
const DEFAULT_MINUTES: u8 = 30;
fn accept(value: u8) {
    println!("参数：{value}");
}
fn main() {
    let inferred = 12;
    let annotated: u8 = 12;
    let suffixed = 12_u8;
    accept(inferred);
    let _: u8 = inferred;
    println!("三种写法：{inferred} / {annotated} / {suffixed}");
    println!("常量：{DEFAULT_MINUTES}");
}
```

预期输出：

```text
参数：12
三种写法：12 / 12 / 12
常量：30
```

`inferred` 后来传给接收 `u8` 的函数，因此整数文字 `12` 在这里被约束为 `u8`。推断不是先把它永久定成 `i32`，再在调用处偷偷转换。第二种写法把约束写在变量上，第三种把类型后缀写在数字文字上；这三个绑定最终都是 `u8`。

编译器会一起检查声明、运算、函数参数和返回值等位置的约束。如果其他位置没有给出足够的约束，整数和浮点文字通常分别回退到 `i32` 和 `f64`；如果约束互相冲突，就报告错误。

以下完整程序故意无法编译，下载包中为 `compile-fail/syntax02-reassign.rs`：

```rust
fn main() {
    let mut value = 20_u32;
    value = "二十";
    println!("{value}");
}
```

预期诊断包含 `E0308`。

这里 `mut` 只允许重新赋值，不能取消已经确定的 `u32` 类型。遮蔽则会建立新绑定，所以 `let value = "二十";` 可以采用新类型。

### 类型标注、类型后缀和 as 各做什么

| 写法 | 作用 |
| --- | --- |
| `let n: u8 = 12;` | 约束绑定的类型 |
| `let n = 12_u8;` | 约束这个数字文字的类型 |
| `value as u8` | 对已有表达式执行允许的显式转换 |
| `u32::from(value)` | 使用这个类型提供的 `From` 转换 |

以下完整程序故意无法编译，下载包中为 `compile-fail/syntax02-mixed.rs`：

```rust
fn main() {
    let small = 10_u8;
    let wide = 20_u16;
    let total = small + wide;
    println!("{total}");
}
```

预期诊断包含 `E0308`。

编译器不会在这次加法里自行选择把哪一边转换成另一种类型。可以先把 `small` 扩宽为 `u16`，再和 `wide` 相加；选择转换方向时也要考虑结果范围。

完整程序，下载包中为 `syntax/syntax02-conversion.rs`：

```rust
fn main() {
    let wide = 300_u16;
    let narrow = wide as u8;
    let extended = u32::from(wide);
    assert_eq!(narrow, 44);
    assert_eq!(extended, 300);
    println!("窄化：{narrow}，扩宽：{extended}");
}
```

预期输出：

```text
窄化：44，扩宽：300
```

整数从 `u16` 窄化为 `u8` 时会截掉高位，所以 300 得到 44，不能把 `as` 当成范围校验。这里的 `u32::from(wide)` 是扩宽转换，保留原数值。需要“范围超出就报错”的转换时，应在学过第七章的 `Result` 后使用相应的 `TryFrom`，而不是先截断再检查。

自查：不运行程序，解释 `let n = 12; accept(n);` 中的类型如何确定，再说明把 `let` 改成赋值为什么不能改变类型。若要把 300 存进 `u8`，先写清需求是拒绝输入还是允许截断。

## 2.10 把本节内容组合起来

把姓名、学习时长、进度计算和数组记录放进同一个程序，就得到下面的例子。用它替换自己的整个 `main.rs`：

```rust
fn main() {
    let name = "小林";
    let mut minutes: u32 = 20;
    minutes += 10;
    let target: u32 = 45;
    let remaining = target - minutes;
    let finished: bool = minutes >= target;
    let progress = f64::from(minutes) / f64::from(target) * 100.0;
    let record = (name, minutes);
    let days = [20, 30, 25];

    println!("{} 今天学习了 {} 分钟", record.0, record.1);
    println!("还差 {remaining} 分钟，完成了吗：{finished}");
    println!("进度：{progress:.1}%");
    println!("第一天：{} 分钟", days[0]);

    let input = " 42 ";
    let input = input.trim();
    println!("去掉首尾空白：{input}");
}
```

预期输出：

```text
小林 今天学习了 30 分钟
还差 15 分钟，完成了吗：false
进度：66.7%
第一天：20 分钟
去掉首尾空白：42
```

下载包中对应 `basics/examples/ch02_variables.rs`，在 `rust-course` 目录运行：

```sh
cargo run -p rust-basics --example ch02_variables
```

先预测：把初始分钟数从 20 改成 25，哪些输出会改变？实际运行后，应看到学习 35 分钟、还差 10 分钟、进度 77.8%；`days[0]` 来自另一份数组，仍是 20。

如果把时长改得超过目标，当前 `u32` 减法 `target - minutes` 会下溢，因为结果不能表示为非负整数。整数类型有范围，不能无限加减；例如 `u32` 的范围是 0～4,294,967,295。

计算“还差多少”时，可以把那一行改成：

```rust
let remaining = target.saturating_sub(minutes);
```

只替换这一行即可。这个方法会把低于 0 的差值限制为 0。如果需要判断是否发生溢出，可以使用 `checked_sub`；它的返回形式留到第六节学过 `Option` 后再解释。不要依赖整数溢出后的值，调试与 release 配置的默认检查行为可能不同。

## 2.11 练习一：把分钟换成小时和分钟

给定 `total_minutes = 137`，独立打印：

```text
137 分钟 = 2 小时 17 分钟
```

再把输入改成 60、59、0，分别预测结果。

<details>
<summary>参考答案：先自己完成再展开</summary>

```rust
fn main() {
    let total_minutes: u32 = 137;
    let hours = total_minutes / 60;
    let minutes = total_minutes % 60;
    println!("{total_minutes} 分钟 = {hours} 小时 {minutes} 分钟");
}
```

输入 60 得到 1 小时 0 分钟，59 得到 0 小时 59 分钟，0 得到 0 小时 0 分钟。

</details>

## 2.12 练习二：计算商品总价

单价 1290 分，数量 3。用变量计算总分，再打印 `总价：38.70 元`。要求全程使用整数，不先转成浮点数。分不足两位时，在前面补零。

<details>
<summary>参考答案：先自己完成再展开</summary>

```rust
fn main() {
    let price_cents: u32 = 1290;
    let quantity: u32 = 3;
    let total_cents = price_cents * quantity;
    println!("总价：{}.{:02} 元", total_cents / 100, total_cents % 100);
}
```

`{:02}` 表示至少两位，不足时补零。下载包中运行 `cargo run -p rust-basics --example answer02`。

再把单价改成 105 分、数量改成 1，预期 `总价：1.05 元`。用这个输入检查，就能发现是否把金额错印成了 `1.5`。

</details>

## 2.13 进入下一节前检查

尝试不看示例，写出一个程序：记录今天和昨天的学习分钟数，计算总和与平均值，判断总和是否达到 60，并打印结果。平均值用浮点除法。

你还应能解释 `let` 与 `let mut` 的区别，预测 `5 / 2` 与 `5.0 / 2.0`，区分 `=` 与 `==`，说明三个元素的数组为什么不能访问第 3 号索引。

下一节将根据这些真假条件选择不同操作，再把重复的计算写成函数。

## 官方延伸阅读与验证

- [Rust Reference：let 声明与模式](https://doc.rust-lang.org/reference/statements.html#let-statements)
- [Rust Reference：数字文字与类型后缀](https://doc.rust-lang.org/reference/expressions/literal-expr.html#integer-literal-expressions)
- [Rust Reference：数值转换](https://doc.rust-lang.org/reference/expressions/operator-expr.html#numeric-cast)

- [变量与可变性](https://doc.rust-lang.org/book/ch03-01-variables-and-mutability.html)
- [Rust 数据类型](https://doc.rust-lang.org/book/ch03-02-data-types.html)

文档查阅与示例复核日期：2026-10-13。正文完整程序使用 macOS arm64、Rust 1.99.0、Cargo 1.99.0 验证；标为故意无法编译的例子按失败条件检查。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：安装与第一个程序](/posts/rust-01-setup/) · [下一章：函数与控制流程](/posts/rust-03-functions/)
