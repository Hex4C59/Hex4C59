#[path = "../../test_support/mod.rs"]
mod support;
use std::fs;
use std::process::Command;
use support::Sandbox;

fn run(sandbox: &Sandbox, args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_taskbook-plus"))
        .args(args)
        .env("TASKBOOK_FILE", sandbox.0.join("tasks.tsv"))
        .current_dir(&sandbox.0)
        .output()
        .unwrap()
}

#[test]
fn filters_and_removes_persisted_tasks_without_changing_read_only_queries() {
    let sandbox = Sandbox::new("plus");
    for title in ["学习 Rust", "买水果", "复习 Rust"] {
        assert!(run(&sandbox, &["add", title]).status.success());
    }
    assert!(run(&sandbox, &["done", "1"]).status.success());
    let path = sandbox.0.join("tasks.tsv");
    let before = fs::read(&path).unwrap();
    let pending = run(&sandbox, &["pending"]);
    assert!(pending.status.success());
    assert_eq!(
        String::from_utf8(pending.stdout).unwrap(),
        "2 [ ] 买水果\n3 [ ] 复习 Rust\n"
    );
    let search = run(&sandbox, &["search", "Rust"]);
    assert!(search.status.success());
    assert_eq!(
        String::from_utf8(search.stdout).unwrap(),
        "1 [x] 学习 Rust\n3 [ ] 复习 Rust\n"
    );
    assert_eq!(fs::read(&path).unwrap(), before);
    assert!(run(&sandbox, &["remove", "2"]).status.success());
    let list = run(&sandbox, &["list"]);
    assert_eq!(
        String::from_utf8(list.stdout).unwrap(),
        "1 [x] 学习 Rust\n3 [ ] 复习 Rust\n"
    );
    assert!(run(&sandbox, &["add", "第四条"]).status.success());
    let tasks = taskbook::storage::decode(&fs::read_to_string(path).unwrap()).unwrap();
    assert_eq!(
        tasks.iter().map(|task| task.id).collect::<Vec<_>>(),
        [1, 3, 4]
    );
}

#[test]
fn rejects_bad_queries_and_removal_without_overwriting_the_file() {
    let sandbox = Sandbox::new("plus");
    assert!(run(&sandbox, &["add", "保留这条"]).status.success());
    let path = sandbox.0.join("tasks.tsv");
    let before = fs::read(&path).unwrap();
    for args in [
        vec!["remove", "99"],
        vec!["remove", "0"],
        vec!["search", "  "],
        vec!["pending", "extra"],
    ] {
        let output = run(&sandbox, &args);
        assert_eq!(output.status.code(), Some(1));
        assert!(!output.stderr.is_empty());
        assert_eq!(fs::read(&path).unwrap(), before);
    }
}

#[test]
fn empty_query_result_does_not_create_a_file() {
    let sandbox = Sandbox::new("plus");
    let result = run(&sandbox, &["pending"]);
    assert!(result.status.success());
    assert_eq!(
        String::from_utf8(result.stdout).unwrap(),
        "没有符合条件的任务\n"
    );
    assert!(!sandbox.0.join("tasks.tsv").exists());
}
