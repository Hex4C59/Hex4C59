fn main() {
    let scores = [50, 60, 85, 40, 100];
    let passed: Vec<i32> = scores
        .iter()
        .copied()
        .filter(|score| *score >= 60)
        .collect();
    let total: i32 = passed.iter().sum();
    assert_eq!(passed, [60, 85, 100]);
    assert_eq!(total, 245);
    println!("及格成绩：{passed:?}，合计：{total}");
}
