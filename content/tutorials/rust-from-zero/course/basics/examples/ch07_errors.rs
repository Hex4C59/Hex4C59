use std::io;

fn parse_minutes(input: &str) -> Result<u32, String> {
    let minutes = input
        .trim()
        .parse::<u32>()
        .map_err(|error| format!("请输入非负整数：{error}"))?;
    if minutes == 0 {
        return Err(String::from("分钟数必须大于 0"));
    }
    Ok(minutes)
}

fn main() {
    println!("请输入今天学习的分钟数：");
    let mut input = String::new();
    match io::stdin().read_line(&mut input) {
        Ok(0) => eprintln!("输入已结束，没有读到数据"),
        Ok(_) => match parse_minutes(&input) {
            Ok(minutes) => println!("已记录 {minutes} 分钟"),
            Err(message) => eprintln!("输入有误：{message}"),
        },
        Err(error) => eprintln!("读取输入失败：{error}"),
    }
}

#[cfg(test)]
mod tests {
    use super::parse_minutes;

    #[test]
    fn accepts_spaces_and_rejects_invalid_input() {
        assert_eq!(parse_minutes(" 30\n"), Ok(30));
        for input in ["0", "-1", "abc", "4294967296", ""] {
            assert!(parse_minutes(input).is_err());
        }
    }
}
