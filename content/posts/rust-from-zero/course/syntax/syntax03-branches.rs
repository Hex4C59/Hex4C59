fn choose(valid: bool) -> i32 {
    if valid {
        10
    } else {
        return 0;
    }
}
fn main() {
    println!("{} / {}", choose(true), choose(false));
    let mut count = 0;
    assert_eq!(count, 0);
    let assignment = count = 3;
    assert_eq!(assignment, ());
    println!("赋值后的数：{count}，赋值表达式：{assignment:?}");
}
