use std::collections::HashSet;
use std::error::Error;
use std::fmt;
use std::fs::{self, OpenOptions};
use std::io::{self, Write};
use std::path::Path;

use serde::{Deserialize, Serialize};
use taskbook::{Task, validate_title};

#[derive(Debug)]
pub enum StoreError {
    Io(io::Error),
    Json(serde_json::Error),
    InvalidData(String),
}

impl fmt::Display for StoreError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(_) => write!(f, "文件操作失败"),
            Self::Json(_) => write!(f, "JSON 内容无法解析或生成"),
            Self::InvalidData(message) => write!(f, "{message}"),
        }
    }
}

impl Error for StoreError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Io(error) => Some(error),
            Self::Json(error) => Some(error),
            Self::InvalidData(_) => None,
        }
    }
}

impl From<io::Error> for StoreError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

impl From<serde_json::Error> for StoreError {
    fn from(error: serde_json::Error) -> Self {
        Self::Json(error)
    }
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Document {
    version: u32,
    tasks: Vec<StoredTask>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct StoredTask {
    id: u64,
    title: String,
    done: bool,
}

fn validate(tasks: &[Task]) -> Result<(), StoreError> {
    let mut ids = HashSet::new();
    for task in tasks {
        if task.id == 0 || !ids.insert(task.id) {
            return Err(StoreError::InvalidData(format!(
                "任务编号无效或重复：{}",
                task.id
            )));
        }
        validate_title(&task.title).map_err(StoreError::InvalidData)?;
    }
    Ok(())
}

pub fn encode(tasks: &[Task]) -> Result<String, StoreError> {
    validate(tasks)?;
    let document = Document {
        version: 1,
        tasks: tasks
            .iter()
            .map(|task| StoredTask {
                id: task.id,
                title: task.title.clone(),
                done: task.done,
            })
            .collect(),
    };
    Ok(serde_json::to_string_pretty(&document)?)
}

pub fn decode(input: &str) -> Result<Vec<Task>, StoreError> {
    let document: Document = serde_json::from_str(input)?;
    if document.version != 1 {
        return Err(StoreError::InvalidData(format!(
            "不支持文件格式版本 {}",
            document.version
        )));
    }
    let tasks: Vec<Task> = document
        .tasks
        .into_iter()
        .map(|task| Task {
            id: task.id,
            title: task.title,
            done: task.done,
        })
        .collect();
    validate(&tasks)?;
    Ok(tasks)
}

pub fn load(path: &Path) -> Result<Vec<Task>, StoreError> {
    match fs::read_to_string(path) {
        Ok(content) => decode(&content),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(Vec::new()),
        Err(error) => Err(StoreError::Io(error)),
    }
}

pub fn save(path: &Path, tasks: &[Task]) -> Result<(), StoreError> {
    let content = encode(tasks)?;
    fs::write(path, content)?;
    Ok(())
}

pub fn migrate(source: &Path, destination: &Path) -> Result<usize, StoreError> {
    let input = fs::read_to_string(source)?;
    let tasks = taskbook::storage::decode(&input).map_err(StoreError::InvalidData)?;
    let content = encode(&tasks)?;
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(destination)?;
    file.write_all(content.as_bytes())?;
    Ok(tasks.len())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trips_unicode_quotes_and_completion() {
        let tasks = vec![Task {
            id: 7,
            title: String::from("读 \"Rust\"，再练习 🦀"),
            done: true,
        }];
        let text = encode(&tasks).unwrap();
        assert_eq!(decode(&text).unwrap(), tasks);
        assert!(text.contains("\\\"Rust\\\""));
        assert_eq!(decode(&encode(&[]).unwrap()).unwrap(), []);
    }

    #[test]
    fn distinguishes_json_syntax_from_business_validation() {
        assert!(matches!(decode("not-json"), Err(StoreError::Json(_))));
        for input in [
            r#"{"version":2,"tasks":[]}"#,
            r#"{"version":1,"tasks":[{"id":0,"title":"Rust","done":false}]}"#,
            r#"{"version":1,"tasks":[{"id":1,"title":" ","done":false}]}"#,
            r#"{"version":1,"tasks":[{"id":1,"title":"Rust","done":false},{"id":1,"title":"重复","done":true}]}"#,
        ] {
            assert!(
                matches!(decode(input), Err(StoreError::InvalidData(_))),
                "{input}"
            );
        }
        for input in [
            r#"{"version":1,"tasks":[{"id":1,"title":"Rust","done":"false"}]}"#,
            r#"{"version":1,"tasks":[{"id":1,"title":"Rust"}]}"#,
            r#"{"version":1,"tasks":[],"typo":true}"#,
            r#"{"version":1,"tasks":[{"id":1,"title":"Rust","done":false,"typo":true}]}"#,
        ] {
            assert!(matches!(decode(input), Err(StoreError::Json(_))), "{input}");
        }
    }

    #[test]
    fn encoding_also_rejects_invalid_task_fields() {
        for task in [
            Task {
                id: 0,
                title: String::from("Rust"),
                done: false,
            },
            Task {
                id: 1,
                title: String::from("bad\ttitle"),
                done: false,
            },
        ] {
            assert!(matches!(encode(&[task]), Err(StoreError::InvalidData(_))));
        }
        let task = || Task {
            id: 1,
            title: String::from("Rust"),
            done: false,
        };
        assert!(encode(&[task(), task()]).is_err());
    }
}
