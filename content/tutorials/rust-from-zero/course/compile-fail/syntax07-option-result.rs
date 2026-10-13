fn first_number(numbers: &[u32]) -> Result<u32, &'static str> {
    let first = numbers.first()?;
    Ok(*first)
}
fn main() {
    println!("{:?}", first_number(&[]));
}
