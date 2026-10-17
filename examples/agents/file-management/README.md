# 文件管理 Agent：提案、批准、日志与撤销

Python 3.11+。默认使用 `fixture`（本地固定模型响应），文件工具仍会真实读写临时合成文件。运行不访问模型服务，也不使用 HOME 或 Git checkout 作为工作区。

## 下载包中运行

下载博客中的 `file-management.zip`，解压后在包含 `app.py` 的目录执行：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
python -m unittest -v
```

ZIP 由仓库统一打包，包含本目录文件、共享 `agent_runtime.py` 和锁定直接依赖的 `requirements.txt`。本例没有额外依赖。若在源码目录验证，用仓库中的 `examples/agents/common` 作为 `PYTHONPATH`；下载包不需要设置它。

默认演示的实际输出：

```text
[fixture 本地固定响应] model=complete; pending=2
[fixture] dry-run: notes=True; trash=True
[fixture] approved: moved=True; deleted=True
[fixture] reopened journal: delete_undo=True; move_undo=True; bytes_restored=True
[fixture] temporary workspace cleaned on exit; no live model called
```

演示为新建临时目录里的两个已知合成操作提供固定审批口令，再重新创建应用对象并撤销。真实 CLI 的批准和撤销都读取用户输入，模型工具没有批准入口。独立进程之间的持久恢复另外由测试覆盖。

## 在显式临时工作区中操作

以下命令适用于 macOS/Linux 的 shell；不向当前项目写业务文件：

```bash
WORKSPACE="$(mktemp -d)"
mkdir "$WORKSPACE/sorted"
printf 'keep this note\n' > "$WORKSPACE/notes.txt"
OP_ID="$(python app.py --workspace "$WORKSPACE" --queue move --source notes.txt --destination sorted/notes.txt | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
python app.py --workspace "$WORKSPACE" --status
python app.py --workspace "$WORKSPACE" --apply "$OP_ID"
```

最后一条会显示提案，并要求输入 `APPROVE`、一个空格和终端显示的完整操作 ID。输入 `n`、`y` 或其他内容都会拒绝，文件不变。没有一键批准所有提案的入口。

再次调用程序，撤销刚才的移动：

```bash
python app.py --workspace "$WORKSPACE" --undo "$OP_ID"
```

本次要求 `UNDO`、一个空格和该 ID。撤销按执行顺序后进先出；原路径若被占用，或者目标内容、身份发生变化，程序拒绝覆盖。

演示带备份删除：

```bash
DELETE_ID="$(python app.py --workspace "$WORKSPACE" --queue delete --source notes.txt | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
python app.py --workspace "$WORKSPACE" --apply "$DELETE_ID"
python app.py --workspace "$WORKSPACE" --undo "$DELETE_ID"
```

每一步仍需用户输入相应口令。删除前的字节保存在工作区 `.file-agent/journal.sqlite3` 的快照中，不是永久擦除。请保留整个工作区及状态目录，直到不再需要恢复。

不想执行尚未批准的操作时：

```bash
python app.py --workspace "$WORKSPACE" --queue copy --source notes.txt --destination sorted/copy.txt
python app.py --workspace "$WORKSPACE" --status
```

从输出复制待取消 ID，再运行 `python app.py --workspace "$WORKSPACE" --cancel ID`，其中 `ID` 要替换为该值。取消只改变日志状态，不改业务文件；快照仍保留。

## 可选 live 规划

先在自己的终端设置 `OPENAI_API_KEY`、`OPENAI_MODEL`，按需设置 `OPENAI_BASE_URL`。不把密钥写进代码、文章、日志或提交：

```bash
python app.py --workspace "$WORKSPACE" --live --task '查看目录，为整理 notes.txt 提出移动方案，不执行'
```

live 只让模型调用 `list_directory`、`queue_operation` 和 `preview`。执行仍需要单独的 `--apply` 与用户口令。客户端在 `finally` 中关闭；缺少凭据或模型服务失败时返回错误，不悄悄改用 fixture。本次未调用真实模型服务，不能据离线测试断言模型规划质量。

## 恢复与范围

- 普通文件每个最多 1 MiB，同时最多 20 条待确认提案。支持移动、复制、带备份删除；重命名可用同目录移动表达。父目录必须已经存在。
- 绝对路径、`..`、符号链接路径、已有目标、外部硬链接、目录操作、跨文件系统操作、特殊 setuid/setgid 权限和状态目录操作均拒绝。路径使用目录中实际的大小写。
- `.file-agent` 保存 SQLite 日志、短期暂存文件和另一个用于应用互斥的 SQLite 文件。初始化与每次操作先恢复未结束记录：`applying` 回滚，`undoing` 继续撤销；确认执行的 `applied` 可供下次进程撤销。
- 文件内容先保存在日志，创建目标使用同一文件系统中的硬链接“创建新名字”，不会替换已有目标。暂存链接清理后业务文件恢复为独立文件。支持本例的本地文件系统必须提供 SQLite 锁和硬链接。
- 如果日志写入失败、备份校验失败或恢复路径冲突，程序不报告恢复成功。若日志已经提交执行结果，则保留该结果，要求查看状态或明确撤销，不能把一个错误返回简单理解为“什么都没发生”。
- 移动也通过备份创建目标、再移除源文件。移动、复制和撤销只处理字节和普通权限，不保留原 inode、修改时间、ACL 或扩展属性。删除状态目录会失去快照和撤销记录；本例不提供快照清理策略，取消操作也保留历史。
- 这是可信本地用户的目录边界，不是 OS 沙箱。不要让不可信进程同时替换目录、篡改日志，或把本例用于网络盘、云同步竞争和重要文件。测试未覆盖断电、磁盘硬件损坏或其他操作系统的完整文件系统语义。

测试真实修改临时文件，并覆盖新应用对象、新 CLI 进程、拒绝/取消、目录越界、符号链接、冲突、内容变化、日志故障、备份损坏及实际子进程异常退出后的恢复。测试只证明这些具体文件流程，没有评估模型能力。
