+++
title = "Rust 底层入门 01：值、地址、内存布局与资源释放"
date = 2026-10-15
lastmod = 2026-10-15
draft = false
author = "Hex4C59"
description = "用三个可运行实验观察大小、对齐、字段偏移、String 的堆缓冲区和析构顺序，区分语言保证、编译器表现与资源管理。"
summary = "size_of 为什么量不到字符串的全部内存？移动 String 改变了什么？借用结束后为什么值还没有释放？从实验建立内存与资源管理的认识，再连接到 Web Server 的缓冲区和连接生命周期。"
tags = ["Rust", "内存布局", "资源管理"]
categories = ["programming"]
source_kind = "original"
article_type = "concept"
series = ["rust-from-zero"]
series_role = "appendix"
series_label = "底层 01：内存与释放"
ShowToc = true
+++

读到 `let next = value` 时，除了判断还能不能使用 `value`，还可以继续问：值占多少字节，内部管理着哪一块内存，执行这行代码是否需要重新分配，最后由谁释放资源？这些问题把所有权规则连接到了程序实际管理的数据。

本篇建议在[所有权](/posts/rust-04-ownership/)、[集合](/posts/rust-05-collections/)、[结构体](/posts/rust-06-modeling/)和[trait](/posts/rust-09-traits/)之后阅读。三个实验依次观察布局、堆缓冲区和析构；所有代码都使用安全 Rust，打印或比较原始指针时只把它当作地址值，不解引用。

## 先区分值的类型、存放位置与管理的资源

