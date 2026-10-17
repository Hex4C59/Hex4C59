# 可运行的本地语料 Research Agent

这个例子把研究任务分成规划、工具研究、整理报告、检查和修订五步。默认使用**本地固定响应（fixture）**控制模型，搜索和读取的却是真实文件。它会故意生成一次错误引用，再依据检查反馈修订，并重新检查。

默认语料是两份虚构的「南岚团队」规程。它们只是合成测试资料，不是现实政策。固定响应验证程序流程，不验证模型选题、搜索或研究的能力。

## 下载包运行

需要 Python 3.11 或更新版本。下载包包含本例全部文件，以及共享的 `agent_runtime.py`、`requirements.txt` 和运行层说明 `RUNTIME.md`。以下命令使用 POSIX shell：

```bash
unzip research.zip -d research-demo
cd research-demo
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --requirement requirements.txt
python app.py
python -m unittest -v test_app
```

在仓库中开发时，共享文件位于旁边的 `common/`。先在自己的虚拟环境中安装 `../common/requirements.txt`，再执行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../common python app.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../common python -m unittest -v test_app
```

入口是 `python app.py`。本例没有注册名为 `research-agent` 的安装命令。仓库根目录也可使用 `PYTHONPATH=examples/agents/common python -m examples.agents.research`。

## 实际捕获的默认输出

以下输出来自 2026-10-17 的本地运行（Python 3.11.16），不是联网调研记录：

```text
mode=fixture (本地固定响应；无联网检索)
corpus=本地合成语料：虚构的南岚团队规程，不代表现实政策
plan.questions=2
tool.search=2 tool.fetch=2 notes=2
check revision=0 passed=false issues=unknown_citation:N999
check revision=1 passed=true issues=none
status=complete
citations=N1:S1,N2:S2
workspace=temporary (已清理；用 --workspace 显式保留)
```

`N999` 是固定响应故意写入的未知笔记号。程序没有给它补造来源，而是拒绝首稿，将原因传回整理步骤；第二稿引用实际保存的 `N1` 和 `N2`，再经检查后才成为接受的报告。

同一份源码还按主打包器清单做过平铺 ZIP 验证：解压到 `research-demo` 后，不设置 `PYTHONPATH`，`python app.py`、`python -m app`、`python .` 和 27 项测试全部通过。

默认工作文件写入系统临时目录并在退出时清理。要保留结果，显式选择目录：

```bash
python app.py --workspace ./research-output
```

每次创建新的 `run-<随机编号>/`，其中有 `plan.json`、`sources.json`、`notes.json`、`drafts.json`、`checks.json`、`result.json` 和 `report.md`。已有运行不会被覆盖。`sources.json` 保存本次读到的文本快照；它可能含有你的私有资料，请按资料本身的权限管理。

## 换成自己的语料

准备一个目录，放入 UTF-8 纯文本或 Markdown 文件，再创建 `corpus.json`。下面是格式示例，文件内容由你提供：

```json
{
  "label": "我的产品资料",
  "documents": [
    {
      "id": "Policy1",
      "title": "产品记录规则",
      "file": "policy.txt",
      "publisher": "资料所有者",
      "published_at": "2026-10-01"
    }
  ]
}
```

`label` 和 `documents` 必填；每条资料的 `id`、`title`、`file` 必填。`publisher`、`published_at`、`url` 可省略。`file` 相对于清单所在目录，不能是绝对路径、包含 `..` 或经过符号链接。`url` 仅是你提供的书目信息，程序不会抓取或验证该地址。

```bash
python app.py --corpus ./my-corpus/corpus.json \
  --task '整理这份资料对研究记录的要求。' --workspace ./research-output
```

仍不加 `--live` 时，固定策略按前两份资料的 ID 搜索，从实际工具返回中摘录首个至少 12 字符的非空行。它用于验证你的文件能否走通工具链，不会理解任意研究任务；真实内容是否相关由你判断。只有一份资料也可以运行。

## 使用 live 模型

先在自己的终端设置 `OPENAI_API_KEY` 和 `OPENAI_MODEL`；所选服务和模型必须支持 Chat Completions 工具调用。兼容服务可另设 `OPENAI_BASE_URL`。然后运行：

```bash
python app.py --live --corpus ./my-corpus/corpus.json \
  --task '比较这些资料对记录与复核的要求，指出覆盖不到的问题。' \
  --timeout 60 --request-timeout 10 --max-revisions 2 \
  --workspace ./research-output
