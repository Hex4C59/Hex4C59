fn main() {
    let item = Some(String::from("Rust"));
    if let Some(ref text) = item {
        let _: &String = text;
        println!("ref 绑定：{text}");
    }
    let &number = &42_i32;
    println!("去掉引用这一层：{number}");
    println!("原值：{item:?}");
}
