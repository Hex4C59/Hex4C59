use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

const USAGE: &str = "用法：checkpoint12 <文件> add <分钟数> | <文件> total";

enum Command {
    Add(u32),
    Total,
}

fn parse_minutes(input: &str) -> Result<u32, String> {
    let value = input
        .trim()
        .parse::<u32>()
        .map_err(|_| String::from("分钟数必须是整数"))?;
    validate_minutes(value)
}

fn validate_minutes(value: u32) -> Result<u32, String> {
    if !(1..=1440).contains(&value) {
        return Err(String::from("每条记录必须在 1～1440 分钟之间"));
    }
    Ok(value)
}

fn parse_args(args: &[String]) -> Result<(PathBuf, Command), String> {
    match args {
        [file, command, minutes] if command == "add" => {
            Ok((PathBuf::from(file), Command::Add(parse_minutes(minutes)?)))
        }
        [file, command] if command == "total" => Ok((PathBuf::from(file), Command::Total)),
        _ => Err(USAGE.to_string()),
    }
}

fn decode(input: &str) -> Result<Vec<u32>, String> {
    let mut records = Vec::new();
    for (index, line) in input.lines().enumerate() {
        let minutes =
            parse_minutes(line).map_err(|message| format!("第 {} 行：{message}", index + 1))?;
        records.push(minutes);
    }
    Ok(records)
}

fn encode(records: &[u32]) -> Result<String, String> {
    let mut output = String::new();
    for minutes in records {
        validate_minutes(*minutes)?;
        output.push_str(&format!("{minutes}\n"));
    }
    Ok(output)
}

fn load(path: &Path) -> Result<Vec<u32>, String> {
    match fs::read_to_string(path) {
        Ok(input) => decode(&input),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(Vec::new()),
        Err(error) => Err(format!("读取失败：{error}")),
    }
}

fn total(records: &[u32]) -> Result<u64, String> {
    let mut sum = 0_u64;
    for minutes in records {
        sum = sum
            .checked_add(u64::from(*minutes))
            .ok_or_else(|| String::from("总时长超出范围"))?;
    }
    Ok(sum)
}

fn run() -> Result<(), String> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let (path, command) = parse_args(&args)?;
    let mut records = load(&path)?;
    match command {
        Command::Add(minutes) => {
            records.push(minutes);
            let content = encode(&records)?;
            fs::write(&path, content).map_err(|error| format!("保存失败：{error}"))?;
            println!("已记录 {minutes} 分钟");
        }
        Command::Total => println!("累计 {} 分钟", total(&records)?),
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn format_round_trip_includes_empty_and_boundary_values() {
        for records in [vec![], vec![1], vec![25, 40, 1440]] {
            assert_eq!(decode(&encode(&records).unwrap()).unwrap(), records);
        }
        assert_eq!(total(&[]).unwrap(), 0);
        assert_eq!(total(&[25, 40]).unwrap(), 65);
    }

    #[test]
    fn invalid_records_and_blank_lines_are_rejected() {
        for input in ["0", "1441", "abc", "25\n\n40\n", "-1"] {
            assert!(decode(input).is_err(), "{input:?}");
        }
        assert!(decode("25\nabc\n").unwrap_err().contains("第 2 行"));
        assert!(encode(&[0]).is_err());
    }

    #[test]
    fn wrong_arity_and_invalid_minutes_are_rejected() {
        for args in [
            vec!["data.txt", "add"],
            vec!["data.txt", "total", "extra"],
            vec!["data.txt", "add", "0"],
        ] {
            let args: Vec<String> = args.into_iter().map(String::from).collect();
            assert!(parse_args(&args).is_err());
        }
    }
}
