fn main() {
    let owned = String::from("Rust");
    let take = move || owned;
    println!("{}", take());
    println!("{}", take());
}
