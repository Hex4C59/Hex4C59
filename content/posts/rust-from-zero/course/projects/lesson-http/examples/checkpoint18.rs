use std::error::Error;
use std::process::ExitCode;

use clap::Parser;

#[derive(Parser)]
#[command(about = "顺序读取最多三个本机课程服务")]
struct Args {
    #[arg(long = "port", required = true, num_args = 1..=3,
        value_parser = clap::value_parser!(u16).range(1..))]
    ports: Vec<u16>,
}

fn main() -> ExitCode {
    let args = Args::parse();
    let mut succeeded = 0;
    let mut failed = 0;
    for port in args.ports {
        match lesson_http::fetch(port) {
            Ok(lesson) => {
                println!("端口 {port}：{}，{} 分钟", lesson.title, lesson.minutes);
                succeeded += 1;
            }
            Err(error) => {
                eprintln!("端口 {port} 请求失败：{error}");
                let mut cause = error.source();
                while let Some(source) = cause {
                    eprintln!("原因：{source}");
                    cause = source.source();
                }
                failed += 1;
            }
        }
    }
    println!("成功 {succeeded} 项，失败 {failed} 项");
    if failed == 0 {
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}
