fn main() {
    let name = "小林";
    let mut minutes: u32 = 20;
    minutes += 10;
    let target: u32 = 45;
    let remaining = target - minutes;
    let finished: bool = minutes >= target;
    let progress = f64::from(minutes) / f64::from(target) * 100.0;
    let record = (name, minutes);
    let days = [20, 30, 25];

    println!("{} 今天学习了 {} 分钟", record.0, record.1);
    println!("还差 {remaining} 分钟，完成了吗：{finished}");
    println!("进度：{progress:.1}%");
    println!("第一天：{} 分钟", days[0]);

    let input = " 42 ";
    let input = input.trim();
    println!("去掉首尾空白：{input}");
}
