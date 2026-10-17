# Skill 写作 Agent：先写文件，再读取产物检查

Python 3.11+。默认 `python app.py` 运行 **fixture / 本地固定响应**，不调用模型 API。
响应由 `ScriptedModel` 指定，工具调度、YAML 解析、读写、授权检查和产物验证都是真实代码。
它验证执行流程，不评测模型写作质量。

## 下载包运行

下载教程提供的 `skills.zip`。ZIP 根目录直接放置 `app.py` 等文件，明确解压到一个新目录；包内有共享的 `agent_runtime.py`
和 `requirements.txt`，以及本例的 `requirements-extra.txt`。

```sh
unzip skills.zip -d skills
cd skills
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-extra.txt
python app.py
python -m unittest -v test_app
```

Windows 可用 `.venv\Scripts\python.exe` 代替激活后的 `python`。本轮实际检查环境为
macOS arm64、Python 3.11.16；未在 Windows/Linux 上验证这个示例。

源码目录使用公共 runtime，运行方式为：

```sh
python -m pip install -r ../common/requirements.txt -r requirements-extra.txt
PYTHONPATH=../common python app.py
PYTHONPATH=../common python -m unittest -v test_app
```

公共依赖固定为 OpenAI SDK 3.33.0、jsonschema 4.26.0；本例增加 PyYAML 6.0.3，
用完整的安全 YAML 解析器读取 Skill，而不是用正则近似 YAML。

## 工作区和示例规则

未提供 `--workspace` 时，程序建立独立临时目录，完成后清理。
若想留下产物，请明确提供数据目录；以下 `mktemp` 示例适用于 macOS/Linux：

```sh
work=$(mktemp -d)
python app.py --workspace "$work"
cat "$work/drafts/article.md"
```

主程序会把随包的可信示例复制到缺失路径，不覆盖已有文件：

```text
workspace/
├── inputs/source-notes.md          # 合成任务资料
├── inputs/skill-proposal.json      # 待人审阅的新 Skill 提案
├── drafts/article.md              # Agent 写出的草稿
└── skills/
    ├── write-blog/SKILL.md
    ├── write-blog/references/structure.md
    └── explain-code/SKILL.md
```

这些是本教程自己规定的练习格式，和本博客的发布规范无关。没有作者、系列号、固定图数等假设。
已有工作区中同名示例保留原样；修改它们会影响下一次扫描和运行。

`SkillLoader.scan()` 只扫描 `skills/*/SKILL.md`。每份文件须有 YAML front matter：
`name`、`description`、非空 `triggers` 列表、`references` 列表，以及带一级标题的正文。
名称须与所在目录一致，重复字段、未知字段、非法名称会拒绝加载。
`triggers` 和 `references` 是这个加载器的自定义字段，不是所有 Skill 平台的通用 API。

- 自动匹配对任务和触发词做 `casefold()` 后比较连续子串，按路径排序；不做语义检索。
- `--skill write-blog` 按名称精确选择；可重复参数组合。不存在的名字会报错，不悄悄退回自动匹配。
- `--no-skills` 明确选空列表；没有命中也不意味着加载全部规范。
- 扫描时缓存 Skill 正文；只读取选中 Skill 明确列出的参考文件，参考路径限制在该 Skill 目录。
- 创建新 Skill 后立即重新扫描；当轮可调用 `match_skills` 取得新规则。已发出的初始 system 内容不会被追溯修改。

## 文章门禁看什么

`execute()` 不把“文章已保存”当结果。共享循环结束后，`check_artifact()` **从磁盘重新读取指定文件**：

1. 文件本轮须经 `write_file` 成功写入；旧文件不能替代本轮缺失的产物。
2. 读取后的 SHA-256 必须与最近一次成功写入记录一致。
3. `+++` 中的 TOML 可解析，`title`、`description` 为非空字符串，`draft = true`，`tags` 为非空字符串列表。
4. 正文须含指定主题文本，以及有内容的“先给结论”“示例”“参考资料”二级章节。
5. 代码围栏闭合，至少有一段非空 `python` 围栏，Python 语法可解析。此处不执行文章代码。
6. “参考资料”中有 Markdown 链接；外链只能使用有主机名的 HTTPS URL；本地链接必须指向工作区内存在的普通文件，不能经符号链接越界。

任何缺失或不符合都会令 `artifact_check.ok` 为 false，CLI 退出 `1`。
循环本身返回 `complete`、超时、工具调用失败，和文章门禁是分别记录的；有工具错误不会报告整体完成。

门禁是针对这套样例格式写出的程序，不会自动理解任意 Skill 的检查清单。
`--no-skills` 只改变模型收到的规则，不关闭产物门禁。这个入口用于草稿任务，不是通用聊天入口。

