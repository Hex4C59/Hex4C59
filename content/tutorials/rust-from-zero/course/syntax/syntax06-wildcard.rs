fn main() {
    let item = Some(String::from("Rust"));
    if let Some(_) = item {
        println!("存在");
    }
    println!("{item:?}");
}
