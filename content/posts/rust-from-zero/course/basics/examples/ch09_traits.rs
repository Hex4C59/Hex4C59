use std::fmt::Display;

struct Pair<T> {
    first: T,
    second: T,
}

trait Summary {
    fn summary(&self) -> String;
}

struct Note {
    title: String,
}

impl Summary for Note {
    fn summary(&self) -> String {
        format!("笔记：{}", self.title)
    }
}

fn print_summary(item: &impl Summary) {
    println!("{}", item.summary());
}

fn print_value<T: Display>(value: T) {
    println!("{value}");
}

fn longer<'a>(left: &'a str, right: &'a str) -> &'a str {
    if left.len() >= right.len() {
        left
    } else {
        right
    }
}

fn main() {
    let pair = Pair {
        first: 3,
        second: 8,
    };
    print_value(pair.first + pair.second);
    let note = Note {
        title: String::from("借用"),
    };
    print_summary(&note);
    let left = String::from("rust");
    let right = String::from("cargo");
    println!("字节更多的是：{}", longer(&left, &right));
}
