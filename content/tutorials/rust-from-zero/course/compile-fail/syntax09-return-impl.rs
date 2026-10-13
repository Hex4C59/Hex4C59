use std::fmt::Display;
fn choose(first: bool) -> impl Display {
    if first { 1 } else { "two" }
}
fn main() {
    println!("{}", choose(true));
}
