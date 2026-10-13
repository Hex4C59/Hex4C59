#[path = "../../test_support/mod.rs"]
mod support;
use std::fs;
use std::process::Command;
use support::Sandbox;

fn run(sandbox: &Sandbox, args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_error-lab"))
        .args(args)
        .current_dir(&sandbox.0)
        .output()
        .unwrap()
}

#[test]
fn accepts_text_and_a_file_from_the_command_line() {
    let sandbox = Sandbox::new("errors");
    let result = run(&sandbox, &["30"]);
    assert!(result.status.success());
    assert_eq!(
        String::from_utf8(result.stdout).unwrap(),
        "已记录 30 分钟\n"
    );
    assert!(result.stderr.is_empty());
    fs::write(sandbox.0.join("minutes.txt"), " 45\n").unwrap();
    let result = run(&sandbox, &["--file", "minutes.txt"]);
    assert!(result.status.success());
    assert_eq!(
        String::from_utf8(result.stdout).unwrap(),
        "已记录 45 分钟\n"
    );
}

#[test]
fn reports_the_category_and_source_only_when_present() {
    let sandbox = Sandbox::new("errors");
    let number = run(&sandbox, &["abc"]);
    assert_eq!(number.status.code(), Some(1));
    let message = String::from_utf8(number.stderr).unwrap();
    assert!(message.starts_with("错误：分钟数不是有效的非负整数\n原因："));
    let zero = run(&sandbox, &["0"]);
    assert_eq!(zero.status.code(), Some(1));
    assert_eq!(
        String::from_utf8(zero.stderr).unwrap(),
        "错误：分钟数必须大于 0\n"
    );
    let missing = run(&sandbox, &["--file", "missing.txt"]);
    assert_eq!(missing.status.code(), Some(1));
    assert!(
        String::from_utf8(missing.stderr)
            .unwrap()
            .starts_with("错误：无法读取分钟文件\n原因：")
    );
    for args in [vec![], vec!["--file"], vec!["30", "extra"]] {
        let usage = run(&sandbox, &args);
        assert_eq!(usage.status.code(), Some(1));
        assert_eq!(
            String::from_utf8(usage.stderr).unwrap(),
            "错误：用法：error-lab <分钟> | --file <文件路径>\n"
        );
    }
}
