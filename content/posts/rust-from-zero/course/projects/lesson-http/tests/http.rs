use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::process::Command;
use std::thread;
use std::time::Duration;

use lesson_http::{FetchError, MAX_BODY, fetch};

fn read_request(stream: &mut TcpStream) {
    stream
        .set_read_timeout(Some(Duration::from_secs(5)))
        .unwrap();
    let mut header = Vec::new();
    while !header.ends_with(b"\r\n\r\n") {
        assert!(header.len() < 8192);
        let mut byte = [0];
        stream.read_exact(&mut byte).unwrap();
        header.push(byte[0]);
    }
    assert!(
        String::from_utf8(header)
            .unwrap()
            .starts_with("GET /lesson.json HTTP/1.1\r\n")
    );
}

fn server(status: &str, body: &str) -> (u16, thread::JoinHandle<()>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let location = if status.starts_with("302") {
        format!("Location: http://127.0.0.1:{port}/redirected\r\n")
    } else {
        String::new()
    };
    let response = format!(
        "HTTP/1.1 {status}\r\n{location}Content-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    );
    let handle = thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        read_request(&mut stream);
        stream
            .set_write_timeout(Some(Duration::from_secs(5)))
            .unwrap();
        let _ = stream.write_all(response.as_bytes());
    });
    (port, handle)
}

#[test]
fn parses_successful_response() {
    let (port, handle) = server("200 OK", r#"{"title":"学习 HTTP 请求","minutes":30}"#);
    let lesson = fetch(port).unwrap();
    handle.join().unwrap();
    assert_eq!(lesson.title, "学习 HTTP 请求");
    assert_eq!(lesson.minutes, 30);
}

#[test]
fn rejects_error_status_and_redirect_without_parsing_body() {
    for status in ["404 Not Found", "302 Found"] {
        let (port, handle) = server(status, "not-json");
        let error = fetch(port).unwrap_err();
        handle.join().unwrap();
        assert!(matches!(error, FetchError::Status(404 | 302)));
    }
}

#[test]
fn rejects_invalid_json_fields_and_business_values() {
    for (body, business) in [
        ("not-json", false),
        (r#"{"title":"Rust","minutes":"30"}"#, false),
        (r#"{"title":"Rust"}"#, false),
        (r#"{"title":"Rust","minutes":30,"unknown":true}"#, false),
        (r#"{"title":" ","minutes":30}"#, true),
        (r#"{"title":"Rust","minutes":0}"#, true),
        (r#"{"title":"Rust","minutes":1441}"#, true),
    ] {
        let (port, handle) = server("200 OK", body);
        let error = fetch(port).unwrap_err();
        handle.join().unwrap();
        if business {
            assert!(matches!(error, FetchError::InvalidData));
        } else {
            assert!(matches!(error, FetchError::Json(_)));
        }
    }
}

#[test]
fn bounds_the_actual_body_size() {
    let valid = r#"{"title":"Rust","minutes":30}"#;
    let at_limit = format!("{valid}{}", " ".repeat(MAX_BODY as usize - valid.len()));
    let (port, handle) = server("200 OK", &at_limit);
    assert_eq!(fetch(port).unwrap().title, "Rust");
    handle.join().unwrap();
    let (port, handle) = server("200 OK", &"x".repeat(MAX_BODY as usize + 1));
    assert!(matches!(fetch(port), Err(FetchError::TooLarge)));
    handle.join().unwrap();
}

#[test]
fn times_out_when_server_does_not_respond() {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let (release, wait) = std::sync::mpsc::channel::<()>();
    let handle = thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        read_request(&mut stream);
        let _ = wait.recv_timeout(Duration::from_secs(5));
    });
    let result = fetch(port);
    release.send(()).unwrap();
    handle.join().unwrap();
    match result {
        Err(FetchError::Http(error)) => assert!(error.is_timeout()),
        other => panic!("expected timeout, got {other:?}"),
    }
}

#[test]
fn cli_prints_data_and_parser_rejects_port_zero() {
    let (port, handle) = server("200 OK", r#"{"title":"Rust","minutes":30}"#);
    let output = Command::new(env!("CARGO_BIN_EXE_lesson-http"))
        .args(["--port", &port.to_string()])
        .output()
        .unwrap();
    handle.join().unwrap();
    assert!(output.status.success());
    assert_eq!(String::from_utf8(output.stdout).unwrap(), "Rust：30 分钟\n");
    let output = Command::new(env!("CARGO_BIN_EXE_lesson-http"))
        .args(["--port", "0"])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
}
