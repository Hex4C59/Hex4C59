fn main() {
    let mut number = 10;
    let slot = &mut number;
    *slot += 1;
    let shorter = &mut *slot;
    *shorter += 2;
    *slot += 3;
    println!("{number}");
}
