+++
title = "Rust 入门 06：结构体、枚举和 Option"
date = 2026-10-12T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "为任务定义数据和方法，用枚举表示命令，用 Option 和 match 处理可能缺失的值。"
summary = "为任务定义数据和方法，用枚举表示命令，用 Option 和 match 处理可能缺失的值。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 6
series_label = "结构体与枚举"
series_part = "理解数据如何使用"
series_number = 6
ShowToc = true
+++

第五章已经能保存一组标题。现在每条任务还需要完成状态，单靠一个字符串就不够了。程序也需要区分“新增”“完成”“列出”这些不同操作。

本章用结构体组织任务数据，用方法修改状态，用枚举表达命令，再用 `Option` 处理可能找不到的数据。学完后，你应该能定义并修改任务列表，也能为一个空列表给出正常提示。文件保存和终端输入留到后续章节。

继续在自己的 `hello-rust` 项目中练习。完整程序可以替换整个 `src/main.rs`，运行 `cargo run`。本章的小例子分别定义自己的类型；运行一个例子时，替换整个文件，避免留下重复的同名定义。

## struct 为数据命名

第二章用元组把几个值放在一起，读取时需要记住各项的位置。任务的字段有明确含义，可以使用结构体。完整程序：

```rust
struct Task {
    title: String,
    done: bool,
}

fn main() {
    let task = Task {
        title: String::from("学习 Rust"),
        done: false,
    };

    println!("标题：{}", task.title);
    println!("已完成：{}", task.done);
}
```

预期输出：

```text
标题：学习 Rust
已完成：false
```

`struct Task` 定义一种新的类型。`title: String` 和 `done: bool` 是字段，分别保存标题和完成状态。创建 `Task` 值时，要给这些字段提供对应类型的值。

`task.title` 和 `task.done` 通过名称访问字段。字段名能直接说明数据含义，不必记住元组的第 0 项代表标题。

`Task` 是类型名，通常采用单词首字母大写的形式；`task` 是变量名。字段名仍使用小写和下划线。定义类型不会自动创建一条任务，`Task { ... }` 才是在构造一个值。

## 调试输出与用户输出

想在检查程序时一次看到所有字段，可以让编译器生成调试输出所需的实现。完整程序：

```rust
#[derive(Debug)]
struct Task {
    title: String,
    done: bool,
}

fn main() {
    let task = Task {
        title: String::from("学习 Rust"),
        done: false,
    };

    println!("调试：{task:?}");
    println!("用户看到：{}，完成状态：{}", task.title, task.done);
}
```

预期输出：

```text
调试：Task { title: "学习 Rust", done: false }
用户看到：学习 Rust，完成状态：false
```

`#[derive(Debug)]` 写在类型定义前，要求编译器生成 `Debug` 所需的实现。现在先用它配合 `{:?}` 检查数据，第九章再学习 trait 的含义。

调试格式包含类型名、字段名等信息，适合排查问题。面向用户的展示可以像第二行那样单独组织。生成 `Debug` 后，这个类型仍没有自动获得 `Copy`，第四章的所有权规则也照常适用。

## impl 把相关行为放在类型旁边

创建任务时，通常希望状态从“未完成”开始；完成任务时，需要修改这个状态。把这些行为放进 `impl Task`。完整程序：

```rust
struct Task {
    title: String,
    done: bool,
}

impl Task {
    fn new(title: &str) -> Self {
        Self {
            title: title.to_string(),
            done: false,
        }
    }

    fn complete(&mut self) {
        self.done = true;
    }

    fn label(&self) -> &str {
        &self.title
    }

    fn into_title(self) -> String {
        self.title
    }
}

fn main() {
    let mut task = Task::new("学习枚举");
    println!("修改前：{}：{}", task.label(), task.done);

    task.complete();
    println!("修改后：{}：{}", task.label(), task.done);

    let title = task.into_title();
    println!("取出的标题：{title}");
}
```

预期输出：

```text
修改前：学习枚举：false
修改后：学习枚举：true
取出的标题：学习枚举
```

`Task::new(...)` 没有 `self` 参数，称为关联函数。它从传入的文本视图创建独立字符串，把状态设为 `false`，再返回新的任务。`Self` 在这个 `impl` 中代表 `Task`。这里的 `new` 是我们定义的函数名，函数体由我们编写。

带 `self` 参数的函数称为方法，用 `task.complete()` 这样的点号形式调用。参数表达方法怎样使用当前对象：