`String` 是一个拥有字符串数据的值。它通过缓冲区指针、长度和容量管理堆上的 UTF-8 字节；长度和容量的单位都是字节。[标准库的表示说明](https://doc.rust-lang.org/std/string/struct.String.html#representation)解释了这三部分。

`String` 值本身可以由局部变量持有，也可以放在 `Box<String>` 中，或作为其他结构体的字段。不能仅凭类型名判断它位于栈上还是堆上。编译器还可能让局部值保存在 CPU 寄存器里，也就是处理器直接用于运算的存储位置，或者消除不影响可观察结果的存储。

因此需要分别记录两件事：值本身的布局，以及它拥有或引用的数据。`size_of` 和 `size_of_val` 测量的是传入类型或所指值的大小，不会沿着指针把所有堆分配加起来。

## 实验一：大小、对齐与字段偏移

大小回答“值占用多少字节”；对齐回答“存放地址需要满足怎样的倍数要求”；字段偏移回答“字段相对整个值的起点在哪里”。为了满足字段的对齐要求，结构体内部可能插入填充字节，大小也要满足整个类型的对齐要求。

将以下完整代码保存为 `systems/layout.rs`。配套下载包已经包含该文件：

```rust
use std::mem::{align_of, offset_of, size_of, size_of_val};

struct RustHeader {
    kind: u8,
    length: u32,
}

#[repr(C)]
struct CHeader {
    kind: u8,
    length: u32,
}

fn main() {
    let rust = RustHeader { kind: 1, length: 7 };
    let c = CHeader { kind: 1, length: 7 };
    assert_eq!((rust.kind, rust.length), (c.kind, c.length));

    println!(
        "usize: size={}, align={}",
        size_of::<usize>(),
        align_of::<usize>()
    );
    println!("String value: {} bytes", size_of::<String>());
    println!("&str value: {} bytes", size_of::<&str>());
    println!("&[u8] value: {} bytes", size_of::<&[u8]>());
    println!(
        "RustHeader: size={}, align={}, kind@{}, length@{}",
        size_of::<RustHeader>(),
        align_of::<RustHeader>(),
        offset_of!(RustHeader, kind),
        offset_of!(RustHeader, length),
    );
    println!(
        "CHeader: size={}, align={}, kind@{}, length@{}",
        size_of::<CHeader>(),
        align_of::<CHeader>(),
        offset_of!(CHeader, kind),
        offset_of!(CHeader, length),
    );

    let bytes = [1_u8, 2, 3, 4];
    let slice: &[u8] = &bytes;
    println!("slice data: {} bytes", size_of_val(slice));
    println!("slice reference: {} bytes", size_of_val(&slice));
}
```

从解压后的 `rust-course` 目录运行。以下是 macOS 终端的复现方式；输出放在 `target` 中，避免混进源码目录：

```sh
mkdir -p target/systems
rustc --edition=2024 -D warnings systems/layout.rs -o target/systems/layout
./target/systems/layout
```

本次在 macOS arm64、rustc 1.99.0 上得到：

```text
usize: size=8, align=8
String value: 24 bytes
&str value: 16 bytes
&[u8] value: 16 bytes
RustHeader: size=8, align=4, kind@4, length@0
CHeader: size=8, align=4, kind@0, length@4
slice data: 4 bytes
slice reference: 16 bytes
```

这里有三处值得逐项解释。

`CHeader` 的 `length` 从偏移 4 开始。`kind` 占用第一个字节，接下来的三个字节用于填充，随后才是四字节整数。整个类型的大小为 8、对齐为 4。这些数字来自本次目标平台。

两个结构体的字段声明顺序相同，实验中的默认 Rust 布局却把 `length` 放到了前面。默认表示没有承诺字段按声明顺序排布；`#[repr(C)]` 则采用 C 表示规定的字段顺序和布局规则。C 表示仍受目标平台影响，也不能替代文件或网络协议的字节编码。[类型布局规范](https://doc.rust-lang.org/reference/type-layout.html)列出了各类表示的保证范围。

`size_of_val(slice)` 测量切片所指的四个字节，`size_of_val(&slice)` 测量切片引用这个值本身。后者在这次运行中占 16 字节，需要携带数据地址和长度信息。`&str` 的本次大小也为 16 字节。应用二进制接口（Application Binary Interface，ABI）约定分别编译的代码如何交换数据和调用函数。不要把这些大小观察直接变成可以跨版本传给 C 的 ABI 约定，更不要靠猜字段顺序来转换指针。

## 实验二：移动与克隆改变了哪块内存

保存为 `systems/string_move.rs`：

```rust
use std::mem::size_of_val;

fn main() {
    let original = String::from("Rust入门");
    let buffer = original.as_ptr();
    let len = original.len();
    let capacity = original.capacity();

    let moved = original;
    assert_eq!(moved.as_ptr(), buffer);
    assert_eq!(moved.len(), len);
    assert_eq!(moved.capacity(), capacity);

    let cloned = moved.clone();
    assert_eq!(moved, cloned);
    assert_ne!(moved.as_ptr(), cloned.as_ptr());

    println!("UTF-8 bytes: {}", moved.len());
    println!("Unicode scalar values: {}", moved.chars().count());
    println!("move keeps the buffer: {}", moved.as_ptr() == buffer);
    println!("clone uses another buffer: {}", cloned.as_ptr() != buffer);

    let long = "x".repeat(1_000);
    println!("short String value: {} bytes", size_of_val(&moved));
    println!("long String value: {} bytes", size_of_val(&long));
    println!("long String data: {} bytes", long.len());

    let boxed = Box::new(moved);
    assert_eq!(boxed.as_str().as_ptr(), buffer);
    println!("Box<String> value: {} bytes", size_of_val(&boxed));
    println!(
        "boxing keeps the string buffer: {}",
        boxed.as_str().as_ptr() == buffer
    );
}
```

```sh
rustc --edition=2024 -D warnings systems/string_move.rs -o target/systems/string_move
./target/systems/string_move
```

本次输出：

```text
UTF-8 bytes: 10
Unicode scalar values: 6
move keeps the buffer: true
clone uses another buffer: true
short String value: 24 bytes
long String value: 24 bytes
long String data: 1000 bytes
Box<String> value: 8 bytes
boxing keeps the string buffer: true
```

`Rust入门` 占 10 个 UTF-8 字节，`chars()` 数到 6 个 Unicode 标量值。标量值也不能通用地当作屏幕上的可见字符数；组合字符会使这两个计数继续分开。

执行 `let moved = original` 后，字符串缓冲区地址、长度和容量都保留了。原来的绑定不能再使用，新的绑定接管该值。这个移动没有要求克隆字符串内容；CPU 最后执行哪些复制或寄存器操作，由编译器生成的代码决定。[所有权章节](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html)区分了移动与深复制。

这里的 `clone()` 创建了内容相同的另一份非空字符串。两份字符串同时存在，使用不同的缓冲区。这个地址比较针对当前的非空例子；空字符串可以不分配缓冲区，不能用空串的地址相等来判断它们共享一份需要释放的数据。

短字符串和含有 1,000 个字节的长字符串，其 `String` 值在本次运行中都占 24 字节。字符串内容增加的是缓冲区中的数据，`size_of_val(&long)` 没有把那 1,000 个字节计入。这个数还不是程序完整的内存占用，分配器可能有额外的管理成本。

[`Box<T>`](https://doc.rust-lang.org/std/boxed/struct.Box.html) 用指针拥有堆上的一个 `T` 值。最后把 `moved` 放进 `Box`，这里的 `T` 就是 `String`。`Box<String>` 这个值在本次目标上占 8 字节，它通过指针拥有其中的 `String`；原先的字符串缓冲区地址仍然保留。这样就能区分 `Box`、被装入的 `String` 值，以及字符串字节这几层对象。

## 实验三：借用结束与资源释放是不同的时间点

借用检查关心引用在需要使用时是否仍然有效。某次借用的最后一次使用结束，并不意味着拥有数据的局部变量立刻执行析构。先用一个带名字的资源观察销毁顺序。

保存为 `systems/drop_order.rs`：

```rust
struct Resource(&'static str);

impl Drop for Resource {
    fn drop(&mut self) {
        println!("drop {}", self.0);
    }
}

fn main() {
    let outer = Resource("outer");
    {
        let first = Resource("first");
        let second = Resource("second");
        println!("before drop(first)");
        drop(first);
        println!("second is still available: {}", second.0);
    }
    println!("back in outer scope: {}", outer.0);
}
```

```sh
rustc --edition=2024 -D warnings systems/drop_order.rs -o target/systems/drop_order
./target/systems/drop_order
```

输出为：

```text
before drop(first)
drop first
second is still available: second
drop second
back in outer scope: outer
drop outer
```

`drop(first)` 把 `first` 的所有权交给标准库函数，触发提前销毁。`second` 在内层作用域正常结束时销毁，`outer` 在外层作用域正常结束时销毁。这里观察的是具名局部变量；不同层级和类型的销毁顺序要按[析构规则](https://doc.rust-lang.org/std/ops/trait.Drop.html#drop-order)分别判断。

代码中的 `Drop::drop(&mut self)` 定义清理动作；[`std::mem::drop(value)`](https://doc.rust-lang.org/std/mem/fn.drop.html) 则是接收一个值的普通函数，参数在函数返回前被销毁。对于本例的非 `Copy` 资源，它接收的是所有权；对于 `Copy` 类型，传入的可以只是副本。把这两层分开，才容易解释为什么同一个函数名对不同类型有不同的使用后果。

这就是资源获取即初始化（Resource Acquisition Is Initialization，RAII）在 Rust 中的一个入口：用值拥有资源，在值正常销毁时执行清理。这个实验的资源只打印消息，实际的文件和网络句柄怎样释放，需要继续查看相应类型的实现与系统接口。

类型检查不保证析构一定执行。例如，安全函数 [`std::mem::forget`](https://doc.rust-lang.org/std/mem/fn.forget.html) 就能跳过值的析构；进程直接退出或以中止方式结束，也可能绕过清理。解释一个程序的资源管理时，要检查实际经过了哪条退出路径。

下面是完整的预期编译失败例子，下载包中的位置为 `compile-fail/systems-borrow-drop.rs`：

```rust
fn main() {
    let owner = String::from("hello");
    let view = &owner;
    drop(owner);
    println!("{view}");
}
```

```sh
rustc --edition=2024 compile-fail/systems-borrow-drop.rs
```

本次编译器报告 `E0505`：后面的 `println!` 还要使用 `view`，而 `drop(owner)` 会移动并销毁它借用的所有者。把打印移到 `drop(owner)` 之前，这次借用就能先结束，再释放所有者。这里是编译时的引用约束，没有给引用附加运行时的垃圾回收计数器。

## 把观察带到 Web Server 项目里

后续接收连接、解析请求和分配任务时，每一步都要同时追踪值和资源：

- 连接交给工作线程时，哪一个 Rust 值被移动，谁在处理结束后持有清理责任？
- 接收缓冲区里保存了多少有效字节，请求中的切片能使用到什么时候？
- 解析器如果只保存借用，下一次读取或扩容之前需要满足什么条件？
- 线程池关闭时，连接、任务、发送端和工作线程应按什么顺序结束？

这些问题会随着[Web Server 路线](/posts/rust-from-zero/#webserver-project)逐步展开。一个请求处理成功，只验证了某次输入输出；还需要解释过程中哪些数据被复制、哪些内存被借用，以及资源何时释放。

## 独立检查

1. 对调 `CHeader` 两个字段的声明顺序，先预测偏移，再运行。说明大小和字段顺序为什么要分开检查。
2. 把 `Rust入门` 改成 `é`，预测字节长度和 Unicode 标量值数量；再尝试空串，说明哪一个关于缓冲区地址的断言需要重新考虑。
3. 将失败例子的打印移到 `drop(owner)` 前面。确认可以编译后，再把打印放回原处，指出借用的哪一次使用改变了结果。
4. 把资源实验中的 `drop(first)` 改为 `std::mem::forget(first)`。检查哪一条析构消息消失，再说明安全 Rust 为什么仍然允许资源泄漏。

## 复现范围与资料

2026-10-15 在 macOS arm64、rustc 1.99.0、目标 `aarch64-apple-darwin` 上运行三个完整程序，调试构建和 `-O` 优化构建各一次，均通过断言且本次输出一致；使用 `-D warnings` 编译，源码通过 Rust 2024 edition 的 rustfmt 检查。故意失败的程序确认得到 `E0505`。另检查六种练习变体：字段调序、Unicode 文本、空串断言失败及修正、提前结束借用、跳过析构；其中空串保留原地址断言时的失败是预期结果。输出中的大小与偏移只描述本次目标和编译器；最低 Rust 1.85、其他架构和操作系统未在本轮运行。

主要依据是 [Rust 类型布局规范](https://doc.rust-lang.org/reference/type-layout.html)、[`String` 标准库文档](https://doc.rust-lang.org/std/string/struct.String.html)、[所有权说明](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html)、[`Drop` 文档](https://doc.rust-lang.org/std/ops/trait.Drop.html)和 [`forget` 的安全性说明](https://doc.rust-lang.org/std/mem/fn.forget.html)。外部资料核对日期：2026-10-15。

[回到教材目录](/posts/rust-from-zero/) · [查看系统机制学习路线](/posts/rust-from-zero/#systems-route) · [下载配套源码](/posts/rust-from-zero/course.zip)
