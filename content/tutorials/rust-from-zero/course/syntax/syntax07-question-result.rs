use std::num::ParseIntError;
fn concise(input: &str) -> Result<u32, ParseIntError> {
    let number = input.parse::<u32>()?;
    Ok(number)
}
fn expanded(input: &str) -> Result<u32, ParseIntError> {
    let number = match input.parse::<u32>() {
        Ok(number) => number,
        Err(error) => return Err(From::from(error)),
    };
    Ok(number)
}
fn within_block(input: &str) -> Result<u32, ParseIntError> {
    let number = { input.parse::<u32>()? };
    println!("解析后的代码：{number}");
    Ok(number)
}
fn main() {
    for input in ["12", "bad"] {
        assert_eq!(concise(input), expanded(input));
    }
    println!("成功：{}", concise("12").unwrap());
    assert!(within_block("bad").is_err());
    println!("调用方仍继续执行");
}
