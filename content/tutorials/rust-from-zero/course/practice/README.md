# Rust 教材第 13～15 章练习

本目录是独立 Cargo 工作区，需与下载包的上层 `taskbook` 包保留相对位置。详细运行方式见上一层 `README.md` 和教材正文。

- `taskbook-plus`：复用 `../../taskbook`，增加未完成筛选、标题搜索和删除。
- `error-lab`：结构化输入与文件错误，提供原始错误原因。
- `taskbook-json`：复用已有核心逻辑，以 JSON 保存并迁移 TSV 数据。

先运行 `cargo fetch --locked`，再执行教材对应的 Cargo 命令。首次获取 Serde 与 serde_json 依赖需要网络；完成后可加 `--offline`。
