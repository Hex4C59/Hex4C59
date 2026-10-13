+++
title = "Rust 入门 18：请求本机 HTTP 服务，读取 JSON 响应"
date = 2026-10-13T09:00:00+08:00
lastmod = 2026-10-13T09:00:00+08:00
draft = false
author = "Hex4C59"
description = "用 reqwest 的阻塞客户端访问本机 HTTP 服务，分别处理状态码、JSON、数据校验、响应大小和超时，再用本机测试固定这些行为。"
summary = "用 reqwest 的阻塞客户端访问本机 HTTP 服务，分别处理状态码、JSON、数据校验、响应大小和超时，再用本机测试固定这些行为。"
tags = ["Rust", "编程入门", "教程"]
categories = ["Programming"]
series = ["rust-from-zero"]
series_order = 18
series_number = 18
series_label = "HTTP 请求"
series_part = "文件、命令行与网络"
ShowToc = true
+++

前面几章的数据来自命令行和本地文件。现在换一种来源：向一个 HTTP 服务发出请求，读取它返回的 JSON，再转成 Rust 结构体。

本章做一个独立的 `lesson-http` 小项目。它只请求 `127.0.0.1` 上的练习服务，不访问外部 API，不需要账号或密钥。完成后，你应该能区分“请求没有成功”“服务器返回 404”“JSON 格式不对”和“数据不符合规则”。

需要先理解 `Result`、自定义错误、Serde 和 clap。这一章使用阻塞客户端：执行请求时，当前线程等待结果。异步 Rust、同时请求多个服务和 HTTPS 配置留到后续专题。

## 先看一次请求的经过

HTTP（Hypertext Transfer Protocol，超文本传输协议）是一种请求与响应协议。这个练习中的过程是：

1. 客户端连接本机练习端口，请求 `/lesson.json`。
2. 服务返回状态码和响应体。
3. 客户端先检查状态码，再读取有限大小的响应体。
4. Serde 检查 JSON 的结构和字段类型。
5. 业务代码检查标题和分钟数，再打印课程信息。

`200` 表示本次 HTTP 请求成功，`404` 表示请求的资源没有找到。状态码属于响应信息；收到 200 后，仍可能遇到损坏 JSON 或不合理数据。我们不能只用一次 `?` 把这些层次都省掉。

本章希望得到这样的响应体：

`lesson-http/fixtures/lesson.json` 的完整内容：

```json
{"title":"学习 HTTP 请求","minutes":30}
```

标题不能只有空白，分钟数必须在 1～1440 之间。这是练习的业务规则，不是 HTTP 协议的限制。

## 准备项目和依赖

进入下载包的 `rust-course/projects`。如果从空目录跟写，建立 `lesson-http/src`、`examples` 和 `fixtures`，再把 `lesson-http` 加入工作区的 `members`。

`lesson-http/Cargo.toml` 的完整内容：

```toml
[package]
name = "lesson-http"
version = "0.1.0"
edition = "2024"
rust-version = "1.85"
publish = false

[dependencies]
clap = { version = "=4.6.7", features = ["derive"] }
reqwest = { version = "=0.13.5", default-features = false, features = ["blocking"] }
serde = { version = "=1.0.229", features = ["derive"] }
serde_json = "=1.0.154"
```

本章固定 reqwest 0.13.5。`blocking` 启用阻塞客户端；`default-features = false` 关闭默认功能，这个练习只用本机明文 HTTP，没有启用 TLS（Transport Layer Security，传输层安全协议）。以后请求 HTTPS 服务时需要重新选择和配置 TLS 功能，不能把本章配置直接当作通用网络客户端。

代码没有开启 reqwest 的 `json` 功能，因为它会先限制响应体大小，再由 `serde_json` 解析。`projects/Cargo.lock` 记录直接及间接依赖选择，首次运行 `cargo fetch --locked` 需要网络。我们在 rustc 1.99.0 上验证；清单声明的 Rust 1.85 最低版本没有实际运行验证。

## 客户端的完整实现

`lesson-http/src/lib.rs` 的完整内容：

