use std::env;
use std::error::Error;
use std::path::Path;
use std::process::ExitCode;

use error_lab::{AppError, parse_minutes, read_minutes};

fn run() -> Result<(), AppError> {
    let args: Vec<String> = env::args().skip(1).collect();
    let minutes = match args.as_slice() {
        [input] if input != "--file" => parse_minutes(input)?,
        [flag, path] if flag == "--file" => read_minutes(Path::new(path))?,
        _ => return Err(AppError::Usage),
    };
    println!("已记录 {minutes} 分钟");
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
