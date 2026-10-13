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