| 参数 | 方法的权限 |
| --- | --- |
| `&self` | 借用当前对象，读取它 |
| `&mut self` | 独占地借用当前对象，允许修改它 |
| `self` | 取得当前对象所有权 |

`complete` 需要可变借用，所以调用方的 `task` 必须允许修改。`label` 只读取标题，返回 `&str`，没有复制整个字符串；返回的视图依赖任务中的标题继续有效。

`into_title` 接收 `self`，会取得任务所有权，再把标题交出来。调用后不能再使用原来的 `task`。这与第四章把 `String` 传给按值参数遵循同一条规则，只是现在移动的是自定义类型。

## 把任务放进列表后怎样修改

结构体也可以作为 `Vec` 的元素。完整程序：

```rust
struct Task {
    title: String,
    done: bool,
}

impl Task {
    fn new(title: &str) -> Self {
        Self {
            title: title.to_string(),
            done: false,
        }
    }

    fn complete(&mut self) {
        self.done = true;
    }
}

fn main() {
    let mut tasks = vec![Task::new("学习借用"), Task::new("写练习")];

    for task in &mut tasks {
        task.complete();
    }

    for task in &tasks {
        println!("{}：{}", task.title, task.done);
    }
    println!("任务数：{}", tasks.len());
}
```

预期输出：

```text
学习借用：true
写练习：true
任务数：2
```

第一轮遍历取得每条任务的可变引用，调用方法修改原任务。第二轮共享借用列表，只读取数据。两个循环结束后，列表仍可使用。

包含 `String` 的 `Task` 没有自动获得 `Copy`。如果先创建 `task`，再写 `vec![task]`，任务就移进了列表。后面要通过列表读取或借用它，不能继续使用移动前的整个 `task`。

## enum 表示几种互斥情况

结构体把几个字段组合成一个值。枚举则规定：一个值属于列出的哪一种情况。比如一次命令可以是新增、完成或列出，还可以按情况携带不同数据。

完整程序：

```rust
enum Command {
    Add(String),
    Done(u64),
    List,
}

fn describe(command: &Command) {
    match command {
        Command::Add(title) => println!("新增：{title}"),
        Command::Done(id) => println!("完成编号：{id}"),
        Command::List => println!("列出全部任务"),
    }
}

fn main() {
    let commands = [
        Command::Add(String::from("写练习")),
        Command::Done(1),
        Command::List,
    ];

    for command in &commands {
        describe(command);
    }
    println!("命令数：{}", commands.len());
}
```

预期输出：

```text
新增：写练习
完成编号：1
列出全部任务
命令数：3
```

`Add`、`Done`、`List` 叫枚举变体：

- `Add(String)` 携带一个拥有内容的标题。
- `Done(u64)` 携带要完成的任务编号。
- `List` 不需要额外数据。

`Command::Add(...)` 和 `Command::List` 都是 `Command` 类型的值。一个命令在某一时刻只有一个变体，例如新增命令携带标题，列出命令不携带数据。

`describe` 接收 `&Command`，因此只借用命令。`match` 判断当前变体，进入对应分支，并把携带的数据绑定给 `title` 或 `id`。这里匹配的是引用，字段也通过引用访问，没有把标题从命令中拿走。

本例只是描述命令，并没有真的新增或删除任务。第十一章再把命令接到任务列表的实际操作上。

## match 要覆盖所有可能

`match` 按模式选择分支，`=>` 后面写该分支要执行的表达式或代码块。它要求覆盖输入类型的所有可能情况。

在上一段程序中暂时删除 `Command::List => ...` 那一行，再运行 `cargo check`，应看到 `E0004`，提示还有变体没有处理。修复后重新检查。

如果以后给 `Command` 增加新变体，逐一列出情况的 `match` 也会指出遗漏的位置，提醒我们更新相应逻辑。

和第三章的 `if` 一样，`match` 可以产生值。完整程序：

```rust
enum TaskState {
    Todo,
    Done,
}

fn main() {
    for state in [TaskState::Todo, TaskState::Done] {
        let label = match state {
            TaskState::Todo => "待完成",
            TaskState::Done => "已完成",
        };
        println!("{label}");
    }
}
```

预期输出：

```text
待完成
已完成
```

选中的分支把文本交给 `label`。所有可能产生结果的分支需要得到兼容类型，不能让一个分支返回文本、另一个返回整数。

`_` 可以匹配剩下的情况。完整程序：

```rust
fn main() {
    for rounds in [0, 1, 3] {
        let message = match rounds {
            0 => "尚未开始",
            1 => "完成第一轮",
            _ => "完成多轮",
        };
        println!("{rounds}：{message}");
    }
}
```

