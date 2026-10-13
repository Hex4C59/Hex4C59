fn left<'a, 'b>(first: &'a str, _second: &'b str) -> &'a str {
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
