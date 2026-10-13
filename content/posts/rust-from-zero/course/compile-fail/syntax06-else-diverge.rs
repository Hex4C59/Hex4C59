fn main() {
    let item = Some(7);
    let Some(number) = item else {
        println!("没有值");
    };
    println!("{number}");
}
