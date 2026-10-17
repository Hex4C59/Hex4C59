+++
title = "Skill 实战：教 Agent 写你风格的博客"
date = 2026-03-29T18:00:00+08:00
draft = false
author = "Hex4C59"
description = "用可运行的 Python 示例扫描和匹配 Skill，限制工作区读写，授权后保存新规则，并重新读取实际文章检查结构；默认离线运行，可选接入真实模型。"
summary = "模型说文章已保存，文件真的存在并符合格式吗？本例把 Skill 扫描、工具权限和文章验收分别实现：写后从磁盘重读产物，漏写或格式错误就失败；创建长期 Skill 需要对完整提案明确授权，随后重新扫描。固定响应验证流程，不证明模型写作质量。"
tags = ["Agent Skills", "提示词工程", "Writing"]
categories = ["ai"]
series = ["agent-engineering"]
series_order = 22
difficulty = "intermediate"
article_type = "tutorial"
topics = ["skill", "knowledge", "prompt-engineering", "writing-agent", "domain-expert"]
frameworks = ["OpenAI"]
ShowToc = true
source_kind = "original"
lastmod = 2026-10-17
+++

模型最后回复“文章已保存”，不能说明文章已经写出，更不能说明它符合规范。如果检查者只收到这句话，即使它认真列出检查清单，也没有看到需要检查的对象。

这篇教程把过程做完整：从 Markdown 文件选择写作规则，让 Agent 通过受限工具写出一篇草稿，再由 Python **重新打开那份文件**检查。用户允许长期保存一条规则时，才调用已经注册的 `create_skill` 工具，并立即重新扫描文件库。

读者需要能读写简单 Python，理解函数、JSON 和文件路径。这里的 Skill 是带元数据的操作说明；加载它会改变模型收到的文字，不会训练模型，也不会增加文件权限。示例默认运行本地固定响应，只有显式选择 `--live` 才调用配置的模型服务。

[Skill 概念篇](/agent/skill-teach-agent-how-to-work/)介绍了把领域规则放进独立文档的思路。本篇关注这套文档怎样被选中、怎样参与调用，以及写出文件以后究竟验证了什么。

## 先给结论

- 把规则放进 Skill 文件，可以独立维护说明；程序仍须实现扫描、匹配和读取，文件不会自己生效。
- 工具权限由 Python 检查。模型不能通过增加“已批准”参数来覆盖文件，也不能绕过 `create_skill` 直接改规则库。
- 文章验收读取磁盘产物。文件缺失、不是本轮写出、结构不符合要求，都会使命令退出失败。
- 本例只检查结构和少量文本条件。它不判定事实、代码运行结果或作者风格；fixture 通过也不是模型能力证据。

## 先运行完整示例

下载[Skill Agent 完整示例](/downloads/agent-examples/skills.zip)，解压后进入 `skills` 目录。需要 Python 3.11 或更高版本；下载包自带共享 runtime 和固定依赖清单。

以下命令适用于 macOS/Linux 的 shell：

```sh
unzip skills.zip -d skills
cd skills
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
python -m unittest -v test_app
```

Windows 可以用 `.venv\Scripts\python.exe` 执行相同的 Python 命令，无需使用上面的激活方式。本次实际运行环境是 macOS arm64、Python 3.11.16，没有在 Windows 或 Linux 上重跑本例。

默认命令会创建独立临时工作区，复制随包的示例资料和规则，完成后清理。它不把文章写进当前项目。若想查看并保留文件，可以明确提供数据目录：

```sh
work=$(mktemp -d)
python app.py --workspace "$work"
cat "$work/drafts/article.md"
```

默认运行的实际输出先标明：

```text
mode=fixture scenario=success (本地固定响应)
```

随后 JSON 中的 `status` 为 `complete`，`selected_skills` 为 `["write-blog"]`，`artifact_check.artifact_read` 为 `true`、`errors` 为空，`semantic_correctness` 为 `"not-assessed"`。这表示固定响应确实调用了工具，文件被读回并通过结构检查；没有调用模型 API。

