use std::env;
use std::error::Error;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use taskbook::{add_task, mark_done, render_tasks};
use taskbook_json::storage::{self, StoreError};
use taskbook_plus::{Command, parse_args, pending, remove_task, render_selection, search};

fn run() -> Result<(), StoreError> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.first().map(String::as_str) == Some("migrate") {
        let [_, source, destination] = args.as_slice() else {
            return Err(StoreError::InvalidData(String::from(
                "用法：taskbook-json migrate <TSV源文件> <JSON新文件>",
            )));
        };
        let count = storage::migrate(Path::new(source), Path::new(destination))?;
        println!("已迁移 {count} 条任务");
        return Ok(());
    }
    let command = parse_args(&args).map_err(|message| {
        let message = if message == taskbook_plus::USAGE {
            message.replace("taskbook-plus", "taskbook-json")
        } else {
            message
        };
        StoreError::InvalidData(message)
    })?;
    let path = env::var_os("TASKBOOK_JSON_FILE")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("tasks.json"));
    let mut tasks = storage::load(&path)?;
    match command {
        Command::Base(taskbook::Command::Add(title)) => {
            let id = add_task(&mut tasks, &title).map_err(StoreError::InvalidData)?;
            storage::save(&path, &tasks)?;
            println!("已添加任务 {id}");
        }
        Command::Base(taskbook::Command::List) => print!("{}", render_tasks(&tasks)),
        Command::Base(taskbook::Command::Done(id)) => {
            mark_done(&mut tasks, id).map_err(StoreError::InvalidData)?;
            storage::save(&path, &tasks)?;
            println!("已完成任务 {id}");
        }
        Command::Pending => print!("{}", render_selection(&pending(&tasks))),
        Command::Search(query) => {
            let selected = search(&tasks, &query).map_err(StoreError::InvalidData)?;
            print!("{}", render_selection(&selected));
        }
        Command::Remove(id) => {
            remove_task(&mut tasks, id).map_err(StoreError::InvalidData)?;
            storage::save(&path, &tasks)?;
            println!("已删除任务 {id}");
        }
    }
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("错误：{error}");
            let mut source = error.source();
            while let Some(cause) = source {
                eprintln!("原因：{cause}");
                source = cause.source();
            }
            ExitCode::FAILURE
        }
    }
}
