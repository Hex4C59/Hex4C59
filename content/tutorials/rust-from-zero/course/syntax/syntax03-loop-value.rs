fn main() {
    let found = 'search: loop {
        for number in 1..=3 {
            if number == 2 {
                break 'search number;
            }
        }
    };
    println!("找到：{found}");
}
