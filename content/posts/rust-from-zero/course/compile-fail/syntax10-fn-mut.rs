fn twice(action: impl Fn()) {
    action();
    action();
}
fn main() {
    let mut count = 0;
    let increase = || {
        count += 1;
    };
    twice(increase);
}