## 文件和规则分别放在哪里

下载包中的 `app.py` 是实现来源，`test_app.py` 验证行为。共享的 `agent_runtime.py` 负责模型与工具之间的循环，按 JSON Schema 检查参数，再调用登记的 Python 函数。模型请求使用工具，与工具实际执行，是两项工作；这一分工也可对照 [OpenAI 的函数调用说明](https://developers.openai.com/api/docs/guides/function-calling)。

运行时的数据目录采用下面的布局：

```text
workspace/
├── inputs/source-notes.md
├── inputs/skill-proposal.json
├── drafts/article.md
└── skills/
    ├── write-blog/SKILL.md
    ├── write-blog/references/structure.md
    └── explain-code/SKILL.md
```

`source-notes.md` 是合成任务资料：只讨论一个进程中的 Python 字典缓存，明确没有性能测量。文章中的数据和条件按这个范围写，不编造耗时、命中率或费用。

两份 Skill 也是本教程自己的练习规则。它们不代表这个博客当前的 front matter、文章长度、系列编号或配图规范。启动时只补上缺失的随包示例，不覆盖工作区已有文件。

## Skill 怎样被加载和选中

先看随包的写作 Skill。下面直接引用同一份源文件：

{{< agent-code example="skills" file="sample-skills/write-blog/SKILL.md" >}}

文件开头 `---` 包住的是 YAML 元数据，后面是给 Agent 阅读的正文。这个加载器要求四项元数据：

| 字段 | 在本例中的用途 |
| --- | --- |
| `name` | 精确选择的名称，必须与所在目录名一致 |
| `description` | 告诉模型这份规则用于什么 |
| `triggers` | 自动匹配使用的连续文本片段 |
| `references` | 选中后还需读取的参考文件，相对于本 Skill 目录 |

`triggers`、`references` 是这个加载器自定义的字段，不是所有 Skill 平台都支持的接口。程序使用 PyYAML 的安全加载器解析 YAML，拒绝重复键、缺少字段、未知字段和不合要求的名称，不再用几条正则猜测 YAML 内容。

`SkillLoader.scan()` 按路径排序扫描 `skills/*/SKILL.md`，解析并缓存正文。只扫描这一层，不递归寻找任意深度的 Skill。每次扫描替换原有注册表，所以刷新不会把同一文件重复加入内存。

选择有三种明确用法：

```sh
python app.py
python app.py --skill write-blog
python app.py --no-skills
```

第一条按任务文字匹配：任务和触发词都经过 `casefold()`，只比较是否包含连续子串。例如 `BLOG DRAFT` 能命中 `blog draft`；“明天天气怎样”不会命中。它不理解近义词，也没有使用向量检索。

第二条精确选择名称，可重复 `--skill` 组合规则；名称不存在时直接报错。第三条明确选空列表，不退回自动匹配。没有匹配也不会加载全部 Skill。

选中后，`context()` 才读取 `references` 列出的文件，且路径只能留在该 Skill 的目录。写作规范及其参考内容，与基础说明组成传给公共循环的一条 system 消息。新规则是输入中的指导，仍受用户任务和工具权限约束；程序没有实现任意规则之间的语义冲突检测。

## 文件工具怎样限制读写

本例注册了 `read_file`、`write_file`、`match_skills` 和 `create_skill` 四个工具。名称、schema 和 handler 都在 `tools_for()` 中，工具不是只向模型展示一份参数说明。

`read_file` 只能读取工作区内的 UTF-8 普通文件，每次最多 64 KiB。`write_file` 只能写 `drafts/` 下的 Markdown 文件，大小限制相同。绝对路径、父目录跳转、符号链接都会被拒绝；写作工具不能修改 `skills/` 或 `inputs/`。因此，即使模型要求把一条新规则写入规则库，普通写工具也不能替它绕过持久化授权。

第一次写入新草稿不需要覆盖批准。若目标已经存在，先查看内容，再在下一次运行中明确授权：

```sh
cat "$work/drafts/article.md"
python app.py --workspace "$work" --approve-overwrite drafts/article.md
```

批准绑定启动时读到的文件摘要，只能使用一次。文件在批准后改变，写入会被拒绝。工具参数中没有供模型填写的 `approved` 或 `overwrite` 开关。

这些检查是可信本地用户工作区的边界，不是操作系统沙箱，也不防另一个恶意进程同时替换目录。临时文件加替换用于本例写入，不等于实现文件锁或任意崩溃恢复。

## 质量门禁必须看到实际文章

`write_file` 返回路径、字节数和 SHA-256。摘要标识这次写入的内容，不能代替文章本身。共享循环结束后，`execute()` 总会调用 `check_artifact()`，由它重新读取指定文件并检查：

1. 文件能读取，而且本轮确实通过写工具写入过。上一次留下的合格文章不能冒充本轮产物。
2. 读回内容的摘要与本轮最后一次成功写入记录一致；写入后文件被替换，检查不会继续采用内存里的旧正文。
3. 文章的 TOML front matter 能解析，`title`、`description` 是非空字符串，`draft = true`，`tags` 是非空字符串列表。
4. 正文出现任务指定的主题，并包含有内容的“先给结论”“示例”“参考资料”二级章节。
5. 代码围栏闭合，至少有一个标为 `python` 的非空代码块；Python 能解析出语句。这里不执行文章代码。
6. 参考资料包含 Markdown 链接。HTTPS 外链需要有主机名；本地引用必须指向工作区内存在的普通文件，不能通过符号链接越界。

这是针对本教程草稿格式写出的 Python 门禁，不会从任意 Skill 的文字清单自动生成。`--no-skills` 只改变模型收到的指导，不关闭门禁。这个入口验收的是一篇草稿，并不是任意任务都能使用的通用聊天入口。

门禁失败时，程序不会因为最后一句回复好听而报告完成。反过来，结构通过也不等于事实正确：一个主题词可能出现在错误解释里，一个链接可能指向不可靠的内容，能解析的 Python 也可能算错。结果因此明确保留 `semantic_correctness: "not-assessed"`，事实与风格仍需人工审阅。

## 用漏写和错误文件检验门禁

下面两个命令是刻意保留的负例，都应退出 `1`：

```sh
python app.py --fixture skip
python app.py --fixture invalid
```

`skip` 的固定响应只说“文章已保存”，没有调用写工具。公共循环会正常交回这句话，文章门禁却得到 `artifact_read: false`，因此整体是 `validation-failed`。工作区即使已有一篇合法文章，也会因“本轮没有写入”而失败。

`invalid` 确实写出一份缺少 front matter 和代码的文件。门禁能够读到它，`artifact_read` 为 `true`，但错误列表不为空，仍不能报告完成。

这组差异比给最后回复打分更直接：检查对象始终是磁盘文件；两次最后回复相同，结果却取决于文章是否存在、内容是什么。文件失败时会留下可检查的错误原因，显式工作区中的产物也保留供人查看，不自动修改或重新发布。

## 创建长期 Skill，需要批准完整提案

用户在一次对话里纠正措辞，不自动表示希望长期保留规则。把偏好写进 Skill 会影响之后的任务，因此本例将批准放在模型之外。

随包的 `sample-data/skill-proposal.json` 是可审阅的合成提案，包含名称、用途、触发词和完整正文。先查看，再明确批准：

```sh
cat sample-data/skill-proposal.json
python app.py --fixture learn --approve-skill-proposal inputs/skill-proposal.json
```

默认临时工作区复制的是完全相同的随包提案。若要跨运行保留新 Skill，使用显式工作区，并查看工作区中的提案后再批准；已有草稿也须另行批准覆盖：

```sh
cat "$work/inputs/skill-proposal.json"
python app.py --workspace "$work" --fixture learn \
  --approve-skill-proposal inputs/skill-proposal.json \
  --approve-overwrite drafts/article.md
```

`Workspace.approve_proposal()` 记录完整提案的摘要。`create_skill` 只接受与批准完全一致的名称、说明、触发词和正文，不接受模型自行声明的批准。它不会覆盖已有 Skill 目录；普通写工具也不能写入这个目录。

创建成功后，`SkillLoader.scan()` 立即重新读取规则库。`learn` 固定响应随后真正调用 `match_skills("缓存检查")`，能够取得新建的 `explain-cache` 正文。扫描次数从 `1` 变成 `2`，当前注册表包含新规则。已经发出的初始 system 消息不会被追溯修改；本轮通过匹配工具取得新内容，下一轮任务则从刷新后的库选择。

不带批准参数执行 `python app.py --fixture learn` 会拒绝创建，退出 `1`，也不会产生新 Skill。测试还让模型给工具增加 `approved: true`，确认 schema 会拒绝额外参数。这些规则由工具处理函数和参数验证执行，不只写在 prompt 里。

这与[记忆类型与设计](/agent/memory-types-and-design/)讨论的持久化有关，但本例保存的是人明确批准的操作说明，没有实现自动推断用户偏好或从对话自行学习。

## 完整实现与可选模型调用

下面引用下载包所使用的 `app.py`。规则扫描、工具注册、授权与文章门禁都以这份源码为准，无需把多个过时片段拼起来：

{{< agent-code example="skills" file="app.py" >}}

默认 `ScriptedModel` 只重放规定的工具调用，不能替你生成任意主题。`--task`、`--topic` 可以改变请求和主题检查；固定响应仍是那段缓存练习，不因此成为真实生成模型。

若要接入真实模型，先在自己的进程环境配置 `OPENAI_API_KEY` 和 `OPENAI_MODEL`，兼容服务可另设 `OPENAI_BASE_URL`，然后运行：

```sh
python app.py --live
```

凭据缺失会明确报错，不会回退到 fixture。公共 `model_from_env()` 使用 Chat Completions 适配器，所选模型需要支持该 API 和函数调用。应用在 `finally` 中等待 `aclose()`，成功、失败或取消后都负责关闭。网络、权限、费用和模型实际输出另行取决于所选服务；本轮没有 API 凭据，没有进行真实请求或模型质量评测。

## 验证范围与后续使用

本次在 macOS arm64、Python 3.11.16 环境运行 `python -m unittest -v test_app`，27 项测试通过。测试使用标准库 unittest，模型部分为本地固定响应，实际检查文件、YAML、工具 schema、摘要和扫描结果。

重点覆盖正常写后重读、漏写、无效结构、写后文件变化、旧文件冒充、路径越界、符号链接、一次性覆盖批准、精确提案授权及创建后重新匹配。还检查超时和取消，以及 live 适配器的关闭路径；适配器测试使用替代模型，不产生网络请求。

当前规则库只做关键词和名称选择；没有语义检索、规则冲突裁决、自动修订、代码执行或发布功能。真实模型可能漏读规则，也可能提交结构正确但内容错误的文章。把事实资料、人工审阅与自动结构门禁分别安排，才能知道每一步究竟提供了什么证据。

[Research Agent](/agent/build-research-agent/)可以继续讨论资料收集，[文件管理 Agent](/agent/build-file-management-agent/)与[Coding Agent](/agent/build-cli-coding-agent/)讨论其他实际工具，[多 Agent 代码审查](/agent/build-multi-agent-code-review/)则把审阅职责分开。无论换哪种任务，传入一份规范都不能替代工具权限或产物验证。

*上一篇：[MCP 集成实战：让 Agent 连接真实服务](/agent/build-mcp-agent/)*

*下一篇：[持久记忆实战：让 Agent 跨会话记住用户](/agent/build-persistent-memory-agent/)*
