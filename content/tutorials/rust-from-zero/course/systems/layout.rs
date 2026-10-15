use std::mem::{align_of, offset_of, size_of, size_of_val};

struct RustHeader {
    kind: u8,
    length: u32,
}

#[repr(C)]
struct CHeader {
    kind: u8,
    length: u32,
}

fn main() {
    let rust = RustHeader { kind: 1, length: 7 };
    let c = CHeader { kind: 1, length: 7 };
    assert_eq!((rust.kind, rust.length), (c.kind, c.length));

    println!(
        "usize: size={}, align={}",
        size_of::<usize>(),
        align_of::<usize>()
    );
    println!("String value: {} bytes", size_of::<String>());
    println!("&str value: {} bytes", size_of::<&str>());
    println!("&[u8] value: {} bytes", size_of::<&[u8]>());
    println!(
        "RustHeader: size={}, align={}, kind@{}, length@{}",
        size_of::<RustHeader>(),
        align_of::<RustHeader>(),
        offset_of!(RustHeader, kind),
        offset_of!(RustHeader, length),
    );
    println!(
        "CHeader: size={}, align={}, kind@{}, length@{}",
        size_of::<CHeader>(),
        align_of::<CHeader>(),
        offset_of!(CHeader, kind),
        offset_of!(CHeader, length),
    );

    let bytes = [1_u8, 2, 3, 4];
    let slice: &[u8] = &bytes;
    println!("slice data: {} bytes", size_of_val(slice));
    println!("slice reference: {} bytes", size_of_val(&slice));
}
