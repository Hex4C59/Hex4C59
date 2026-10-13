use std::collections::HashMap;

fn total(numbers: &[i32]) -> i32 {
    let mut sum = 0;
    for number in numbers {
        sum += *number;
    }
    sum
}

fn main() {
    let text = String::from("你好 Rust");
    println!("字节数：{}，标量值数：{}", text.len(), text.chars().count());
    println!("第一个标量值：{:?}", text.chars().next());

    let mut minutes = vec![20, 30, 40];
    minutes.push(10);
    for value in &mut minutes {
        *value += 5;
    }
    println!("记录：{minutes:?}");
    println!("前两天合计：{}", total(&minutes[..2]));
    println!("第十条记录：{:?}", minutes.get(9));

    let mut counts = HashMap::new();
    for word in "rust cargo rust".split_whitespace() {
        let count = counts.entry(word).or_insert(0);
        *count += 1;
    }
    println!("rust 出现 {} 次", counts["rust"]);
}
