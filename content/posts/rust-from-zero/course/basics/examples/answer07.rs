fn parse_age(input: &str) -> Result<u8, String> {
    let age = input
        .trim()
        .parse::<u8>()
        .map_err(|_| String::from("年龄必须是整数"))?;
    if age > 150 {
        return Err(String::from("年龄不能超过 150"));
    }
    Ok(age)
}

fn main() {
    assert_eq!(parse_age(" 18 "), Ok(18));
    assert_eq!(parse_age("0"), Ok(0));
    for input in ["151", "256", "-1", "abc", ""] {
        assert!(parse_age(input).is_err());
    }
    println!("年龄校验通过");
}
