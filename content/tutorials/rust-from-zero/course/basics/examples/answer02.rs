fn main() {
    let price_cents: u32 = 1290;
    let quantity: u32 = 3;
    let total_cents = price_cents * quantity;
    println!("总价：{}.{:02} 元", total_cents / 100, total_cents % 100);
}
