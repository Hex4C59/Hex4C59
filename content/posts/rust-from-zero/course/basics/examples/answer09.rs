trait Label {
    fn label(&self) -> &str;
}

struct Bookmark {
    title: String,
}

impl Label for Bookmark {
    fn label(&self) -> &str {
        &self.title
    }
}

fn print_label(item: &impl Label) {
    println!("{}", item.label());
}

fn main() {
    let bookmark = Bookmark {
        title: String::from("Rust 官方文档"),
    };
    print_label(&bookmark);
    assert_eq!(bookmark.label(), "Rust 官方文档");
}