预期输出：

```text
0：尚未开始
1：完成第一轮
3：完成多轮
```

这个例子只传入非负轮数。`_` 本身并不表示“大于 1”，而是表示前面模式没匹配的所有值。给每种命令定义明确行为时，逐一写出变体通常比直接用 `_` 忽略它们更容易发现遗漏。

## Option 表示可能没有值

第五章的 `get`、`pop`、`chars().next()` 都可能拿不到一项，所以返回值需要表达“有”或“没有”。标准库用 `Option<T>` 表示这两种情况：`Some(value)` 保存一个值，`None` 表示没有值。`T` 是其中那个值的类型。

| 操作 | 返回类型示例 | 没有值的情况 |
| --- | --- | --- |
| 整数切片的 `get` | `Option<&i32>` | 索引越界 |
| 整数列表的 `pop` | `Option<i32>` | 列表为空 |
| 文本的 `chars().next()` | `Option<char>` | 文本为空 |

`Option` 本身就是枚举，处理它的方法与刚才的 `Command` 相同。完整程序：

```rust
fn main() {
    let records = vec![20, 30];

    for index in [0, 9] {
        match records.get(index) {
            Some(minutes) => println!("索引 {index}：{minutes} 分钟"),
            None => println!("索引 {index}：没有记录"),
        }
    }
}
```

预期输出：

```text
索引 0：20 分钟
索引 9：没有记录
```

`Some(minutes)` 是一种模式：如果结果有值，就把内部的值绑定给 `minutes`，执行这一分支。`None` 则匹配没值的情况。这里的 `minutes` 是借来的整数引用，打印时可以直接使用它。

`index` 用于索引，编译器在这里把它推断为 `usize`，这是 Rust 用于集合长度和索引的整数类型。本例中不必手写标注。

`Option`、`Some`、`None` 不需要手工 `use`，它们通过 Rust 的预导入机制自动可见。`String` 和 `Vec` 也在常用的预导入名称中，`HashMap` 则仍需要引入。

## 写一个返回 Option 的查询函数

自己的函数也可以表达“可能找不到”。下面查询第一条任务，同时处理有任务和空列表两种输入。完整程序：

```rust
struct Task {
    title: String,
    done: bool,
}

fn first_task(tasks: &[Task]) -> Option<&Task> {
    tasks.first()
}

fn show_first(tasks: &[Task]) {
    match first_task(tasks) {
        Some(task) => println!("第一项：{}，已完成：{}", task.title, task.done),
        None => println!("还没有任务"),
    }
}

fn main() {
    let tasks = vec![Task {
        title: String::from("写练习"),
        done: false,
    }];
    let empty: Vec<Task> = Vec::new();

    show_first(&tasks);
    show_first(&empty);
    println!("原列表仍有 {} 项", tasks.len());
}
```

预期输出：

```text
第一项：写练习，已完成：false
还没有任务
原列表仍有 1 项
```

`tasks.first()` 借用第一项；列表为空时返回 `None`。`Option<&Task>` 表示“可能存在的、借来的任务”，没有创建独立任务，也没有把第一项移出列表。

返回引用与第四章的规则一致：任务必须仍然有效，才能通过这个引用使用它。这里的函数返回输入切片里的任务，没有返回函数自己创建后又清理掉的局部值。第九章再解释这种签名中省略的生命周期关系。

空列表是查询时正常可能遇到的情况，不必为了读取第一项就直接索引 `tasks[0]`。

## if let 只关心其中一种情况

如果只在找到任务时做一件事，没有任务时无需额外处理，可以使用 `if let`。完整程序：

```rust
fn main() {
    let mut titles: Vec<String> = Vec::new();

    if let Some(title) = titles.first() {
        println!("初始标题：{title}");
    }

    titles.push(String::from("学习 Option"));

    if let Some(title) = titles.first() {
        println!("加入后：{title}");
    }
}
```

预期输出：

```text
加入后：学习 Option
```

第一次查询得到 `None`，代码块被跳过。第二次得到 `Some`，里面的标题引用绑定给 `title`，再执行打印。

`if let Some(title) = ...` 中的 `Some(title)` 是匹配模式：找到值时，为其中的数据建立绑定。需要给有值和没值两种情况都显示提示时，可以继续使用 `match`，也可以给 `if let` 写 `else`。

## 用 first_mut 修改可能为空的列表

共享引用只能读取任务。要修改第一条任务，使用 `first_mut()`，取得 `Option<&mut Task>`。完整程序：

