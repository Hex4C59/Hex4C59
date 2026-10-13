fn first_number(numbers: &[u32]) -> Option<u32> {
    let first = numbers.first()?;
    Some(*first)
}
fn main() {
    println!("{:?} / {:?}", first_number(&[3, 4]), first_number(&[]));
}
