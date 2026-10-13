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
