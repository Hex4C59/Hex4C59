use std::fmt::Display;
fn same<T: Display>(left: T, right: T) {
    println!("{left} / {right}");
}
fn main() {
    same(1, "two");
}
