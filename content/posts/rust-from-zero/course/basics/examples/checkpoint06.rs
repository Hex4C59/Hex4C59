struct Book {
    title: String,
    finished: bool,
}

enum Command {
    Add(String),
    Finish(String),
    List,
}

fn add_book(books: &mut Vec<Book>, title: &str) -> bool {
    let title = title.trim();
    if title.is_empty() {
        return false;
    }
    for book in books.iter() {
        if book.title == title {
            return false;
        }
    }
    books.push(Book {
        title: title.to_string(),
        finished: false,
    });
    true
}

fn finish_by_title(books: &mut [Book], title: &str) -> bool {
    for book in books {
        if book.title == title {
            book.finished = true;
            return true;
        }
    }
    false
}

fn apply(books: &mut Vec<Book>, command: &Command) {
    match command {
        Command::Add(title) => println!("新增成功：{}", add_book(books, title)),
        Command::Finish(title) => println!("标记成功：{}", finish_by_title(books, title)),
        Command::List => {
            if books.is_empty() {
                println!("还没有书");
            }
            for book in books {
                let state = if book.finished { "已读" } else { "未读" };
                println!("{}：{state}", book.title);
            }
        }
    }
}

fn main() {
    let mut books = Vec::new();
    let commands = [
        Command::List,
        Command::Add(String::from("Rust 入门")),
        Command::Add(String::from("写练习")),
        Command::Add(String::from("Rust 入门")),
        Command::Finish(String::from("Rust 入门")),
        Command::Finish(String::from("不存在")),
        Command::List,
    ];
    for command in &commands {
        apply(&mut books, command);
    }
    assert!(!add_book(&mut books, " "));
    assert_eq!(books.len(), 2);
    assert!(books[0].finished);
    assert!(!books[1].finished);
    assert!(!finish_by_title(&mut [], "Rust 入门"));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn invalid_additions_preserve_the_list() {
        let mut books = Vec::new();
        assert!(add_book(&mut books, " Rust 入门 "));
        assert!(!add_book(&mut books, "Rust 入门"));
        assert!(!add_book(&mut books, " \n "));
        assert_eq!(books.len(), 1);
        assert_eq!(books[0].title, "Rust 入门");
    }

    #[test]
    fn finishing_one_book_preserves_other_books() {
        let mut books = Vec::new();
        add_book(&mut books, "Rust 入门");
        add_book(&mut books, "写练习");
        assert!(finish_by_title(&mut books, "Rust 入门"));
        assert!(finish_by_title(&mut books, "Rust 入门"));
        assert!(books[0].finished);
        assert!(!books[1].finished);
        assert!(!finish_by_title(&mut books, "不存在"));
        assert_eq!(books.len(), 2);
    }

    #[test]
    fn an_empty_list_can_be_queried_and_displayed() {
        let mut books = Vec::new();
        assert!(!finish_by_title(&mut books, "Rust"));
        apply(&mut books, &Command::List);
        assert!(books.is_empty());
    }
}
