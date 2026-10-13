use error_lab::{AppError, parse_minutes};
use std::error::Error;

fn main() {
    for input in ["abc", "0"] {
        let error = parse_minutes(input).unwrap_err();
        let category = match &error {
            AppError::Number(_) => "数字格式错误",
            AppError::ZeroMinutes => "业务规则错误",
            _ => "其他错误",
        };
        println!(
            "{input}：{category}，有底层原因：{}",
            error.source().is_some()
        );
    }
}
