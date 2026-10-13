fn main() {
    let number = 1;
    let mut view = &number;
    *view = 2;
    println!("{view}");
}
