fn plus_one(base: i32) -> i32 {
    base + 1
}

fn procedure() {
    println!("函数体已执行");
}
fn main() {
    let value = {
        let base = 4;
        base + 1
    };
    let no_value = {
        plus_one(4);
    };
    let result: () = procedure();
    assert_eq!(no_value, ());
    assert_eq!(result, ());
    println!("块的值：{value}，丢弃后：{no_value:?}");
}
