use std::path::PathBuf;

use clap::{Parser, Subcommand};
use taskbook_json::storage::{self, StoreError};

#[derive(Debug, Parser)]
#[command(name = "taskbook-cli", version, about = "管理本地 JSON 待办任务")]
pub struct Cli {
    #[arg(
        long,
        global = true,
        default_value = "tasks.json",
        help = "任务文件路径"
    )]
    pub file: PathBuf,
    #[command(subcommand)]
    pub command: Command,
}

#[derive(Debug, Subcommand)]
pub enum Command {
    #[command(about = "新增任务")]
    Add { title: String },
    #[command(about = "列出全部任务")]
    List,
    #[command(about = "标记任务完成")]
    Done {
        #[arg(value_parser = clap::value_parser!(u64).range(1..))]
        id: u64,
    },
    #[command(about = "列出未完成任务")]
    Pending,
    #[command(about = "按标题搜索")]
    Search { query: String },
    #[command(about = "删除任务")]
    Remove {
        #[arg(value_parser = clap::value_parser!(u64).range(1..))]
        id: u64,
    },
    #[command(about = "备份到一个新文件")]
    Backup { destination: PathBuf },
    #[command(about = "从备份恢复到 --file 指定的新文件")]
    Restore { source: PathBuf },
}

pub fn execute(cli: Cli) -> Result<String, StoreError> {
    match &cli.command {
        Command::Backup { destination } => {
            let count = taskbook_backup::copy_snapshot(&cli.file, destination)?;
            return Ok(format!(
                "已备份 {count} 个任务到 {}\n",
                destination.display()
            ));
        }
        Command::Restore { source } => {
            let count = taskbook_backup::copy_snapshot(source, &cli.file)?;
            return Ok(format!("已恢复 {count} 个任务到 {}\n", cli.file.display()));
        }
        _ => {}
    }
    let mut tasks = storage::load(&cli.file)?;
    let output = match cli.command {
        Command::Add { title } => {
            let id = taskbook::add_task(&mut tasks, &title).map_err(StoreError::InvalidData)?;
            storage::save(&cli.file, &tasks)?;
            format!("已添加任务 {id}\n")
        }
        Command::List => taskbook::render_tasks(&tasks),
        Command::Done { id } => {
            taskbook::mark_done(&mut tasks, id).map_err(StoreError::InvalidData)?;
            storage::save(&cli.file, &tasks)?;
            format!("已完成任务 {id}\n")
        }
        Command::Pending => taskbook_plus::render_selection(&taskbook_plus::pending(&tasks)),
        Command::Search { query } => {
            let found = taskbook_plus::search(&tasks, &query).map_err(StoreError::InvalidData)?;
            taskbook_plus::render_selection(&found)
        }
        Command::Remove { id } => {
            taskbook_plus::remove_task(&mut tasks, id).map_err(StoreError::InvalidData)?;
            storage::save(&cli.file, &tasks)?;
            format!("已删除任务 {id}\n")
        }
        Command::Backup { .. } | Command::Restore { .. } => unreachable!(),
    };
    Ok(output)
}
