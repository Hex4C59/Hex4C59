mod tools {
    pub mod inner {
        fn hidden() {}
    }
}
fn main() {
    tools::inner::hidden();
}
