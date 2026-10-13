fn main() {
    let item = Some(String::from("Rust"));
    if let Some(_text) = item {
        println!("存在");
    }
    println!("{item:?}");
}
