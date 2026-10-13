fn total_minutes(days: [u32; 3]) -> u32 {
    let mut total = 0;
    for minutes in days {
        total += minutes;
    }
    total
}

fn reached_target(total: u32, target: u32) -> bool {
    total >= target
}

fn main() {
    let days: [u32; 3] = [20, 30, 40];
    let target: u32 = 90;
    let total = total_minutes(days);
    let message = if reached_target(total, target) {
        "已达标"
    } else {
        "未达标"
    };

    println!("三天总计：{total} 分钟");
    println!("目标：{target} 分钟，{message}");

    for minutes in days {
        println!("单日记录：{minutes} 分钟");
    }
}
