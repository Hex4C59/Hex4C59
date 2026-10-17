# Agent 实战教程实现与验证修订

日期：2026-10-17。

本轮承接[已发布文章的易读性审阅](published-article-readability-audit-2026-10-17.md)，处理其中仍缺完整实现的七篇 Agent 实战教程、五篇机制文章的错误示例，并同步调试文章中的运行轨迹。用户要求把实现、教程验证和提交发布一并完成，共修订 14 篇相关稿件。

## 实现与文章的对应方式

完整源码保存在 [examples/agents](../../examples/agents/README.md)。七个实战项目与一个机制示例包共用工具调用循环，各自包含入口、测试和演示数据。正文通过 `agent-code` shortcode 读取源码，发布构建从同一目录生成下载包；ZIP 加入公共运行层和依赖版本，不再要求读者从分散片段拼装项目。

默认演示使用明确标为 `fixture` 的固定模型响应，同时实际操作临时文件、SQLite、HTTP 或 MCP 子进程。它验证程序执行与失败处理，不能作为线上模型选择工具或研究质量的证据。环境没有模型 API 密钥，线上服务需要读者按 README 配置；已安装 SDK 的异步请求接口通过真实本地 HTTP 服务核对。

## 验证范围

- 公共运行层：参数 Schema、错误回传、工具执行顺序、轮次和调用上限、异步超时、取消、路径越界、符号链接、原子写入及 SDK HTTP 接口。
- 下载包：检查源码一致、缺失文件、依赖版本、符号链接、私有文件和重复路径；解压后从项目目录运行测试与演示。
- Rust：重新解压现有课程 ZIP，运行三个 Cargo 工作区的测试和文档测试、25 个独立程序、31 个故意编译失败的反例，以及基础和练习工作区的示例入口。共执行 118 条命令，56 项 Rust 测试通过；缺少 CLI 参数时按预期拒绝，并另用正确参数验证跨进程保存。
- 站点：现有及新增检查共 71 项通过；评论服务 45 项测试通过。

实际命令包括：

```sh
python3 -m unittest discover -s scripts/tests -v
node --test services/comments/tests/*.test.mjs
python scripts/check_agent_examples.py --fresh-env
python3 scripts/build.py

git diff --check
```

Python 示例使用 Python 3.11.16；Rust 使用 rustc/cargo 1.99.0、2024 edition。Rust 的本次结果仍只代表 macOS arm64，不代替最低版本和其他系统的实测。

## 逐项修复与结果

七个实战 ZIP 均已按各自 `requirements.txt` 在独立、干净的 Python 虚拟环境安装，移除 `PYTHONPATH` 后从解压目录运行。141 项应用测试全部通过，七个默认入口均退出 0；公共运行层另有 12 项测试通过。

| 项目 | 修复内容 | 应用测试 |
| --- | --- | ---: |
| [CLI Coding](../../content/agent/build-cli-coding-agent/index.md) | 完整入口、审批与文件差异、真实命令结果、超时取消清理、实际 JSONL 轨迹 | 11 |
| [文件管理](../../content/agent/build-file-management-agent/index.md) | 路径限制、逐项确认、持久日志、删除备份、跨进程撤销、失败恢复和冲突拒绝 | 30 |
| [MCP](../../content/agent/build-mcp-agent/index.md) | 官方 SDK 初始化和分页发现、名称路由、错误解码、两个实际 stdio 服务及退出清理 | 17 |
| [并行代码审查](../../content/agent/build-multi-agent-code-review/index.md) | 本地 diff 输入、有界并发、结构化意见与引用检查、超时和部分结果、真实报告渲染 | 10 |
| [持久记忆](../../content/agent/build-persistent-memory-agent/index.md) | SQLite CRUD、用户范围、逐项保存许可、新进程检索、历史与实际请求预算 | 19 |
| [Research](../../content/agent/build-research-agent/index.md) | 本地语料搜索与读取、来源摘录、引用校验、修订后重新检查、失败退出及完整入口 | 27 |
| [Skill](../../content/agent/build-skill-expert-agent/index.md) | 实际技能发现和参考加载、工作区写入与覆盖许可、授权创建后重扫、读取产物检查 | 27 |

