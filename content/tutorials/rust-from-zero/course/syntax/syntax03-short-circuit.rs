fn right() -> bool {
    println!("计算右侧");
    true
}
fn main() {
    let a = false && right();
    let b = true || right();
    let c = true && right();
    println!("{a} / {b} / {c}");
}
