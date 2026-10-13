fn main() {
    let wide = 300_u16;
    let narrow = wide as u8;
    let extended = u32::from(wide);
    assert_eq!(narrow, 44);
    assert_eq!(extended, 300);
    println!("窄化：{narrow}，扩宽：{extended}");
}