```rust
use std::error::Error;
use std::fmt;
use std::io::{self, Read};
use std::time::Duration;

use serde::Deserialize;

pub const MAX_BODY: u64 = 4096;

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Lesson {
    pub title: String,
    pub minutes: u32,
}

#[derive(Debug)]
pub enum FetchError {
    Http(reqwest::Error),
    Io(io::Error),
    Json(serde_json::Error),
    Status(u16),
    TooLarge,
    InvalidData,
}

impl fmt::Display for FetchError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Http(_) => write!(f, "HTTP 请求失败"),
            Self::Io(_) => write!(f, "读取响应失败"),
            Self::Json(_) => write!(f, "响应不是符合格式的 JSON"),
            Self::Status(code) => write!(f, "服务器返回 HTTP {code}"),
            Self::TooLarge => write!(f, "响应超过 {MAX_BODY} 字节"),
            Self::InvalidData => write!(f, "端口、课程标题或分钟数无效"),
        }
    }
}

impl Error for FetchError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Http(error) => Some(error),
            Self::Io(error) => Some(error),
            Self::Json(error) => Some(error),
            _ => None,
        }
    }
}

impl From<reqwest::Error> for FetchError {
    fn from(error: reqwest::Error) -> Self {
        Self::Http(error)
    }
}

impl From<io::Error> for FetchError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

impl From<serde_json::Error> for FetchError {
    fn from(error: serde_json::Error) -> Self {
        Self::Json(error)
    }
}

pub fn fetch(port: u16) -> Result<Lesson, FetchError> {
    if port == 0 {
        return Err(FetchError::InvalidData);
    }
    let client = reqwest::blocking::Client::builder()
        .no_proxy()
        .redirect(reqwest::redirect::Policy::none())
        .connect_timeout(Duration::from_secs(1))
        .timeout(Duration::from_secs(2))
        .build()?;
    let response = client
        .get(format!("http://127.0.0.1:{port}/lesson.json"))
        .send()?;
    if !response.status().is_success() {
        return Err(FetchError::Status(response.status().as_u16()));
    }
    let mut bytes = Vec::new();
    response.take(MAX_BODY + 1).read_to_end(&mut bytes)?;
    if bytes.len() as u64 > MAX_BODY {
        return Err(FetchError::TooLarge);
    }
    let lesson: Lesson = serde_json::from_slice(&bytes)?;
    if lesson.title.trim().is_empty() || !(1..=1440).contains(&lesson.minutes) {
        return Err(FetchError::InvalidData);
    }
    Ok(lesson)
}
```

`Lesson` 是期望的响应数据。`Deserialize` 让 Serde 生成从 JSON 读取它的实现，`deny_unknown_fields` 要求未知字段也报错。这个练习采用严格格式；真实服务是否允许额外字段，需要按它的协议选择。

`FetchError` 保留了六类失败。请求、响应读取和 JSON 失败有底层原因，`source()` 会把它们交给调用者；状态码、过大响应和业务校验失败则已经由自己的变体表达。

### 为什么限制地址和重定向

`fetch` 只接收端口，地址由代码构造为 `http://127.0.0.1:{port}/lesson.json`。读者不会把服务地址输错成外部网站。`no_proxy()` 让这个客户端不经过代理；关闭重定向后，302 会作为不成功的状态码返回，而不会继续访问响应里指定的新地址。

这些设置限定了本章练习的连接方式。它们没有实现面向任意用户网址的访问控制，也没有给真实服务增加认证。不要为了请求外部地址，只把 `127.0.0.1` 换掉就沿用所有假设。

### 超时与响应大小解决不同问题

连接阶段的超时设为 1 秒，阻塞客户端的连接、读写等待超时设为 2 秒。服务连接上却一直不返回响应时，等待也会结束。

这里不能把 2 秒解释成整个 `fetch` 函数的绝对截止时间：阻塞响应的 `Read` 调用会为每次读取等待应用超时，缓慢分段返回的内容仍可能延长整个过程。本章没有额外实现贯穿所有步骤的总耗时上限。这两个值适合本机练习，其他场景需要重新确定超时策略。

`response` 实现了 `Read`，所以可以用第十二章熟悉的读取接口。`take(MAX_BODY + 1)` 最多取 4097 字节：若真的读到第 4097 字节，就能判断响应超过 4096 字节；否则读取结束后交给 JSON 解析。

只看 `Content-Length` 不够，它可能缺失，也不能替代对实际内容的限制。本例直接限制要装入 `Vec<u8>` 的响应体字节。这个数字没有描述整个 HTTP 库的内存消耗，也不是对所有网络资源的完整限制。

这里读取的是字节，因此使用 `serde_json::from_slice`。如果内容不是有效 JSON，包括其中的文本编码无效，会返回 JSON 错误。HTTP 响应成功之后，解析和校验仍可能失败。

## 为程序提供一个端口参数

