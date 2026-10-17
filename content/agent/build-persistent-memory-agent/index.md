+++
title = "持久记忆实战：让 Agent 跨会话记住用户"
date = 2026-03-30T10:00:00+08:00
draft = false
author = "Hex4C59"
description = "用真实 SQLite 按用户保存已确认的偏好和事件，跨进程检索，执行更新删除，并在每次模型调用前强制检查字符预算。"
summary = "以可下载、可运行的 Python 示例实现用户范围、逐项确认、SQLite 事务和有界上下文。离线固定响应驱动真实工具，在独立临时应用中保存记忆，再启动新进程读取并检查另一用户的数据没有进入请求。"
tags = ["Agent", "记忆", "Persistent Memory"]
categories = ["ai"]
series = ["agent-engineering"]
series_order = 23
difficulty = "intermediate"
article_type = "tutorial"
topics = ["memory", "persistent-memory", "episodic-memory", "semantic-memory", "user-modeling"]
frameworks = ["OpenAI"]
ShowToc = true
source_kind = "original"
lastmod = 2026-10-17
+++

你告诉 Agent 喜欢简洁的回答，下次启动时仍希望沿用这个偏好。要实现它，程序必须把这条偏好写到进程之外，还要知道它属于哪个用户、是否已获保存许可、什么时候应该读回。

[记忆概念篇](/agent/memory-types-and-design/)区分了当前消息、过去事件、稳定资料和操作方法。当前消息帮助完成眼前的任务；情景记忆保存“上次做过什么”；语义记忆保存较稳定的事实或偏好；[上一篇 Skill 教程](/agent/build-skill-expert-agent/)则处理可复用的操作规范。本篇实现其中的事件与偏好，并把短期对话留在有界的内存列表里。

本文面向会写 Python、理解工具调用循环的读者。完成后，你可以用命令行查看、创建、更新、搜索和删除记忆；再次启动时，同一用户能读到已保存的记录，另一用户的数据不会因共用数据库而混进来。默认演示使用 **fixture／本地固定响应**，实际执行 SQLite、文件工具和独立子进程，不需要模型凭据。

## 先给结论

1. 记忆只有提交到数据库后才跨进程存在。这里在确认写入时立即提交，不把保存押在正常退出上，也不在退出时重新提取旧对话。
2. 事件和偏好用途不同，但可以在同一事务数据库里存储。每条记录都带用户、种类、键、值、来源会话和修订号；每次查询和修改都绑定用户。
3. 模型提出的内容不等于用户同意保存。工具只能写入命令行事先确认的具体键和值，确认不能由模型自己添加一个布尔参数来代替。
4. 检索结果仍可能过时或包含错误指令。它们作为用户消息中的历史数据传入，正文提示当前要求优先；这有助于区分来源，但不能证明模型免疫提示注入。
5. 条目数量上限不等于上下文长度上限。本例同时限制存储、检索和历史，并在每次实际调用模型前测量 `messages` 与 `tools` 的规范 JSON 字符数，超过预算就裁剪或拒绝调用。

## 整体架构

一次输入经过以下步骤：

1. 入口显式选择工作目录、用户和会话，打开 SQLite 文件。
2. 读取该用户的已确认偏好，并按任务中的词搜索事件；构造不超过 2200 字符的检索记录列表。
3. 把当前任务、来源会话、检索记录和短期历史放进用户消息，进入共享工具循环。
4. 每次模型请求之前，`BudgetedModel` 检查完整消息和工具定义，必要时删除旧历史或完整的旧工具交换。
5. 模型请求记忆工具时，应用先检查参数；写入还要匹配来自命令行的逐项确认，随后才进入事务。
6. 本次回答结束后，只在内存中保留受限的对话历史。程序退出时不再自动写入资料。

`user` 决定记录属于谁，`session` 记录这次写入来自哪次会话。两次会话使用相同用户和数据目录，才能共享长期记忆；仅仅更换会话名不会更换用户。这里的用户标识是受信任本地调用者选择的范围，不是账号认证，也不能阻止有数据库文件权限的其他进程直接读写。

