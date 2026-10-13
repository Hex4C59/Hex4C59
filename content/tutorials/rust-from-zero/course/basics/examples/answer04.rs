fn append_mark(text: &mut String) {
    text.push('！');
}

fn main() {
    let mut message = String::from("继续练习");
    append_mark(&mut message);
    println!("{message}");
    assert_eq!(message, "继续练习！");
}
