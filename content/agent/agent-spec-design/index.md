+++
title = "Agent Spec：如何用自然语言定义一个可执行系统"
date = 2026-04-04T01:50:00+08:00
draft = false
author = "Hex4C59"
description = "系统解析 Agent Spec 的本质，说明它与普通 Prompt 的区别，并给出一套包含六大核心组件的工程化设计方法论与通用模板。"
summary = "从 Prompt Engineering 进阶到 Agent Workflow Design。系统分析 Agent Spec 的六大核心组件、四步设计流程以及常见避坑指南，帮你用自然语言定义真正的系统工作流。"
tags = ["Agent", "Agent Spec", "Prompt", "Workflow", "LLM"]
categories = ["Agent"]
series = ["agent-engineering"]
series_order = 25
difficulty = "intermediate"
article_type = "concept"
topics = ["agent-spec", "prompt-engineering", "workflow", "design-pattern"]
frameworks = ["LangChain"]
ShowToc = true
+++

从"会写提示词（Prompt）"升级到"会设计智能体规范（Agent Spec）"，是 Agent 开发者必须跨越的一道坎。这一层级已经脱离了语言技巧的范畴，进入到了真正的系统设计领域。

在这篇文章里，我们将探讨 Agent Spec Prompt 的本质，并为你提供一套工程化的方法论、可复用的模板以及设计原则，让你的 Agent 不再只是被动聊天的机器，而是能独立完成复杂循环任务的"可执行系统"。

---

## 先给结论

1. **Agent Spec Prompt 的本质是用自然语言定义一个"可执行系统"。** 它不是普通 prompt，而更像是一个状态机（state machine）、一个工作流引擎（workflow engine）或专用的领域语言（DSL）。
2. **一个合格的 Agent Spec 必须包含 6 大核心组件：** 目标（Goal）、工作流（Workflow）、迭代机制（Iteration）、约束规则（Rules）、拆解能力（Decomposition）与输出规范（Output Contract）。
3. **最容易漏掉的是终止条件。** 没有收敛机制和终止条件 = 无尽纠结与无限的机器幻觉（Hallucination）。
4. **Agent 设计的本质就是程序化思维：** 把任务拆成流程，加循环，加约束，定义收敛，规定输出结构。

---

## Agent Spec 的 6 大核心组件

在设计 Agent Spec 时，你的 Prompt 必须像代码架构一样严谨，包含以下 6 块组件：

### 1. Goal（目标）

定义任务"最终要达成什么"。
好的目标必须是**可验证**的，并且有明确的**终态**（done condition）。

**常见的错误写法（太模糊）：**
```text
帮我优化一下这些文档
```

**工程化的写法：**
```text
将输入的散乱文档集合，重构为结构清晰、命名规范统一的工程文档体系，包含功能说明、API 接口和部署指南三部分。
```

### 2. Workflow（工作流）

定义任务"怎么做"，本质上它是一条 pipeline（流水线）。

一个清晰的 workflow 可能长这样：
`遍历 → 分析 → 修改 → 迭代 → 输出`

关键点在于，每一步都必须是**可执行步骤**，顺序要清晰，不能给模型留有歧义。

### 3. Loop / Iteration（迭代机制）

**这是 Agent 和普通 Prompt 的分水岭。** 系统要不要反复做某件事？

你必须在 Spec 中定义：
- 是否需要循环？
- 循环的条件是什么？
- 终止条件（收敛机制）是什么？

例如：
```text
重复审查和优化文档内容，直到无法提出实质性改进或经过 3 轮优化为止。
```
这个机制确保了 Agent 会自我收敛，而不是陷入死循环。

### 4. Rules / Constraints（约束规则）

约束机制用于控制 AI 不"发散"或"跑偏"。主要包括：

- **风格约束**：使用工程化语言，保持简洁。
- **行为约束**：如果判断条件满足，直接执行无需反复确认。
- **安全约束**：不允许覆盖未备份的原始数据。

### 5. Decomposition（拆解能力）

面对复杂输入，Agent 必须具备"分而治之"的能力。如果把所有东西搓成一坨执行，最终产出肯定不可维护。你需要告诉它：
- 如何拆任务
- 如何拆文档
- 如何拆模块

### 6. Output Contract（输出规范）

由于它是系统的一部分，后续往往会有解析层来处理它的输出。你需要定义输出"长什么样"（比如 JSON 格式、Markdown 结构等）。如果不定义约束，AI 会随意输出自然语言的废话，导致流程中断。

