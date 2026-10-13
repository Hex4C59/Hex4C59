#[derive(Debug)]
struct Point {
    x: i32,
}
fn main() {
    let point = Point { x: 3 };
    let numbers = vec![point.x, 4];
    assert_eq!(numbers.len(), 2);
    println!("{point:?} / {numbers:?}");
}