`lesson-http/src/main.rs` 的完整内容：

```rust
use std::error::Error;
use std::process::ExitCode;

use clap::Parser;

#[derive(Parser)]
#[command(version, about = "从本机练习服务器读取课程")]
struct Args {
    #[arg(long, value_parser = clap::value_parser!(u16).range(1..))]
    port: u16,
}

fn main() -> ExitCode {
    let args = Args::parse();
    match lesson_http::fetch(args.port) {
        Ok(lesson) => {
            println!("{}：{} 分钟", lesson.title, lesson.minutes);
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("错误：{error}");
            let mut cause = error.source();
            while let Some(source) = cause {
                eprintln!("原因：{source}");
                cause = source.source();
            }
            ExitCode::FAILURE
        }
    }
}
```

`--port` 必须提供，且值在 `u16` 能表示的正整数范围内。clap 先拒绝端口 0；库函数也检查 0，避免其他调用者绕过 CLI 后传入它。

网络或数据失败以退出码 1 结束，参数错误以退出码 2 结束。成功时只把课程信息写到标准输出，错误和底层原因写到标准错误。

## 启动只处理一次连接的练习服务

配套的 `serve` 示例是一个本机测试夹具：为了让客户端有确定的输入，固定返回一段响应。它不路由请求，不实现完整 HTTP 服务器，也不适合接受真实用户流量。先把前面的 JSON 保存到 `lesson-http/fixtures/lesson.json`，再建立下面的文件。

`lesson-http/examples/serve.rs` 的完整内容：

```rust
use std::io::{Read, Write};
use std::net::TcpListener;
use std::time::Duration;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mode = std::env::args()
        .nth(1)
        .unwrap_or_else(|| String::from("ok"));
    let (status, body) = match mode.as_str() {
        "ok" => ("200 OK", include_str!("../fixtures/lesson.json").to_owned()),
        "missing" => ("404 Not Found", String::from("missing")),
        "bad-json" => ("200 OK", String::from("not-json")),
        "bad-data" => ("200 OK", String::from(r#"{"title":"Rust","minutes":0}"#)),
        "large" => ("200 OK", "x".repeat(5000)),
        _ => return Err("模式：ok | missing | bad-json | bad-data | large".into()),
    };
    let listener = TcpListener::bind("127.0.0.1:0")?;
    println!("本机练习端口：{}", listener.local_addr()?.port());
    println!("只接收一次连接，响应后退出");
    let (mut stream, _) = listener.accept()?;
    stream.set_read_timeout(Some(Duration::from_secs(5)))?;
    stream.set_write_timeout(Some(Duration::from_secs(5)))?;
    let mut header = Vec::new();
    while !header.ends_with(b"\r\n\r\n") {
        if header.len() >= 8192 {
            return Err("请求头过长".into());
        }
        let mut byte = [0];
        stream.read_exact(&mut byte)?;
        header.push(byte[0]);
    }
    write!(
        stream,
        "HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    )?;
    stream.flush()?;
    Ok(())
}
```

`127.0.0.1:0` 要求系统分配可用端口。这里的 0 用于服务器绑定，与客户端必须使用实际端口不同。服务打印端口后等待一次连接，写完响应就退出。

`include_str!` 在编译时把练习 JSON 放入示例中，不依赖运行时的工作目录。修改 JSON 后，通过 Cargo 重新运行示例即可重新编译。

读取请求头只是为了等待客户端发完请求。代码限制头部长度，并给这一次连接设置读写超时；它没有实现完整的 HTTP 解析。服务在接受连接前会等待，你可以在自己的终端按 Ctrl+C 结束它。

### 用两个终端完成一次请求

两个终端都进入 `rust-course/projects`。终端 A 运行：

```sh
cargo run -p lesson-http --example serve
```

它会输出类似下面的内容。端口由系统分配，每次可能不同：

```text
本机练习端口：54321
只接收一次连接，响应后退出
```

终端 B 使用 A 实际显示的端口。下面的 54321 只是示例数字，运行时必须替换：

```sh
cargo run -p lesson-http -- --port 54321
```

成功输出：

```text
学习 HTTP 请求：30 分钟
```

第一条命令启动一次性服务；第二条发出请求。服务响应后退出，下一次请求之前需要重新启动。这里的“本机”指客户端和服务在同一台机器上，不能把另一个机器显示的端口直接用于本机地址。

## 把失败条件逐项试出来

重新启动服务时，可以指定一种响应模式。每次都先启动 A，再用新的端口运行 B：

