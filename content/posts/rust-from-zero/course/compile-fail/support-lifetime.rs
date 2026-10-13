fn main() {
    let view;
    {
        let title = String::from("学习 Rust");
        view = title.as_str();
    }
    println!("{view}");
}
