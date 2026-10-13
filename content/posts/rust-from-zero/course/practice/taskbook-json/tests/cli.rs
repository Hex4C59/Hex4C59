#[path = "../../test_support/mod.rs"]
mod support;
use std::fs;
use std::process::Command;
use support::Sandbox;
use taskbook_json::storage::{StoreError, decode, migrate};

fn run(sandbox: &Sandbox, args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_taskbook-json"))
        .args(args)
        .env("TASKBOOK_JSON_FILE", sandbox.0.join("tasks.json"))
        .current_dir(&sandbox.0)
        .output()
        .unwrap()
}

#[test]
fn persists_json_and_supports_extended_commands() {
    let sandbox = Sandbox::new("json");
    assert!(run(&sandbox, &["list"]).status.success());
    assert!(!sandbox.0.join("tasks.json").exists());
    for title in ["读 \"Rust\" 🦀", "买水果", "复习 Rust"] {
        assert!(run(&sandbox, &["add", title]).status.success());
    }
    assert!(run(&sandbox, &["done", "1"]).status.success());
    let path = sandbox.0.join("tasks.json");
    let before = fs::read(&path).unwrap();
    assert!(run(&sandbox, &["search", "Rust"]).status.success());
    assert!(run(&sandbox, &["pending"]).status.success());
    let bad_args = run(&sandbox, &["unknown"]);
    assert_eq!(bad_args.status.code(), Some(1));
    assert!(
        String::from_utf8(bad_args.stderr)
            .unwrap()
            .starts_with("错误：用法：taskbook-json ")
    );
    assert_eq!(fs::read(&path).unwrap(), before);
    assert!(run(&sandbox, &["remove", "2"]).status.success());
    let tasks = decode(&fs::read_to_string(path).unwrap()).unwrap();
    assert_eq!(tasks.len(), 2);
    assert_eq!(tasks[0].title, "读 \"Rust\" 🦀");
    assert!(tasks[0].done);
    assert_eq!(tasks[1].id, 3);
    let list = run(&sandbox, &["list"]);
    assert_eq!(
        String::from_utf8(list.stdout).unwrap(),
        "1 [x] 读 \"Rust\" 🦀\n3 [ ] 复习 Rust\n"
    );
}

#[test]
fn corrupt_or_invalid_json_is_never_saved_as_a_new_list() {
    let sandbox = Sandbox::new("json");
    let path = sandbox.0.join("tasks.json");
    for original in [
        b"not-json".as_slice(),
        br#"{"version":2,"tasks":[]}"#.as_slice(),
        br#"{"version":1,"tasks":[{"id":0,"title":"Rust","done":false}]}"#.as_slice(),
        b"\xff".as_slice(),
    ] {
        fs::write(&path, original).unwrap();
        let result = run(&sandbox, &["add", "不应写入"]);
        assert_eq!(result.status.code(), Some(1));
        assert!(!result.stderr.is_empty());
        assert_eq!(fs::read(&path).unwrap(), original);
    }
}

#[test]
fn migration_preserves_source_and_refuses_an_existing_destination() {
    let sandbox = Sandbox::new("migration");
    let source = sandbox.0.join("source.tsv");
    let destination = sandbox.0.join("destination.json");
    let input = "7\t1\t读 \"Rust\" 🦀\n12\t0\t写练习\n";
    fs::write(&source, input).unwrap();
    let result = run(&sandbox, &["migrate", "source.tsv", "destination.json"]);
    assert!(result.status.success());
    assert_eq!(
        String::from_utf8(result.stdout).unwrap(),
        "已迁移 2 条任务\n"
    );
    assert_eq!(fs::read_to_string(&source).unwrap(), input);
    let before = fs::read(&destination).unwrap();
    let tasks = decode(std::str::from_utf8(&before).unwrap()).unwrap();
    assert_eq!(
        tasks.iter().map(|task| task.id).collect::<Vec<_>>(),
        [7, 12]
    );
    assert!(tasks[0].done);
    assert!(!tasks[1].done);
    let again = run(&sandbox, &["migrate", "source.tsv", "destination.json"]);
    assert_eq!(again.status.code(), Some(1));
    assert_eq!(fs::read(&destination).unwrap(), before);
    assert_eq!(fs::read_to_string(&source).unwrap(), input);
    assert!(matches!(migrate(&source, &source), Err(StoreError::Io(_))));
    assert_eq!(fs::read_to_string(&source).unwrap(), input);
}

#[test]
fn migration_does_not_create_destination_for_bad_or_missing_source() {
    let sandbox = Sandbox::new("migration");
    let source = sandbox.0.join("source.tsv");
    let destination = sandbox.0.join("destination.json");
    assert!(migrate(&source, &destination).is_err());
    assert!(!destination.exists());
    fs::write(&source, "bad-data\n").unwrap();
    assert!(matches!(
        migrate(&source, &destination),
        Err(StoreError::InvalidData(_))
    ));
    assert!(!destination.exists());
    assert_eq!(fs::read_to_string(&source).unwrap(), "bad-data\n");
}