| 终端 A 命令的模式 | 响应 | 客户端应报告 |
| --- | --- | --- |
| `cargo run -p lesson-http --example serve -- missing` | HTTP 404 | `服务器返回 HTTP 404` |
| `cargo run -p lesson-http --example serve -- bad-json` | HTTP 200，正文为 `not-json` | JSON 格式错误，带底层原因 |
| `cargo run -p lesson-http --example serve -- bad-data` | HTTP 200，分钟数为 0 | 数据无效 |
| `cargo run -p lesson-http --example serve -- large` | HTTP 200，正文 5000 字节 | 响应超过 4096 字节 |

404 模式的响应体也不是 JSON，但客户端会先报告状态码，不会把它误归类为 JSON 解析错误。遇到这种输出，先检查请求路径和服务响应，再检查 JSON 格式。

请求一个没有服务监听的端口，会遇到连接错误；具体文本由操作系统和 HTTP 库提供。服务接受请求却迟迟不响应时，会遇到超时。配套测试覆盖了后一种情况，不依赖公开网站是否可用。

## 让测试只连接自己的本机夹具

配套 `tests/http.rs` 启动临时本机端口，收到一次请求后返回固定响应。每个测试拥有自己的监听器，不使用固定端口，也不请求公网。运行：

```sh
cargo test -p lesson-http --test http
```

6 个测试检查正常 JSON、404 与 302、错误字段和业务值、实际响应大小、无响应时的超时，以及 CLI 输出和端口 0 的拒绝。

服务器辅助函数还检查收到的请求行是 `GET /lesson.json HTTP/1.1`，避免只判断输出而漏掉客户端请求了错误路径。夹具使用线程同时等待请求；这里只要求理解“服务和客户端需要同时运行”，线程的所有权与协调会在并发专题继续讲。

超时测试让服务先读到请求，再通过一个通道等待测试结束。客户端必须因超时返回，测试随后通知服务退出并回收线程。测试没有靠公开网络变慢来碰运气，也没有把“等待了大约两秒”写成性能指标。

## 练习：兼容服务的旧字段名

假设旧服务用 `name` 表示课程标题，新服务改为 `title`。让同一个 `Lesson` 接受任一名称，同时保持未知字段、分钟数和空标题的原有规则。

<details>
<summary>参考答案：先自己完成再展开</summary>

在 `Lesson` 的 `title` 字段上增加属性。下面是需要替换原定义的完整结构体；其他代码保持原样：

```rust
#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Lesson {
    #[serde(alias = "name")]
    pub title: String,
    pub minutes: u32,
}
```

现在，`{"name":"Rust","minutes":30}` 和 `{"title":"Rust","minutes":30}` 都可以读取，得到的 Rust 字段仍叫 `title`。业务检查发生在反序列化之后，所以旧名字并不能绕过分钟数或空标题的限制。

如果同一份 JSON 同时包含 `name` 和 `title`，Serde 会将它们视为同一个字段的重复输入并报错；这个属性没有决定“后者覆盖前者”。为兼容添加别名时，要一起检查这种歧义。

配套主版本没有预先加这个别名。修改后，再用本机响应分别测试新名称、旧名称和两个名称同时出现的情况，不要只验证成功的一条路径。

</details>

## 接着学什么

现在，一个命令已经能发出请求，检查响应，再打印经过校验的数据。可以先关闭答案，用这个结构独立重做一个只读客户端：明确输入地址的范围、成功数据格式，以及每一层可能出现的失败。

待办工具的备份和命令行接口可以继续完善。网络客户端也可以再学异步、并发请求和重试，但每项都需要新的行为约定；例如重试写入请求之前，要先确认重复操作会带来什么结果。

## 官方延伸阅读

- [reqwest 0.13.5 阻塞客户端的配置](https://docs.rs/reqwest/0.13.5/reqwest/blocking/struct.ClientBuilder.html)
- [Response 的状态码、读取接口和错误处理](https://docs.rs/reqwest/0.13.5/reqwest/blocking/struct.Response.html)
- [Read::take：限制读取的字节数量](https://doc.rust-lang.org/std/io/trait.Read.html#method.take)
- [Serde 字段别名](https://serde.rs/field-attrs.html)
- [HTTP 语义标准 RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)

外部文档查阅日期：2026-10-13。

---

[教材目录与源码下载](/posts/rust-from-zero/) · [上一章：用 clap 整理命令行接口](/posts/rust-17-clap/)
