use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Note {
    title: String,
    #[serde(default)]
    tags: Vec<String>,
}

fn main() -> Result<(), serde_json::Error> {
    let note: Note = serde_json::from_str(r#"{"title":"Rust 练习"}"#)?;
    assert!(note.tags.is_empty());
    println!("{}", serde_json::to_string(&note)?);
    assert!(serde_json::from_str::<Note>(r#"{"title":"Rust","tags":"学习"}"#).is_err());
    Ok(())
}
