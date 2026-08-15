+++
title = "从代码补全到规范驱动：AI Coding Agent 软件工程的演进与 DeepSeek Harness"
date = 2026-08-16T02:10:20+08:00
lastmod = 2026-08-16T02:10:20+08:00
draft = false
author = "Hex4C59"
description = "从自动程序设计、代码补全和对话式生成讲到仓库级 Coding Agent，并以固定 commit 的 DeepSeek Harness 为例分析文档、Agent 指令、测试、Review、CI 与权限边界如何共同约束软件工程 Agent。"
summary = "AI Coding Agent 的难点不只在生成代码，还在于理解项目事实、执行受限操作、验证真实结果和划分责任。本文回顾这条演进路径，并用 DeepSeek Harness 的源码、文档、测试与 CI 建立一张可核验的工程证据图。"
tags = ["Agent", "Coding Agent", "Software Engineering", "DeepSeek Harness", "Repository-level Agent", "Testing"]
categories = ["Agent"]
series = ["DeepSeek Harness"]
series_order = 1
difficulty = "intermediate"
article_type = "concept"
topics = ["coding-agent", "repository-level-agent", "software-engineering", "tool-use", "testing", "security"]
frameworks = ["DeepSeek Harness", "Cordis", "TypeScript"]
ShowToc = true
+++

## 这篇文章要解决什么问题

本文面向有 Git、测试和 Continuous Integration（CI）基础的软件开发者，也面向需要评估 AI Coding Agent 的技术负责人。读者只需要了解大语言模型（Large Language Model，LLM）的基本概念，不需要先使用过某个具体 Agent。本文要回答的问题是：当模型从编辑器里补全几行代码，发展到可以浏览仓库、修改多个文件、执行命令和反复修复时，项目约束、验证机制和责任边界为什么会成为系统的一部分。