## 项目结构

[下载完整示例 ZIP](/downloads/agent-examples/persistent-memory.zip)。ZIP 根目录包含：

```text
app.py                 # SQLite、记忆工具、预算包装器和入口
agent_runtime.py       # 共享异步模型适配器与工具循环
requirements.txt       # 共享固定依赖
README.md              # 完整命令和边界
test_app.py            # 标准库 unittest 测试
```

使用 Python 3.11 或更新版本。在下载文件所在目录执行：

```sh
unzip persistent-memory.zip -d memory-agent
cd memory-agent
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
python -m unittest -v
```

PowerShell 使用 `.venv\Scripts\Activate.ps1` 激活环境。默认演示不发出模型请求，但共享循环仍需要依赖中的 `jsonschema` 来检查工具参数。仓库内运行时，在 `examples/agents/persistent-memory` 目录给命令加上 `PYTHONPATH=../common`；ZIP 已包含公共文件，无需这个设置。

默认执行只使用临时目录。数据库在其中的 `state/memory.sqlite3`，生成的练习程序在 `demo_application/main.py`；它们与本教程入口 `app.py` 分开，退出演示后临时目录会清理。

## 第一步：记忆存储后端

`MemoryStore` 把偏好和事件保存在一张表里，以用户、种类和键作为联合主键。例如，同一个用户可以同时拥有偏好 `response_style` 和事件 `demo.health`；另一用户使用相同键也不会覆盖它们。

写入先开始 `BEGIN IMMEDIATE` 事务，再判断这个键是否已经存在。新建记录时，同时检查每用户 64 条和全库 1024 条的上限，随后新增或更新并提交。把检查和修改放在同一事务里，才能避免两个写入者都看到“还剩一个名额”后各自插入。已存在的键仍可在达到数量上限时更新。

每个值最多 512 个 Unicode 字符，键最多 64 个字符。查询使用绑定参数，搜索中的百分号、下划线和引号都按普通文本处理。搜索是子串匹配，ASCII 字母忽略大小写；它没有调用嵌入接口，也没有宣称能找到语义相近但用词不同的事件。

更新只替换当前用户、当前种类下的同名键，并增加 `revision`。来源会话随本次确认更新。这套规则能回答“哪个值后来被确认”，但不会自动理解“语言”和“开发环境”是否在谈同一件事。

数据库损坏、结构不符合当前版本或被其他写入者锁住时，程序会返回错误。它不会把打不开的旧文件删除后重建为空库。事务中的配额或写入失败会回滚；读取错误也不会伪装成“这个用户没有记忆”。

## 第二步：记忆管理器

`retrieved_context` 先取最多五条偏好，再用任务中的有限数量词语搜索事件，去掉重复记录，并逐条检查加入后是否仍在 2200 字符以内。只加入完整记录，不把一段被截断的 JSON 冒充有效资料。

这里的偏好按键排序后选择，事件按字面匹配选择。因此，保存了记录不代表它一定进入当前请求；没有被检索到，也不代表数据库丢了。需要精确检查某条记录时，调用 `memory_get` 或直接执行 `get`，不要让模型从回答风格反推存储是否成功。

模型不能在工具参数里选择另一个用户。工具的处理函数在创建时就绑定了入口选择的用户和会话；如果模型给 `memory_get` 增加 `user_id`，参数检查会拒绝多余字段。

保存与删除也由应用判断。普通讨论不触发保存；命令行的 `--confirm-preference KEY VALUE` 只允许这组具体内容写入一次。模型换了值、换了键，或者使用已经消耗的确认，都得到工具错误。删除对应 `--confirm-delete KIND KEY`，不会因为模型声称“用户已确认”就放行。

## 第三步：构建 ReAct 循环

