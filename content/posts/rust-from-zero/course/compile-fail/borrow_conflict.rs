fn main() {
    let mut text = String::from("Rust");
    let borrowed = &text;
    text.push('!');
    println!("{borrowed}");
}