Research 示例的来源工具只读用户显式选择的本地语料，模型仍自主选择工具和处理顺序；在线模式更换模型，不把它称为已实现互联网搜索。引用检查可拒绝不存在或不匹配的摘录，不能判断来源本身是否真实。

[调试文章](../../content/agent/agent-observability-debugging/index.md)改用 CLI 实跑轨迹；[Reflection](../../content/agent/reflection-agent/index.md)修正异步客户端，并指向 Research 的完整运行例子。机制示例在独立虚拟环境安装后，从实际平铺 ZIP 中运行，71 项测试和默认入口通过：

| 文章或模块 | 修复内容 | 测试 |
| --- | --- | ---: |
| [Planning](../../content/agent/planning-plan-and-execute/index.md)与[上下文](../../content/agent/context-memory-state-management/index.md) | 超时、失败和上限不再标完成；实际调用前强制预算，整组保留或移除工具交换 | 29 |
| [人工确认](../../content/agent/human-in-the-loop/index.md)与[多 Agent 协作](../../content/agent/multi-agent-collaboration/index.md) | SQLite 持久请求、身份/正文/期限绑定、一次性决定与认领、带版本的任务更新、确认后推进消息游标 | 18 |
| [Guardrails](../../content/agent/guardrails-safety-boundary/index.md) | 所有受支持工具入口检查并拒绝不允许操作，批准绑定具体内容和现有文件摘要 | 22 |
| 汇总入口 | 解压后运行全部模块，以及选择单个模块和拒绝无效选项 | 2 |

八个包合计 **212 项应用测试**，公共运行层另有 **12 项**。14 篇相关稿件的桌面与手机排版共检查 **28 次**，无整页横向溢出或脚本错误，所有代码块的复制按钮均可用；Markdown 导出保留原始代码围栏。

正式构建及只含已提交文件的干净副本构建均通过：373 个 HTML、20050 个站内地址和锚点、119 条搜索记录；119 篇原有文章地址不变。干净副本没有带入工作区原有的未提交内容或未使用的演示资源。

## 下载包验收摘要

下面的 SHA-256 来自干净依赖环境中通过测试的实际 ZIP；正式构建生成的八个包与这些值逐一相同。

| 下载包 | SHA-256 |
| --- | --- |
| cli-coding.zip | `0a158a84d1eb6991e84461a06b6d6f9a76e20abcd3109c4cd42cc23307adbc3a` |
| file-management.zip | `ff7d8f87e88eeb6987163e670c56371893def7f6c58aa873ec1fd2d38e47dcb8` |
| mcp.zip | `08297c3b5a1d04191eaa69b9ef7b3bca287250fce0eb85cc8042099927658970` |
| multi-agent-review.zip | `d3dc39f18fadd4bff5dd877ec21a4e4ab6a5afd6a07fc4b85fca5cf9ebdb3c3f` |
| persistent-memory.zip | `3a4323e94b39fd736e975dd485167b25b9cee2acc7b0430ce4f6d867f419f242` |
| research.zip | `2fd504bc231ae6754aedc0aceaeccb2d933fd592572895d84e396a4c912e370b` |
| skills.zip | `aa3ea4d66404016bbe97bbf4ae6d421f46847e239339fef5f06978fd21681379` |
| mechanisms.zip | `71868392a81d964287ac0b2a9a089c55815c05a4c4d43bcbfcce06770b0325ce` |



## 提交与发布

提交按逻辑分开：

- `eee2537`：博客易读性规则和写作流程。
- `2f5ae8e`：92 篇文章的易读性修订。
- `4df751c`：14 篇相关稿件的实现修订、八个示例包、共享运行层与 CI。Reflection 的易读性和客户端修复分别位于前后两个提交，因此文章总数仍为 105 篇。

以上提交已推送到 `source`。2026-10-17，[GitHub Pages 构建与部署](https://github.com/Hex4C59/Hex4C59/actions/runs/39020707224)成功；`ubuntu-latest` 的固定依赖安装、八个下载包运行、站点测试、评论测试和正式构建均通过。

部署后实际取回公开站点的八个 ZIP：每个 SHA-256 都与上表通过测试的包相同。另检查 14 篇相关文章，均返回 HTTP 200。线上下载文件与本地验收版本一致；凭据、生成的站点目录和虚拟环境没有加入提交。

本记录和第一阶段逐篇清单另作一次文档提交。工作区原有、与本次修复无关的修改继续保留。
