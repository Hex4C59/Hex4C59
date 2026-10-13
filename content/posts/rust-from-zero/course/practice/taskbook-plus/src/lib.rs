use taskbook::Task;

pub const USAGE: &str = "用法：taskbook-plus add <标题> | list | done <编号> | pending | search <关键词> | remove <编号>";

#[derive(Debug, PartialEq, Eq)]
pub enum Command {
    Base(taskbook::Command),
    Pending,
    Search(String),
    Remove(u64),
}

pub fn parse_args(args: &[String]) -> Result<Command, String> {
    match args {
        [command] if command == "pending" => Ok(Command::Pending),
        [command, query] if command == "search" => {
            let query = query.trim();
            if query.is_empty() {
                return Err(String::from("搜索关键词不能为空"));
            }
            Ok(Command::Search(query.to_string()))
        }
        [command, id] if command == "remove" => {
            let id = id
                .parse::<u64>()
                .map_err(|_| String::from("编号必须是正整数"))?;
            if id == 0 {
                return Err(String::from("编号必须大于 0"));
            }
            Ok(Command::Remove(id))
        }
        _ => taskbook::parse_args(args)
            .map(Command::Base)
            .map_err(|message| {
                if message == taskbook::USAGE {
                    USAGE.to_string()
                } else {
                    message
                }
            }),
    }
}

pub fn pending(tasks: &[Task]) -> Vec<&Task> {
    tasks.iter().filter(|task| !task.done).collect()
}

pub fn search<'a>(tasks: &'a [Task], query: &str) -> Result<Vec<&'a Task>, String> {
    let query = query.trim();
    if query.is_empty() {
        return Err(String::from("搜索关键词不能为空"));
    }
    Ok(tasks
        .iter()
        .filter(|task| task.title.contains(query))
        .collect())
}

pub fn render_selection(tasks: &[&Task]) -> String {
    if tasks.is_empty() {
        return String::from("没有符合条件的任务\n");
    }
    let mut output = String::new();
    for task in tasks {
        let mark = if task.done { "x" } else { " " };
        output.push_str(&format!("{} [{mark}] {}\n", task.id, task.title));
    }
    output
}

pub fn remove_task(tasks: &mut Vec<Task>, id: u64) -> Result<(), String> {
    let index = tasks
        .iter()
        .position(|task| task.id == id)
        .ok_or_else(|| format!("找不到任务 {id}"))?;
    tasks.remove(index);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use taskbook::{add_task, mark_done};

    #[test]
    fn filters_without_changing_tasks() {
        let mut tasks = Vec::new();
        add_task(&mut tasks, "学习 Rust").unwrap();
        add_task(&mut tasks, "买水果").unwrap();
        add_task(&mut tasks, "复习 Rust").unwrap();
        mark_done(&mut tasks, 1).unwrap();
        let before = taskbook::render_tasks(&tasks);
        assert_eq!(
            render_selection(&pending(&tasks)),
            "2 [ ] 买水果\n3 [ ] 复习 Rust\n"
        );
        assert_eq!(
            render_selection(&search(&tasks, "Rust").unwrap()),
            "1 [x] 学习 Rust\n3 [ ] 复习 Rust\n"
        );
        assert!(search(&tasks, "rust").unwrap().is_empty());
        assert!(search(&tasks, " \t ").is_err());
        assert_eq!(taskbook::render_tasks(&tasks), before);
    }

    #[test]
    fn search_result_borrows_tasks_without_borrowing_query() {
        let mut tasks = Vec::new();
        add_task(&mut tasks, "学习 Rust").unwrap();
        let selected;
        {
            let query = String::from("Rust");
            selected = search(&tasks, &query).unwrap();
        }
        assert_eq!(selected[0].title, "学习 Rust");
    }

    #[test]
    fn empty_selection_has_a_message() {
        assert_eq!(render_selection(&pending(&[])), "没有符合条件的任务\n");
        let mut tasks = Vec::new();
        add_task(&mut tasks, "学习 Rust").unwrap();
        mark_done(&mut tasks, 1).unwrap();
        assert!(pending(&tasks).is_empty());
    }

    #[test]
    fn removal_keeps_other_ids_and_reports_missing_id() {
        let mut tasks = Vec::new();
        for title in ["第一条", "第二条", "第三条"] {
            add_task(&mut tasks, title).unwrap();
        }
        remove_task(&mut tasks, 2).unwrap();
        assert_eq!(tasks.iter().map(|task| task.id).collect::<Vec<_>>(), [1, 3]);
        let before = taskbook::render_tasks(&tasks);
        assert!(remove_task(&mut tasks, 99).is_err());
        assert_eq!(taskbook::render_tasks(&tasks), before);
        assert_eq!(add_task(&mut tasks, "第四条"), Ok(4));
    }

    #[test]
    fn deleting_highest_id_can_reuse_it_on_the_next_add() {
        let mut tasks = Vec::new();
        add_task(&mut tasks, "第一条").unwrap();
        add_task(&mut tasks, "第二条").unwrap();
        remove_task(&mut tasks, 2).unwrap();
        assert_eq!(add_task(&mut tasks, "新第二条"), Ok(2));
    }

    #[test]
    fn parses_extended_commands_and_rejects_invalid_forms() {
        let args = |parts: &[&str]| {
            parts
                .iter()
                .map(|part| part.to_string())
                .collect::<Vec<_>>()
        };
        assert_eq!(parse_args(&args(&["pending"])), Ok(Command::Pending));
        assert_eq!(
            parse_args(&args(&["search", " Rust "])),
            Ok(Command::Search(String::from("Rust")))
        );
        assert_eq!(parse_args(&args(&["remove", "2"])), Ok(Command::Remove(2)));
        assert_eq!(
            parse_args(&args(&["list"])),
            Ok(Command::Base(taskbook::Command::List))
        );
        for parts in [
            vec!["pending", "extra"],
            vec!["search"],
            vec!["search", " "],
            vec!["remove", "0"],
            vec!["remove", "-1"],
            vec!["remove", "18446744073709551616"],
        ] {
            assert!(parse_args(&args(&parts)).is_err());
        }
    }
}
