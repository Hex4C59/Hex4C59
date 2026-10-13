use std::error::Error;
use std::process::ExitCode;

use clap::Parser;
use taskbook_cli::{Cli, execute};

fn main() -> ExitCode {
    let cli = Cli::parse();
    match execute(cli) {
        Ok(output) => {
            print!("{output}");
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
