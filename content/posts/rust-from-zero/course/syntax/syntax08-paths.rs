mod tools {
    pub(super) fn twice(value: i32) -> i32 {
        self::inner::add(value, value)
    }
    mod inner {
        pub(super) fn add(left: i32, right: i32) -> i32 {
            left + right
        }
    }
}
use crate::tools::twice as double;
fn main() {
    println!("{}", double(6));
}
