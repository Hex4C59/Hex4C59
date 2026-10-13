fn main() {
    let mut item = Some(String::from("Rust"));
    match &mut item {
        Some(text) => text.push('!'),
        None => {}
    }
    if let Some(text) = &item {
        let _: &String = text;
        println!("借用：{text}");
    }
    let owned = match item {
        Some(text) => text,
        None => String::new(),
    };
    println!("取得所有权：{owned}");
}
