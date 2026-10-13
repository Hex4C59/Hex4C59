use std::error::Error;
use std::process::ExitCode;

use clap::Parser;

#[derive(Parser)]
#[command(version, about = "从本机练习服务器读取课程")]
struct Args {
    #[arg(long, value_parser = clap::value_parser!(u16).range(1..))]
    port: u16,
}

fn main() -> ExitCode {
    let args = Args::parse();
    match lesson_http::fetch(args.port) {
        Ok(lesson) => {
            println!("{}：{} 分钟", lesson.title, lesson.minutes);
            ExitCode::SUCCESS
        }
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
