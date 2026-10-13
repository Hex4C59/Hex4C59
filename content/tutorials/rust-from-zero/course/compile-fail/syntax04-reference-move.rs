fn main() {
    let mut number = 10;
    let slot = &mut number;
    let later = slot;
    println!("{} / {}", *slot, *later);
}
