use std::fmt::Display;
fn same<T: Display>(left: T, right: T) {
    println!("同一个 T：{left} / {right}");
}
fn separate(left: impl Display, right: impl Display) {
    println!("独立类型：{left} / {right}");
}
fn with_where<T, U>(left: T, right: U)
where
    T: Display,
    U: Display,
{
    println!("where 写法：{left} / {right}");
}
fn main() {
    same(1, 2);
    separate(1, "two");
    with_where(1, "two");
}
