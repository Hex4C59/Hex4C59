pub mod storage;

pub const USAGE: &str = "用法：taskbook add <标题> | list | done <正整数编号>";

#[derive(Debug, PartialEq, Eq)]
pub struct Task {
    pub id: u64,
    pub title: String,
    pub done: bool,
}

#[derive(Debug, PartialEq, Eq)]
pub enum Command {
    Add(String),
    List,
    Done(u64),
}

pub fn parse_args(args: &[String]) -> Result<Command, String> {
    match args {
        [command, title] if command == "add" => Ok(Command::Add(title.clone())),
        [command] if command == "list" => Ok(Command::List),
        [command, id] if command == "done" => {
            let id = id
                .parse::<u64>()
                .map_err(|_| String::from("编号必须是正整数"))?;
            if id == 0 {
                return Err(String::from("编号必须大于 0"));
            }
            Ok(Command::Done(id))
        }
        _ => Err(USAGE.to_string()),
    }
}

pub fn validate_title(title: &str) -> Result<(), String> {
    if title.trim().is_empty() {
        return Err(String::from("标题不能为空"));
    }
    if title.contains(['\t', '\n', '\r']) {
        return Err(String::from("标题不能包含制表符或换行"));
    }
    Ok(())
}

pub fn add_task(tasks: &mut Vec<Task>, title: &str) -> Result<u64, String> {
    validate_title(title)?;
    let id = tasks
        .iter()
        .map(|task| task.id)
        .max()
        .unwrap_or(0)
        .checked_add(1)
        .ok_or_else(|| String::from("任务编号已用完"))?;
    tasks.push(Task {
        id,
        title: title.trim().to_string(),
        done: false,
    });
    Ok(id)
}

pub fn mark_done(tasks: &mut [Task], id: u64) -> Result<(), String> {
    let task = tasks
        .iter_mut()
        .find(|task| task.id == id)
        .ok_or_else(|| format!("找不到任务 {id}"))?;
    task.done = true;
    Ok(())
}

pub fn render_tasks(tasks: &[Task]) -> String {
    if tasks.is_empty() {
        return String::from("还没有任务\n");
    }
    let mut output = String::new();
    for task in tasks {
        let mark = if task.done { "x" } else { " " };
        output.push_str(&format!("{} [{mark}] {}\n", task.id, task.title));
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(parts: &[&str]) -> Vec<String> {
        parts.iter().map(|part| part.to_string()).collect()
    }

    #[test]
    fn parses_commands_and_rejects_wrong_arity() {
        assert_eq!(
            parse_args(&args(&["add", "学习 Rust"])),
            Ok(Command::Add("学习 Rust".into()))
        );
        assert_eq!(parse_args(&args(&["list"])), Ok(Command::List));
        assert_eq!(parse_args(&args(&["done", "2"])), Ok(Command::Done(2)));
        for input in [
            vec![],
            args(&["add"]),
            args(&["list", "extra"]),
            args(&["unknown"]),
            args(&["done", "0"]),
            args(&["done", "-1"]),
            args(&["done", "abc"]),
            args(&["done", "18446744073709551616"]),
        ] {
            assert!(parse_args(&input).is_err());
        }
    }

    #[test]
    fn adds_and_completes_without_changing_other_tasks() {
        let mut tasks = Vec::new();
        assert_eq!(add_task(&mut tasks, " 学习 Rust "), Ok(1));
        assert_eq!(add_task(&mut tasks, "写练习"), Ok(2));
        assert_eq!(mark_done(&mut tasks, 2), Ok(()));
        assert!(!tasks[0].done);
        assert!(tasks[1].done);
        assert_eq!(mark_done(&mut tasks, 2), Ok(()));
        assert!(mark_done(&mut tasks, 9).is_err());
        assert_eq!(render_tasks(&tasks), "1 [ ] 学习 Rust\n2 [x] 写练习\n");
    }

    #[test]
    fn invalid_title_does_not_mutate_tasks() {
        let mut tasks = Vec::new();
        for title in ["", "   ", "a\tb", "a\nb", "a\rb"] {
            assert!(add_task(&mut tasks, title).is_err());
            assert!(tasks.is_empty());
        }
    }

    #[test]
    fn refuses_id_overflow() {
        let mut tasks = vec![Task {
            id: u64::MAX,
            title: "最后一项".into(),
            done: false,
        }];
        assert!(add_task(&mut tasks, "新任务").is_err());
        assert_eq!(tasks.len(), 1);
    }

    #[test]
    fn empty_list_has_a_message() {
        assert_eq!(render_tasks(&[]), "还没有任务\n");
    }
}
