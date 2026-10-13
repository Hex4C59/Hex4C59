#[path = "../../test_support/mod.rs"]
mod test_support;

use std::fs;
use std::process::{Command, Output};
use test_support::Sandbox;

fn run(sandbox: &Sandbox, args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_taskbook-cli"))
        .current_dir(&sandbox.0)
        .args(args)
        .output()
        .unwrap()
}

fn text(output: Output) -> String {
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    String::from_utf8(output.stdout).unwrap()
}

#[test]
fn commands_use_selected_file_and_queries_do_not_write() {
    let sandbox = Sandbox::new("clap-commands");
    assert_eq!(
        text(run(
            &sandbox,
            &["--file", "chosen.json", "add", "学习 Rust"]
        )),
        "已添加任务 1\n"
    );
    text(run(&sandbox, &["add", "写练习", "--file", "chosen.json"]));
    text(run(&sandbox, &["done", "1", "--file", "chosen.json"]));
    let path = sandbox.0.join("chosen.json");
    let saved = fs::read(&path).unwrap();
    for command in [vec!["list"], vec!["pending"], vec!["search", "Rust"]] {
        let mut args = vec!["--file", "chosen.json"];
        args.extend(command);
        let output = text(run(&sandbox, &args));
        assert!(!output.is_empty());
        assert_eq!(fs::read(&path).unwrap(), saved);
    }
    assert_eq!(
        text(run(&sandbox, &["--file", "chosen.json", "pending"])),
        "2 [ ] 写练习\n"
    );
    text(run(&sandbox, &["--file", "chosen.json", "remove", "1"]));
    assert_eq!(
        text(run(&sandbox, &["--file", "chosen.json", "list"])),
        "2 [ ] 写练习\n"
    );
    assert!(!sandbox.0.join("tasks.json").exists());
}

#[test]
fn help_and_version_succeed_without_loading_a_file() {
    let sandbox = Sandbox::new("clap-help");
    fs::write(sandbox.0.join("tasks.json"), "broken").unwrap();
    assert!(text(run(&sandbox, &["--help"])).contains("--file"));
    assert!(text(run(&sandbox, &["add", "--help"])).contains("<TITLE>"));
    assert_eq!(text(run(&sandbox, &["--version"])), "taskbook-cli 0.1.0\n");
    assert_eq!(
        fs::read_to_string(sandbox.0.join("tasks.json")).unwrap(),
        "broken"
    );
}

#[test]
fn parser_errors_exit_two_and_business_errors_exit_one() {
    let sandbox = Sandbox::new("clap-errors");
    for args in [
        vec!["done", "0"],
        vec!["done", "abc"],
        vec!["done"],
        vec!["list", "extra"],
        vec!["unknown"],
    ] {
        let output = run(&sandbox, &args);
        assert_eq!(output.status.code(), Some(2));
        assert!(output.stdout.is_empty());
        assert!(!output.stderr.is_empty());
        assert!(!sandbox.0.join("tasks.json").exists());
    }
    let output = run(&sandbox, &["add", " "]);
    assert_eq!(output.status.code(), Some(1));
    assert!(!sandbox.0.join("tasks.json").exists());
}

#[test]
fn backup_restore_refuse_existing_targets_and_missing_sources() {
    let sandbox = Sandbox::new("clap-backup");
    text(run(&sandbox, &["add", "学习 Rust"]));
    let saved = fs::read(sandbox.0.join("tasks.json")).unwrap();
    text(run(&sandbox, &["backup", "backup.json"]));
    text(run(
        &sandbox,
        &["--file", "restored.json", "restore", "backup.json"],
    ));
    assert_eq!(fs::read(sandbox.0.join("restored.json")).unwrap(), saved);
    assert_eq!(
        run(&sandbox, &["restore", "backup.json"]).status.code(),
        Some(1)
    );
    assert_eq!(
        run(&sandbox, &["--file", "new.json", "restore", "missing.json"])
            .status
            .code(),
        Some(1)
    );
    assert!(!sandbox.0.join("new.json").exists());
    assert_eq!(fs::read(sandbox.0.join("tasks.json")).unwrap(), saved);
}
