# Rust 从零开始：配套源码

这份源码配合《Rust 从零开始》中文教材使用。先安装 Rust 工具链，再在终端进入本文件所在的 `rust-course` 目录。第 1～14 章的业务示例只使用标准库和本地库，第 15～16 章使用 Serde 与 serde_json，第 17 章加入 clap，第 18 章使用 reqwest 访问本机服务。基础、`practice` 和 `projects` 三个工作区分别运行。

项目采用 2024 edition，声明最低 Rust 版本为 1.85。本次于 2026-10-12 在 macOS arm64、rustc 1.99.0、cargo 1.99.0 上验证；没有实际验证最低版本或其他操作系统。

2026-10-13 展开第 4～6 章后，在同一平台和工具链上核对了正文中的 47 个正常程序、8 个故意编译失败的例子、1 个故意触发 panic 的例子，以及 13 种输入或代码变体。`ch06_modeling` 展示空任务列表的查询，`answer06` 检查只标记第一本书，以及空列表返回 `false` 的情况。

2026-10-13 展开第 7～12 章后，直接从正文运行了 35 个正常程序，确认 7 个故意编译失败的例子，并检查 21 种输入或代码变体。第八章的库项目，以及第十一章到第十二章的待办工具，都按正文从新建 Cargo 项目重建，检查模块可见性、测试失败与恢复、错误传播、跨进程保存和无效输入不覆盖原文件。

## 第一次运行

```sh
rustc --version
cargo --version
cargo run -p rust-basics --example ch01_hello
```

每条 Cargo 命令都可以增加 `--offline`，例如 `cargo run --offline -p rust-basics --example ch01_hello`。工具链本身需要预先安装。

## 教材与示例对应关系

| 章 | 示例名称或项目入口 |
| --- | --- |
| 01 安装和首个程序 | `ch01_hello` |
| 02 变量和类型 | `ch02_variables`、`answer02` |
| 03 函数与循环 | `ch03_flow`、`answer03` |
| 04 所有权与借用 | `ch04_ownership`、`answer04` |
| 05 字符串与集合 | `ch05_collections`、`answer05` |
| 06 结构体与枚举 | `ch06_modeling`、`answer06` |
| 07 输入与错误 | `ch07_errors`、`answer07` |
| 08 模块与测试 | `ch08_modules`、`basics/src/`、`basics/tests/` |
| 09 泛型、trait、生命周期 | `ch09_traits`、`answer09` |
| 10 闭包与迭代器 | `ch10_iterators`、`answer10` |
| 11 项目核心逻辑 | `taskbook/src/lib.rs`、`taskbook/examples/memory.rs` |
| 12 文件与命令行 | `taskbook/src/storage.rs`、`taskbook/src/main.rs`、`taskbook/tests/cli.rs` |
| 13 筛选、搜索与删除 | `practice/taskbook-plus/`、`selection` 示例 |
| 14 自定义错误 | `practice/error-lab/`、`inspect` 示例 |
| 15 Serde 与 JSON | `practice/taskbook-json/`、`serde_basics`、`answer15` 示例 |

运行基础示例和答案时，替换命令末尾的名称：

```sh
cargo run -p rust-basics --example ch04_ownership
cargo run -p rust-basics --example answer04
cargo run -p rust-basics --example ch07_errors
```

第 7～12 章展开后的辅助程序在文章中给出，可按标注单独复制运行。其中 `examples/parse.rs` 和 `examples/format.rs` 需要在自己的跟写项目中新建；下载包保留教材主示例和完整项目入口。

第 7 章示例需要你输入一行并回车。`30` 是有效输入；`abc`、`0`、`-1` 是失败条件。第 1 章答案、第 8 章新增测试、第 11 章新增统计函数和第 12 章损坏文件练习在教材正文中给出。

## 第 13～15 章练习工作区

从本文件所在的 `rust-course` 目录进入 `practice`：

```sh
cd practice
cargo fetch --locked
cargo run -p taskbook-plus --example selection
cargo run -p error-lab --example inspect
cargo run -p taskbook-json --example serde_basics
cargo run -p taskbook-json --example answer15
```

本轮固定 Serde 1.0.229 和 serde_json 1.0.154；`practice/Cargo.lock` 记录具体依赖选择。首次获取需要网络，完成后可以使用 `--offline`。这不是对最低工具链或其他系统的实测证明。

`taskbook-plus` 沿用 TSV 文件与 `TASKBOOK_FILE`；JSON 工具使用 `TASKBOOK_JSON_FILE`，默认文件为 `tasks.json`。筛选、搜索和列出不保存文件。删除最高编号后，新增可能复用该编号。