本例复用共享的异步工具循环，文件与记忆工具依次执行，结果以 JSON 返回。工具失败是 `ok:false` 的数据，模型可以检查并说明失败；助手最后说“已完成”并不能把一次失败写入变成成功。

`MemoryAgent.ask` 的准备工作都在模型调用之前完成：检查当前任务长度，读取当前用户的记忆，再组装包含 `current_task`、`retrieved_memory` 和 `session_history` 的输入。历史资料没有被追加成第二条 system 消息。工具处理函数也不接受模型传来的用户范围或确认标志。

完整 `app.py` 如下，与下载包共用同一份源码：

{{< agent-code example="persistent-memory" file="app.py" >}}

其中 `write_demo_file` 只能写入工作目录中的独立 `demo_application` 子目录。路径检查拒绝绝对路径、父目录跳转和符号链接路径。它是受信任本地练习的路径约束，没有操作系统沙箱，也没有开放任意 shell 命令。

## 第四步：入口与会话管理

除默认临时演示外，命令都要求提供 `--workspace`、`--user` 和 `--session`。数据目录默认是显式工作目录下的 `state`；需要另选位置时用 `--data-dir`。程序没有默认用户，也不会自行在 HOME 或源码目录建立长期数据。

以下命令在解压目录执行，只使用新建练习目录和合成偏好。macOS／Linux 可以用 `mktemp`；PowerShell 读者先新建自己的练习目录，再把该路径赋给 `$memory_demo`。

```sh
memory_demo=$(mktemp -d)
python app.py put --workspace "$memory_demo" --user sample-a --session one --key response_style --value 'synthetic concise' --confirm
python app.py get --workspace "$memory_demo" --user sample-a --session two --key response_style
python app.py search --workspace "$memory_demo" --user sample-a --session two --query concise --limit 5
python app.py put --workspace "$memory_demo" --user sample-a --session two --key response_style --value 'synthetic short paragraphs' --confirm
python app.py delete --workspace "$memory_demo" --user sample-a --session two --key response_style --confirm
python app.py get --workspace "$memory_demo" --user sample-a --session three --key response_style
```

每条命令都启动一个新进程。更新后的修订号从 1 变成 2；删除返回 `{"deleted":true}`，最后一次读取返回 `{"record":null}`。去掉写入或删除命令的 `--confirm` 会失败，不修改记录。`--kind episode` 可以操作事件；不提供时默认操作偏好。

如果希望通过 Agent 工具保存一条偏好，先在命令行确认具体值：

```sh
python app.py chat --workspace "$memory_demo" --user sample-a --session four --confirm-preference response_style 'synthetic concise' --task '保存我已确认的值，然后查询记忆。'
```

未加 `--live` 时，这仍是固定响应驱动的真实工具演示。命令输出明确带 `fixture`，应再用 `get` 或 `search` 检查实际记录。

在线模式由共享适配器读取 `OPENAI_API_KEY` 和 `OPENAI_MODEL`，可选读取 `OPENAI_BASE_URL`。在自己的终端设置它们后执行：

```sh
python app.py chat --live --workspace "$memory_demo" --user sample-a --session five --task '查询已确认的回答偏好；不要保存新资料。'
```

入口使用异步适配器，并在 `finally` 中关闭客户端。没有凭据时直接失败，不会悄悄替换成固定响应。本轮未提供模型凭据，因此没有在线模型行为或质量的验收结果。

## 一次完整的执行过程

下面是 2026-10-17 实际运行 `python app.py` 的离线输出。输入偏好和事件都是合成数据，模型响应是固定夹具，数据库、工具调用、子进程与应用执行是真实的。

### 第一次会话（Agent 还没有任何记忆）

第一个子进程在新工作目录中生成应用，按事先确认的内容保存一条偏好和一条事件，然后退出：

```text
fixture / 本地固定响应；真实 SQLite、独立子进程和临时演示应用
fixture seed: user=demo-alice session=session-1; saved=2
fixture request budget: max=3986/16000 characters
```

