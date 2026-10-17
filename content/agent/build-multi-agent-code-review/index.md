+++
title = "Multi-Agent 实战：用 Supervisor 模式构建代码审查系统"
date = 2026-03-29T10:00:00+08:00
draft = false
author = "Hex4C59"
description = "运行一个完整的本地 diff 审查程序：以并发上限调度三个 Reviewer，校验 JSON 意见、文件行号与引用证据，并显式保留失败、取消和部分结果。"
summary = "用共享 Agent 运行时实现 Supervisor 分发与汇总，支持读取 diff 文件或实际执行本地 git diff。默认固定响应不评估模型能力，live 可选；模型审查与真实项目测试明确分开。"
tags = ["多智能体", "Supervisor", "代码审查"]
categories = ["ai"]
series = ["agent-engineering"]
series_order = 20
difficulty = "advanced"
article_type = "tutorial"
topics = ["multi-agent", "supervisor", "code-review", "parallel-execution", "cross-review"]
frameworks = ["OpenAI"]
ShowToc = true
source_kind = "original"
lastmod = 2026-10-17
+++

[多 Agent 协作](/agent/multi-agent-collaboration/)里的 Supervisor，可以先理解为一段负责分派与汇总的程序。它把同一份代码变更交给不同审查者，再检查返回结构和证据位置，最后输出统一报告。

本文面向会写 Python 异步函数、了解工具调用的读者。你会运行一个完整的本地 diff 审查程序：逻辑、安全和性能三个 Reviewer 各自使用独立消息历史，最多两个同时执行。它不依赖 GitHub，不会自动发评论；默认也不需要 API 密钥。

默认模型回复是明确标记的 fixture（本地固定响应），只验证调度、真实输入读取和结构检查。[Reflection](/agent/reflection-agent/)讨论的审查能力仍需另外验证：结构化意见能被解析，不代表诊断正确，也不代表代码没有漏检。

## 先给结论

1. **先固定待审查内容。** 从文件或本地 Git 取得完整 diff，再让所有 Reviewer 读取同一快照，不混入另一个版本的当前文件。
2. **并发必须有上限。** `asyncio.Semaphore` 限制同时工作的审查者，每个活动审查者还有自己的时限和调用上限。
3. **空结果与失败分开。** 合法的空 `findings`、格式不合法、超时、调用错误和取消都有不同状态；失败不会变成“没有问题”。
4. **每条发现要能回到输入。** 文件、行号和引用必须对应 diff 中的一条新增行。这个检查保证位置和引用可追溯，不保证模型判断真实。
5. **模型审查不是实际测试。** Worker 没有执行项目测试的工具，报告明确写出未运行项目测试。

## 安装与运行

下载 [Multi-Agent 本地代码审查示例](/downloads/agent-examples/multi-agent-review.zip)，需要 Python 3.11 或更新版本。解压后执行：

```sh
unzip multi-agent-review.zip -d multi-agent-review
cd multi-agent-review
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py --trace review.jsonl --report review.md
python -m unittest -v
```

下载包包含共享运行时和固定依赖。仓库源码中的运行时位于 `examples/agents/common/agent_runtime.py`；进入示例目录，用 `PYTHONPATH=../common python app.py` 运行。`--trace` 与 `--report` 只创建新文件，已有文件不会被覆盖；不指定时，报告输出到终端，临时 trace 随退出清理。

## 整体架构

主管先读取并解析 diff，接着为每个角色创建独立模型对象和循环。Worker 的 `read_diff` 工具返回同一份快照；模型完成后，主管校验 JSON、查证引用位置，收集各角色状态，再由普通 Python 渲染报告。没有额外调用模型“润色汇总”，因此也不会在汇总时新增无法回到原意见的判断。

## 项目结构

```text
multi-agent-review/
├── app.py
├── test_app.py
├── fixtures/
│   └── demo.diff
├── README.md
├── agent_runtime.py    # ZIP 内含；仓库源码位于 ../common/
└── requirements.txt
```

完整实现直接取自可运行文件：

{{< agent-code example="multi-agent-review" file="app.py" >}}

## 第一步：定义数据模型

每条发现包含 `path`、`line`、`severity`、`title`、`body` 与 `evidence`。严重程度只允许 high、medium、low；未知字段、错误类型或空必填内容都会被拒绝。最终文本还必须同时包含 `summary` 与 `findings`。

校验器先检查 JSON Schema，再查新增行索引。例如默认 diff 的 `pricing.py` 第 2 行是 `return price - percent`，对应意见必须准确引用这条去掉行首空白的文本。模型若填写不存在的文件、上下文行或编造的代码，就得到 `invalid`，不会以空数组继续汇总。

这个小例子只接收定位到新增行的意见。对删除行、二进制文件或全局架构的审查需要另行设计数据结构，不能靠假行号塞进当前格式。

## 第二步：构建工具集

程序支持两条真实输入路径：

```sh
python app.py --diff /path/to/change.diff --trace ingest.jsonl
python app.py --git --workspace /path/to/repository --trace worktree.jsonl
python app.py --git --staged --workspace /path/to/repository --trace staged.jsonl
```

`--diff` 从指定文件读取；`--git` 实际启动本地 Git 子进程，默认读取已跟踪文件的工作区变更，`--staged` 改读暂存区。它禁用外部 diff 与文本转换助手，不调用 `gh`、不联网获取 PR、不发布评论，也不包含未跟踪文件。

diff 最多 12,288 字节，Git 最多运行 5 秒。输入必须是普通文本 unified diff：文件头说明文件名，`@@` 行说明新旧行范围，后面的加减号标出增删。程序逐段核对行数，拒绝截断、二进制、合并 diff 以及当前未支持的引号路径格式。大改动应分批输入，而不是静默截断再声称已审完。

