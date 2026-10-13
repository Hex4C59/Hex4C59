fn left<'a>(first: &'a str, _second: &'a str) -> &'a str {
    first
}
fn main() {
    let outer = String::from("外层");
    let result;
    {
        let inner = String::from("内层");
        result = left(&outer, &inner);
    }
    println!("{result}");
}
