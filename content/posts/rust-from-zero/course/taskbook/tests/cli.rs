use std::fs;
use std::path::PathBuf;
use std::process::{Command, Output};
use std::sync::atomic::{AtomicU64, Ordering};

static NEXT_ID: AtomicU64 = AtomicU64::new(0);

struct Sandbox(PathBuf);

impl Sandbox {
    fn new() -> Self {
        let id = NEXT_ID.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!("rust-taskbook-{}-{id}", std::process::id()));
        fs::create_dir(&path).unwrap();
        Self(path)
    }

    fn run(&self, args: &[&str]) -> Output {
        Command::new(env!("CARGO_BIN_EXE_taskbook"))
            .args(args)
            .env("TASKBOOK_FILE", self.0.join("tasks.tsv"))
            .output()
            .unwrap()
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn persists_across_processes() {
    let sandbox = Sandbox::new();
    let empty = sandbox.run(&["list"]);
    assert!(empty.status.success());
    assert_eq!(String::from_utf8(empty.stdout).unwrap(), "还没有任务\n");
    assert!(!sandbox.0.join("tasks.tsv").exists());
    assert!(sandbox.run(&["add", "学习 Rust 🦀"]).status.success());
    assert!(sandbox.run(&["add", "写练习"]).status.success());
    assert!(sandbox.run(&["done", "1"]).status.success());
    let list = sandbox.run(&["list"]);
    assert!(list.status.success());
    assert_eq!(
        String::from_utf8(list.stdout).unwrap(),
        "1 [x] 学习 Rust 🦀\n2 [ ] 写练习\n"
    );
}

#[test]
fn bad_input_and_corrupt_files_do_not_overwrite_data() {
    let sandbox = Sandbox::new();
    assert!(sandbox.run(&["add", "保留这条"]).status.success());
    let path = sandbox.0.join("tasks.tsv");
    let original = fs::read(&path).unwrap();
    for args in [
        vec!["done", "99"],
        vec!["add", "   "],
        vec!["add", "a\tb"],
        vec!["done", "abc"],
        vec!["list", "extra"],
    ] {
        let output = sandbox.run(&args);
        assert!(!output.status.success());
        assert!(!output.stderr.is_empty());
        assert_eq!(fs::read(&path).unwrap(), original);
    }
    fs::write(&path, "坏数据\n").unwrap();
    assert!(!sandbox.run(&["add", "新任务"]).status.success());
    assert_eq!(fs::read_to_string(&path).unwrap(), "坏数据\n");
    fs::write(&path, [0xff]).unwrap();
    assert!(!sandbox.run(&["list"]).status.success());
    assert_eq!(fs::read(&path).unwrap(), [0xff]);
}

#[test]
fn reports_write_failure() {
    let sandbox = Sandbox::new();
    let output = Command::new(env!("CARGO_BIN_EXE_taskbook"))
        .args(["add", "测试"])
        .env("TASKBOOK_FILE", sandbox.0.join("missing-parent/tasks.tsv"))
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(
        String::from_utf8(output.stderr)
            .unwrap()
            .contains("无法写入")
    );
}