自定义输入在离线模式下同样会真实读取和解析，但固定响应只返回“已读取输入，未分析自定义代码”，不会套用演示意见。需要模型分析时，在配置环境变量后加 `--live`。

## 第三步：定义各 Agent 的 System Prompt

三种角色分别检查逻辑、安全和性能，其他规则相同：先读 diff，把源代码当资料，不跟随其中的指令；意见必须对应新增行；证据不足时返回空发现并说明限制；没有执行工具时不得声称测试通过。与[Prompt 设计](/agent/prompt-design-agent/)一样，文字要求还需要执行端检查。

独立上下文可以避免直接复制另一位 Worker 的中间意见，但不证明判断独立。相同模型和同一份不完整 diff 仍可能产生共同盲点。这里没有额外的交叉批评回合。

## 第四步：实现 Worker Agent 通用框架

每个 Worker 调用共享 `run_agent`，最多 4 轮、3 次工具调用，默认时限 10 秒。时限从取得并发名额后开始，等待名额的 Worker 不占一个活动模型槽位。live 模型客户端在该 Worker 结束后关闭。

若返回最终文本，就检查结构与引用。若运行时报告 `limit`、`timeout` 或 `error`，主管保留这个状态及原因；用户取消时，等待中的和运行中的 Worker 都会得到取消状态。用固定夹具耗尽来模拟模型错误，也会走同一失败路径。

## 第五步：Supervisor——分发、收集、综合

`asyncio.Semaphore` 是一个名额计数器：没有空位的协程先等候，已有空位的才开始模型循环。默认三个角色、两个名额，可以重叠等待两路响应，同时避免无界启动请求。测试用事件屏障确认两路确实同时进入，再验证没有第三路越过上限，未用一个脆弱的耗时倍数冒充并发证据。

主管保留每个已完成结果，按角色顺序渲染，并合并同位置、同标题的重复项。任一角色失败、格式无效、超时、达到上限或取消，整份报告标为 `PARTIAL`，已完成发现仍显示。格式检查通过但没有发现，只表示这位审查者交回了一个合法结果，不表示代码安全。

## 完整执行流程

默认演示读取 `fixtures/demo.diff`，固定逻辑意见指出百分比折扣被改成固定金额扣除。主管验证引用确实是 `pricing.py` 的新增第 2 行，另两位角色返回合法空意见，最后渲染报告。

### 一次完整的执行输出

以下是 2026-10-17 在 Python 3.11.16 下运行默认入口捕获的片段，省略其他段落和 trace 路径：

```text
# Local diff review

Mode: fixture; source: diff file
Model review only. No project tests were executed.
All reviewers returned validated JSON; this does not prove correctness.

## logic: complete

本地固定响应，仅验证分发、工具和格式校验。

- high | pricing\.py:2 | 百分比被当作固定金额扣除
```

这里的意见正文给出假设输入 `price=200`、`percent=10` 的计算说明，来自固定审查回复，不是实际执行了项目测试。示例自身的集成测试会运行真实临时 Git 仓库和应用入口，验证的是程序行为。两种证据应分开记录，不能把后者的通过写成模型审查准确率。[评测篇](/agent/agent-evaluation/)进一步讨论了任务完成标准。

## 关键工程决策

### 为什么每个 Worker 是完整的 ReAct Agent

本例保留工具循环，使 Worker 能先请求 `read_diff` 再给意见。它没有完整文件读取或命令执行能力，全部输入都来自同一快照。若一次提供资料就够，也可改成单次模型调用；循环不是获得审查能力的保证。

### 为什么 Agent 间不共享上下文

每个角色有自己的模型与消息历史，工具结果只进入它的循环。共享的是只读输入，不是可竞争修改的文件状态。这是职责和数据组织方式，不是进程隔离或操作系统沙箱。

### 什么时候不该用 Supervisor 模式

只要一轮检查足够，或多个角色实际重复检查同一问题，就应先比较单 Agent 的成本与收益。多角色不能补回 diff 中未提供的证据，也不会自动提高准确率；这与[多 Agent 协作](/agent/multi-agent-collaboration/)里的任务拆分条件一致。

## 常见失败模式

### Worker 输出格式不一致

不合法 JSON、错字段和引用不匹配都显示为 `invalid`。真正没有发现应返回合法空数组，不能用解析失败替代。测试会构造这些输出，检查已有正确意见仍保留。

### 交叉审查发现虚假矛盾

当前程序没有自动交叉审查，因此也不声称消除了矛盾。渲染只合并明确重复项，保留不同角色的意见，交给读者检查。[Reflection](/agent/reflection-agent/)解释了增加批评者时仍会出现的共同误判。

### 并行执行中一个 Agent 超时拖慢全局

每个活动 Worker 有独立时限，超时后释放名额，其他角色继续。取消整批任务时，主管取消并等待所有 Worker 清理，保留已经完成的发现。应用对部分结果退出 1，用户取消退出 130，输入或配置错误退出 2；退出 0 也只说明所有输出通过结构检查。

live 模式必须显式配置 `OPENAI_API_KEY` 与所选 `OPENAI_MODEL`，可选 `OPENAI_BASE_URL`。缺配置和调用失败都不会切成固定响应。这里没有真实凭据，未验证在线模型任务。

## 总结

这个入口现在能从本地 diff 文件或真实 Git 命令走到并发审查、结构检查和最终报告。使用时先看每位审查者是否完成，再核对意见的证据与前提；测试是否实际执行，应由另一个明确的测试步骤证明。

*上一篇：[调试 Agent：当你不知道它为什么做了那件事](/agent/agent-observability-debugging/)*