本文的历史范围从早期自动程序设计和程序综合思想开始，截止到 2026 年 8 月 16 日。这里的“历史”只讨论 AI 辅助软件开发及其相邻的工程基础设施，不把编译器、集成开发环境（Integrated Development Environment，IDE）或静态分析器都重新命名为 AI。文章的案例研究固定在 [DeepSeek Harness 的 `master` 分支 commit `47f943859bef60e4160492346772ded9b24f765a`](https://github.com/deepseek-ai/deepseek-harness/tree/47f943859bef60e4160492346772ded9b24f765a)，分析日期为 2026-08-16。

读完本文，读者应当能够区分代码补全、对话式代码生成、Coding Agent 和仓库级 Agent 工程，解释它们各自减轻的劳动与新增的风险；能够从 DeepSeek Harness 的文档、源码、测试和 CI 中复核本文的判断；还能够为自己的仓库设计一个最小的、可审查的文档优先流程。本文不会把“文档优先”“规范驱动”或“Agent 软件工程”写成 DeepSeek Harness 的官方术语。这些词是本文为了比较不同工程材料而采用的分析框架。

## 先给结论

这项研究得到的结论不是“模型越强，软件工程就越自动化”，而是下面四个更窄的判断。

1. **AI 辅助开发的演进改变了交互单位和反馈回路。** 代码补全处理光标附近的片段，对话式助手处理一次问题与回答，Coding Agent 处理一组工具调用，仓库级 Agent 工程则必须处理项目事实、持久状态、权限、测试、Review 和发布检查。后一阶段增加的不是一个更长的 Prompt，而是一组新的工程责任。
2. **项目约束只有进入 Agent 可见且可检查的路径，才会影响行为。** DeepSeek Harness 的 `AGENTS.md`、架构文档和 Agent preset 共同说明了约束；`dsh-agent-instructions` 会将工作区指令加载成持久的用户消息，并在文件工具成功触达新范围后刷新上下文。这是仓库中可以直接观察到的实现，不等于所有 Coding Agent 都会自动读取文档。
3. **测试、CI 和 Review 的职责不同。** 测试把部分行为变成可重复的断言，CI 在干净环境、多个运行时或发布路径上重复检查，Review 处理测试难以表达的设计意图、权限风险、兼容性和业务语义。DeepSeek Harness 的测试规范明确要求验证真实世界，而不是只相信 Agent 的自我报告；它也明确把测试描述为行为检查，而不是正确性的形式化证明。
4. **DeepSeek Harness 是一个适合观察这些关系的开发预览项目，但不是中心假设的证明。** 固定 commit 显示了插件式架构、会话日志、工具执行流水线、工作区指令加载、审批和沙箱等材料。本文没有在真实模型上执行仓库级任务，也没有得到成功率、成本或延迟数据，因此不能据此声称它解决了 Agent 软件工程的全部问题。

## 术语、范围与证据方法

### 四个容易混淆的对象

本文按“模型拥有的环境和反馈”区分四个对象。

| 对象 | 模型通常看到什么 | 模型可以做什么 | 人仍然负责什么 |
|---|---|---|---|
| 代码补全 | 光标附近的代码、编辑器缓冲区和少量文件上下文 | 接受、拒绝或修改一段候选代码 | 判断意图、运行检查、合并修改 |
| 对话式代码生成 | 用户问题、对话历史和显式粘贴的代码 | 生成解释、代码片段或补丁文本 | 把文本放入正确仓库，确认版本和依赖，验证结果 |
| Coding Agent | 任务、系统提示、工具 Schema、工具结果和当前工作区 | 读取文件、编辑文件、运行命令、调用测试，并根据结果继续行动 | 授权操作范围、审核 diff、处理外部影响和最终合并 |
| 仓库级 Agent 工程 | 以上内容，加上架构文档、分层指令、配置、持久日志、质量门和发布规则 | 在项目约束和预算内执行多步任务，留下可追踪证据 | 维护事实来源、定义验收标准、决定风险接受和最终责任 |

“仓库级”不表示模型一次读完整个仓库，也不表示它拥有仓库的全部权限。它表示任务的正确性依赖跨文件关系、构建入口、测试命令、配置和维护规则；Agent 因而需要一个能持续补充上下文并接受外部验证的工作流。

### 历史阶段为什么这样划分

本文使用“交互单位、反馈回路、质量控制和责任边界”作为分期依据，而不是单纯按模型参数量分期。早期程序综合主要讨论如何从规格构造程序；IDE、CASE 和静态分析属于传统软件工程基础设施；机器学习后来把代码库当作可学习的结构和语言；代码模型把生成粒度推进到函数和文件；Agent 再把生成放进一个可以执行动作、观察结果并继续决策的环境。每次变化都解决了一类重复劳动，同时把新的前提和失败模式交给下一阶段。

### 资料调研记录

下表记录本文使用的主要外部资料。访问日期均为 2026-08-16。论文中的实验数字只用于说明当时任务和测量的边界，不用于推断 DeepSeek Harness 的性能。

| 来源 | 作者或组织、发布日期 | 类型与支撑结论 | 局限 |
|---|---|---|---|
| [Toward automatic program synthesis](https://doi.org/10.1145/362566.362568) | Zohar Manna、Richard Waldinger，1971-03 | 原始论文；说明可以用定理证明从规格中抽取递归和迭代程序，代表早期程序综合思路。 | 以形式规格和数学证明为前提，不描述现代仓库、依赖和交互式开发流程。 |
| [No Silver Bullet: Essence and Accidents of Software Engineering](https://doi.org/10.1109/MC.1987.1663532) | Frederick P. Brooks Jr.，1987-04 | 原始论文；用于区分软件工程中的本质复杂度和工具能够消除的偶然复杂度。 | 不是 AI 辅助开发实验，也不提供 Coding Agent 的实现方案。 |
| [On the naturalness of software](https://doi.org/10.1109/ICSE.2012.6227135) | Abram Hindle、Earl T. Barr、Zhendong Su、Mark Gabel、Premkumar Devanbu，2012-06 | 原始论文；说明软件具有可用统计语言模型描述的“自然性”，为代码检索和预测提供学习视角。 | 重点是统计规律，不等于模型理解了程序语义或项目意图。 |
| [A Survey of Machine Learning for Big Code and Naturalness](https://doi.org/10.1145/3212695) | Miltiadis Allamanis、Earl T. Barr、Premkumar Devanbu、Charles Sutton，2018-07-31 | 综述；覆盖代码搜索、表示、生成、程序分析等机器学习方向，帮助确定历史范围。 | 发表早于当前 LLM Agent，不能直接代表今天的产品能力。 |
| [CodeBERT: A Pre-Trained Model for Programming and Natural Languages](https://arxiv.org/abs/2002.08155) | Zhangyin Feng 等，2020-02-19 | 原始论文；展示预训练代码模型对自然语言代码搜索和文档生成的支持。 | 评测任务是模型表示和下游任务，不是可修改仓库的执行循环。 |
| [Evaluating Large Language Models Trained on Code](https://arxiv.org/abs/2107.03374) | Mark Chen 等，2021-07-07 | 原始论文；介绍 Codex 和 HumanEval，并同时报告长链操作、变量绑定等限制。 | HumanEval 由函数级题目组成，不能代替真实仓库任务评测。 |
| [Introducing GitHub Copilot: your AI pair programmer](https://github.blog/news-insights/product-news/introducing-github-copilot-ai-pair-programmer/) | GitHub、Nat Friedman，2021-06-29 | 官方产品资料；记录 Copilot 技术预览的交互定位，即根据当前代码给出整行或函数建议。 | 产品发布材料不是独立评测，不能单独支撑生产质量或效率结论。 |
| [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) | Shunyu Yao 等，2022-10-06 | 原始论文；说明把推理轨迹和外部行动交替组织，可以获得信息、更新计划并处理异常。 | 实验包含问答和交互环境，不专门针对代码仓库。 |
| [SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770) | Carlos E. Jimenez 等，2023-10-10 | 原始评测论文；把真实 GitHub issue、代码库和对应修改作为评测输入，明确了仓库级任务的多文件和长上下文要求。 | 初始数据集覆盖 12 个 Python 仓库；结果随任务集合、模型和修复判定方法变化。 |
| [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793) | John Yang、Carlos E. Jimenez 等，2024-05-06 | 原始论文；把文件编辑、仓库导航、程序执行组织成 Agent-Computer Interface（ACI），并在 SWE-bench 等任务上测量。 | 论文中的 pass@1 结果绑定具体模型、接口和 benchmark 版本，不能外推到其他 Agent。 |
| [OpenHands: An Open Platform for AI Software Developers as Generalist Agents](https://arxiv.org/abs/2407.16741) | Xingyao Wang 等，2024-07-23 | 原始项目论文；展示可写代码、调用命令行、浏览网页、使用沙箱和评测框架的平台化方向。 | 平台和评测集合持续变化，论文中的贡献者和任务数量不是本地仓库的稳定事实。 |

这些资料之间不存在一条可以简单写成“模型越来越强，所以自然产生 Agent”的单线因果链。Manna 和 Waldinger 讨论的是规格到程序的构造，Hindle 和 Allamanis 讨论代码的统计结构，Codex 和 Copilot 把交互粒度推向代码建议，ReAct 说明行动与观察的反馈回路，SWE-bench 则把问题放回真实 issue 和仓库。它们回答的是不同问题，本文只把它们放在同一张分析表中比较。

## AI 辅助软件开发的历史演进

### 总览表

| 阶段 | 大致时间 | 代表技术或系统 | 开发者的交互单位 | 主要解决的问题 | 新暴露或引入的问题 | 质量控制方式 |
|---|---|---|---|---|---|---|
| 1. 自动程序设计与程序综合 | 1950s–1970s | 编译器、自动程序设计思想、定理证明式程序综合 | 形式规格、算法性质或受限领域问题 | 减少从规格到实现的手工推导，探索“描述要做什么而不是逐句写什么” | 规格难写，搜索和证明可能爆炸，构造结果依赖形式化程度 | 证明、等价变换、编译和人工检查；这一阶段不应整体称为 AI 产品 |
| 2. 软件工程自动化基础设施 | 1970s–2000s | IDE、CASE、代码检索、编译器诊断、静态分析、重构工具 | 项目、文件、符号和一次编辑操作 | 减少导航、重命名、构建、诊断和重复编辑的机械劳动 | 工具配置与项目规则分散，误报和漏报需要解释，工具不知道业务意图 | 编译、类型检查、静态规则、单元测试、Review；主要是传统工程基础设施 |
| 3. 机器学习与 Big Code | 2000s–2010s | n-gram 代码模型、代码搜索、程序分析模型、代码表示学习 | 代码查询、候选片段、AST/调用关系、分类或排序任务 | 从大规模代码中学习相似性、惯用法和缺陷信号，降低搜索和 triage 成本 | 训练库偏差、语义相似不等于行为相同、数据泄漏和可解释性问题 | 检索 precision/recall、分类指标、静态分析、人工抽检和测试 |
| 4. 神经代码模型与代码补全 | 2017–2021 | DeepCoder、CodeBERT、Codex、Copilot 技术预览 | 光标、函数、docstring 或局部文件上下文 | 生成语法完整的函数、调用样例、测试草稿和 API 使用方式 | “看起来合理”但不正确的代码、上下文不足、依赖版本错误、安全与许可证风险 | 编译、lint、单元测试、HumanEval 等函数级评测和开发者接受/修改 |
| 5. 对话式代码助手 | 2022–2023 | 聊天式 LLM 助手、代码解释和补丁生成 | 一次自然语言问题、对话历史和用户粘贴的代码 | 把搜索、解释、方案比较和代码生成放到同一对话，减少切换工具的认知负担 | 对话状态不是仓库真源，模型会编造 API、忽略隐含约束，执行责任容易模糊 | 用户复制后运行测试、检查版本、审查 diff；质量控制仍在对话之外 |
| 6. 能够调用工具的 Coding Agent | 2022–2024 | ReAct 类循环、终端/文件工具、SWE-agent 等 ACI | 一个任务加上一轮轮工具调用及其结果 | 让模型探索环境、编辑文件、运行测试并根据反馈迭代 | 工具选择错误、循环、部分修改、权限过大、输出截断、失败恢复和成本不可控 | 工具 Schema、超时/取消、沙箱、轨迹日志、测试、补丁检查和人工批准 |
| 7. 仓库级 Agent 工程 | 2023–2026 | SWE-bench、OpenHands、项目级 Agent preset、文档和 CI 约束 | 仓库任务、项目事实、持久会话、策略和验收证据 | 把跨文件理解、工具执行、测试和协作纳入一个可审查工作流 | 指令过时或冲突、上下文预算、测试盲区、权限/密钥/网络风险、责任和变更归属不清 | 文档与源码、Agent 指令、单元/e2e/snapshot、CI、Review、日志和恢复策略的分层组合 |

### 1. 从“自动写程序”到“用规格构造程序”

早期自动程序设计和程序综合并不是今天意义上的 Coding Agent。它们研究的是编译、受限领域语言、数学规格和证明如何减少手工编程。Manna 和 Waldinger 的[原始论文](https://doi.org/10.1145/362566.362568)把规格诱导出的定理作为程序构造依据，并讨论从证明中抽取递归或迭代程序的方式。这里的交互单位不是“请修改这个 Git 仓库”，而是规格和可证明的性质。

相比纯手工实现，这条路线减少了算法推导和部分代码书写。它新增的前提也很强：开发者必须表达足够精确的规格，系统必须能在可接受的搜索空间内完成证明或变换。规格不完整时，系统不会自动知道业务意图；证明搜索失败时，开发者仍要回到问题建模。于是工程实践逐渐把更多精力放在语言、编译器、模块化和开发工具上，而不是等待通用程序综合解决全部编程问题。

### 2. IDE、CASE 和静态分析：主要是工程基础设施，不是 AI

集成开发环境、Computer-Aided Software Engineering（CASE）工具、代码检索、重构和静态分析器主要解决的是“人已经知道要改什么，但完成这件事很费手”的问题。符号跳转、批量重命名、增量编译、类型错误定位和规则检查，把交互单位从单行文本提升到文件、符号和项目。

这一步降低了导航和机械编辑的认知负担，却没有让工具自动获得产品意图。静态分析可以发现某类数据流问题，但通常不能决定一个兼容性变化是否值得引入；重构工具可以保证一组语法变换，却不保证业务行为符合预期。Brooks 对软件工程本质复杂度和偶然复杂度的区分，仍然适合用来提醒我们：工具可以削减一部分偶然复杂度，但不等于消除了需求、设计和协作的本质复杂度（见 [原始论文](https://doi.org/10.1109/MC.1987.1663532)）。

这一阶段依赖显式的语法树、类型系统、构建入口和规则配置，质量控制也主要由编译器、静态规则、测试和人工 Review 完成。它为后续学习代码提供了结构化数据和可执行反馈，但没有提供一个能够理解自然语言任务并自主组合这些工具的决策者。

### 3. 机器学习把代码库变成可学习的“Big Code”

2000 年代到 2010 年代，机器学习开始用于代码搜索、缺陷预测、程序分析、代码表示和生成。Hindle 等人观察到软件具有统计上的“自然性”，因此可以用语言模型捕捉开发者反复使用的局部模式（见 [原始论文](https://doi.org/10.1109/ICSE.2012.6227135)）。Allamanis 等人的[综述](https://doi.org/10.1145/3212695)则把这一时期的研究放在 Big Code 框架下，覆盖代码搜索、表示、生成和分析等多个任务。

相对于纯规则工具，学习方法可以从大量仓库中发现开发者没有手写出来的相似性和惯用法，减少“我知道大概想找什么，但不知道关键词”的搜索负担。它依赖更大的前提：训练语料具有代表性，代码和标签之间存在可学习的关系，评测切分不会让重复代码造成数据泄漏。

新的错误模式是语义错配。一个代码片段可能在词法和结构上相似，却读取了不同配置、承担了不同权限或依赖不同的调用顺序。模型给出的排序、分类或缺陷信号还需要静态规则、人工抽检和测试确认。这些限制推动研究从检索相似片段进一步走向代码的联合表示和生成。

### 4. 神经代码模型与代码补全：把预测粒度推向函数

CodeBERT 将编程语言和自然语言放在同一个预训练框架中，论文报告了自然语言代码搜索和文档生成任务上的结果（见 [论文](https://arxiv.org/abs/2002.08155)）。Codex 则直接研究了用代码训练的大语言模型的 Python 代码生成能力，发布了 HumanEval 作为函数级功能正确性评测；论文也明确记录了长链操作和变量绑定方面的困难（见 [论文](https://arxiv.org/abs/2107.03374)）。GitHub 在 2021 年发布 Copilot 技术预览时，把产品交互描述为根据当前代码建议整行或整个函数（见 [官方发布说明](https://github.blog/news-insights/product-news/introducing-github-copilot-ai-pair-programmer/)）。

这一阶段相对上一阶段的改进是生成粒度和自然语言接口：开发者可以从光标、函数签名或 docstring 出发得到一个候选实现，而不必先把问题翻译成检索关键词。它减少了模板代码、API 胶水和简单测试草稿的书写劳动。

但函数级生成也把“可编译”与“正确”分开了。模型可能使用已经变化的 API，漏掉项目约定，或者生成对安全边界不合适的代码。训练数据、上下文窗口、语言版本和依赖版本成为新的前提；编译、lint、单元测试和人工审查成为不可省略的反馈回路。只在编辑器局部上下文中生成的系统，遇到跨文件约束时自然会暴露上下文不足。

### 5. 对话式代码助手：交互单位从光标变成问题

对话式代码助手把代码解释、方案比较、补丁生成和测试建议放入同一轮自然语言对话。它比单纯补全更容易处理“为什么报错”“有哪几种设计”“请解释这段代码”等问题，也让开发者能够逐步补充背景，减少在搜索引擎、文档和编辑器之间切换的次数。

它解决的是交互成本，而不是仓库事实问题。对话历史可以保留上下文，却不会自动成为构建系统、配置文件或当前分支的权威状态；用户没有粘贴的约束，模型通常无法确认。常见的新错误包括虚构 API、忽略未显示的配置、把一个合理的示例误当成可直接合并的补丁，以及开发者误以为“已经在聊天中解释过”就等于项目已经记录了该决定。

因此这一阶段仍把执行权和验证权留给人。开发者需要把输出放回真实仓库，运行真实命令，查看 diff，并对未覆盖的设计风险负责。对话式助手为下一阶段准备了自然语言任务接口，但还缺少受控行动和稳定的观察结果。

### 6. Coding Agent：模型进入工具反馈回路

ReAct 论文把推理轨迹和外部行动交替组织起来：行动可以获取信息，观察结果可以帮助模型更新计划并处理异常（见 [原始论文](https://arxiv.org/abs/2210.03629)）。在软件工程任务中，SWE-agent 进一步把文件创建、编辑、仓库导航和程序执行组织成面向 Agent 的接口，并在 SWE-bench 等任务上评估这种接口（见 [项目论文](https://arxiv.org/abs/2405.15793)）。

Coding Agent 相对于对话助手的关键变化不是“会写更多代码”，而是模型可以在真实工作区中执行动作并看到动作结果。交互单位变成“任务 + 工具调用 + 工具返回值”，反馈回路从“用户判断回答”变成“模型读取文件、修改文件、运行测试、解释错误并继续”。这减少了开发者手动搬运代码、执行命令和把错误重新描述给模型的重复劳动。

新的前提包括工具 Schema、路径和命令权限、超时与取消、输出大小、状态持久化、模型调用预算和失败恢复。如果工具允许任意命令却没有边界，Agent 的能力也会放大误操作的影响；如果只返回截断的错误，Agent 可能沿着错误方向重复尝试；如果没有硬性结束条件，失败循环会同时增加成本和文件变更风险。

质量控制因此从“看一段代码”扩展为工具结果、工作区状态、测试结果、最终 diff 和执行日志。SWE-bench 的任务定义很能说明这一步的难度：问题来自真实 issue 和对应 Pull Request，修复经常需要协调多个函数、类和文件，并与执行环境交互（见 [评测论文](https://arxiv.org/abs/2310.06770)）。它同时也说明了边界：基准测试测量的是特定任务集合中的修复结果，不是所有真实工程的可靠性。

### 7. 仓库级 Agent 工程：增加项目约束和责任层

仓库级 Agent 工程处理的是 Coding Agent 单独无法保证的部分：项目事实从哪里来，模型看到哪些事实，哪些动作必须经过权限策略，什么结果算通过，谁检查无法自动化的判断，以及失败后如何恢复。OpenHands 把代码编辑、命令行、网页、沙箱、多个 Agent 和评测放到一个平台中（见 [项目论文](https://arxiv.org/abs/2407.16741)）；这类系统开始把“模型循环”之外的环境和治理也视为产品表面。

SWE-bench 把仓库级任务变成了可测量的问题集合，但 DeepSeek Harness 展示的是另一种材料：它把模型、工具、会话日志、文件系统、Shell、沙箱、审批、Agent preset 和工作流拆成可组合的插件。该仓库的 README 将自己定位为由 DeepSeek AI 开发的开源 agent harness，并明确标注为 developer preview；这足以支持“它是一个观察 Agent 工程约束的案例”，不足以支持“它代表了行业最佳实践”。

这一阶段减少的是跨工具协调和重复的上下文搬运，同时引入最高层次的风险：文档可能过时，指令可能冲突，权限可能过大，测试可能不覆盖设计语义，模型调用可能昂贵且延迟高，部分修改可能留在工作区，而责任人却误以为 Agent 已经“完成”。因此下一节不把仓库的材料描述成一条神奇的自动化链，而是逐项检查每个材料实际承担了什么。

## 从代码生成到仓库级 Agent：系统边界发生了什么

可以把系统边界的变化写成下面这条信息流。它是本文的抽象模型，不是 DeepSeek Harness 官方命名的流程图。

```text
维护者维护事实来源和任务验收标准
        |
        v
AI Coding Agent 读取架构、开发指南、Agent 指令和当前仓库
        |
        v
Agent 分析任务，形成计划，声明将修改的范围和验证方式
        |
        v
工具调用经过权限、审批、沙箱、超时和取消策略
        |
        v
Agent 修改代码并运行针对性测试，结果和过程写入可观察记录
        |
        v
完整检查、CI 和构建验证可执行的部分
        |
        v
维护者 Review diff、设计判断、业务语义和风险
        |
        v
接受、修改、回滚或继续迭代，并同步受影响的文档和约束
```

代码补全主要位于这条链的“候选代码”位置；对话助手主要位于“自然语言解释和候选方案”位置；Coding Agent 扩展到“工具调用和观察”；仓库级 Agent 工程必须把链条两端的维护者责任、事实来源和发布门也纳入设计。把最后一层压缩成一个更长的 system prompt，会遗漏权限、持久化、CI 和 Review 的职责。

## DeepSeek Harness 是什么

### 公开定位与研究基线

[DeepSeek Harness README](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/README.md) 将 `dsh` 定义为 DeepSeek AI 开发的开源 agent harness，核心架构是“everything is a plugin”，底层使用 Cordis。README 同时把项目标为 developer preview，并警告会有兼容性破坏。根目录 `package.json` 的版本是 `0.1.0-rc.5`，`packageManager` 是 `pnpm@11.7.0`；固定 commit 没有对应的 Git tag，因此本文不用“最近稳定版本”这个更强的说法。

本文没有把 DeepSeek Harness 当成一个模型 benchmark，也没有把“agent harness”解释成官方宣称的自主软件工程师。本文只研究它如何组织模型循环周围的工程约束。下面的记录把已验证、未验证和推断分开。

| 项目 | 本文基线 |
|---|---|
| 仓库 | [`deepseek-ai/deepseek-harness`](https://github.com/deepseek-ai/deepseek-harness) |
| 分支、commit | `master`，`47f943859bef60e4160492346772ded9b24f765a`；提交信息为 `release: dsh@0.1.0-rc.5 & publish the dsh family publicly` 的合并提交；截至分析时没有 tag |
| 分析日期 | 2026-08-16 |
| 操作系统 | Linux x86_64，内核 `7.0.0-28-generic` |
| 运行时 | Node.js `v22.23.1`，Python `3.12.3`；Hugo 版本属于本文所在博客，不是 Harness 运行前提 |
| 依赖 | 仓库锁定 `pnpm@11.7.0`；实际安装使用 pnpm `11.7.0`，根包版本 `0.1.0-rc.5` |
| 模型和模型配置 | 没有调用模型；`DEEPSEEK_API_KEY` 未设置，没有验证 `DEEPSEEK_BASE_URL`、provider、model 或真实 API 请求 |
| 关键配置 | 使用仓库默认测试配置；没有修改 preset、沙箱、审批、遥测或模型配置 |
| 实际执行 | `git ls-remote`、浅克隆、`pnpm install --frozen-lockfile`、`pnpm exec vitest run packages/core/agent-loop/tests/loop.spec.ts`、`pnpm run typecheck`；安装和类型检查均成功，聚焦测试 54/54 通过 |
| 未验证部分 | Web UI、headless/ACP 真实入口、真实 DeepSeek API、需要密钥的 e2e、完整覆盖率、跨 macOS/Windows 的沙箱、E2B/远程后端、性能、成本、延迟和真实仓库修复成功率 |

安装时 pnpm 报告了若干 workspace 循环依赖和当前平台跳过 `linux-arm64` 原生包的警告。这些警告没有阻止锁文件检查、安装、聚焦测试或类型检查；它们也不应被改写成“所有平台都已验证”。

### 目录与组合边界

根目录 [`AGENTS.md`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/AGENTS.md) 将仓库分为 `vendor/`、`packages/`、`apps/`、`examples/`、`docs/` 和 `.agents/notes/` 等区域，并要求修改 `packages/` 前先读架构文档。`packages/core` 提供 session、system prompt、tools、agent 和 agent-loop 等产品主干；Shell、filesystem、sandbox、interaction、credentials、subagent、workflow 等能力位于其他包组。

架构文档的核心判断是：Cordis 插件向共享上下文贡献服务、类型化事件和可逆副作用；模型适配器、工具注册表、会话日志和 Agent loop 都是插件。因此“插件式”首先表示可替换的组合方式，不能自动推出“每个插件都拥有独立安全沙箱”。是否隔离还取决于加载的 provider、preset、realm 和外部运行环境。

`docs/architecture.md` 将可扩展点分为三类：持久的 session 事件、携带活跃 Agent 的 `agent/*` 事件，以及附着在能力 seam 上的事件。一个 step 是一次模型请求加上它调用的工具，一个 turn 可以包含多个 step。这个划分把“模型看到了什么”和“Agent 当前正在做什么”分开：前者需要能够从 session log 重建，后者是实时控制和状态。

## 文档、规范、Agent、测试、Review 和 CI 如何协作

### 证据表：每种工程材料负责什么

下表只列出对本文论证直接有用的材料。链接全部固定到研究 commit；“证据类型”区分仓库事实、运行时实现、测试规范和作者分析。

| 工程材料 | 仓库路径 | 它规定或实现了什么 | 证据类型 | 对文章结论的支持 |
|---|---|---|---|---|
| 产品 README | [`README.md`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/README.md) | 说明 `dsh` 的开源定位、Cordis 插件架构、developer preview 状态和源码运行命令。 | 仓库事实 | 不能把项目简介或预览版状态写成稳定能力或 benchmark 结果。 |
| 根 Agent 指令 | [`AGENTS.md`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/AGENTS.md) | 规定目录、命令、密钥处理、测试选择、文档同步、插件约束和 vendoring 规则。 | Agent 指令 | 说明约束被写成 Agent 可读取的操作材料，而不是只存在于口头经验中。 |
| 文档 Agent 指令 | [`docs/AGENTS.md`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/docs/AGENTS.md) | 规定文档层级、事实单一归属、引用、预算和 machine-checkable 链接。 | 文档规范 | 说明文档本身也有维护边界，文档优先不等于文档永远正确。 |
| 架构文档 | [`docs/architecture.md`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/docs/architecture.md) | 描述插件组合、profile/bundle、turn/step、session log、capability seam 和扩展入口。 | 架构事实与设计意图 | 让 Agent 或维护者先理解系统边界，再决定改 loop 还是增加插件。 |
| 开发与贡献指南 | [`docs/development.md`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/docs/development.md)、[`CONTRIBUTING.md`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/CONTRIBUTING.md) | 规定 Node/pnpm 前置条件、typecheck、构建、文档同步、CI 组织；贡献指南在该快照中说明暂不接受外部 PR。 | 开发流程事实 | 说明“维护者 Review”有权限和组织前提，不能假定公开仓库自动接受所有 Agent 产物。 |
| Agent preset 与指令加载器 | [`apps/cli/config/agent-presets/standard/agent.cordis.yml`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/apps/cli/config/agent-presets/standard/agent.cordis.yml)、[`packages/context/agent-instructions/README.md`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/packages/context/agent-instructions/README.md) | standard preset 挂载 `dsh-agent-instructions`；插件读取 `$DSH_HOME/AGENTS.md` 与项目根到 cwd 的指令文件，将 baseline 放入持久历史，并在成功的文件工具结果后观察嵌套指令变化。 | 运行时实现与配置 | 说明“文档进入模型上下文”是一个有生命周期、大小预算和刷新规则的实现，不是自动发生的魔法。 |
| Prompt 与 session | [`packages/core/system-prompt/src/index.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/packages/core/system-prompt/src/index.ts)、[`packages/core/session/src/types.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/packages/core/session/src/types.ts) | Prompt 由 section、context、tool schema 和变量组装；session event 记录 user message、assistant chunk/message、tool call/result 和 request header，模型可见内容要求可重建。 | 运行时实现 | 说明上下文、日志和可复现性是同一条数据流的不同投影。 |
| Agent loop | [`packages/core/agent-loop/src/agent.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/packages/core/agent-loop/src/agent.ts) | turn/step 生命周期依次执行 pre-step、模型流、工具调用和 turn-stopping；请求错误可以由 waterfall 返回 retry，取消使用 AbortSignal，dispose 等待工作停稳。 | 运行时实现 | 说明 Agent 不是一次生成，而是有状态、可取消和可恢复策略的执行循环。 |
| 工具执行流水线 | [`docs/tool-execution-pipeline.md`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/docs/tool-execution-pipeline.md)、[`packages/core/tools/src/index.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/packages/core/tools/src/index.ts) | `tools/pre-execute` 可 allow/deny/ask；之后经过 guard、`tools/execute`、tool body、`tools/post-execute`、结果归一化和 `tools/result`。 | 运行时实现与架构图 | 说明权限、超时、重试、结果重写和 UI 呈现可以是 loop 外的策略层。 |
| 测试规范与测试 | [`docs/testing.md`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/docs/testing.md)、[`packages/core/agent-loop/tests/loop.spec.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/packages/core/agent-loop/tests/loop.spec.ts) | 定义 unit、coverage、real API、snapshot、browser 和真实入口层级；要求 e2e 重新读取文件或运行命令验证世界，而不是信任 Agent 输出。 | 测试规范与实测 | 说明测试把要求变成检查，但检查范围和测试层级决定了它能发现什么。 |
| CI 与文档发布 | [`.github/workflows/ci.yml`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/.github/workflows/ci.yml)、[`.github/workflows/e2e.yml`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/.github/workflows/e2e.yml)、[`.github/workflows/docs-pages.yml`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/.github/workflows/docs-pages.yml) | CI 分开运行静态、覆盖率、消费者/快照、兼容性和密钥 e2e；文档 workflow 运行 `doc-sync`；真实 API secret 只在受信 job 使用。 | CI 配置事实 | 说明 CI 重复验证提交和发布路径，并把密钥暴露面限制在具体 job；它仍不是语义正确性的证明。 |
| Review 维护流程 | [`docs/cookbook/maintaining-dsh-code-review.md`](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/docs/cookbook/maintaining-dsh-code-review.md) | 对 `dsh-code-review` skill 的维护流程要求保存 diff、核对人类反馈与落地补丁，并由维护者独立阅读 diff、决定丢弃、批处理或提升。 | 特定维护流程 | 直接支持“Review 处理测试无法替代的判断”；不能扩展成所有外部贡献都遵循同一流程的证据。 |

表中的“文档优先”和“规范驱动”是本文对这些材料关系的归纳。DeepSeek Harness README、架构文档或代码没有把它们作为正式方法论名称。更准确的描述是：仓库把一部分项目约束放进了文档和指令，把一部分约束放进了类型、事件、工具流水线和测试，再由 CI 重复执行其中一部分。

### 文档如何成为 Agent 的上下文

根目录 `AGENTS.md` 的作用首先是给维护者和 Agent 看的操作规则；它并不会因为存在于 Git 仓库中就自动进入模型请求。当前 commit 的 standard preset 显式加载 `@deepseek-ai/dsh-agent-instructions`，这个插件的 README 说明了更具体的生命周期：第一条符合条件的 `agent/pre-step` 会组合 baseline；它读取 `$DSH_HOME/AGENTS.md`，再按项目根到会话 cwd 的目录顺序读取候选文件；成功的 `read`、`write` 和 `edit` 结果还会触发嵌套指令的重新发现。

这个实现同时暴露了文档优先的成本。指令有 `maxBytes` 预算，重复的 `AGENTS.md` 与 `CLAUDE.md` 可以折叠，文件改变或消失时需要产生替换或删除上下文；如果文件读取失败，系统不能简单地把“没读到”当成“文件不存在”。因此文档既是上下文来源，也是有大小、版本和错误状态的运行时输入。

文档还承担不同层次的责任。`docs/architecture.md` 规定“新增行为应接入已记录的扩展点”；`docs/development.md` 规定如何安装、构建和运行检查；包 README 和源码 JSDoc 规定局部接口；`AGENTS.md` 规定本次修改时的操作边界。把所有内容塞进一个根文档会让每个 Agent 都接收过多上下文，也会让局部规则失去所有权。DeepSeek Harness 的 `docs/AGENTS.md` 用“one home per fact”约束这种重复。

### Prompt、session log 与上下文可重建性

`dsh-system-prompt` 把有序 section、动态 context、工具 Schema 和变量组合成模型输入；工具插件可以加入自己的操作提示。架构文档进一步提出“model-visible means logged”：任何抵达模型请求的内容都必须能从 session log 重建。`SessionEventMap` 中可以看到 `user/message`、原始 `assistant/chunk`、组装后的 `assistant/message`、`tool/call`、`tool/result` 和 request header 等事件。

这项设计的工程意义是，测试、UI 回放、恢复和审计可以围绕同一个持久事实流构建，而不是各自保存一份“模型当时大概看到了什么”。它不代表日志能够证明模型的内部推理正确，也不代表日志自动保存了所有外部文件状态。特别是，session log 不是任意文件修改的事务快照；恢复会话和回放工具结果与回滚工作区是不同问题。

### 工具、测试和 CI 如何形成反馈回路

DeepSeek Harness 的工具流水线先记录模型请求的 tool call，再进入 `tools/pre-execute`。这一层可以允许、拒绝或请求审批；monotonic guard 继续限制执行；`tools/execute` 适合超时、重试和指标包装；工具主体完成后，`tools/post-execute` 可以接受、替换结果或追加下一轮上下文；最终结果被归一化并写入 `tool/result`。这样做的好处是政策不需要被硬编码到每一个工具，但代价是维护者必须理解事件顺序和调用方的所有权。

测试规范把反馈回路分成层级。unit 测试验证局部注册表和边界条件；coverage 是行覆盖门，不是行为正确性的证明；snapshot 测试固定可重复的协议、日志和展示；real-API e2e 才会触达真实模型和 provider。测试规范还要求 e2e 通过重新运行命令或重新读取文件来验证外部世界，避免 Agent 只输出“我已经完成”就通过测试。

CI 的作用是把这些检查搬到提交或发布路径，并在干净环境和运行时矩阵中重复执行。固定 commit 的 GitHub Actions CI 分开运行 `check:ci:static`、`check:ci:coverage`、`check:ci:consumers` 和 Node 兼容性任务；真实 API workflow 将 `DEEPSEEK_API_KEY` 限制在可信 job，并明确禁止用 `pull_request_target` 运行不可信 fork 代码。文档 Pages workflow 运行 `doc-sync`。这些是 CI 配置的事实，不代表本文在本地重跑了每一条 CI lane。

### Review 补上测试表达不了的部分

测试可以判断“给定输入下某个行为是否满足断言”，但很难单独判断以下问题：这项改动是否放在正确的扩展点，是否扩大了不必要的权限，是否破坏了一个没有测试覆盖的兼容性承诺，是否误把临时策略写进公共 API，或者文档是否仍然准确。Review 需要读取 diff、设计材料、测试结果和失败边界，并作出接受、修改、回滚或继续实验的判断。

这个案例的证据需要保持窄。仓库的 `CONTRIBUTING.md` 在固定快照中说目前不能接受外部 PR；`maintaining-dsh-code-review.md` 描述的是一个由指定维护者维护 `dsh-code-review` skill 的流程，其中明确要求维护者独立阅读 diff，不把 reviewer 的结论当成最终决定。它支持“人类判断不可被测试或第二个模型自动替代”的工程原则，但不能被夸大为仓库所有代码变更的公开审查统计。

### 文档如何跟随代码变化

仓库把文档更新放在多个可执行要求中：包级公开行为变化要同步 README 或 JSDoc；文档变化运行 `pnpm run doc-sync`；部分源码声明通过 `ts type-equiv` 或生成目录与文档保持一致；非平凡变化还要求 Agent Note。这个安排降低了接口变化后留下旧说明的概率，但不消除维护成本。规则只能检查它知道的映射，不能判断新设计是否应该存在；人仍然需要在修改代码时识别受影响的事实来源。

因此，文档优先不是“先写一份不会过时的百科全书”。更实际的含义是：先确认事实的唯一归属，再让 Agent、测试和 CI 使用这些事实，最后让 Review 检查它们是否仍然表达正确意图。

## 一个最小的、可审查的实践流程

下面分开写三类内容：DeepSeek Harness 已经实现的做法、适用于一般项目的建议、以及本文的抽象模型。只有第一类可以用“仓库当前实现”描述。

### 1. 建立项目事实来源

一个最小仓库可以建立如下事实地图：

| 事实 | 唯一来源 | Agent 使用方式 | 自动检查 |
|---|---|---|---|
| 运行入口、支持版本和不保证的能力 | README/发布说明 | 任务开始时读取，回答“能不能这样跑” | 入口 smoke、版本检查 |
| 模块边界和扩展点 | 架构文档、公共 API JSDoc | 形成计划时读取，决定改哪个模块 | typecheck、架构约束测试、Review |
| 本仓库的工作顺序和禁止事项 | 根与子目录 Agent 指令 | 首次请求前加载；进入子目录后按范围刷新 | 指令预算、冲突和加载测试 |
| 行为验收和失败条件 | 测试、fixture、CI 脚本 | 任务中运行；不要只复制测试名称 | unit/e2e/snapshot/CI |
| 设计取舍和历史原因 | 决策记录或 Agent Note | 只在相关改动读取 | Review 是否仍适用 |

DeepSeek Harness 采用了多层文件和生成目录。一般项目不必复制全部层级，但要避免同一个事实在 README、Prompt、脚本和 Issue 中各自有一份未经同步的版本。一个规则如果不能指出它的来源、执行位置或失效条件，就不应被模型当成硬约束。

### 2. 组织架构文档、开发指南和 Agent 指令

推荐把三种文档分开：

- 架构文档只回答系统由什么组成、边界在哪里、扩展点是什么。它不应变成每个函数的实现手册。
- 开发指南回答如何准备环境、运行检查、构建发布和处理常见失败。它应给完整命令和工作目录。
- Agent 指令回答当前 Agent 执行任务时必须遵守什么：先读哪些文件、哪些目录可改、哪些命令需要批准、什么情况下停止、如何报告未验证结果。

DeepSeek Harness 的 `standard` preset 把 Agent 指令加载器和 plan mode 放进 Agent-plane 配置；其 plan mode 文本要求先探索仓库，在计划获准前只做非变更读取和静态检查。这是一种当前配置中的做法，不应误读成所有 preset 或所有部署都具有相同行为。

指令内容还需要显式声明优先级和冲突处理。例如，仓库事实优先于模型记忆；当前代码和测试优先于旧的工作日志；安全和权限规则优先于完成任务的便利；不能读取到的规则标记为未验证，而不是静默跳过。对于密钥、网络和生产环境，指令应当描述“禁止什么”和“如何请求人工确认”，而不仅是写一句“请注意安全”。

### 3. 把任务写成可验收的对象

下面是通用任务模板，不是 DeepSeek Harness 的配置文件，也不是可直接执行的命令：

```text
任务目标：用一句话描述可观察的最终状态。

范围：允许修改的目录、文件和接口。
不在范围内：明确禁止触碰的目录、依赖、生成物和外部服务。
前置事实：必须先读取的架构、开发指南、测试和配置。
验收标准：每一条都能对应一个命令、测试、文件状态或人工判断。
验证命令：给出工作目录、完整命令、预期退出码或输出。
失败条件：测试失败、规则冲突、权限不足、输出被截断或环境缺失时停止。
恢复方式：保存 diff 和日志；说明继续、重试、恢复会话或人工回滚的条件。
```

这样的任务比“实现这个功能并确保测试通过”多写几行，却减少了模型自行猜测范围的空间。验收标准不能只写“Agent 说完成”；应当要求外部检查重新读取文件、运行程序或比对结构化输出。

### 4. 修改前先探索仓库

Agent 开始修改前，至少需要确认工作区状态、入口、相关实现、约束文件、现有测试和验证命令。一个通用的只读探索顺序可以是：

```sh
git status --short
find .. -name AGENTS.md -o -name CLAUDE.md
rg -n "相关符号|配置键|测试名称" .
sed -n '1,240p' README.md
sed -n '1,240p' docs/architecture.md
```

实际项目应当用自己的目录和搜索工具替换示例命令；这里的片段只是说明顺序，不能当成适用于所有仓库的完整脚本。探索的目标不是把所有文件读进上下文，而是建立一张最小事实图：当前实现在哪里，约束由谁拥有，验证从哪个入口开始，哪些文件受影响。

### 5. 形成计划，再修改和验证

计划至少应包含目标、文件范围、数据流、测试、权限、失败恢复和未解决问题。对跨文件任务，先把“要修改的代码”和“要更新的事实来源”列在同一个计划里，避免实现完成后才发现接口文档、fixture 或配置目录已过时。

修改阶段应尽量使用小而可观察的操作：每次修改后检查语法和局部 diff；不要让 Agent 在没有测试结果的情况下连续重写同一个文件；每轮工具调用记录命令、退出码、标准错误和工作目录；对会改变外部状态的操作设置独立的审批点。

验证阶段至少分三层：

1. 针对性测试验证改动的直接行为和失败路径。
2. 相关模块的完整检查验证接口、类型、构建和集成关系。
3. Review 验证测试没有表达的设计、风险和范围，并确认 diff 没有混入无关修改。

以下命令均在固定 commit 的 DeepSeek Harness checkout 根目录执行。前置条件是 Node.js `v22.23.1` 和 pnpm `11.7.0`；安装依赖时可能需要访问 package registry，但这些检查不需要 `DEEPSEEK_API_KEY`。若 pnpm 版本或锁文件不匹配，`--frozen-lockfile` 会使安装失败；依赖安装未完成时，后续测试和类型检查不应被当作有效结果。实际执行的无密钥验证是：

```sh
pnpm install --frozen-lockfile
pnpm exec vitest run packages/core/agent-loop/tests/loop.spec.ts
pnpm run typecheck
```

预期结果是安装命令退出成功，Vitest 报告 54/54 个测试通过，类型检查退出码为 0。本文实际观察到的结果分别是锁文件安装成功、聚焦测试 54/54 通过、类型检查退出成功。这个结果只能说明该 commit 在本文记录的 Linux/Node 环境中通过了这些检查，不能说明真实模型能完成仓库任务，也不能替代完整 CI、真实 API、其他操作系统或人工 Review。

### 6. 明确责任分配

| 工作 | Agent 可以做 | 自动检查可以做 | 维护者必须做 |
|---|---|---|---|
| 事实发现 | 搜索、阅读、标注冲突和未知项 | 检查文件存在、生成文档同步、类型引用 | 决定哪份事实是当前权威来源 |
| 代码修改 | 按范围编辑、解释 diff、运行命令 | 编译、lint、测试、快照、构建和 smoke | 判断设计是否进入正确扩展点，是否扩大风险 |
| 权限操作 | 在已授权工具内请求一次性批准 | 检查策略、沙箱和拒绝路径 | 决定是否给生产、网络、密钥或破坏性操作授权 |
| 失败处理 | 保存错误、停止循环、提出下一步 | 重复确定性检查、保留日志和 artifact | 选择重试、修改、回滚、恢复会话或放弃 |
| 发布 | 准备补丁、说明验证结果和未验证部分 | 在 CI 中重复门禁和矩阵检查 | 接受最终变更并承担发布后的责任 |

这张表中的“Agent 可以做”不是“Agent 应该拥有无限权限”。它只表示在明确配置的工具和工作区内可以执行；权限配置缺失时，默认应当是停止或拒绝，而不是猜测一个更宽的权限。

## 安全、权限、成本、延迟、兼容性和失败恢复

### 文件系统、命令、网络和密钥

DeepSeek Harness 的沙箱文档把 `read-only`、`workspace-write` 和 `danger-full-access` 定义为文件效果模式，同时明确说网络和进程可见性不属于这个词汇。这个区分很重要：文件写入受限不等于网络被隔离，命令不能写工作区不等于命令没有读取或探测其他资源的能力。

本地 sandbox provider 在 Linux 上优先尝试 bubblewrap，再尝试 Landlock；macOS 使用 Seatbelt，Windows 使用 ACL restricted-token runner。文档还明确报告 `full` 或 `partial` enforcement，并列出 Windows ACL、旧 Landlock ABI 和 macOS `sandbox-exec` 的限制。若没有可用后端，受限调用应以 `SANDBOX_UNAVAILABLE` 失败，不能静默退化成无约束执行。

`bash` 工具的 README 也没有把“有 sandbox”写成默认事实：没有 sandboxing executor 时，命令使用 executor 提供的全部权限；有 sandbox 时，权限策略、拒绝标记和一次性升级由工具与 `ctx.approval` 协作处理。升级应该由真实拒绝触发，要求最窄的更宽模式和理由；拒绝、取消、没有 answerer 或审批上下文时，命令不执行。

凭据保护需要单独考虑。防御性文档要求子进程获得清洗后的环境，避免 `KEY`、`SECRET`、`TOKEN` 和 `PASSWORD` 类变量泄漏到输出、环境或 spill 文件；临时文件使用私有目录、随机名称和仅所有者权限。GitHub 的真实 API workflow 还把 secret 限定在具体测试步骤，并禁止用 `pull_request_target` 检出不可信 fork 的代码后运行带密钥任务。这些机制降低了暴露面，但不能把仓库的默认配置描述成绝对安全保证。

### 成本与延迟

仓库事实中可以直接看到一些控制点：agent-loop 的 `maxTokens` 是每请求输出上限，工具流水线有并行调用上限，Shell executor 有超时和输出截断，workspace instruction 有 `maxBytes`，compaction 会处理过长上下文。它们分别限制输出、并发、单次执行、输入指令和历史增长，不能合并成一个“任务成本上限”。

本文没有调用模型，因此没有成本、首 token 延迟、总延迟、token 数量或成功率测量。一般项目需要在任务级定义预算，例如最大模型请求数、最大总 token、最长墙钟时间、最大并发工具数、最大 diff 大小和最大重试次数，并在运行时强制执行。只把“请节省 token”写在 Prompt 中不是预算控制。

### 兼容性与失败恢复

DeepSeek Harness 当前仍是 developer preview，根包要求 Node.js `^22.19.0 || >=24.0.0`，CI 还覆盖 Node 22.19、24 和 26。不同平台的 sandbox runner、原生包、Shell 和文件系统语义不同；本文只验证了 Linux x86_64 上的无密钥路径。固定 commit 的 session format version 仍为 `0`，根指令明确说没有兼容性承诺；恢复旧会话和升级持久格式不能假定为稳定能力。

失败恢复也有多个层次：

- Agent loop 可以在模型请求错误的 waterfall 中选择 retry，使用 AbortSignal 协作取消，dispose 等待资源和任务收敛。
- 工具调用在执行前记录 call，在执行后记录 result；拒绝、超时、异常和取消可以成为模型可见结果或结构化失败。
- session persistence 可以支持 resume、replay 或 fork，具体取决于挂载的 provider；它保存的是会话事实，不是任意工作区文件的快照。
- 文件编辑可以有 read-before-edit 或版本观察策略，但仓库没有证据表明所有任意 Shell 写入都能被全局事务回滚。维护者仍需保存 diff，并在失败后选择人工回滚、修复后重试或从干净 checkout 重新开始。

最小安全策略是：在破坏性操作前建立可恢复 checkpoint；每一轮保留 diff、命令、退出码和日志；达到预算、权限拒绝或连续相同失败时停止；恢复时先重新读取事实和当前文件，不要盲目重放旧动作。

## 常见误解

### “有 AGENTS.md，模型就一定会遵守”

不一定。文件必须被具体 Agent 的 loader 发现、读取、放入上下文，并且不能超出预算或与更近的规则冲突。即便加载成功，文本约束也需要工具策略和测试来执行。DeepSeek Harness 的 `dsh-agent-instructions` 是一个实现例子，不是文件名本身带来的通用协议。

### “文档优先就是 Prompt 优先”

不等于。Prompt 是一次请求的输入，文档是由项目维护的事实来源。Prompt 可以引用文档、摘要文档或动态加载文档，但不能替代源码、配置、测试和 CI。项目行为变化后只改 Prompt 而不改事实来源，会制造第二套规范。

### “测试通过就代表 Agent 修改正确”

不等于。测试只覆盖已写出的断言和运行环境；它可能漏掉业务语义、权限扩大、数据迁移、文档错误和未覆盖平台。DeepSeek Harness 自己的测试规范也把“测试行为”和“证明正确性”区分开来。

### “CI 是更严格的 Review”

不完全是。CI 擅长重复确定性检查、矩阵兼容性、构建 artifact 和密钥隔离；Review 擅长判断设计意图、范围、风险和未来维护成本。两者互相补充，不能互相替代。

### “审批通过后，Agent 对这个项目就获得了长期权限”

DeepSeek Harness 的审批和沙箱文档描述的是一次调用或明确策略状态的授权。一次 `allowed-once` 升级不应被理解为永久放宽所有工具；会话模式、工具 guard 和执行器仍然可以拒绝后续操作。一般系统也应避免把一次人工选择扩展成全局长期信任。

### “会话日志可以回滚代码”

不能直接推出。日志可以支持重放、审计、恢复会话和重建模型可见消息；任意文件和外部服务的副作用需要独立的 checkpoint、事务或补偿机制。没有这些机制时，回滚仍是人工或工具层的工作。

### “插件式架构自动带来安全隔离”

不对。插件式架构主要描述组合和替换；DeepSeek Harness 需要通过 `isolate` realm、sandbox provider、approval policy 和工具执行 guard 共同表达不同的作用域。没有加载或正确配置这些组件时，能力边界会改变。

## 适用边界与未解决问题

本文的中心假设获得了部分支持：随着交互从补全片段扩大到仓库任务，项目事实、上下文、工具策略、测试和 Review 确实进入了系统设计。DeepSeek Harness 的固定 commit 提供了对应的文档、指令、事件、工具、沙箱、测试和 CI 证据。但以下问题仍不能从本次研究中得到强结论。

- **没有真实模型实验。** 本文没有测量任何模型在 DeepSeek Harness 上完成仓库任务的成功率、平均步骤、token 成本、延迟或修复质量。聚焦测试和 typecheck 只验证了代码基础设施。
- **没有跨平台安全结论。** Linux 的一次安装和测试不能代表 macOS Seatbelt、Windows ACL、Landlock 旧 ABI、E2B 或远程 provider 的完整性。
- **没有证明文档一定新鲜。** 文档同步门禁可以发现部分漂移，但无法判断架构判断是否仍然合理，也无法阻止 Agent 选择错误或恶意的事实来源。
- **没有证明权限模型覆盖所有威胁。** 文件 sandbox 不包含网络和进程可见性；命令执行、提示词注入、恶意仓库内容、供应链依赖和外部服务副作用需要独立威胁模型。
- **没有通用回滚保证。** session log、取消和 resume 解决的是生命周期和上下文问题，不能自动撤销任意 Shell 命令或外部 API 请求。
- **兼容性处于预览阶段。** 当前 commit 没有稳定 tag，根包是 `0.1.0-rc.5`，README 明确警告会有兼容性破坏。引用源码时应固定 commit，并在项目行为变化后更新文章和验证记录。

对小型、低风险、测试完善的仓库，增加 Agent 指令、计划模式、日志和多层门禁可能比任务本身更复杂。对涉及生产数据、密钥、迁移、基础设施或法律责任的任务，应该先收紧权限并保留人工审批，而不是因为模型能够调用工具就扩大自动化范围。

## 总结

1. AI 辅助软件开发的关键变化是交互单位、反馈回路和责任边界的变化，不是单一模型能力的线性升级。
2. 代码补全和对话式生成可以降低局部编码劳动；仓库级 Coding Agent 还必须理解项目事实、执行受限动作、观察真实结果并留下可审查证据。
3. DeepSeek Harness 的固定 commit 把插件组合、Agent 指令、session log、工具流水线、测试、CI、审批和沙箱放在了可以逐项检查的工程材料中；“文档优先”“规范驱动”是本文的归纳名称，不是项目官方术语。
4. 测试和 CI 能重复验证可执行行为，Review 负责设计、语义、权限和责任判断；session log 支持恢复和审计，但不自动提供工作区回滚。
5. 实践时先固定事实来源和任务验收，再让 Agent 探索、计划、修改和验证；对成本、网络、密钥、文件系统、平台差异和失败恢复设置明确边界，并把未验证部分写出来。

## 延伸阅读

- [Agent Spec：如何把 Agent 行为写成可执行规范](/agent/agent-spec-design/)：本文把项目规范作为工程材料，那里更集中讨论规范本身的设计。
- [从零构建 CLI Coding Agent](/agent/build-cli-coding-agent/)：从工具注册、ReAct 循环、上下文管理和 CLI 实现角度理解 Coding Agent 的最小结构。
- [Human-in-the-Loop：Agent 什么时候必须请求人工介入](/agent/human-in-the-loop/)：继续讨论审批、暂停、恢复和人工责任边界。
- [Agent 的安全边界与 Guardrails](/agent/guardrails-safety-boundary/)：补充提示词注入、工具权限和纵深防御的威胁模型。
- [Agent 评测：自动指标与人工判断](/agent/agent-evaluation/)：解释为什么任务成功率、轨迹质量、成本和人工可接受性需要分开测量。
- [Agent 可观测性与调试](/agent/agent-observability-debugging/)：从日志、Trace、Metrics 和 Replay 继续研究本文强调的证据链。
- [DeepSeek Harness 固定 commit 的 README](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/README.md)、[架构文档](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/docs/architecture.md) 和 [测试规范](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/docs/testing.md)：案例研究的原始资料。