```

`--live` 必须同时提供 `--corpus`。这只切换模型：研究工具仍然是本地文件搜索和读取，不会访问公网、内网、云元数据地址或语料中的 URL。模型会收到任务、目录、已读取文本和笔记；启用前应确认这些资料可以发送到配置的模型服务。客户端由共享 `model_from_env()` 创建，所有阶段调用同一个异步 `complete()` 接口，退出时在 `finally` 中关闭。

本次环境没有模型或搜索服务密钥，因此没有做真实模型联网验收，也没有新的网络研究发现。`mode=live` 表示执行路径，不能当成质量认证。

## 质量门槛实际检查什么

`save_note` 只接受本轮已读取来源中的原文片段。宿主分配笔记号，记录来源 ID、SHA-256 内容摘要、读取时间及 Python 字符区间 `[start, end)`；后者不是字节偏移。摘要用于确认本次引用的内容版本，不代表来源权威或事实真实。

报告用 JSON 的 `claims` 列表组织每个研究问题的证据。每条事实必须逐字等于所引用笔记的摘录。程序检查报告格式、问题覆盖、笔记号、来源摘要和摘录位置；把已知笔记号贴到一句原文没有的结论后面也会失败。Markdown 引用由宿主根据实际笔记生成，模型不能自行提供新引用 URL。

另一轮模型审查会收到草稿、笔记、来源文本及机器检查结果，检查相关性、遗漏与误导性概括。只有机器检查无问题且模型同意通过，才设置 `status=complete`。模型不能推翻机器拒绝。每次修订都传入上一稿和反馈，随后再次做两层检查。

这是刻意保守的摘录式研究流程：按问题选择和组织证据，**不接受自由改写的事实句**。标题和资料局限说明仍是模型文字，需要人工阅读。来源可能过时、互相转载或与问题无关；逐字匹配不能证明真实性、独立性、覆盖充分性或因果关系。修订只利用现有笔记，不重新搜索；如果缺资料，重写几遍也不能补足证据。

## 限制、失败和测试

默认总期限 60 秒、单次模型请求及一次来源工具等待 10 秒；最多 2 次修订，因此最多检查 3 稿。每题最多 8 轮模型交互、12 次工具调用，最多读取 8 个不同来源、保存 24 条笔记。语料清单最多 32,000 字节、20 份资料，每份文本最多 24,000 字节；超限、空文本、无效 UTF-8 与 NUL 内容均报错，不裁剪后假装完整。模型返回也有 32,000 字符上限。

| 状态或原因 | 行为与退出码 |
| --- | --- |
| `complete` | 最终稿通过，退出 0 |
| `quality_failed` | 修订耗尽；只保留失败草稿，退出 1 |
| `limit` / `error` | 轮数、工具次数、空搜索、读取错误或模型返回出错，退出 1 |
| `timeout` | 模型等待或整体流程到期，工作未完成，退出 124 |
| 来源工具超时 | 作为工具错误交给模型；若没有取得证据，流程失败 |
| 配置错误 | 缺少 live 配置、语料格式错误等，退出 2 |
| 用户中断 | 清理客户端后退出 130 |

可运行 `python app.py --max-revisions 0` 观察默认首稿被拒绝的分支：没有修订额度时，程序不会跳过检查或接受失败草稿。

本例的 27 项 `unittest` 覆盖成功、失败、真实文件读取与自定义语料、两种入口、共享 `ScriptedModel` 回放、伪造摘录、已知引用配上无依据结论、损坏摘要、空结果、来源读取错误、畸形清单、越界/符号链接、文本大小、请求超时、跨阶段总期限、取消、修订与工具上限、live 配置缺失和客户端关闭。

超时通过取消正在等待的异步任务工作，不能强行终止已在工作线程中开始的文件系统读取。路径检查适用于当前用户控制的本地语料和工作目录，不能替代操作系统沙箱，也不防御其他进程并发替换文件的竞争。实现依据可参阅 [Python 3.11 的异步超时与取消](https://docs.python.org/3.11/library/asyncio-task.html#timeouts)及 [hashlib](https://docs.python.org/3.11/library/hashlib.html)（核对于 2026-10-17）。
