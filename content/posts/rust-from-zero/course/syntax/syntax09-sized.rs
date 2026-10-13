use std::fmt::Display;
fn show<T: Display + ?Sized>(value: &T) {
    println!("{value}");
}
fn length<const N: usize>(_values: &[u32; N]) -> usize {
    N
}
fn main() {
    show::<str>("Rust");
    println!("{} / {}", length(&[1, 2]), length(&[1, 2, 3]));
}
