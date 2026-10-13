use std::fmt::Display;
fn show<T: Display>(value: &T) {
    println!("{value}");
}
fn main() {
    show::<str>("Rust");
}
