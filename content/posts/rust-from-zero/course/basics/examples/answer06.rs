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

fn finish_first(books: &mut [Book]) -> bool {
    match books.first_mut() {
        Some(book) => {
            book.finish();
            true
        }
        None => false,
    }
}

fn main() {
    let mut books = vec![Book::new("Rust 入门")];
    books.push(Book::new("写练习"));
    assert!(finish_first(&mut books));
    assert!(books[0].finished);
    assert!(!books[1].finished);

    for book in &books {
        println!("{}：{}", book.title, book.finished);
    }

    let mut empty: Vec<Book> = Vec::new();
    assert!(!finish_first(&mut empty));
    println!("空列表已处理");
}
