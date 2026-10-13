use std::error::Error;
use std::path::Path;
use std::process::ExitCode;

use taskbook_json::storage::StoreError;

fn run() -> Result<(), StoreError> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.as_slice() {
        [command, source, destination] if command == "backup" || command == "restore" => {
            let count = taskbook_backup::copy_snapshot(Path::new(source), Path::new(destination))?;
            let action = if command == "backup" {
                "备份"
            } else {
                "恢复"
            };
            println!("已{action} {count} 个任务到 {destination}");
            Ok(())
        }
        _ => Err(StoreError::InvalidData(String::from(
            "用法：taskbook-backup backup <源文件> <新备份> | restore <备份> <新文件>",
        ))),
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("错误：{error}");
            let mut cause = error.source();
            while let Some(source) = cause {
                eprintln!("原因：{source}");
                cause = source.source();
            }
            ExitCode::FAILURE
        }
    }
}
