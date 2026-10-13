fn main() {
    let mut title = String::from("学习 Rust");
    let view = &title;
    title.push('!');
    println!("{view}");
}
