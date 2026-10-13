const DEFAULT_MINUTES: u8 = 30;
fn accept(value: u8) {
    println!("参数：{value}");
}
fn main() {
    let inferred = 12;
    let annotated: u8 = 12;
    let suffixed = 12_u8;
    accept(inferred);
    let _: u8 = inferred;
    println!("三种写法：{inferred} / {annotated} / {suffixed}");
    println!("常量：{DEFAULT_MINUTES}");
}
