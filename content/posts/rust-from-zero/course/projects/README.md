# Rust 教材第 16～18 章项目

本目录是独立 Cargo 工作区。保持与上层 `taskbook` 和 `practice` 的相对位置；完整运行方式和验证范围见上一层 `README.md` 及对应教材。

- `taskbook-backup`：源 JSON 校验、备份与恢复到新文件。
- `taskbook-cli`：clap 子命令与文件选项，复用任务逻辑、JSON 和备份。
- `lesson-http`：请求同机的练习服务，检查状态码、响应大小、JSON、业务字段和超时。

先运行 `cargo fetch --locked`。依赖完成后，可使用 `--locked --offline`。`serve` 是一次性本机响应夹具，每次请求前需重新运行，不是完整 HTTP 服务器。
