struct Book {
    title: String,
    finished: bool,
}

impl Book {
    fn new(title: &str) -> Self {
        Self {
            title: title.to_string(),
            finished: false,
        }
    }

    fn finish(&mut self) {
        self.finished = true;
    }
}

fn main() {
    let mut books = [Book::new("Rust 入门")];
    if let Some(book) = books.first_mut() {
        book.finish();
        println!("{}：{}", book.title, book.finished);
    }
    assert!(books[0].finished);
}
