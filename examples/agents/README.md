# Agent 实战教程配套项目

这里保存七篇实战文章的完整可运行示例，另有一个 `mechanisms` 下载包，配合五篇机制文章验证规划、上下文预算、审批、协作与工具限制。每个目录都有入口、说明和测试；`common/` 提供工具调用循环。文章中的完整代码由 Hugo 从这里读取，发布构建把同一份源码打成 ZIP，避免正文与下载包各维护一份实现。

默认演示不需要密钥，模型响应来自标为 `fixture` 的固定数据。演示实际执行文件操作、SQLite、子进程或 MCP 协议。它能检查程序如何处理这些响应，不能证明线上模型会选择相同动作。

在仓库根目录准备 Python 3.11 或更新版本的环境：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r examples/agents/requirements.txt
.venv/bin/python scripts/check_agent_examples.py
```

最后一条命令生成临时 ZIP，解压到临时目录，分别运行每个项目的测试和默认演示。增加 `--fresh-env` 会按每个 ZIP 的 `requirements.txt` 分别创建干净虚拟环境并安装依赖，用来检查下载包是否漏写依赖；安装需要访问包源。它不会把测试数据放进当前目录，也不需要模型服务。Windows 使用 `.venv\Scripts\python.exe`。

读者从文章下载 ZIP 后，在解压得到的项目目录中运行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
.venv/bin/python -m unittest discover -v
```

在线模型模式通过 `--live` 显式启用；配置方法及工具权限见各项目 README。公共运行层读取环境中的 `OPENAI_API_KEY`、`OPENAI_MODEL` 和可选 `OPENAI_BASE_URL`。请使用支持 Chat Completions 工具调用的模型与服务，不要把密钥写入文章或配置文件。

`python3 scripts/build.py` 将 ZIP 写入站点产物的 `downloads/agent-examples/`，检查归档与源码一致后再检查站内链接。生成的下载包属于发布产物，不提交到源码仓库。普通 `hugo server` 可以预览正文；检查下载入口时使用完整构建产物。