---

## 编排工作流的 4 步设计法

在编写 Agent Spec 时，可以遵循这个实用的"4步法"：

### Step 1：把任务"程序化"

在写每一段描述时，先问自己：**如果这是代码，我会怎么写？**

当你脑海中有了类似这样的伪代码：
```python
for file in folder:
    optimize(file)
    while can_improve:
        refine(file)
```
再把这段逻辑翻译成严谨的自然语言指令。

### Step 2：加入"智能体能力"

赋予这个流程判断和决策能力：
- 增加判断条件（if）
- 控制循环流（while）
- 细化任务拆分（split）
- 引入思考空间（decide）

### Step 3：加入约束（防止失控）

补齐各种边界情况的防御：
- "当遇到未知术语时，不要自行编造，应保持原文标注。"
- "命名必须遵守驼峰规范。"
- "输出过程中不要产生解释性废话。"

### Step 4：定义终止条件

最重要的一步，补齐收敛条件。明确到底满足什么标准时，这个 Agent 可以结束当次执行，返回最终结果。

---

## Agent Spec 通用模板

强烈建议收藏下面这套模板，这是你编写新 Agent 时的绝佳骨架：

```text
# Goal
<定义最终目标，必须有明确终态>

# Workflow
1. <可执行步骤 1>
2. <可执行步骤 2>
...

# Iteration
- 循环执行 <某步骤>
- 直到满足：
  <明确的终止条件>

# Decomposition
- 当满足以下条件时拆分：
  <拆分规则>
- 对拆分后的单元重复执行本流程

# Rules
- <约束准则 1>
- <约束准则 2>

# Naming / Structure (optional)
- <命名规范要求>
- <目录/输出结构规范>

# Output Contract
最终输出必须满足：
- <条件 1>
- <条件 2>
- <格式定义，如 JSON Schema>
```

---

## 设计质量的 5 个评判标准

写完一个 Agent Spec 后，试着用这 5 个维度来评判它是否优秀：

1. **可执行性（Executable）**：指令是不是悬在空中的？能不能直接按步骤跑下来（甚至是由人脑对照模拟执行）？
2. **收敛性（Convergence）**：循环逻辑会不会导致无限幻觉？是否一定会在某个时刻结束？
3. **可控性（Controllability）**：它会不会乱改不该改的数据？有没有输出无法解析的内容？
4. **可扩展性（Scalability）**：如果以后要加新规则，能不能在当前的流程结构中平滑插入？
5. **可组合性（Composable）**：这份 Spec 能不能被封装起来，作为更大 Multi-Agent 系统中的一个节点甚至工具（Tool）被嵌套调用？

---

## 绝不能犯的错误

在日常编写中，一定要避免这几个让 Agent 崩溃的死穴：

- ❌ **没有终止条件**：AI 可能会陷入自我推翻的死循环，一直改下去。
- ❌ **目标太模糊**：导致 Agent 的输出质量极度不稳定，有时候好有时候坏。
- ❌ **全开放无约束**：让 AI 自由发挥的代价就是流程系统崩溃。
- ❌ **将一次性任务包装为 Agent**：如果没有用到迭代（Iteration）和状态流转，它只是个普通 prompt，不需要强行上 Agent。
- ❌ **缺乏输出结构设计**：导致下游系统无法对接使用。

---

## 进阶：你可以做得更远

理解并写好 Agent Spec，意味着你的能力模型已经处于 **Agent Workflow Designer（智能体工作流设计师）** 层级。对比整个 AI 系统分层：

| Level | 能力定位 |
| ----- | ------------------ |
| L1    | 普通问答使用 |
| L2    | Prompt Engineering (提示词工程师) |
| L3    | **Agent Spec 设计 (当前层级)** |
| L4    | Multi-Agent 架构 |
| L5    | Autonomous 甚至通用认知系统 |

下一步，你可以尝试将这份 Spec 转化为真正可执行的 Python Agent 脚本（比如基于 LangChain 或原生集成），或者将任务水平拆分，设计一个带有自我评估机制的 Multi-Agent 协作网络，甚至引入动态的评分函数（类似强化学习机制中的 Reward Model）。

从这一刻开始，你不再仅仅是"使用 AI"，而是在"设计智能系统"。

---

*上一篇：[Human-in-the-Loop：Agent 什么时候应该停下来问你](/agent/human-in-the-loop/)*