这两条记录已经提交，不依赖交互循环正常退出后再做提取。父进程随后为另一个合成用户保存相反的回答偏好，作为隔离检查的干扰数据。

### 第二次会话（Agent 已经记住了用户信息）

另一个子进程重新构造存储和客户端，使用同一用户、新会话读取；它检查实际送给固定模型的每份请求里都没有另一用户的偏好：

```text
fixture restart: user=demo-alice session=session-2; response_style=简洁，先给结论
fixture isolation: other user's preference absent from every model request
fixture request budget: max=3098/16000 characters
demo_application/main.py: {"status": "ok"}
fixture: temporary workspace removed; tutorial app.py was not modified
```

最后一段还实际执行了独立应用。这里的应用是标准库编写的 `health` 函数演示，输出 JSON 状态；它不是尚未运行的 FastAPI／数据库配置示意。3986 和 3098 是这版固定输入下测得的最大请求字符数，工具说明或输入改变后数值也会改变。

## 记忆的维护策略

### 冲突解决

同一个键代表同一项资料。假设某项目从 Python 3.9 升到 3.12，可以确认更新 `demo_app.python_version`；若分别保存成“语言”和“环境”，程序不会判断它们冲突，也不会合并不同项目的版本。这里没有固定的模型置信度来冒充核验。

偏好与事件也不应互相替代。“这次回答请详细展开”未必是长期回答风格，“某个演示用了 Python”也未必意味着所有项目都用 Python。模型可以协助提出候选项，但本例的长期写入仍取决于具体内容的外部确认。

### 记忆容量管理

本例拒绝超过配额的新记录，允许更新和确认删除；没有自动删除“低重要性”资料的后台任务。SQLite 页数还按每个应用连接设置 16 MiB 上限，这不包含回滚日志的全部开销，也不能约束绕过应用直接操作数据库的程序。

删除工具会清空当前客户端的短期历史，并且不再把本轮加入历史。后续输入重新检索数据库，因此不会因退出提取把刚删除的资料重新存回去。不过，删除前已经发给模型的当前输入无法撤回；SQLite 的逻辑删除也不等于把所有磁盘残留安全擦除。

## 记忆系统的工程权衡

### 延迟预算

本例没有嵌入请求，也不在退出时额外调用提取模型。一次输入仍要读取数据库并执行模型工具循环，SQLite 方法在本地同步执行，锁等待有有限超时。这里没有网络延迟或吞吐测量，不能由离线夹具的运行时间推断真实服务速度。

在线适配器负责异步模型请求，应用负责调用前字符检查；两件事不能互相代替。等待模型时可以取消，已经提交的记忆仍保留，没有提交的动作也不会因为取消而自动补做。

### 存储成本

长期记录受条目数和单条长度约束，但 512 字符不是 512 字节。中文、emoji、SQLite 页和日志都会影响实际磁盘空间。需要部署时，应使用自己的数据测量文件增长；不能把示例限额直接当成服务器容量估算。

### 什么时候不需要持久记忆

一次性任务、没有用户概念的独立请求，以及用户不愿保存资料的场景，都可以只保留当前消息。对需要反复协作的助手，长期记忆的价值在于减少已经明确确认过的信息重复输入，同时让用户仍能查看、纠正和删除它。

## 和其他方案的对比

| 选择 | 需要应用解决的问题 | 本文覆盖范围 |
| --- | --- | --- |
| 本地 SQLite | 用户范围、确认、事务、检索与配额 | 已实现并用本地测试检查 |
| 向量索引 | 相似度检索之外仍需处理用户、来源、纠正和删除 | 未接入，也未做检索质量比较 |
| MCP 记忆服务 | 工具连接、身份来源、服务权限与资料生命周期 | 可复用工具边界，本文未运行该服务 |

