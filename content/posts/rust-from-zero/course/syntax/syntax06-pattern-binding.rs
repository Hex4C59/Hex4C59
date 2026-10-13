fn main() {
    let wanted = 5;
    let item = Some(7);
    if let Some(wanted) = item {
        println!("新绑定：{wanted}");
    }
    println!("外层：{wanted}");
    match item {
        Some(number) if number == wanted => println!("相等"),
        Some(number) => println!("不同：{number}"),
        None => println!("没有值"),
    }
}
