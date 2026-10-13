#[path = "../../test_support/mod.rs"]
mod test_support;

use std::fs;
use std::io;
use std::process::Command;
use taskbook_backup::copy_snapshot;
use taskbook_json::storage::{self, StoreError};
use test_support::Sandbox;

const VALID: &str =
    "{\"version\":1,\"tasks\":[{\"id\":7,\"title\":\"学习 Rust\",\"done\":true}]}\n";

#[test]
fn backup_and_restore_preserve_bytes_and_task_data() {
    let sandbox = Sandbox::new("snapshot-roundtrip");
    let source = sandbox.0.join("tasks.json");
    let backup = sandbox.0.join("backup.json");
    let restored = sandbox.0.join("restored.json");
    fs::write(&source, VALID).unwrap();
    assert_eq!(copy_snapshot(&source, &backup).unwrap(), 1);
    fs::write(&source, "damaged").unwrap();
    assert_eq!(copy_snapshot(&backup, &restored).unwrap(), 1);
    assert_eq!(fs::read(&backup).unwrap(), VALID.as_bytes());
    assert_eq!(fs::read(&restored).unwrap(), VALID.as_bytes());
    assert_eq!(fs::read_to_string(&source).unwrap(), "damaged");
    let tasks = storage::load(&restored).unwrap();
    assert_eq!(tasks[0].id, 7);
    assert!(tasks[0].done);
}

#[test]
fn existing_destination_and_same_path_are_refused() {
    let sandbox = Sandbox::new("snapshot-existing");
    let source = sandbox.0.join("source.json");
    let destination = sandbox.0.join("existing.json");
    fs::write(&source, VALID).unwrap();
    fs::write(&destination, "keep me").unwrap();
    for target in [&destination, &source] {
        match copy_snapshot(&source, target).unwrap_err() {
            StoreError::Io(error) => assert_eq!(error.kind(), io::ErrorKind::AlreadyExists),
            error => panic!("unexpected error: {error}"),
        }
    }
    assert_eq!(fs::read_to_string(&destination).unwrap(), "keep me");
    assert_eq!(fs::read_to_string(&source).unwrap(), VALID);
}

#[test]
fn missing_or_invalid_sources_do_not_create_a_destination() {
    let sandbox = Sandbox::new("snapshot-invalid");
    let source = sandbox.0.join("source.json");
    let destination = sandbox.0.join("new.json");
    assert!(copy_snapshot(&source, &destination).is_err());
    assert!(!destination.exists());
    for input in ["not-json", r#"{"version":2,"tasks":[]}"#] {
        fs::write(&source, input).unwrap();
        assert!(copy_snapshot(&source, &destination).is_err());
        assert!(!destination.exists());
        assert_eq!(fs::read_to_string(&source).unwrap(), input);
    }
    fs::write(&source, [0xff]).unwrap();
    assert!(copy_snapshot(&source, &destination).is_err());
    assert!(!destination.exists());
}

#[test]
fn cli_reports_backup_restore_and_failure() {
    let sandbox = Sandbox::new("snapshot-cli");
    fs::write(sandbox.0.join("tasks.json"), VALID).unwrap();
    let run = |args: &[&str]| {
        Command::new(env!("CARGO_BIN_EXE_taskbook-backup"))
            .current_dir(&sandbox.0)
            .args(args)
            .output()
            .unwrap()
    };
    let output = run(&["backup", "tasks.json", "backup.json"]);
    assert!(output.status.success());
    assert_eq!(
        String::from_utf8(output.stdout).unwrap(),
        "已备份 1 个任务到 backup.json\n"
    );
    assert!(
        run(&["restore", "backup.json", "restored.json"])
            .status
            .success()
    );
    let output = run(&["restore", "backup.json", "tasks.json"]);
    assert_eq!(output.status.code(), Some(1));
    assert!(String::from_utf8(output.stderr).unwrap().contains("原因："));
    assert_eq!(
        fs::read_to_string(sandbox.0.join("tasks.json")).unwrap(),
        VALID
    );
}
