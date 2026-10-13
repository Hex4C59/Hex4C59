fn invalid() -> &'static str {
    let text = String::from("Rust");
    &text
}

fn main() {
    println!("{}", invalid());
}