原先引用的 [MCP `server-memory` 参考实现](https://github.com/modelcontextprotocol/servers)提供实体、关系和观察记录这一种组织思路。若已有 [MCP 集成](/agent/build-mcp-agent/)，可以继续研究它的存储接口；具体版本和权限需要另行验证。把资料交给一个服务，并不会替应用决定哪些内容获得了保存许可。

## 常见问题与解决

### Agent 过度使用记忆

先查看当前请求中究竟检索了哪些记录。系统提示要求只在相关时使用，但本例会优先选择有限数量偏好，它们仍可能不适合当前任务。应先纠正记录的范围或明确本次要求，再考虑改变检索规则；不能只凭模型“看起来记得”判断实现正确。

### 记忆提取质量不高

本例没有自动提取步骤。保存失败时先区分：没有外部确认、工具参数不合法、配额已满，还是数据库操作失败。工具给出的 `ok:false` 是错误证据，模型最后的自然语言不能覆盖它。

如果以后加自动候选提取，应先检查模型是否把临时指示、助手猜测或未验证的任务结果当成长期事实，再交给用户确认。不要只在退出时无条件保存裁剪后的对话。

### 语义记忆膨胀

存储配额、检索预算和模型请求预算分别限制不同对象：

| 对象 | 当前限制 | 到达限制时的动作 |
| --- | --- | --- |
| 当前任务 | 1200 字符 | 拒绝输入，不静默删掉当前要求 |
| 单条长期值 | 512 字符 | 拒绝写入 |
| 长期记录 | 每用户 64 条、全库 1024 条 | 拒绝新键，仍可更新或删除 |
| 检索记录列表 | 规范 JSON 最多 2200 字符 | 跳过装不下的完整记录 |
| 当前客户端历史 | 最多 8 对消息、规范 JSON 最多 4000 字符 | 截短历史文字并移除最旧整对 |
| 每次模型输入 | `messages` 加 `tools` 的规范 JSON 最多 16000 字符 | 先裁剪，再拒绝装不下的请求 |

这里的压缩是确定性的裁剪，没有调用模型生成摘要。`BudgetedModel` 先移除旧历史，再移除检索记录，最后移除完整的旧 assistant／tool 交换；最新交换不能完整装入时，就在底层模型调用前返回失败。它不会留下只有工具结果、却找不到对应调用的半组消息。

字符数用 Python `len` 测量规范 JSON 中的 Unicode 码点，包含工具参数定义、当前任务和工具结果。它不是 token 估计，也不包括 HTTP 封装、模型名或输出长度。程序记录每次实际传给模型适配器的测量值，不能把 16000 字符说成某个模型通用的上下文 token 上限。

## 总结

跨会话记忆在这里是一条可复查的流程：用户选择范围并确认具体资料，程序在事务中保存；新进程按同一用户读取，再把有限记录作为历史数据交给模型。相同目录不是用户隔离，保存成功也不是资料永远正确；来源、当前要求和修改删除入口仍然要保留。

本轮在 macOS arm64、Python 3.11.16、SQLite 3.53.4 上运行了默认演示和 19 项 `unittest`。测试检查了真实进程重启、另一用户排除、更新删除、并发写入、损坏或锁定数据库、无效工具参数、确认的一次性使用、历史长度、完整工具交换裁剪、调用前拒绝、取消和异步客户端关闭。所有资料都是合成数据，数据库和独立应用都位于临时目录。

这些检查证明了所列本地行为，没有验证在线模型质量、断电恢复、账号认证、多租户服务或安全擦除。完整测试和命令在下载包中；清理练习时只删除自己创建的临时目录。

也可以对照同系列的 [Coding Agent](/agent/build-cli-coding-agent/)、[Research Agent](/agent/build-research-agent/)、[文件管理 Agent](/agent/build-file-management-agent/)和[代码审查](/agent/build-multi-agent-code-review/)，思考哪些工具结果值得提出为记忆候选。本文没有把这几套应用合并验收。

*上一篇：[Skill 实战：教 Agent 写你风格的博客](/agent/build-skill-expert-agent/)*