这些是**结构检查和文本启发式**。主题词出现不证明解释正确，链接存在不证明资料真实，
Python 能解析不证明能正确运行，更不证明作者风格。结果固定写 `semantic_correctness: "not-assessed"`。
测试中甚至放入一个结构合规但算术事实错误的段落，确认程序没有声称验证语义。

## 失败对照

```sh
python app.py --fixture skip
python app.py --fixture invalid
```

两条命令**都应退出 1**。`skip` 只返回“文章已保存”，但没有写文件，因此
`artifact_read` 为 false。`invalid` 实际写出缺少 TOML 和代码围栏的文件，
`artifact_read` 为 true，门禁仍失败。不要把这两个负例改成成功来使演示“全绿”。

默认演示实际输出开头为：

```text
mode=fixture scenario=success (本地固定响应)
```

其后 JSON 的 `status` 为 `complete`，`selected_skills` 为 `["write-blog"]`，
`artifact_check.artifact_read` 为 true，`errors` 为空，语义正确性为 `not-assessed`。
它没有调用 OpenAI，也没有产生写作能力评测分数。

## 覆盖现有草稿

`write_file` 仅能写工作区 `drafts/` 下的 `.md` 文件，每次最多 64 KiB。
`read_file` 仅能读同一工作区内、最多 64 KiB 的 UTF-8 普通文件。
绝对路径、父目录跳转、符号链接均被拒绝，普通写工具不能修改 `skills/` 或 `inputs/`。

若明确选择工作区后再次运行默认命令，会拒绝覆盖现有草稿。先读文件确认，再明确授权：

```sh
cat "$work/drafts/article.md"
python app.py --workspace "$work" --approve-overwrite drafts/article.md
```

批准记录绑定启动时的现有内容摘要，并且只消费一次；审阅后文件变化会使批准失效。
模型工具参数里没有 `approved` 或 `overwrite` 开关。这些检查适用于可信本地用户工作区，
不防其他进程抢先替换目录，也不是操作系统沙箱或文件锁。

## 新 Skill：授权、持久化和重新扫描

本例已注册并实现 `create_skill`，不会把用户的一次纠正自动保存成长期规则。
授权对象是提案的完整 `name`、`description`、`triggers`、`content`，不只是名称。
先查看随包的合成提案，然后由人明确批准该文件：

```sh
cat sample-data/skill-proposal.json
python app.py --fixture learn --approve-skill-proposal inputs/skill-proposal.json
```

默认临时工作区会从 `sample-data` 复制完全相同的提案；这个命令明确授权本次演示持久化它。
若要跨运行保留，请先用 `--workspace` 建立工作区、查看其中的提案，再传同一路径批准：

```sh
cat "$work/inputs/skill-proposal.json"
python app.py --workspace "$work" --fixture learn \
  --approve-skill-proposal inputs/skill-proposal.json \
  --approve-overwrite drafts/article.md
```

`learn` fixture 确实经过公共循环调用 `create_skill`，随后调用 `match_skills`。
批准精确匹配时，创建 `skills/explain-cache/SKILL.md`，扫描次数由 1 变 2，
下一次匹配“缓存检查”能够取得新规则。不覆盖已有 Skill 目录；再次运行会拒绝创建同名目录。

不传批准参数运行 `python app.py --fixture learn` 应退出 1，`tool_errors` 为 1，
不会创建新 Skill。模型自行增加 `approved: true` 也会被工具 schema 拒绝。
直接用 `write_file` 写 `skills/` 的绕过方式同样被拒绝。

## 可选 live

先在自己的进程环境配置 `OPENAI_API_KEY`、`OPENAI_MODEL`；兼容服务可另设 `OPENAI_BASE_URL`。
不把凭据写进源码、Skill 或输出日志，然后执行：

```sh
python app.py --live
```

该入口使用公共 `model_from_env()` 的 Chat Completions 适配器；所选模型须支持该 API 和函数调用。
应用在 `finally` 中 `await model.aclose()`。
缺少凭据会明确报错；不会悄悄退回 fixture。没有配置 live 凭据的本轮只验证了离线执行，
以及用替代模型检查关闭和取消路径，没有运行真实 API 或评估模型质量。

## 测试与剩余范围

`test_app.py` 使用标准库 unittest，覆盖实际文件读回、遗漏/错误/过期产物、路径边界、
一次性覆盖批准、精确 Skill 提案授权、创建后重新扫描、工具 schema 防自授权、
超时和取消时的客户端关闭。所有文件放在各测试专用临时目录，结束清理。

没有执行生成文章中的代码，没有验证外链内容或所有 Markdown 语法，没有检测规则之间的语义冲突，
也没有证明工作区抵抗恶意并发进程。默认 fixture 只是一段确定的缓存草稿；修改任务文字不会把它变成生成模型。
用完显式工作区后，检查路径再删除自己创建的目录；默认临时工作区无需手动清理。
