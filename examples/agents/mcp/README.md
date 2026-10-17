# MCP：固定模型响应，真实本地服务

默认演示用 `ScriptedModel`（fixture，本地固定模型响应）发出两次工具调用。连接器、两个 FastMCP 服务进程、stdio 消息、文件读取和进程关闭都是真实执行。它验证协议接入，不验证模型选择工具或回答问题的能力。

依赖 Python 3.11+。MCP SDK 固定为 `mcp==1.30.0`，使用该版本的 `ClientSession`、`stdio_client` 和 FastMCP。只安装依赖时需要网络；默认运行不使用模型 API、npm 或外部 MCP 服务。

## 下载包运行

先下载文章提供的 `mcp.zip`，在空目录执行以下命令。ZIP 内的文件直接位于根目录，解压后 `app.py`、公共的 `agent_runtime.py` 和依赖文件在同一层；另有 `RUNTIME.md` 与公共运行层测试 `test_runtime.py`。

以下命令用于 macOS/Linux shell：

```sh
unzip mcp.zip -d mcp-demo
cd mcp-demo
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-extra.txt
.venv/bin/python app.py
.venv/bin/python -m unittest -v test_app.py
```

仓库内运行时，先使用已装好上述依赖的虚拟环境，再执行：

```sh
cd examples/agents/mcp
PYTHONPATH=../common python app.py
PYTHONPATH=../common python -m unittest -v test_app.py
```

默认入口会创建临时目录，写入合成的 `note.txt`，退出后删除。不会在 HOME 或仓库中生成工作数据。默认配置用当前 Python 解释器启动随包提供的 `local_server.py` 两次；两个服务读取同一份合成文件，各自返回 `local` 或 `mirror` 标签。

## 实跑结果

2026-10-17，Python 3.11.16、MCP SDK 1.30.0 的本地运行输出节选如下。两条 `tool-result` 的完整 JSON 不在此节选中；实际运行会打印它们，包括服务标签、路径和文件内容。

```text
mode=fixture (local fixed model responses; real MCP subprocesses)
mcp-sdk=1.30.0
local initialize -> protocol=2025-11-25
local tools/list -> read_note
mirror initialize -> protocol=2025-11-25
mirror tools/list -> read_note
model tools -> local__read_note, mirror__read_note
local tools/call read_note -> call.ok
mirror tools/call read_note -> call.ok
agent.status=complete; tool_calls=2
fixture: predetermined calls finished; inspect the real tool results above.
fixture.check=passed
connections=closed
```

协议版本来自初始化响应，没有在连接器里写死。`fixture.check=passed` 还会检查是否得到两次成功的真实工具返回；文件缺失时进程返回非零，不能仅凭 fixture 最后一条文本宣称成功。

## 配置与入口

- `app.py`：组装模型、连接器与公共工具循环；默认 fixture，`--live` 才调用模型服务。
- `connector.py`：官方 SDK 连接、初始化、分页发现、名称映射、参数校验、结果与错误解码，以及 `AsyncExitStack` 清理。
- `local_server.py`：官方 SDK FastMCP 服务，提供真实的只读 `read_note` 工具。
- `config.json`：两个实际启动项；`$PYTHON` 代表当前解释器，完整参数 `{workspace}` 才会替换为工作目录。
- `test_app.py`：真实进程协议集成测试；特殊错误服务也用官方 SDK，未伪造连接器响应。

配置必须只有 `servers`，其内包含 1～8 个服务。每项只接受 `command`、字符串数组 `args`、`cwd`、`env_from` 和 `timeout_seconds`；前两项必填。相对 `cwd` 从配置文件所在目录解析；带目录的程序路径从该 `cwd` 解析，裸命令名从 PATH 查找。重复 JSON 键、未知字段、缺失程序、错误类型、缺失环境变量与无效期限会在启动任何进程之前被拒绝。

`env_from` 是要从宿主环境转发的变量名列表，默认空。不要把凭据写进配置；SDK 还会提供自身定义的基础环境。宿主的模型密钥不会被连接器整份复制给子进程。

配置能够启动指定程序，必须由用户信任。字符串数组避免经过 shell 解释，但不限制程序本身的权限。不要让模型生成的内容直接变成启动配置。

本适配器将模型工具名设为 `服务别名__远端工具名`，并保存到具体会话的映射。服务别名最多 16 个字符、不能含 `__`；组合后的名称必须符合本适配器的 64 字符限制。不兼容的工具名会明确报错，不会截短后覆盖另一个工具。

发现的参数必须是对象 Schema；禁止额外顶层参数，输入和输出 Schema 都不接受文档外 `$ref`，避免在参数验证时下载远端 Schema。工具定义过多、重复分页游标或超过 20 页也会拒绝。本例没有承诺接受任意 MCP 服务的全部 Schema。

## 使用自己的目录或真实模型

```sh
python app.py --workspace /path/to/private-notes
```

该目录必须已存在，并有 UTF-8 的 `note.txt`。程序不会替你创建或覆盖它。默认 fixture 仍执行固定的两次读取；改配置或改 `--task` 不会使 fixture 学会新任务。

设置 `OPENAI_API_KEY` 和 `OPENAI_MODEL` 后，可选择真实模型路径：

```sh
python app.py --live --workspace /path/to/private-notes --task '读取 note.txt 并说明两次返回的标签'
```

兼容服务还可设置 `OPENAI_BASE_URL`。需要支持工具调用的模型；网络请求可能收费。本轮没有真实模型密钥，未验证这条模型 API 路径。模型客户端在 `finally` 中关闭。

## 验证与边界

测试覆盖两个同名工具的实际路由、合成文件内容、工具级 `isError` 后继续调用、JSON-RPC 错误、文本/非文本及结构化内容保留、分页发现、非法配置与 Schema、目录逃逸拒绝、第二个服务启动失败、发现失败、请求期限、Agent 总期限、调用期间取消和初始化期间取消。

连接清理由同一任务中的 `AsyncExitStack` 按逆序退出 SDK 上下文完成；不要另开任务调用 `stack.aclose()`，否则会破坏 SDK 的 AnyIO 取消作用域。POSIX 测试读取本轮临时 PID 标记，确认上下文退出后进程已消失。测试不把该检查升级为 Windows 或任意后代进程树的验证证据。

`read_note` 拒绝绝对路径、上级目录、符号链接、非普通文件和超过 8192 字节的文件。`delay_seconds`（0～5 秒）仅用于期限与取消练习。路径检查假定目录私有、没有别的进程并发替换路径；它不是操作系统沙箱。MCP 也不会替宿主取得用户授权。接入写入工具、远程服务或真实账户时，仍需实现对应的确认、凭据管理、认证与隔离。

本轮测试中，SDK 在终止一个不响应的测试进程组时报告权限拒绝，随后退回终止单个进程；该进程的 PID 消失检查通过。未据此宣称完整后代树隔离。

## 核对依据

核对日期：2026-10-17。

- [官方 Python SDK v1 文档](https://py.sdk.modelcontextprotocol.io/v1/)
- [v1.30.0 README](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/README.md)
- [ClientSession 固定版本源码](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/src/mcp/client/session.py)
- [stdio 传输固定版本源码](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/src/mcp/client/stdio/__init__.py)
- [PyPI：mcp 1.30.0](https://pypi.org/project/mcp/1.30.0/)
- [MCP 生命周期规范](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
