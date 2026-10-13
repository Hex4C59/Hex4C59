use std::collections::HashSet;
use std::fs;
use std::io::ErrorKind;
use std::path::Path;

use crate::{Task, validate_title};

pub fn encode(tasks: &[Task]) -> Result<String, String> {
    let mut output = String::new();
    let mut ids = HashSet::new();
    for task in tasks {
        validate_title(&task.title)?;
        if task.id == 0 || !ids.insert(task.id) {
            return Err(format!("任务编号无效或重复：{}", task.id));
        }
        let done = if task.done { 1 } else { 0 };
        output.push_str(&format!("{}\t{done}\t{}\n", task.id, task.title));
    }
    Ok(output)
}

pub fn decode(input: &str) -> Result<Vec<Task>, String> {
    let mut tasks = Vec::new();
    let mut ids = HashSet::new();
    for (index, line) in input.lines().enumerate() {
        let line_number = index + 1;
        let invalid = || format!("第 {line_number} 行格式无效");
        let parts: Vec<&str> = line.splitn(3, '\t').collect();
        let [id, done, title] = parts.as_slice() else {
            return Err(invalid());
        };
        let id = id.parse::<u64>().map_err(|_| invalid())?;
        if id == 0 || !ids.insert(id) {
            return Err(format!("第 {line_number} 行编号为 0 或重复"));
        }
        let done = match *done {
            "0" => false,
            "1" => true,
            _ => return Err(invalid()),
        };
        validate_title(title).map_err(|message| format!("第 {line_number} 行：{message}"))?;
        tasks.push(Task {
            id,
            title: title.to_string(),
            done,
        });
    }
    Ok(tasks)
}

pub fn load(path: &Path) -> Result<Vec<Task>, String> {
    match fs::read_to_string(path) {
        Ok(content) => decode(&content),
        Err(error) if error.kind() == ErrorKind::NotFound => Ok(Vec::new()),
        Err(error) => Err(format!("无法读取 {}：{error}", path.display())),
    }
}

pub fn save(path: &Path, tasks: &[Task]) -> Result<(), String> {
    let content = encode(tasks)?;
    fs::write(path, content).map_err(|error| format!("无法写入 {}：{error}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unicode_tasks_round_trip() {
        let tasks = vec![
            Task {
                id: 1,
                title: "学习 Rust 🦀".into(),
                done: false,
            },
            Task {
                id: 4,
                title: "完成练习".into(),
                done: true,
            },
        ];
        assert_eq!(decode(&encode(&tasks).unwrap()), Ok(tasks));
        assert_eq!(decode(""), Ok(Vec::new()));
        assert_eq!(decode("1\t0\t测试\r\n").unwrap()[0].title, "测试");
    }

    #[test]
    fn rejects_corrupt_records() {
        for content in [
            "broken",
            "0\t0\ta\n",
            "x\t0\ta\n",
            "1\t2\ta\n",
            "1\t0\t\n",
            "1\t0\ta\tb\n",
            "1\t0\ta\n1\t1\tb\n",
            "\n",
        ] {
            assert!(decode(content).is_err(), "意外接受了 {content:?}");
        }
    }

    #[test]
    fn refuses_to_encode_invalid_public_fields() {
        let tasks = vec![Task {
            id: 0,
            title: "无效".into(),
            done: false,
        }];
        assert!(encode(&tasks).is_err());
        let tasks = vec![Task {
            id: 1,
            title: "a\tb".into(),
            done: false,
        }];
        assert!(encode(&tasks).is_err());
    }
}
