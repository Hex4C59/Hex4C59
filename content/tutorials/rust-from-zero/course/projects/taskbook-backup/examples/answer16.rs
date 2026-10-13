use taskbook_json::storage;

fn same_tasks(left: &str, right: &str) -> Result<bool, storage::StoreError> {
    Ok(storage::decode(left)? == storage::decode(right)?)
}

fn main() -> Result<(), storage::StoreError> {
    let compact = r#"{"version":1,"tasks":[]}"#;
    let spaced = "{ \"version\": 1, \"tasks\": [] }";
    println!("任务相同：{}", same_tasks(compact, spaced)?);
    println!("字节相同：{}", compact.as_bytes() == spaced.as_bytes());
    assert!(same_tasks(compact, "broken").is_err());
    Ok(())
}
