fn print_number(item: Option<i32>) {
    let Some(number) = item else {
        println!("没有值");
        return;
    };
    println!("数字：{number}");
}
fn main() {
    print_number(Some(7));
    print_number(None);
}