迁移使用 `cargo run -p taskbook-json -- migrate <TSV源文件> <JSON新文件>`，尖括号部分需换成实际路径。源文件只读，目标已存在时拒绝写入；缺失或损坏源文件不创建目标。新目标写入中断可能留下不完整文件，未实现事务、恢复或并发写入协调。

在 `practice` 目录复查：

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --offline -- -D warnings
cargo test --workspace --offline
cargo test --workspace --all-targets --offline
cargo build --workspace --release --offline
```

第十三章的批量清除和第十四章的分钟数上限练习在正文给出，不预先修改主版本。第十五章的默认字段练习保存为 `answer15`。

## 第 16～18 章项目

从 `rust-course` 进入新的独立工作区：

```sh
cd projects
cargo fetch --locked
cargo run -p taskbook-cli -- --help
cargo run -p lesson-http --example serve
```

- `taskbook-backup`：验证源 JSON，原样复制到新文件；备份和恢复都拒绝已有目标。
- `taskbook-cli`：复用旧任务与 JSON 逻辑，使用 clap 的子命令、`--file`、帮助和版本接口；不读取旧包的任务文件环境变量。
- `lesson-http`：使用 reqwest 阻塞客户端请求 `127.0.0.1` 的一次性练习服务。服务打印实际端口后，在另一个同机终端运行 `cargo run -p lesson-http -- --port 实际端口`，将最后一个参数换成显示的数字。每次请求前需重新启动服务。

本轮固定 clap 4.6.7、reqwest 0.13.5，并沿用 Serde 1.0.229 与 serde_json 1.0.154。`projects/Cargo.lock` 固定间接依赖。首次获取需要网络，之后可用 `--locked --offline`；本机请求练习没有启用 TLS，不访问公网或使用账号密钥。

备份前先停止其他写入程序。复制没有事务、锁或断电恢复；目标创建后若写入失败，可能留下部分内容。恢复创建新文件，旧任务文件仍保留。普通 JSON 保存也继续覆盖整个文件。HTTP 的阻塞读写超时不是整个 `fetch` 函数的绝对截止时间。

在 `projects` 中复查：

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked --offline -- -D warnings
cargo test --workspace --all-targets --locked --offline
cargo build --workspace --release --locked --offline
```

第十六章的任务比较答案保存为 `answer16`；第十七章的 `stats` 和第十八章的字段别名练习在正文中提供，主版本未预先加入。各工作区的 `cargo test` 不会执行其他工作区的测试。

## 分级练习与项目验收

教材新增两篇独立附录：分级练习与项目验收、常见错误排查。第四、九章的图解随网页提供，下载包保留对应代码。

前两个阶段在外层 `rust-course` 运行：

```sh
cargo run -p rust-basics --example checkpoint06
cargo test -p rust-basics --example checkpoint06
cargo run -p rust-basics --example checkpoint12 -- practice-minutes.txt total
cargo test -p rust-basics --example checkpoint12
```

`checkpoint06` 在内存中管理书单；`checkpoint12` 是独立的学习时长记录器，文件每行一个 1～1440 的整数。文件缺失时 `total` 输出 0 而不创建文件；`add` 覆盖保存全文，没有事务、文件锁和写入中断恢复。用专门的练习目录检查文件行为。

第十八章后的顺序客户端位于 `projects/lesson-http/examples/checkpoint18.rs`。在同机启动最多三个一次性服务，再从 `projects` 运行 `cargo run -p lesson-http --example checkpoint18 -- --port 端口1 端口2`，将端口占位文字换成实际数字。失败后继续请求后续端口；全部成功退出 0，任一请求失败退出 1，参数错误退出 2。它仍只访问本机，不实现整个批次的绝对截止时间。

## 故意失败的例子

`compile-fail/` 不属于 Cargo 的正常构建目标。它们用于观察编译器如何拒绝不合法程序，在当前目录单独运行：

```sh
rustc --edition 2024 compile-fail/moved_value.rs
rustc --explain E0382
```

| 文件 | 预期错误 | 原因 |
| --- | --- | --- |
| `immutable.rs` | E0384 | 对不可变变量重新赋值 |
| `mismatched_types.rs` | E0308 | 文本变量被赋成整数 |
| `moved_value.rs` | E0382 | 移动后继续访问原绑定 |
| `borrow_conflict.rs` | E0502 | 共享借用仍需使用时修改同一数据 |
| `dangling.rs` | E0515 | 返回指向局部变量的引用 |
| `string_index.rs` | E0277 | 试图用整数索引字符串 |
| `missing_lifetime.rs` | E0106 | 多个输入引用的返回关系未说明 |
| `support-move.rs` | E0382 | 排错附录：移动后打印旧绑定 |
| `support-borrow.rs` | E0502 | 排错附录：共享引用仍需使用时修改字符串 |
| `support-lifetime.rs` | E0597 | 排错附录：内层所有者销毁后使用引用 |

