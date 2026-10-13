fn main() {
    let text = String::from("Rust");
    let first = &text;
    let second = first;
    println!("{first} / {second} / {text}");
}
