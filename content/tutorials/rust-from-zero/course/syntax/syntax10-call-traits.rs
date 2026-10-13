fn twice(action: impl Fn()) {
    action();
    action();
}
fn twice_mut(mut action: impl FnMut()) {
    action();
    action();
}
fn once(action: impl FnOnce() -> String) -> String {
    action()
}
fn main() {
    let title = String::from("拥有但只读取");
    let read = move || println!("{title}");
    twice(read);
    let mut count = 0;
    let increase = || {
        count += 1;
        println!("计数：{count}");
    };
    twice_mut(increase);
    assert_eq!(count, 2);
    let owned = String::from("交出字符串");
    let take = move || owned;
    println!("{}", once(take));
}
