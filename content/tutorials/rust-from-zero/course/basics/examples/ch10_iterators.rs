fn main() {
    let minutes = [10, 35, 50, 20];
    let threshold = 30;
    let selected: Vec<i32> = minutes
        .iter()
        .copied()
        .filter(|minutes| *minutes >= threshold)
        .map(|minutes| minutes + 5)
        .collect();
    println!("筛选后：{selected:?}");
    let total: i32 = selected.iter().sum();
    println!("合计：{total}");

    let titles = vec![String::from("读书"), String::from("写代码")];
    for (index, title) in titles.iter().enumerate() {
        println!("{}：{title}", index + 1);
    }
    println!("原列表仍可使用，共 {} 项", titles.len());

    let upper: Vec<String> = titles
        .into_iter()
        .map(|title| format!("任务：{title}"))
        .collect();
    println!("新列表：{upper:?}");
}
