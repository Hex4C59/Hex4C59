fn count_passed(scores: [u32; 3]) -> u32 {
    let mut passed = 0;
    for score in scores {
        if score >= 60 {
            passed += 1;
        }
    }
    passed
}

fn main() {
    assert_eq!(count_passed([59, 60, 90]), 2);
    assert_eq!(count_passed([0, 59, 58]), 0);
    assert_eq!(count_passed([60, 60, 60]), 3);
    println!("练习通过");
}