这些命令应该失败，不要为了让整套教材“零错误”把它们加到正常构建目标中。错误措辞和提示可能因编译器版本而异。

## 最终项目

先运行不读写文件的内存版本：

```sh
cargo run -p taskbook --example memory
```

在一份新解压的练习目录中运行完整工具：

```sh
cargo run -p taskbook -- list
cargo run -p taskbook -- add "学习 Rust"
cargo run -p taskbook -- add "写练习"
cargo run -p taskbook -- done 1
cargo run -p taskbook -- list
```

默认在当前工作目录中读写 `tasks.tsv`。如果有已有任务，两条新增命令会接着分配编号，而不是固定得到 1、2。不要把它指向其他程序的数据文件。

macOS / Linux 可以为一次运行指定文件：

```sh
TASKBOOK_FILE=practice-tasks.tsv cargo run -p taskbook -- list
```

PowerShell 可以先运行 `$env:TASKBOOK_FILE = "practice-tasks.tsv"`，随后运行 Cargo 命令；结束后用 `Remove-Item Env:TASKBOOK_FILE` 移除设置。

本工具面向学习和单进程顺序使用。它会覆盖写入整个任务文件；未实现事务、文件锁、并发写入协调和写入中断恢复。

## 复查命令

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --offline -- -D warnings
cargo test --workspace --offline
cargo test --workspace --all-targets --offline
cargo test --workspace --doc --offline
cargo build -p taskbook --release --offline
```

`cargo test --workspace` 包含文档测试，`--all-targets` 包括示例里的测试。它们不会执行每个示例的 `main`；观察示例输出需要分别使用 `cargo run --example`。测试会在独立临时目录读写文件，不使用当前目录的 `tasks.tsv`。

2026-10-12 逐个运行了 19 个正常示例与独立答案，确认 7 个编译失败案例按预期失败，并直接从教材正文重建了第 11～12 章项目，检查读者跟写时的构建、测试和保存结果。文章中的安装步骤未在全新机器上重新执行。

2026-10-13 展开了第 1～3 节，并同步调整 `ch03_flow` 与 `answer03`，使第三节只使用数字、布尔值与固定长度数组。直接从三节正文提取并运行了 32 个完整程序，确认 2 个故意编译失败的例子符合预期，检查了 3 组修改输入，并在新建 Cargo 项目中运行首个程序。

2026-10-13 新增第 13～15 章，在 macOS arm64、rustc 1.99.0、cargo 1.99.0 上运行了练习工作区的 20 项测试和基础工作区的 15 项测试，并通过格式检查、Clippy 与练习工作区 release 构建。另按正文重建三个项目，核对 4 个示例的输出、命令行演示、2 个预期编译错误和 2 道修改练习。基础工作区还在空 Cargo 缓存下离线运行；最低 Rust 1.85 和其他系统仍未实测。

2026-10-13 新增第 16～18 章，在 macOS arm64、rustc 1.99.0、cargo 1.99.0 上运行 `projects` 工作区的 14 项测试，并通过格式检查、Clippy 和 release 构建。另从正文重建 12 个完整文件，运行备份与恢复、命令行演示、1 个独立答案和本机 HTTP 的 5 种响应模式；第十七章统计命令与第十八章字段别名的修改练习也通过了实际测试。最低 Rust 1.85、Windows 和 Linux 仍未实测。

2026-10-13 补充分级练习和排错附录，从正文提取并运行内存书单、文件时长记录器和批量本机客户端。两个基础示例新增的 6 项单元测试通过；另检查跨进程保存、无效参数和损坏文件不被覆盖，确认 3 个预期编译错误及其修正版。批量客户端检查了 4 种响应组合和 3 种参数错误，服务响应改为 45 分钟和 0 分钟的练习也已实际运行。基础与 `projects` 工作区通过格式检查、Clippy 和全目标测试；验证环境仍为 macOS arm64、rustc 1.99.0、cargo 1.99.0，最低工具链和其他系统未在本轮实测。

## 继续练习

先尝试从空项目重写 `taskbook`，再增加只列出未完成任务或关键词搜索。每次只增加一种行为，写清输入、输出和失败条件，再加入对应测试。
