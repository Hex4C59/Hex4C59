fn main() {
    let mut records = vec![10, 20, 30];
    for record in &mut records {
        *record *= 2;
    }
    assert_eq!(records, [20, 40, 60]);
    assert_eq!(records.get(9), None);
    let text = "中文";
    assert_eq!(text.len(), 6);
    assert_eq!(text.chars().count(), 2);
    println!("{records:?}，中文：6 字节、2 个标量值");
}
