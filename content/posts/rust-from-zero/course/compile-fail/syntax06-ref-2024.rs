fn main() {
    let item = Some(String::from("Rust"));
    if let Some(ref text) = &item {
        println!("{text}");
    }
}