```rust
struct Task {
    title: String,
    done: bool,
}

impl Task {
    fn new(title: &str) -> Self {
        Self {
            title: title.to_string(),
            done: false,
        }
    }

    fn complete(&mut self) {
        self.done = true;
    }
}

fn complete_first(tasks: &mut [Task]) -> bool {
    match tasks.first_mut() {
        Some(task) => {
            task.complete();
            true
        }
        None => false,
    }
}

fn main() {
    let mut tasks = vec![Task::new("写练习")];
    let changed = complete_first(&mut tasks);
    println!("修改成功：{changed}");
    println!("{}：{}", tasks[0].title, tasks[0].done);

    let mut empty: Vec<Task> = Vec::new();
    println!("空列表修改成功：{}", complete_first(&mut empty));
}
```

预期输出：

```text
修改成功：true
写练习：true
空列表修改成功：false
```

`Some(task)` 分支拿到可变引用，通过方法修改原任务。分支最后的 `true` 没有分号，是这个 `match` 的结果。空列表进入 `None` 分支，返回 `false`。

参数使用 `&mut [Task]`，因为函数只修改已有元素，不需要增长列表。调用结束后借用结束，`main` 可以继续查看任务。这里索引第 0 项，是因为这个例子刚创建了确定非空的列表；通用查询仍要考虑空列表。

## 承接第二章：区分是否超过目标

第二章用 `saturating_sub` 把负的数学差值限制为 0。当你还需要区分“正好达标”和“已经超过目标”时，可以检查 `checked_sub` 的返回结果。

完整程序：

```rust
fn main() {
    let target: u32 = 45;

    for minutes in [20, 45, 60] {
        match target.checked_sub(minutes) {
            Some(remaining) => println!("已学 {minutes} 分钟，还差 {remaining} 分钟"),
            None => println!("已学 {minutes} 分钟，已超过目标"),
        }
    }
}
```

预期输出：

```text
已学 20 分钟，还差 25 分钟
已学 45 分钟，还差 0 分钟
已学 60 分钟，已超过目标
```

对这里的 `u32`，非负差值可以表示时返回 `Some`，包括 `Some(0)`；数学结果小于 0 时返回 `None`。这样就能用分支表达不同情况。

`Option` 只区分有值和没值，并不会自动解释缺失的原因。第七章学习的 `Result` 会进一步携带失败原因。

你可能在别的代码里见到 `unwrap()`。它在 `Some` 时取出值，在 `None` 时会 panic。列表为空和索引不存在都是本章需要正常处理的输入，使用 `match` 或 `if let` 更符合这些例子的需求。

## 把任务、命令和查询组合起来

下面的完整程序对应下载包的 `basics/examples/ch06_modeling.rs`：

```rust
#[derive(Debug)]
struct Task {
    title: String,
    done: bool,
}

impl Task {
    fn new(title: &str) -> Self {
        Self {
            title: title.to_string(),
            done: false,
        }
    }

    fn complete(&mut self) {
        self.done = true;
    }

    fn label(&self) -> &str {
        &self.title
    }
}

enum Command {
    Add(String),
    Done(u64),
    List,
}

fn describe(command: &Command) {
    match command {
        Command::Add(title) => println!("新增：{title}"),
        Command::Done(id) => println!("完成编号：{id}"),
        Command::List => println!("列出全部任务"),
    }
}

fn first_task(tasks: &[Task]) -> Option<&Task> {
    tasks.first()
}

fn main() {
    let mut task = Task::new("学习枚举");
    task.complete();
    println!("{}：{}", task.label(), task.done);
    let tasks = vec![task];
    match first_task(&tasks) {
        Some(task) => println!("第一项：{}", task.label()),
        None => println!("还没有任务"),
    }
    if let Some(task) = first_task(&tasks) {
        println!("找到：{}", task.label());
    }
    describe(&Command::Add(String::from("写练习")));
    describe(&Command::Done(1));
    describe(&Command::List);

    let empty: Vec<Task> = Vec::new();
    match first_task(&empty) {
        Some(task) => println!("空列表第一项：{}", task.label()),
        None => println!("空列表：还没有任务"),
    }
}
```

预期输出：

```text
学习枚举：true
第一项：学习枚举
找到：学习枚举
新增：写练习
完成编号：1
列出全部任务
空列表：还没有任务
```

在解压后的 `rust-course` 目录运行：

```sh
cargo run -p rust-basics --example ch06_modeling
```

这段代码先创建并修改任务，再把它移入列表；查询函数借用列表，返回可能存在的任务引用。命令的 `match` 描述操作，空列表的 `match` 处理没找到的情况。试着指出每一步是创建值、移动值，还是借用值。

