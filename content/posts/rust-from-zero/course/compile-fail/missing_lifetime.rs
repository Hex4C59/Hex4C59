fn longer(left: &str, right: &str) -> &str {
    if left.len() >= right.len() { left } else { right }
}

fn main() {
    println!("{}", longer("rust", "cargo"));
}
