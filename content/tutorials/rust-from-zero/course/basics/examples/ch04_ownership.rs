fn show_title(title: &str) {
    println!("标题：{title}");
}

fn add_suffix(title: &mut String) {
    title.push_str("（已复习）");
}

fn main() {
    let original = String::from("学习 Rust");
    let mut title = original;
    show_title(&title);
    add_suffix(&mut title);
    show_title(&title);

    let backup = title.clone();
    title.push('！');
    println!("当前：{title}");
    println!("备份：{backup}");

    let count = 3;
    let copied = count;
    println!("两个整数：{count}、{copied}");
}