## 练习：定义一本书

定义 `Book`，保存标题 `String` 和是否读完 `bool`。写 `new` 和 `finish`，再写一个 `finish_first` 函数：通过 `first_mut()` 标记第一本书，成功返回 `true`，空列表返回 `false`。

先创建两本书，只标记第一本。然后传入空列表，确认程序仍能正常结束。

<details>
<summary>参考答案：先自己完成再展开</summary>

```rust
struct Book {
    title: String,
    finished: bool,
}

impl Book {
    fn new(title: &str) -> Self {
        Self {
            title: title.to_string(),
            finished: false,
        }
    }

    fn finish(&mut self) {
        self.finished = true;
    }
}

fn finish_first(books: &mut [Book]) -> bool {
    match books.first_mut() {
        Some(book) => {
            book.finish();
            true
        }
        None => false,
    }
}

fn main() {
    let mut books = vec![Book::new("Rust 入门")];
    books.push(Book::new("写练习"));
    assert!(finish_first(&mut books));
    assert!(books[0].finished);
    assert!(!books[1].finished);

    for book in &books {
        println!("{}：{}", book.title, book.finished);
    }

    let mut empty: Vec<Book> = Vec::new();
    assert!(!finish_first(&mut empty));
    println!("空列表已处理");
}
```

预期输出：

```text
Rust 入门：true
写练习：false
空列表已处理
```

运行 `cargo run -p rust-basics --example answer06`。断言分别检查第一本已读、第二本未读，以及空列表没有可修改的书。`assert!` 要求条件为真，`!` 在这里对布尔值取反。

书籍列表由 `main` 拥有，函数只可变借用其中的元素。返回的 `bool` 报告有没有找到并标记一本书，书籍所有权仍留在调用方。

</details>

## 练习：给命令增加一种情况

给 `Command` 增加不携带数据的 `Clear`，让描述函数打印 `请求清空全部任务`。先只改枚举，运行 `cargo check` 观察遗漏分支；再补齐 `match`，依次描述四种命令。

<details>
<summary>参考答案：先自己完成再展开</summary>

```rust
enum Command {
    Add(String),
    Done(u64),
    List,
    Clear,
}

fn describe(command: &Command) {
    match command {
        Command::Add(title) => println!("新增：{title}"),
        Command::Done(id) => println!("完成编号：{id}"),
        Command::List => println!("列出全部任务"),
        Command::Clear => println!("请求清空全部任务"),
    }
}

fn main() {
    let commands = [
        Command::Add(String::from("写练习")),
        Command::Done(1),
        Command::List,
        Command::Clear,
    ];
    for command in &commands {
        describe(command);
    }
}
```

预期输出：

```text
新增：写练习
完成编号：1
列出全部任务
请求清空全部任务
```

这份答案在正文中给出，可以替换自己项目的 `src/main.rs` 运行。它只描述清空请求，没有执行数据删除。

</details>

完成本章后，可以做[第六章后的分级练习](/posts/rust-practice-checkpoints/#after-ch06)：先修改书籍列表，再按标题标记，最后从空文件实现内存书单。练习分别列出成功、失败和空列表的检查条件，并附可运行答案。

## 进入下一章前检查

关掉参考答案，定义一个有标题和完成状态的任务类型，写一个接收可变切片的函数，完成第一条任务并报告是否成功。分别传入两条任务和空列表，解释为什么两种输入都能正常处理。

你还应能回答：关联函数和方法有什么区别？`&self`、`&mut self`、`self` 分别表达什么权限？`Some(0)` 与 `None` 为什么不是同一回事？增加枚举变体后，为什么原来的 `match` 可能报错？

下一章开始读取终端输入。输入可能不是数字，读文件或读终端也可能失败，我们会用 `Result` 和分支报告这些错误。

## 官方延伸阅读

- [结构体与方法](https://doc.rust-lang.org/book/ch05-03-method-syntax.html)
- [枚举与 Option](https://doc.rust-lang.org/book/ch06-01-defining-an-enum.html)
- [match](https://doc.rust-lang.org/book/ch06-02-match.html)
- [if let](https://doc.rust-lang.org/book/ch06-03-if-let.html)

外部文档查阅日期：2026-10-13。代码验证使用 Rust 2024 edition；工具链版本和实际验证范围见[学习指南](/posts/rust-00-learning-guide/#版本与验证范围)。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：字符串与集合](/posts/rust-05-collections/) · [下一章：输入与错误处理](/posts/rust-07-errors/)
