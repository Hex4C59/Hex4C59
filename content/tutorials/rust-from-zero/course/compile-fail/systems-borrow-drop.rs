fn main() {
    let owner = String::from("hello");
    let view = &owner;
    drop(owner);
    println!("{view}");
}
