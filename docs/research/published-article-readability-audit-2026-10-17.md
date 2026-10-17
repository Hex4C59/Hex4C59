# 已发布文章易读性审阅记录

日期：2026-10-17。本文件记录第一阶段的易读性审阅；后续实现、运行验证与发布见[实战教程实现修订](agent-tutorial-implementation-repair-2026-10-17.md)。

用户授权使用 10 个 subagent 审阅已发布稿件并直接修正。本轮以 Hugo 实际发布列表和站点文章目录配置确定范围，共 **119 篇**；已修改 **105 篇**，保留 **14 篇**。草稿、栏目索引和分类页面不在正文清单内。

各组逐篇审阅，修正陌生术语、抽象名词、主体和指代不清、解释跳步及错误的效果保证；译文保留作者原意，额外说明标为译者注。依据为[技术写作规范](../../.agents/content/technical-writing.md#readability)与[博客写作流程](../../.agents/content/blog-writing-workflow.md)。

理解检查由 Agent 完成，主 agent 复核改稿和受保护内容；没有开展真实读者测试。以下验证属于第一阶段的本地改稿检查，后续提交和部署单独记录。

## 分组与覆盖

环境并发上限为 6，先后启动了 10 个不同 subagent；每组写入范围互不重叠。

| 组 | 范围 | 审阅 | 修改 | 保留 |
| --- | --- | ---: | ---: | ---: |
| 01 | DeepSeek Harness 01–06 | 6 | 6 | 0 |
| 02 | DeepSeek Harness 07–11 | 5 | 5 | 0 |
| 03 | Agent 概念与机制 | 17 | 17 | 0 |
| 04 | Agent 实践与调试 | 8 | 8 | 0 |
| 05 | 软件设计系列 | 11 | 11 | 0 |
| 06 | RTC、基础专题与随笔 | 13 | 8 | 5 |
| 07 | Rust 入门前半程 | 11 | 10 | 1 |
| 08 | Rust 进阶与排障 | 11 | 10 | 1 |
| 09 | 译文 A | 18 | 12 | 6 |
| 10 | 译文 B | 19 | 18 | 1 |

## 主 agent 复核

- 对照审阅前原稿检查代码围栏、公式、标题、引用目标、shortcode、发布地址与 front matter；描述、摘要和修改日期按约定允许更新。少量新增版本链接仍固定到原稿已引用的源码 commit。
- 复核 DeepSeek Harness、软件设计、RTC、RAG 与译文等改稿；把请求生命周期的概览改为浏览器、服务器、模型和工具的具体过程，并恢复两处原有源码快照入口。
- 对照 Anthropic 原文修正 RAG 文中的指标归因：所述检索失败率下降来自给片段补充上下文后的特定组合与实验条件，不能归给任意普通混合检索。来源：[Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)。
- 对照[官方权限文档](https://code.claude.com/docs/en/permissions)，统一两篇 Claude Code 权限说明，并写明核对日期。
- 核对[评估文章原文](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)的起始分数差异，保留数字并添加译者注。
- 将修改日期统一核对到 2026-10-17，避免复用旧 UTC 时分造成次日显示。

## 验证

| 检查 | 结果 |
| --- | --- |
| 逐篇清单和自查记录 | 119/119，10/10 分组 |
| 受保护内容与引用检查 | 通过；示意输出或注释的明确纠错例外另列于下文 |
| Hugo 正式构建与站内链接检查 | 通过；373 个 HTML，20145 个站内地址及锚点，119 条搜索记录 |
| 现有站点测试 | 65 项通过 |
| 发布范围与地址 | 119 篇清单及原有 URL 保持 |
| 正文排版抽查 | 7 篇 × 桌面/手机宽度，共 14 组；无整页横向溢出或脚本错误。外部评论与媒体服务不在此检查范围 |
| Git 差异检查 | git diff --check 通过 |

实际执行了 `python3 -m unittest discover -s scripts/tests -v`、`python3 scripts/build.py --destination "$audit_build_dir"`、`git diff --check`，以及基于原稿快照的对照检查。构建没有执行部署。

本轮没有重跑所有文章附带的教程、模型调用或项目实验。文中原有实验数据仍按原版本、环境与日期理解，不能视为本轮重测结果。

## 示意输出和注释的纠错

18 处纠错涉及 14 个围栏：6 个 Python 围栏只改说明性注释，已核对执行语句不变；8 个围栏更正假设对话或输出。

- [调试 Agent：当你不知道它为什么做了那件事](../../content/agent/agent-observability-debugging/index.md)：把排查轨迹明确标成假设，交代循环上限。
- [从零构建 CLI Coding Agent：ReAct 驱动的实战实现](../../content/agent/build-cli-coding-agent/index.md)：修正请求轮次、输出与结束标记的顺序，把测试结果明确标为假设。
- [文件管理 Agent 实战：当操作不可逆时，Guardrails 怎么落地](../../content/agent/build-file-management-agent/index.md)：更正目录创建、人工确认和撤销的说明；示意对话如实显示新调用没有撤销历史，永久删除没有恢复成功。
- [MCP 集成实战：让 Agent 连接真实服务](../../content/agent/build-mcp-agent/index.md)：标明简化接口不能直接运行，本地记录函数只能返回模型提供的文字。
- [Multi-Agent 实战：用 Supervisor 模式构建代码审查系统](../../content/agent/build-multi-agent-code-review/index.md)：把人工整理的假设报告与程序实际返回的数据分开，不把模型报告当作测试或完整审查证据。
- [持久记忆实战：让 Agent 跨会话记住用户](../../content/agent/build-persistent-memory-agent/index.md)：改正顺序执行与裁剪的注释；演示使用独立应用目录，避免覆盖记忆程序入口；不把用户资料推断为未确认的连接能力。
- [Research Agent 实战：从 RAG 到自主研究](../../content/agent/build-research-agent/index.md)：把未实现的工具日志改成假设交互摘录；来源不足时显示待核实，不假称报告已经达标。
- [Skill 实战：教 Agent 写你风格的博客](../../content/agent/build-skill-expert-agent/index.md)：纠正匹配结果的注释；未读回文章时，各项质量检查显示待核对。

## 第一阶段发现的问题与后续处理

第一阶段发现部分旧实战示例缺完整入口、输出校验、有效的执行限制或失败恢复。当时先更正不实说明并保留待办；下列条目是当时的发现，代码补全及当前运行证据统一记录在[后续修订](agent-tutorial-implementation-repair-2026-10-17.md)。

- Agent 概念与机制：原有产品与版本事实：Claude Code权限行为在HITL与Guardrails两篇间的矛盾已解决，不再列为未解决项。其余MCP、多Agent、Skill、HITL、Guardrails的产品支持列表、工具名、继承、存储及其他默认行为未全面核验；原有版本/配置范围提示保留。
- Agent 概念与机制：当时发现预算参数未生效、规划超时被标为完成、任务板缺并发更新和消息游标、审批请求缺持久化和身份绑定、安全扫描仅加提示等问题。后续已用可执行机制模块和 71 项测试修正；同步客户端与 `await` 的错误也已处理，详情见后续修订。
- Agent 实践与调试：当时缺完整入口和连接器、文件删除备份与跨进程撤销，以及 Skill 产物读回检查。后续七个完整项目已在实际 ZIP 与独立依赖环境中通过 141 项应用测试；调试文章改用实际轨迹。
- 第一阶段的假设数据与译文观点仍按原有来源及条件理解；后续代码测试不改变原文数据的比较条件，也不作为线上模型效果的证据。
- 译文 A：原文两处起始分数的比较条件没有解释。主agent已核对原文并在译文明确加注；原数字保留，不能当作同一组严格对比。

## 逐篇处理记录

“保留”表示该组检查后认为现有解释已满足本次要求；具体判断仍是 Agent 自查。

| 文章 | 处理 | 主要问题、修改或保留理由 |
| --- | --- | --- |
| [DeepSeek Harness 源码解析（一）：从代码补全到仓库级 Agent](../../content/agent/deepseek-harness-agent-engineering/index.md) | 修改 | 说明工具调用在审批通过后才交给工具执行；说明会话事件如何生成模型历史，以及服务选择、操作系统隔离和撤销副作用的区别 |
| [DeepSeek Harness 源码解析（二）：一次用户请求如何经过整个 dsh 系统](../../content/articles/deepseek-harness-request-lifecycle/index.md) | 修改 | 补清 Host、Inbox、Turn、Step、attempt、waterfall 和投影的职责；说明 claim 后默认不自动重新入队、工具独占与取消等待的行为；补清实时帧与结束记录、Step 与 Turn 结束、快照与新增事件衔接，以及写入队列与刷盘的区别 |
| [DeepSeek Harness 源码解析（三）：源码目录、包依赖与文档地图](../../content/articles/deepseek-harness-source-map/index.md) | 修改 | 用具体职责区分接口、实际实现、模型工具和应用选择配置；补清 peer 依赖含义、文件大小分支、读取窗口及本机读取入口；说明 profile、bundle 和后续 patch 怎样影响实际提供者选择 |
| [DeepSeek Harness 源码解析（四）：CLI、Web、Desktop 与 SDK 如何组装同一套运行时](../../content/articles/deepseek-harness-application-entrypoints/index.md) | 修改 | 补清 profile、bundle、patch、配置行与父子配置树的关系；说明 schema、参数转交、根 include、HMR 和未等待的异步工作；补清浏览器启动信息、Desktop 启动注入，以及 SDK 根会话、idle 和后代通知的收集范围 |
| [DeepSeek Harness 源码解析（五）：Context、Service 与依赖注入如何协作](../../content/articles/deepseek-harness-cordis-context-services/index.md) | 修改 | 按服务名、域标签、实现记录两步查找来解释服务解析；补清属性访问、get 探测、inject 等待、提供者就绪与依赖变化的差别；将注册撤销、tracker 代理和 scope 注册层改写为具体归属与清理动作，并补清 realm 的标签组织职责 |
| [DeepSeek Harness 源码解析（六）：类型声明如何接上服务注册](../../content/articles/deepseek-harness-types-service-registration/index.md) | 修改 | 说明类型声明补充成员与运行时登记实际对象分别做什么；补清模块增强与类型导入擦除、get 重载和普通 inject 的开放类型约束；说明 Host/Client 检查单元、源码定位、声明依赖缺失、反例诊断、编译与打包分工及 tarball |
| [DeepSeek Harness 源码解析（七）：五种事件派发怎样执行监听器](../../content/articles/deepseek-harness-event-dispatch/index.md) | 修改 | 说明 TypeScript 识别事件与运行时调用监听器的区别；补充 Context 的用途；先解释插件卸载要撤销登记，再介绍 Fiber、effect 与清理函数；在表格中写明 serial/bail 的停止条件，解释 bail 值；把 Promise 等待与监听器循环分开；写明不调用 next 时后续策略及默认终点均不执行；将生命周期边改为重复创建通知的具体行为；增加明确标注为假设的 R/A/B scope 例子，解释 carrier 携带监听器筛选条件；增加 lastmo |
| [DeepSeek Harness 源码解析（八）：effect、Fiber 与 Scope 怎样清理资源](../../content/articles/deepseek-harness-effect-fiber-scope/index.md) | 修改 | 从停止工作、保留收尾所需资源、关闭写入通道的顺序解释问题，再介绍 effect 与 Fiber；将所有权解释为清理函数登记在哪张名单上，明确同一个 Fiber 和同一个函数对象的条件；补充生成器 yield 的用途，说明登记清理函数与执行清理不同；说明同步重入、等待 setup 返回、查询未完成清理 Promise 的过程；把 layer/undo 解释为作用域注册表及撤回修改的函数；分开注册撤销与业务对象关闭；写明 Scope key 负责查找和事件筛选，Fiber.par |
| [DeepSeek Harness 源码解析（九）：Loader 怎样把配置变成运行中的插件](../../content/articles/deepseek-harness-loader-config-hmr/index.md) | 修改 | 先写清理后重新初始化、保留引用、分发子配置和替换代码，再给出各机制名称及 HMR 全称；解释 schema、模块说明符、entry id、Include 子树冒号和模块命名空间对象的用途；说明配置表达式为何等待子 Fiber 的服务就绪，以及热更新先比较原始输入、再比较有效结果；用监听器仍保存旧 config 的过程解释稳定引用，并说明快照复制与冻结；把 isolate 解释为服务名到 Symbol 再到实现的查找过程；说明迁移后依赖重检；补清旧 Fiber 等待、写队列与 |
| [DeepSeek Harness 源码解析（十）：Agent、AgentHandle 与实例所有权](../../content/articles/deepseek-harness-agent-handle-ownership/index.md) | 修改 | 以关闭资源和注销活对象解释所有权；保留 get 与 create/resume 返回值的区别及安全限制；分别写明调用 Context 登记清理、parentAgent 记录业务父子、parentSession 记录会话来源；说明 factory slot、调用方追踪、loopCtx/ownerCtx/agent.ctx 和预先留出清理位置的用途；解释 Inbox、会话投影和创建公告；明确 await register 等登记，调用返回函数才撤销；用初始化等待监听器、whenI |
| [DeepSeek Harness 源码解析（十一）：Preset、Persona 与默认模型怎样生效](../../content/articles/deepseek-harness-presets-persona-model-selection/index.md) | 修改 | 先说明 Preset 安装哪些插件、Persona 提供哪些段落，以及会话模型选择读取哪些状态；补充 Context/Scope/Session 和 provider/model/reasoningEffort 的职责；解释修订是实际挂载的那份插件树；说明同修订共享注册、使用计数、只读租约、声明列表与实际保留修订的差别；以会话事件重算状态解释投影；补清空白 Turn 检查、选择日志和同名空 Persona 的覆盖顺序；明确动态 Context 是发给模型的信息片段，与 Cor |
| [如何评测一个 Agent：不只是看它回答得好不好](../../content/agent/agent-evaluation/index.md) | 修改 | 说明固定任务、保存轨迹、重复运行与故障注入各自用于什么判断；标注格式示例的局限，区分回归集与未参与调试的新任务评测；修正明确假设的平均数例子，说明模型评分需已知错误和证据校准，阶段用例数量不作统一门槛 |
| [Agent Spec：如何用自然语言定义一个可执行系统](../../content/agent/agent-spec-design/index.md) | 修改 | 用文档整理任务串起目标、处理步骤、三轮上限和输出格式，新增示例明确标为假设；解释状态机、流水线、输出约定和收敛的职责，写明模型与运行程序的分工；保留六项检查与原模板，收窄“必须”“确保”“崩溃”等无条件表述 |
| [上下文与记忆：Agent 为什么会在长任务中失去方向，以及如何设计状态管理](../../content/agent/context-memory-state-management/index.md) | 修改 | 明确本轮输入与外部记录的区别，给出任务状态更新和重新传入的前提；解释检查点、状态处理钩子和按任务压缩的具体动作；标注示例代码省略项及 token 参数未落实的局限，保留代码原文 |
| [Guardrails：如何约束 Agent 不做错事](../../content/agent/guardrails-safety-boundary/index.md) | 修改 | 用原有三个假设场景解释泄露、破坏与间接注入，明确输入、执行、输出各做什么、不能补救什么；补齐分类阈值、参数授权、路径范围和脱敏模式的适用条件；解释沙箱实际应限制的对象，指出原代码只作命令包装；保留全部代码和标识符；核对检测、提示和硬阻断的差别，说明必须覆盖所有执行入口；按2026-10-17官方permissions文档统一说明：权限模式与allow/ask/deny规则共同决定询问；default仅作有条件示例，acceptEdits与允许规则可改变行为；仅在Claude |
| [Human-in-the-Loop：Agent 什么时候应该停下来问你](../../content/agent/human-in-the-loop/index.md) | 修改 | 用原有场景说明已授权自动执行、缺判断暂停及事后审查的差别，场景数字明确为假设；解释Future等待与回调、超时拒绝、请求对应和重启恢复前提；说明确认不能替代验收，修改拒绝比例需结合内容判断；产品默认值保留为原有示例；按2026-10-17官方permissions文档统一说明：权限模式与allow/ask/deny规则共同决定询问；default仅作有条件示例，acceptEdits与允许规则可改变行为；仅在Claude Code产品段落新增官方文档链接及核对日期；明确确认选 |
| [MCP：让 Agent 的工具生态不再各自为战](../../content/agent/mcp-model-context-protocol/index.md) | 修改 | 补齐工具发现到执行回传的职责，解释协议请求与连接配置；保留全部请求、标识符与版本示例，说明关闭动作、认证与兼容仍由实现处理；用数据跨服务传递说明权限判断，补上资源占用和注释可信度限制 |
| [记忆的四种形态：Agent 如何在不同时间尺度上保住它知道的事](../../content/agent/memory-types-and-design/index.md) | 修改 | 解释记忆是外部记录与本轮输入的配合，区分事件、事实和操作规则；用原有用户偏好、失败记录、项目配置说明读取与更新条件；补齐TTL全称与清理动作，说明共享提示词和用户专属信息的不同影响；同步修正程序记忆对比表的“永久/无需检索”简化标签，使表格与按需Skill的条件一致 |
| [多 Agent 协作：当一个 Agent 不够用时，如何让多个 Agent 分工合作](../../content/agent/multi-agent-collaboration/index.md) | 修改 | 按分派、输入、结果归属解释四种模式，补清Handoff示例未转交历史的限制；说明主Agent仍需接收可核查的结果，任务板需防重复认领和校验提交者；把并行、成本和讨论次数写成有前提的比较或假设，保留产品原例与全部代码 |
| [Planning：当 ReAct 不够用时，Agent 如何提前分解目标](../../content/agent/planning-plan-and-execute/index.md) | 修改 | 明确比较的是是否单独保存全局计划，补齐用户流失假设任务中的依赖过程；说明检查点按结果调整待办、保留执行事实，区分修正结论与撤销记录；按原代码解释退出分支和成功状态的缺口，移除无依据的五个子任务门槛 |
| [Prompt 设计：Agent 的系统提示词怎么写](../../content/agent/prompt-design-agent/index.md) | 修改 | 解释系统指令的作用与工具、状态、模型之间的关系；逐项补清调用触发、失败和停止规则的判断依据；说明两种注入都重建本轮输入，标注示例数值与规则效果需实际评测，保留所有提示词代码 |
| [ReAct：模型如何让推理与行动交替运转](../../content/agent/react-paradigm/index.md) | 修改 | 解释动作理由、工具请求和返回结果的分工，保留所有协议与代码；标注数据为流程示意、代码的未实现依赖和第二循环缺少上限；把透明、质量保证和格式保证改为可检查的动作与限制 |
| [Reflection：Agent 如何审视自己的输出并纠正错误](../../content/agent/reflection-agent/index.md) | 修改 | 说明反思的输入、标准、严重程度、修正和轮数上限；用原有竞品宣传案例补清“工具成功”与“证据充分”的差别；明确批评者需证据、独立上下文不保证独立判断，收窄成本与效果结论 |
| [Skill：不改模型、不写代码，教会 Agent 做专家级别的事](../../content/agent/skill-teach-agent-how-to-work/index.md) | 修改 | 沿用明确假设的Hugo写作任务，解释发现、读取、执行三步和验收；说明Skill不修改模型参数、不能保证专家表现，示例安装命令不作真实入口；补齐参考读取条件和MCP职责，并将产品路径列表限定为原文配置示例 |
| [工具接口设计：让 Agent 用得好，比让 Agent 用得上更难](../../content/agent/tool-interface-design/index.md) | 修改 | 以函数设计的四个问题说明文章范围，标注代码为接口示意；解释相关分数、更新时间、截断、错误码分别支持什么判断；写明任务标识如何传回查询，区分启动、运行、失败和完成；保留凭据示例代码但说明其依赖演示用途 |
| [Tool Use：为什么它是 Agent 的核心能力](../../content/agent/tool-use-core-of-agent/index.md) | 修改 | 串起注册、校验、执行、请求结果对应和停止规则；用假设的两次查询区分可并行与必须等待的依赖关系；标注研究示例为流程文本，收窄误调率、提速和接入效果判断，说明最小权限的任务条件 |
| [什么是 Agent：从聊天助手到可执行系统](../../content/agent/what-is-agent/index.md) | 修改 | 用明确假设的读文件、改代码、运行测试过程解释 Agent；把状态解释为任务进度与已有结果，说明工具由执行模块调用、记忆需进入本轮输入；说明工作流和 Agent 可结合，并把模型能力结论改为具体任务中需要检验的前提 |
| [什么是 RAG：让大模型用上你自己的知识库](../../content/agent/what-is-rag/index.md) | 修改 | 区分提问前建索引与收到问题后检索，并解释计量、候选数量和关键词评分；围绕原有退款、错误码和财报例子补齐条件，保留全部代码与原实验数字；说明检索、生成和重排的失败条件与开销；收窄效果保证并修正数据是否进入模型的说明；按主agent提供的2024-09-19一手来源核验结果，将35%/49%/67%分别对应Contextual Embeddings、再结合Contextual BM25、再加重排序，并补top-20及5.7%基线条件 |
| [调试 Agent：当你不知道它为什么做了那件事](../../content/agent/agent-observability-debugging/index.md) | 修改 | 补出目标读者、记录对象及开发者如何从输入、请求、工具结果寻找最早偏差；解释 Trace、Span、LLM、Token 的当前职责，说明可见文字不是内部思维记录；区分展示旧记录与重新请求模型，指出真实重放骨架未完成、参数变化时旧结果不再适用；补足单一活动 Span、未覆盖异常、日志截断和字符估算的局限，告警阈值明确为配置示例；把常见模式的因果断言改为要对照实际消息和执行结果验证的排查步骤，收紧总结；按本轮授权把调试示意的“实际行为”直接改为假设行为，并补足15轮上限是假设条件 |
| [从零构建 CLI Coding Agent：ReAct 驱动的实战实现](../../content/agent/build-cli-coding-agent/index.md) | 修改 | 用用户输入、模型请求、宿主执行和结果追加的过程解释 ReAct，并说明 CLI、LLM 和输出字段；明确教学骨架、未验证依赖及运行边界，去掉无依据的调用减少比例和产品结构推断；说明同名前缀目录、Shell 访问范围、单轮多工具和费用上限的区别；对照代码说明200字符只影响显示，模型历史保留完整结果；解释40条消息裁剪及无用户消息时的丢失；把执行记录明确标为假设，解释 tool_use/end_turn 与本例实际停止字段的区别，补足凭据配置和服务兼容前提；直接修正CLI示意的 |
| [文件管理 Agent 实战：当操作不可逆时，Guardrails 怎么落地](../../content/agent/build-file-management-agent/index.md) | 修改 | 定义操作提案、执行防护、风险分级与 Dry-run，让读者能沿函数返回值看到何时真正改文件；说明 notify 立即执行、两种待确认等级在当前代码中相同，选择批准后未选项仍留队；逐步说明反向栈及其文件不变前提，注明成功后才记录、退出丢失、失败不放回和覆盖/目录撤销的局限；把示意对话中的不可恢复删除等矛盾明确放在围栏前后解释，未改围栏内容；说明每次函数调用新建栈和防护对象、批量提交未挂接、批准不提供文件快照或自动事务回滚；直接删除成功恢复永久删除的错误对话，改为新run_age |
| [MCP 集成实战：让 Agent 连接真实服务](../../content/agent/build-mcp-agent/index.md) | 修改 | 补出 MCP 全称和三种角色，用启动、初始化、读取工具、转换定义、按名称转发的完整过程解释连接器；限定为本地进程通信教学骨架，说明未核对响应编号和协议兼容、未处理通知/并发/超时及仅保留文本；核对原文已有的参考实现仓库，说明 GitHub/SQLite 等旧服务已归档、不同语言服务安装方式不同；保留全部旧配置代码并明确其示意性质；解释模型看到工具不等于获准执行，名称映射、3000字符裁剪及消息裁剪仍需单独处理；把执行记录标为假设，收紧即插即用、质量更稳和固定毫秒开销等没有证据 |
| [Multi-Agent 实战：用 Supervisor 模式构建代码审查系统](../../content/agent/build-multi-agent-code-review/index.md) | 修改 | 用主管分派、Worker独立消息历史、补读工具和最终汇总解释架构，区分消息隔离与权限隔离；把30秒/10秒明确标为无开销假设，说明只有可重叠的 Worker 阶段近似受最慢任务影响；解释数据结构、自报置信度、工作区版本和简单行扫描的证据范围；补足有效空结果、解析失败、未完成的区别，指出交叉步骤缺原代码且不修改最终等级或去重；收紧按行数或文件数跳过维度的建议，说明模型选择和并行收益均需实际验证；将未实现的终端报告排版改为人工整理的ReviewReport字段摘录，令牌数显示与原 |
| [持久记忆实战：让 Agent 跨会话记住用户](../../content/agent/build-persistent-memory-agent/index.md) | 修改 | 把跨会话记忆解释为选摘要、写本地、下次读回，定义事件、资料、向量和相似度在当前流程中的作用；说明逐条候选比较、0.6/0.2/0.2为配置，向量失败改按时间和评分排序，事件表未按用户隔离；对照代码交代两次提取顺序等待、最近20条/每条500字符、同键覆盖和固定置信度；补足正常退出才保存、异常丢失风险、清除不清当前消息导致可能再写入，以及第二条 system 的权限含义；纠正清理阈值与调用状态、移除未测延迟和空间断言，说明 MCP存储与应用提取是不同职责；纠正顺序await被写 |
| [Research Agent 实战：从 RAG 到自主研究](../../content/agent/build-research-agent/index.md) | 修改 | 定义 RAG/Agentic RAG，沿规划、选择工具、阅读、记笔记和综合解释输入输出，限定一次检索为简化基线；把新增例子、规划和执行记录标为假设，明确2025年是示例研究时段而非近期事实；解释搜索分数、自报置信度、转载来源不独立，质量检查只读任务和报告不能核实引用；在开头及安装段说明同步客户端/await与入口缺口，避免将片段宣称为已运行；补足两层裁剪、网络错误、外部指令、内存笔记和修订后不再检查的边界，删除免费额度与无依据收益描述；直接把不存在的逐工具日志移为人工交互摘录 |
| [Skill 实战：教 Agent 写你风格的博客](../../content/agent/build-skill-expert-agent/index.md) | 修改 | 定义自定义 Skill 的文件角色，说明只改变输入，不训练模型或赋予新工具权限，样例不是当前仓库规则；解释启动时扫描、任务时按名称/连续关键词选择、正文拼接及重新加载需求，并说明简化解析限制；用假设输入解释“写一篇”与“写文章”的匹配差别，指出“画几张图”不能保证命中配图Skill；明确模型自查没有读回文章、打印失败仍显示完成，也没有文件写入边界；展示日志改为假设；说明创建工具Schema尚未接入，缩小规范长度和模型微调表格的断言，补足短追问失去匹配与多Skill冲突；直接把 |
| [软件设计导读：怎样形成可检查的判断](../../content/articles/software-design-00-reading-guide/index.md) | 修改 | 用版本来源变化后调用代码是否需要修改，解释设计判断的依据；保留接口与抽象概念，补明只读返回字段即可查询版本；把内部改动集中处理的前提拆清 |
| [抽象的收益与代价：封装何时降低复杂度](../../content/articles/software-design-01-abstraction/index.md) | 修改 | 把对象身份与修改隔离写成两项具体检查：是否同一对象、修改结果是否影响内部数据；说明正常导入不能直接取得内部对象，以及公共入口怎样转向更换后的内部函数；用再次赋值、对象属性、嵌套冻结和模块导出的具体动作解释不同约束 |
| [接口与契约：两段代码怎样可靠地配合工作](../../content/articles/software-design-02-contracts/index.md) | 修改 | 改用日常语言说明前置条件、后置条件和不变量的引入方式；明确读取源码文字、检查完整结果或要求特定内部形式都是额外依赖，并指出实现变化可能影响这些用法 |
| [间接调用与依赖：程序怎样按名称选择要做的事](../../content/articles/software-design-03-indirection/index.md) | 修改 | 说明处理器表何时适用：各项操作按一致方式接收请求、交回结果，并集中登记名称与函数；把请求形状改成入口能处理的对象；明确间接调用后仍依赖操作名称、请求字段和结果约定 |
| [模块边界与信息隐藏：哪些代码应该放在一起](../../content/articles/software-design-04-module-boundaries/index.md) | 修改 | 把集中维护的理由落在创建、查找、修改共同知道任务保存方式，以及换容器时需要一起调整；说明单独移动数据文件后其他操作仍需要知道容器类型和遍历方式；区分涉及多少文件与外部调用者能否继续按原接口工作 |
| [状态与副作用：谁能修改数据，失败后保留什么](../../content/articles/software-design-05-state-effects/index.md) | 修改 | 说明所有者维护当前内存，采用就是把新数据用于后续读取和修改；区分供调用者整理的操作结果与供所有者决定采用的数据；明确先后保存不会自动让第二个所有者取得第一个所有者的新进度 |
| [错误传播与异步边界：需要等待时，成功和失败怎样交回来](../../content/articles/software-design-06-async-errors/index.md) | 修改 | 明确未等待保存 Promise 时，稍后的拒绝不会进入当前 try 的错误处理；包装函数须继续交出 Promise 供外层等待；按既有代码校正流程：先设置忙碌标记，再检查编号、计算任务并发起保存；补清超时只释放忙碌标记时，旧操作仍可能继续采用旧建议 |
| [可测试性：怎样写出能发现问题的检查](../../content/articles/software-design-07-testability/index.md) | 修改 | 明确对象比较要求实际字段和值与预期一致；说明测试函数可能已经结束而操作、断言尚未结束；分别说明任务层失败原因、文件层错误代码，以及真实写入和读回弥补的证据 |
| [重构中的行为保持：换一种实现，怎样确认功能没变](../../content/articles/software-design-08-refactoring/index.md) | 修改 | 说明内部换 Map 后，外部读取和保存仍需要转换成约定数组；解释候选数据就是准备保存、等待所有者采用的新数据；区分内部共享未变化任务与外部获得副本，说明真实文件检查关注保存参数转换后的内容 |
| [持久化与设计演化：任务保存后，怎样重新读回来](../../content/articles/software-design-09-persistence/index.md) | 修改 | 简化读者前提，解释启动函数先读取任务再创建对象；明确更换存储实现后须和任务模块接起来检查真实保存、读回；说明报错前文件替换可能已完成，内存保留旧值不能恢复文件 |
| [软件设计的取舍：抽象、契约与复杂度](../../content/articles/software-design/index.md) | 修改 | 把目录摘要改成“把函数本身存起来与立即执行它”，消除同系列持久化语境下的歧义 |
| [如果 AI 研发自动化引发智能爆炸，会怎样？](../../content/articles/ai-rd-automation-intelligence-explosion/index.md) | 修改 | 添加四处明确标为“译者注”的背景说明，分别解释训练与推理、有效研发劳动力和反馈循环、相对增长率、公式两侧的读法；新增 lastmod=2026-10-17；原译文正文、数字、结论限定、16 条注释与 92 条书目均保留 |
| [读懂 Attention Is All You Need：从一次加权求和到完整 Transformer](../../content/articles/attention-is-all-you-need/index.md) | 修改 | 沿全文补足向量与矩阵、隐藏状态、注意力头、投影和点积的具体动作；解释 softmax 梯度、embedding、dropout、LayerNorm 的统计量、词表分数、损失与反向传播；解释优化器与学习率、复杂度和路径长度、n-gram 与消融；新增 lastmod=2026-10-17 |
| [从任务表到执行计划：数据库建模、SQL、事务与索引](../../content/articles/database-modeling-sql-transactions-indexes/index.md) | 修改 | 把驱动与显式事务的关系写成 Python 模块和 SQL 分别负责什么；解释索引是另外维护的有序查找结构，以及根据索引再到表中取标题的动作；新增 lastmod=2026-10-17，保留所有 SQL、Python、查询计划和运行结果 |
| [RTC 入门 01：实时通话为什么不能一直等](../../content/articles/rtc-01-why-real-time/index.md) | 保留 | 保留原因：完整时间轴、边界计算、缓冲对照、恢复反例与独立练习已让读者可推导条件变化，无需为产生改动而改写；仅做 Agent 理解自查，没有真实读者测试；未重跑模型 |
| [RTC 入门 02：声音从麦克风到扬声器](../../content/articles/rtc-02-audio-path/index.md) | 修改 | 在编码表示处解释媒体负载；把解码状态展开为保留前面解码的信息，说明后续处理依赖它及不同来源必须分开；更新 lastmod=2026-10-17 |
| [RTC 入门 03：从一段收包记录读懂 RTP](../../content/articles/rtc-03-sequence-gap/index.md) | 保留 | 保留原因：全文已经先给具体收包过程，再解释字段、统计和回绕；对照练习覆盖新条件和常见误判；仅做 Agent 理解自查，没有真实读者测试；未重跑脚本 |
| [RTC 入门 04：丢了音频包，重传、FEC 和 PLC 怎么选](../../content/articles/rtc-04-loss-recovery/index.md) | 保留 | 保留原因：三条恢复路径、前置条件、假设案例、真实实验与回退反例均已逐步解释，并明确听感与网络验证缺口；仅做 Agent 理解自查，没有真实读者测试；未重跑 Python/libopus |
| [RTC 入门 05：带宽没跟上，声音为什么越排越晚](../../content/articles/rtc-05-send-queue/index.md) | 修改 | 把门控写成距离上次提交未满规定间隔时让下一个包继续等待；改用“命令行输出”，更新 lastmod=2026-10-17 |
| [RTC 入门 06：怎样从收发记录看出延迟在增长](../../content/articles/rtc-06-delay-trend/index.md) | 保留 | 保留原因：公式、两组同记录不同绝对耗时的反例、三种曲线、时钟与乱序检查以及独立练习已覆盖主要误解；仅做 Agent 理解自查，没有真实读者测试；未重跑模型 |
| [RTC 入门 07：两端怎样找到能通话的网络路径](../../content/articles/rtc-07-connection-setup/index.md) | 修改 | 说明 ICE 凭据用于核对本轮检查请求，证书指纹用于核对握手证书与描述；展开提名的选路动作，并保留候选检查成功与实际选中的区别；把 SRTP 保护写成加密媒体内容、检查是否遭改动；更新 lastmod=2026-10-17 |
| [RTC 实时音视频入门：系列目录](../../content/articles/rtc-from-zero/index.md) | 保留 | 保留原因：目录已说明读者、前置条件、每篇可完成的任务、实验依赖和当前范围，无需重复正文术语或扩大计划；仅做 Agent 理解自查，没有真实读者测试；没有修改目录和后续方向 |
| [Rust 底层入门 01：值、地址、内存布局与资源释放](../../content/articles/rust-memory-model/index.md) | 修改 | 说明值销毁时的清理、只比较地址而不解引用，以及堆缓冲区三项记录各管什么；补足栈、CPU、UTF-8 解释，以明确假设的对齐例子说明地址倍数和字段偏移；区分字节、Unicode 标量值与可见字符，把借用有效性写成资源销毁约束；更新 lastmod=2026-10-17 |
| [主流大语言模型全景指南：比较与实战选型（2026 年 10 月更新）](../../content/posts/practical_guide_to_major_LLM/index.md) | 修改 | 提前介绍 Token、K/M 单位、上下文与最大输出、模型请求和外部工具执行的分工；解释开放权重、回归、缓存、基线、显存与量化、推理预算和采样次数；摘要改为“截至核对日期的型号”，lastmod 更新为 2026-10-17；正文核对截止日期继续为 2026-10-14 |
| [Rust 从零开始：怎么使用这套教材](../../content/tutorials/rust-00-learning-guide/index.md) | 修改 | 把类型、作用域和所有权检查写成读者可以完成的动作；说明问号的函数边界和堆缓冲区的用途 |
| [Rust 入门 01：安装工具，运行第一个程序](../../content/tutorials/rust-01-setup/index.md) | 修改 | 说明库代码的来源以及标准库提供的打印功能；将依赖解析结果展开为 Cargo 选定的依赖和具体版本 |
| [Rust 入门 02：用变量和类型表示数据](../../content/tutorials/rust-02-variables/index.md) | 修改 | 补清只读借用、遮蔽后指向的文本及读取前初始化的要求；解释编译期常量与窄化所保留的数值部分 |
| [Rust 入门 03：函数、判断和循环](../../content/tutorials/rust-03-functions/index.md) | 修改 | 明确分号丢弃结果、单元值含义及提前返回的路径；为格式化报错自查补充必要提示 |
| [Rust 入门 04：所有权、移动和借用](../../content/tutorials/rust-04-ownership/index.md) | 修改 | 说明新旧绑定的管理责任、共享借用冲突与内部可变性的适用边界；逐步跟踪再借用的数值变化，并区分移动引用和值本身 |
| [Rust 入门 05：字符串、列表和字典](../../content/tutorials/rust-05-collections/index.md) | 修改 | 解释索引移出会留下没有值的元素，因此只读场景应借用；补清切片访问范围、原计数的修改及每轮借用的结束 |
| [Rust 入门 06：结构体、枚举和 Option](../../content/tutorials/rust-06-modeling/index.md) | 修改 | 将调试实现和引用匹配规则改成编译器具体做的动作；说明查询取出引用、整数副本、守卫失败后的分支选择及预导入 |
| [Rust 入门 07：读取输入，处理可能失败的操作](../../content/tutorials/rust-07-errors/index.md) | 修改 | 解释输入对象、map_err 的调用条件及问号留下成功值和返回错误的区别；跟踪 Option 查询中的引用与复制，保留并说明年龄示例的消息粒度 |
| [Rust 入门 08：拆分模块，为程序写测试](../../content/tutorials/rust-08-projects/index.md) | 修改 | 具体说明包、crate、模块以及公开调用路径的职责；说明文件需由模块声明连接到库，收窄基础示例的依赖说明并修正章节指代 |
| [Rust 入门 09：读懂泛型、trait 和生命周期](../../content/tutorials/rust-09-traits/index.md) | 修改 | 把泛型、trait 和生命周期分别对应类型选择、方法要求与引用使用范围；解释具体类型、文本大小和编译期长度，并明确练习比较借来标题与独立字符串 |
| [Rust 从零开始：教材目录与配套源码](../../content/tutorials/rust-from-zero/index.md) | 保留 | 目录、发布状态和运行目录已经区分清楚，保留原文 |
| [Rust 入门 10：闭包和迭代器](../../content/tutorials/rust-10-iterators/index.md) | 修改 | 补入明确假设的 27 分钟例子；解释参数与捕获变量、调用约束和筛选可能检查多个输入；补充练习全部不及格时的空列表与总和 |
| [Rust 入门 11：实现待办工具的核心逻辑](../../content/tutorials/rust-11-taskbook/index.md) | 修改 | 解释成功无额外值和失败提前返回；说明 map_err 舍弃解析细节及 abc 与 0 的区别；沿查找、赋值说明失败不修改列表，并补统计条件 |
| [Rust 入门 12：保存数据，完成命令行工具](../../content/tutorials/rust-12-storage/index.md) | 修改 | 用明确假设说明坏行不会产生部分成功列表；解释字段数量、字段内容与行号闭包分工；说明损坏数据练习失败于解码而非读取 |
| [Rust 入门 13：给待办工具增加筛选、搜索和删除](../../content/tutorials/rust-13-taskbook-plus/index.md) | 修改 | 区分成功命令包装与错误消息转换；解释筛选结果仍借用原任务；补入假设编号 7、12 的删除过程和 retain 删除数量边界 |
| [Rust 入门 14：用自定义错误类型保留失败原因](../../content/tutorials/rust-14-typed-errors/index.md) | 修改 | 解释按变体判断不依赖提示文字；用已有 30 与 abc 输入走通问号两条分支；说明原因循环及一天上限与整数表示范围的区别 |
| [Rust 入门 15：用 Serde 保存 JSON，并迁移旧任务](../../content/tutorials/rust-15-serde-json/index.md) | 修改 | 说明 Serde、派生宏和 JSON 函数各自执行的动作；解释往返转换构造独立对象和必需字段检查；补清迁移分支提前返回及默认标签再次写出 |
| [Rust 入门 16：备份任务数据，恢复到新文件](../../content/tutorials/rust-16-backup/index.md) | 保留 | 全文与练习已清楚给出对象、顺序、输入输出和失败边界，保留原稿及原 lastmod，未强行润色 |
| [Rust 入门 17：用 clap 整理命令行接口](../../content/tutorials/rust-17-clap/index.md) | 修改 | 说明字段属性与命令值转换；解释恢复单独处理、先借用再取出命令字段；补清 stats 只读计数并返回文本 |
| [Rust 入门 18：请求本机 HTTP 服务，读取 JSON 响应](../../content/tutorials/rust-18-http/index.md) | 修改 | 解释派生实现把响应字段构造成课程对象；明确状态码、4097 字节、JSON 和分钟数检查顺序；区分参数有效与端口有服务监听 |
| [Rust 入门附录：三个阶段的分级练习与项目验收](../../content/tutorials/rust-practice-checkpoints/index.md) | 修改 | 补清命令借用、标题拥有及查询只读；说明坏行中止解码和总量采用 u64 受检查加法；说明问号退出辅助函数、逐项匹配继续统计并保留失败状态 |
| [Rust 入门附录：从报错位置找到问题](../../content/tutorials/rust-troubleshooting/index.md) | 修改 | 说明移动不会留下可用空字符串；解释共享访问与可变访问冲突及最后使用之后的区别；区分引用变量和被引用数据的存活，补充错误包装与 TASKBOOK_FILE |
| [智能体工程模式 10：先运行测试](../../content/translations/agentic-engineering-patterns-first-run-the-tests/index.md) | 保留 | 未改：测试入口、项目规模与后续验证的三项作用均有具体动作，结论保留作者的概率措辞 |
| [智能体工程模式 14：使用 WebAssembly 和 Gifsicle 构建 GIF 优化工具](../../content/translations/agentic-engineering-patterns-gif-optimization/index.md) | 修改 | 明确作者可能因额外工作放弃添加拖放功能；将 CORS 条件写为服务器允许跨站读取 GIF |
| [智能体工程模式 06：编程智能体如何工作](../../content/translations/agentic-engineering-patterns-how-coding-agents-work/index.md) | 保留 | 未改：从文本补全到历史重传、缓存、工具结果回传的解释顺序完整，术语紧接示例 |
| [智能体工程模式 13：交互式讲解](../../content/translations/agentic-engineering-patterns-interactive-explanations/index.md) | 保留 | 未改：从认知债务到词云放置的动画示例，已经解释对象、尝试步骤与碰撞后的动作 |
| [智能体工程模式 12：按顺序讲解代码](../../content/translations/agentic-engineering-patterns-linear-walkthroughs/index.md) | 修改 | 明确由命令直接读取代码片段，以避免模型手动转录引入幻觉或错误 |
| [智能体工程模式 16：我使用的提示词](../../content/translations/agentic-engineering-patterns-prompts/index.md) | 修改 | 改为在普通对话中构建并展示应用，保留四组提示词及作者使用原则 |
| [智能体工程模式 08：子智能体](../../content/translations/agentic-engineering-patterns-subagents/index.md) | 保留 | 未改：独立上下文、摘要回传、并行适用条件与专家角色均有具体例子和限制 |
| [智能体工程模式 07：与编程智能体协作时如何使用 Git](../../content/translations/agentic-engineering-patterns-using-git-with-coding-agents/index.md) | 保留 | 未改：先解释仓库、提交和分支，再用提示词引入同步、恢复、二分定位和历史整理，条件已明确 |
| [智能体工程模式：系列目录](../../content/translations/agentic-engineering-patterns/index.md) | 保留 | 未改：读者、6 个部分、16 篇主体与独立序言的关系清楚，目录已按原指南顺序组织 |
| [让一组并行 Claude 构建 C 编译器](../../content/translations/building-c-compiler/index.md) | 修改 | 明确一组 Opus Agent 与循环中的 Claude 主体；用具体动作说明验证程序、进度文件和测试抽样；把既有 Harness 译注的简要说明放到首次出现附近 |
| [构建多智能体系统：何时使用、如何使用](../../content/translations/building-multi-agent-systems-when-and-how-to-use-them/index.md) | 修改 | 改为调查信息、选错工具及按所需信息划分工作；解释并行等待时间与总耗时的比较；用译者注说明压缩含义和代码省略项 |
| [理解 AI Agent 评估：方法与实践](../../content/translations/demystifying-evals-for-ai-agents/index.md) | 修改 | 写清能力退步与偶然波动、模式不符导致误判和按完成程度评分；在概率计算旁补入既有独立试验假设的译者注；用译者注明确分布漂移含义，并调整开头和若干长句 |
| [塑造 2026 年软件构建方式的八大趋势](../../content/translations/eight-trends-defining-how-software-gets-built-in-2026/index.md) | 修改 | 改为工程师继续参与并集中运用专业判断；在摘要中补明开发者主体和完全托付任务的约数，简化开头与分类说明 |
| [用 Skills 与 MCP 服务器扩展 Claude 的能力](../../content/translations/extending-claude-capabilities-with-skills-mcp-servers/index.md) | 修改 | 译明既定流程、会前阅读材料、销售机会评审和相关人员资料；明确 Skill 规定信息路径、处理顺序与输出标准；把人员变动后仍需延续的流程写成直接动作，改善摘要与对照表 |
| [构建 AI Agent 的开源工具栈指南](../../content/translations/open-source-stack-for-ai-agents/index.md) | 修改 | 改善工具探寻经历、记忆与运行监测的动作表达；用译者注解释 OCR，译明 LLM 和风险投资机构；以作者个人经验重写描述并补全空摘要 |
| [如何在工程组织中规模化推广 agentic coding](../../content/translations/scaling-agentic-coding/index.md) | 修改 | 译明分阶段推广、内部推广骨干、新员工入职和斜杠命令；解释持续维护文档、投入回报及新人承担工作的关系；按原文试点人数和已有使用经验条件改写摘要 |
| [Skills 详解：与 prompts、Projects、MCP、Subagents 如何分工与配合](../../content/translations/skills-explained/index.md) | 修改 | 用操作流程、背景资料和独立子任务说明组件职责；译明系统提示词、企业客户及项目计划；用译者注解释 RAG，并说明示例名称与 Google Drive 检索内容的差异 |
| [什么是 Model Context Protocol？让 AI 连接你的世界](../../content/translations/what-is-model-context-protocol/index.md) | 修改 | 写明客户端连接、服务器提供工具与数据的分工；把 M×N 问题及 Notion 到 Linear 的资料处理写成具体动作；用译者注说明 stdio 与 SSE，改善摘要和相关直译 |
| [智能体工程模式 15：为博客转邮件简报工具添加新的内容类型](../../content/translations/agentic-engineering-patterns-adding-a-new-content-type/index.md) | 修改 | 明确作者用提示词完成工作的动作，改写版本发布与描述字段的说明；把类型映射改为对应关系，保留推测语气 |
| [智能体工程模式 11：让智能体执行手动测试](../../content/translations/agentic-engineering-patterns-agentic-manual-testing/index.md) | 修改 | 明确智能体执行、调用和检查代码的动作；把界面变化与测试更新的因果拆开，说明记录实际输出为何有助于核对结果 |
| [智能体工程模式 05：反模式——应该避免的做法](../../content/translations/agentic-engineering-patterns-anti-patterns/index.md) | 修改 | 保留作者对新领域的语气，直接解释反模式；把额外工作明确为亲自审查和验证代码，保留全部 PR 条件 |
| [智能体工程模式 04：AI 应该帮助我们写出更好的代码](../../content/translations/agentic-engineering-patterns-better-code/index.md) | 修改 | 改写重构任务、后台执行和方案发现的句子；把结尾落实为交付功能时改善代码质量，保留原作者对成本与能力的强判断 |
| [智能体工程模式 02：如今，编写代码的成本已经很低](../../content/translations/agentic-engineering-patterns-code-is-cheap/index.md) | 修改 | 用项目规划和日常开发说明时间取舍，明确收益与成本的权衡；把回归测试的职责融入原有解释，没有添加新的质量标准 |
| [智能体工程模式 03：积累你已经掌握的实现方法](../../content/translations/agentic-engineering-patterns-hoard-things-you-know-how-to-do/index.md) | 修改 | 明确未运行的主体为 iPhone 应用；说明积累的示例交给智能体参考，以及负责搜索的子智能体如何带回信息 |
| [智能体工程模式·序言：写作计划](../../content/translations/agentic-engineering-patterns-introduction/index.md) | 修改 | 拆开项目介绍与目的，明确持续更新章节的主体；保留 Vibe Coding 对比、作者写作原则、数量与全部历史日期 |
| [智能体工程模式 09：红灯／绿灯测试驱动开发](../../content/translations/agentic-engineering-patterns-red-green-tdd/index.md) | 保留 | 全文已清楚交代先写测试、观察失败、实现到通过及跳过红灯的风险，保持原稿 |
| [智能体工程模式 01：什么是智能体工程？](../../content/translations/agentic-engineering-patterns-what-is-agentic-engineering/index.md) | 修改 | 明确工程师提供工具、描述问题、验证并修改的动作；说明经验由人主动写入指令和框架，保留原作者对模型学习的判断与前提 |
| [Prompt engineering 最佳实践](../../content/translations/best-practices-for-prompt-engineering/index.md) | 修改 | 用提示、智能体方案和改进结果等具体说法重写相关段落；把 one-shot 与 few-shot 已有的数量解释放到首次出现处，补全 LLM 与 CoT 的中文或英文对应；改写格式控制、技巧组合、排错和任务拆分说明，保留全部示例、模型范围和权衡 |
| [超越权限提示：让 Claude Code 更安全、更自主](../../content/translations/beyond-permission-prompts-making-claude-code-more-secure-and-autonomous/index.md) | 修改 | 以明确标记的译者注解释提示注入，避免混入原作者陈述；说明进程把请求交给代理、代理限制域名并请用户确认的过程；将抽象安全措辞和英文普通名词改为自然中文，保留原文安全保证及限制范围 |
| [构建响应式网页布局](../../content/translations/build-responsive-web-layouts/index.md) | 修改 | 以译者注解释三个贯穿全文的布局术语；改写测试、工具类、跨样式表重构和回归风险的说明；澄清问题出现的原因与条件，保留原有设备、尺寸、代码和安装方式 |
| [用 Skills 构建智能体：为专业化工作装备智能体](../../content/translations/building-agents-with-skills-equipping-agents-for-specialized-work/index.md) | 修改 | 说明 Skills 记录任务步骤、文件可由现有工具管理，以及模型按需读取资料；用后文已有职责提前解释 MCP 连接工具和数据源，说明代码作为执行接口的过程；改写多个专业应用段落的动作，保留四层架构、全部 token 数量和专业例子 |
| [构建有效的 Agent 自动化](../../content/translations/building-effective-agent-automations/index.md) | 修改 | 明确应用准备步骤与提前、延迟运行对固定窗口的影响；把沙箱本身的记忆与外部持久存储区分清楚，说明占位符不含真实凭据；改写发布、操作限制和预算暂停的后果，保留游标与台账更新条件 |
| [AI 智能体的常见工作流模式——以及何时使用它们](../../content/translations/common-workflow-patterns-for-ai-agents-and-when-to-use-them/index.md) | 修改 | 用步骤顺序、交接与输入输出来解释工作流和顺序依赖；明确并行结果如何汇总，评估方与生成方如何配合及何时停止；保留三类模式的使用与避免条件、成本比较和单智能体基线 |
| [用 Agent Skills 为真实世界装备智能体](../../content/translations/equipping-agents-for-the-real-world-with-agent-skills/index.md) | 修改 | 用操作步骤、方法与组织背景说明 Skill 保存什么；明确文件头部、按需查读参考资料，以及把经验写入说明和代码；沿用文内已有解释改写脚本结果与分文件建议，保留加载层次和安全要求 |
| [面向长期应用开发的 Harness 设计](../../content/translations/harness-design-long-running-apps/index.md) | 修改 | 把已有架构内容用译者注提前解释，明确与原作者陈述的区别；把交接、评分、验收约定和缺陷报告改为具体动作；围绕能可靠独立完成的任务范围重写评估器价值段，保留 4.5 与 4.6 的条件差异和全部实验数字 |
| [我们如何在两周内将 claude.ai 的速度提升至 3 倍](../../content/translations/how-we-made-claude-ai-faster/index.md) | 修改 | 将原有 p75 与速度比较范围说明以译者注提前呈现；明确用户操作监测、上限只能收紧、切换时保留编辑器和布局偏移的区域与阶段；重写静态到 React 交接和流式渲染的重复处理过程，保留所有测量条件、实验数字和人的审批责任 |
| [快速优化代码性能：从被动分析到主动优化](../../content/translations/optimize-code-performance-quickly/index.md) | 修改 | 明确性能分析、基准测试、跨文件修改和防止性能退步的动作；以译者注解释 N+1 查询过程、ORM 和预加载，原作者能力陈述另起段保留；把事故分诊译为初步判断与分类，保留原有时间指标，未扩大为解决事故 |

## 执行记录

各组按正文或译文任务分支执行 humanizer、humanizer-zh，必要时用 research-explainer 核对解释与来源。检查与修订均限定在用户授权的已发布稿件；已有用户工作和草稿保留。理解自查的问题为：解决什么具体问题、谁在什么条件做什么、改变输入或条件后结果如何变化。
