use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;

use taskbook_json::storage::{self, StoreError};

pub fn copy_snapshot(source: &Path, destination: &Path) -> Result<usize, StoreError> {
    let content = fs::read_to_string(source)?;
    let tasks = storage::decode(&content)?;
    let mut output = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(destination)?;
    output.write_all(content.as_bytes())?;
    Ok(tasks.len())
}
