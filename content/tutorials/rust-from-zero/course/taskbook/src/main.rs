use std::env;
use std::path::PathBuf;
use std::process::ExitCode;

use taskbook::{Command, add_task, mark_done, parse_args, render_tasks, storage};

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().skip(1).collect();
    let command = parse_args(&args)?;
    let path = env::var_os("TASKBOOK_FILE")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("tasks.tsv"));
    let mut tasks = storage::load(&path)?;

    match command {
        Command::Add(title) => {
            let id = add_task(&mut tasks, &title)?;
            storage::save(&path, &tasks)?;
            println!("已添加任务 {id}");
        }
        Command::List => print!("{}", render_tasks(&tasks)),
        Command::Done(id) => {
            mark_done(&mut tasks, id)?;
            storage::save(&path, &tasks)?;
            println!("已完成任务 {id}");
        }
    }
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("错误：{message}");
            ExitCode::FAILURE
        }
    }
}
