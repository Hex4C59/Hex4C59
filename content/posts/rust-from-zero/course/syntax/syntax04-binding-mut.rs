fn increment(slot: &mut i32) {
    *slot += 1;
}
fn main() {
    let mut first = 1;
    let mut second = 10;
    increment(&mut first);
    let mut slot = &mut first;
    *slot += 1;
    slot = &mut second;
    *slot += 3;
    println!("{first} / {second}");
    let mut view = &first;
    println!("改绑前：{view}");
    view = &second;
    println!("改绑后：{view}");
}
