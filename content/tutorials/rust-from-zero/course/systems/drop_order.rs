struct Resource(&'static str);

impl Drop for Resource {
    fn drop(&mut self) {
        println!("drop {}", self.0);
    }
}

fn main() {
    let outer = Resource("outer");
    {
        let first = Resource("first");
        let second = Resource("second");
        println!("before drop(first)");
        drop(first);
        println!("second is still available: {}", second.0);
    }
    println!("back in outer scope: {}", outer.0);
}
