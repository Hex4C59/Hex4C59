use serde::{Deserialize, Serialize};

#[derive(Debug, PartialEq, Serialize, Deserialize)]
struct Settings {
    name: String,
    active: bool,
}

fn main() -> Result<(), serde_json::Error> {
    let settings = Settings {
        name: String::from("Rust 练习"),
        active: true,
    };
    let json = serde_json::to_string(&settings)?;
    println!("{json}");
    let restored: Settings = serde_json::from_str(&json)?;
    assert_eq!(restored, settings);
    println!("读回：{}，启用：{}", restored.name, restored.active);
    Ok(())
}
