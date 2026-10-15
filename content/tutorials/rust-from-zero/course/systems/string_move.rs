use std::mem::size_of_val;

fn main() {
    let original = String::from("Rust入门");
    let buffer = original.as_ptr();
    let len = original.len();
    let capacity = original.capacity();

    let moved = original;
    assert_eq!(moved.as_ptr(), buffer);
    assert_eq!(moved.len(), len);
    assert_eq!(moved.capacity(), capacity);

    let cloned = moved.clone();
    assert_eq!(moved, cloned);
    assert_ne!(moved.as_ptr(), cloned.as_ptr());

    println!("UTF-8 bytes: {}", moved.len());
    println!("Unicode scalar values: {}", moved.chars().count());
    println!("move keeps the buffer: {}", moved.as_ptr() == buffer);
    println!("clone uses another buffer: {}", cloned.as_ptr() != buffer);

    let long = "x".repeat(1_000);
    println!("short String value: {} bytes", size_of_val(&moved));
    println!("long String value: {} bytes", size_of_val(&long));
    println!("long String data: {} bytes", long.len());

    let boxed = Box::new(moved);
    assert_eq!(boxed.as_str().as_ptr(), buffer);
    println!("Box<String> value: {} bytes", size_of_val(&boxed));
    println!(
        "boxing keeps the string buffer: {}",
        boxed.as_str().as_ptr() == buffer
    );
}
