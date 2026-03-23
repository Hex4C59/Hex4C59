+++
title = "Reflection：Agent 如何审视自己的输出并纠正错误"
date = 2026-03-23T14:00:00+08:00
draft = false
author = "Hex4C59"
description = "解释 Reflection 为什么是 Agent 的质量保证层，以及如何用输出后审查、执行中自我纠错和多 Agent 交叉审查发现并修正隐性错误。"
summary = "系统分析 Reflection 在 Agent 系统中的角色、三种实现形态、批评标准设计、失效场景，以及它与 ReAct 和 Planning 的关系。"
tags = ["Agent", "Reflection", "Quality Control", "Reliability", "LLM"]
categories = ["Agent"]
series = ["agent-engineering"]
series_order = 8
difficulty = "intermediate"
article_type = "concept"
topics = ["reflection", "self-critique", "quality-control", "agent", "planning"]
frameworks = ["OpenAI", "Anthropic"]
ShowToc = true
+++

在前面几篇文章里，我们把 Agent 的执行能力搭起来了：[ReAct](/agent/react-paradigm/) 让它边推理边行动，[Planning](/agent/planning-plan-and-execute/) 让它在长任务里保持全局视图，[评测](/agent/agent-evaluation/) 让我们知道它在哪里出问题。

但有一个能力一直没有专门讨论：**当 Agent 完成了一个任务，它能不能自己发现输出有问题，然后主动纠正？**

这就是 Reflection。

---

## 先给结论

1. **Reflection 是让 Agent 对自己的输出做批判性审查的机制。** 不是简单地“再想一遍”，而是用一套明确的标准评估输出质量，发现问题，然后决定是修正还是重新执行。
2. **Reflection 解决的问题是“执行完成 ≠ 执行正确”。** ReAct 和 Planning 让 Agent 能完成任务，但不保证完成得好。Reflection 是质量保证层。
3. **Reflection 有三种形态：输出后审查、执行中自我纠错、多 Agent 交叉审查。** 适用场景不同，复杂度和成本也不同。
4. **Reflection 的效果上限取决于批评能力。** 模型能发现的问题，受限于它自身的判断能力。如果模型对某类错误“无感知”，Reflection 就帮不上忙。
5. **Reflection 有成本，不是所有任务都需要。** 额外的审查轮次意味着额外的延迟和 token 消耗。只在输出质量要求高、错误代价大的任务上引入。

---

## 为什么 ReAct 和 Planning 不够

ReAct 在每一步行动后都有推理，Planning 在每个检查点都会评估进度。听起来已经很完善了，为什么还需要 Reflection？

问题出在**错误的隐蔽性**上。

ReAct 的每步推理是基于当前 Observation 的局部判断，它很擅长发现“工具调用失败”这类显性错误，但很难发现“结论方向错了”这类隐性错误——因为每一步看起来都是合理的，只是最终组合在一起时出了问题。

来看一个具体场景：

```text
任务：分析某产品的竞争态势，给出市场定位建议。

Step 1 - Thought: 先搜索主要竞品信息
Action: search_web("竞品A 产品特性")
Observation: 返回了竞品A的官方宣传内容

Step 2 - Thought: 再搜索竞品B
Action: search_web("竞品B 产品特性")
Observation: 返回了竞品B的官方宣传内容

Step 3 - Thought: 信息足够了，开始分析
Answer: 基于以上信息，建议定位为...
```

每一步的推理和执行都是“正确”的。但最终的分析基于的是两家公司的**官方宣传材料**，不是客观的市场数据。这个根本性的信息偏差，ReAct 的每步推理都没有发现，因为它只在局部判断“这一步做得对不对”，没有在全局判断“整个分析的信息质量怎么样”。

Reflection 要做的，就是在任务执行完成后（或执行中的关键节点），从全局视角问：**这个输出真的好吗？哪里可能有问题？**

---

## Reflection 的三种形态

### 形态一：输出后审查（Post-hoc Reflection）

最简单也最常见的形态。Agent 完成任务后，用另一轮模型调用对输出做批判性评估，发现问题后决定是否修正。

![Reflection 输出后审查流程图](reflection_post_hoc_flow.svg)

*图 1：任务执行完成后，Reflection 会对结果做一次全局审查；如果没有问题就直接输出，如果发现问题则触发修正或重执行。*

实现方式：

```python
import openai
import json

client = openai.OpenAI()

async def reflect_on_output(
    task: str,
    execution_trace: list[dict],
    output: str,
    criteria: list[str] | None = None
) -> dict:
    """
    对 Agent 输出做批判性审查。
    返回：问题列表、严重程度、是否需要修正、修正建议。
    """

    default_criteria = [
        "输出是否完整回答了原始任务",
        "结论是否有充分的信息支撑（没有无依据的推断）",
        "信息来源是否可靠、是否存在明显偏差",
        "是否遗漏了任务中明确要求的内容",
        "输出格式是否符合任务要求",
    ]
    active_criteria = criteria or default_criteria

    trace_summary = "\n".join([
        f"[{s['type']}] {str(s['content'])[:200]}"
        for s in execution_trace
    ])

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": f"""
你是一个严格的质量审查员。请对以下 Agent 的执行结果做批判性评估。

原始任务：
{task}

执行过程摘要：
{trace_summary}

Agent 的输出：
{output}

请根据以下标准逐一评估：
{chr(10).join(f"{i+1}. {c}" for i, c in enumerate(active_criteria))}

对每个发现的问题，说明：
- 问题描述
- 严重程度（致命 / 重要 / 轻微）
- 修正建议

输出 JSON 格式：
{{
  "issues": [
    {{
      "criterion": "对应的评估标准",
      "description": "问题描述",
      "severity": "致命|重要|轻微",
      "suggestion": "修正建议"
    }}
  ],
  "overall_quality": "高|中|低",
  "needs_revision": true/false,
  "revision_scope": "完全重做|局部修正|无需修正"
}}
"""
        }],
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)


async def execute_with_reflection(
    task: str,
    agent_fn,
    tools: list,
    max_reflection_rounds: int = 2
) -> str:
    """
    执行任务 + 输出后审查的完整流程。
    """
    output, trace = await agent_fn(task, tools)

    for round_idx in range(max_reflection_rounds):
        review = await reflect_on_output(task, trace, output)

        # 没有问题或只有轻微问题，直接返回
        fatal_issues = [i for i in review["issues"] if i["severity"] == "致命"]
        important_issues = [i for i in review["issues"] if i["severity"] == "重要"]

        if not fatal_issues and not important_issues:
            break

        # 有致命问题，重新执行
        if fatal_issues:
            revision_prompt = build_revision_prompt(task, output, fatal_issues)
            output, trace = await agent_fn(revision_prompt, tools)

        # 只有重要问题，局部修正
        elif important_issues:
            output = await revise_output(task, output, important_issues)
            break

    return output


def build_revision_prompt(task: str, output: str, issues: list[dict]) -> str:
    issue_text = "\n".join([
        f"- {i['description']}（建议：{i['suggestion']}）"
        for i in issues
    ])
    return f"""
原始任务：{task}

上一次执行的输出存在以下严重问题：
{issue_text}

请重新执行任务，特别注意避免上述问题。
"""
```

### 形态二：执行中自我纠错（In-process Reflection）

不等到任务结束再审查，而是在执行的关键节点插入反思步骤。适合长任务，可以在错误刚萌芽时就发现，而不是等到整个执行路径都跑偏之后。

这种形态通常集成在 Planning 的检查点里：

```python
async def reflective_checkpoint(
    plan: "ExecutionPlan",
    completed_step: "PlanStep",
    recent_trace: list[dict]
) -> dict:
    """
    在每个计划步骤完成后触发反思，检查是否走在正确的轨道上。
    """
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": f"""
任务目标：{plan.goal}
完成标准：{plan.definition_of_done}

刚完成的步骤：{completed_step.description}
步骤结果：{completed_step.result_summary}

最近的执行轨迹：
{format_trace(recent_trace)}

请从以下角度进行反思：

1. 方向检查：当前的执行方向是否仍然指向原始目标？
   有没有被某个工具结果或中间发现带偏？

2. 质量检查：刚完成的步骤，结果的质量如何？
   有没有信息偏差、遗漏或不可靠的来源？

3. 假设检查：执行过程中有没有隐含的假设？
   这些假设是否经过了验证？

4. 风险预判：基于当前进展，后续步骤有什么潜在的风险？

输出 JSON：
{{
  "on_track": true/false,
  "direction_issues": "方向问题描述，无则为 null",
  "quality_issues": "质量问题描述，无则为 null",
  "unverified_assumptions": ["假设1", "假设2"],
  "upcoming_risks": ["风险1", "风险2"],
  "recommended_action": "继续|调整方向|暂停确认|回退重做",
  "adjustment_notes": "如果需要调整，具体说明"
}}
"""
        }],
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)
```

执行中反思的关键是**不要太频繁**。每步都触发反思，成本会翻倍，而且大多数步骤根本不需要反思。合理的触发时机：

- 完成了一个重要的信息收集步骤（此后的推理都依赖这里的信息）
- 工具返回了意外的结果（和预期不符）
- 完成了整体计划的 50% 左右（中期检查）
- 任务即将进入不可逆操作之前（比如写入文件、发送请求）

### 形态三：多 Agent 交叉审查（Multi-Agent Critique）

让一个独立的 Agent 扮演批评者角色，专门审查执行者 Agent 的输出。与前两种形态的区别在于：批评者和执行者使用的是**完全独立的上下文**，批评者不会被执行者的推理路径所影响。

![多 Agent 交叉审查流程图](reflection_multi_agent_critique.svg)

*图 2：把执行者与批评者拆成独立上下文后，可以从不同视角并行审查输出，再综合各方意见决定是否修正。*

```python
async def multi_agent_critique(
    task: str,
    output: str,
    execution_trace: list[dict],
    num_critics: int = 2
) -> dict:
    """
    多个批评者 Agent 从不同角度审查输出，综合意见后给出裁决。
    """
    critic_perspectives = [
        {
            "role": "事实核查员",
            "focus": "检查输出中的每一个事实性陈述是否有来源支撑，是否存在无依据的推断",
        },
        {
            "role": "逻辑审查员",
            "focus": "检查推理链是否有跳跃，结论是否真的从前提中得出，有无自相矛盾",
        },
        {
            "role": "完整性审查员",
            "focus": "检查任务要求的所有方面是否都得到了回答，有无遗漏",
        },
    ]

    # 并行调用多个批评者
    import asyncio
    critic_tasks = [
        call_critic(task, output, perspective)
        for perspective in critic_perspectives[:num_critics]
    ]
    critiques = await asyncio.gather(*critic_tasks)

    # 综合裁决
    combined = await synthesize_critiques(task, output, critiques)
    return combined


async def call_critic(task: str, output: str, perspective: dict) -> dict:
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "system",
            "content": f"你是一个{perspective['role']}。{perspective['focus']}"
        }, {
            "role": "user",
            "content": f"任务：{task}\n\n待审查的输出：\n{output}"
        }],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)
```

多 Agent 交叉审查的成本最高，通常只用于：

- 高风险决策（结果会被直接用于重要业务决策）
- 长篇输出的质量保证（研究报告、分析文档）
- 需要多角度验证的复杂分析

---

## 三种形态的对比

![Reflection 三种形态对比图](reflection_modes_comparison.svg)

*图 3：默认优先使用输出后审查；只有当任务更长、风险更高时，才按需升级到执行中反思或多 Agent 交叉审查。*

---

## Reflection 的质量取决于批评标准的设计

写 Reflection 最容易犯的错误，是让模型做一个过于泛化的自我评估：

```python
# 这种写法几乎没有用
"请检查你的输出是否有问题，如果有，请修正。"
```

模型对“是否有问题”的判断完全没有约束，通常会给出一个自我肯定的结论——“输出质量良好，没有发现明显问题。”

**有效的批评标准需要具体、可操作、针对当前任务的已知风险点。**

不同任务类型有不同的高风险点，批评标准应该对应这些风险：

**信息检索类任务的批评标准：**

```python
RETRIEVAL_CRITERIA = [
    "所有事实性陈述是否都能在工具返回的内容中找到来源",
    "是否混入了工具未返回、来自训练知识的内容",
    "搜索结果是否存在明显的时效性问题（内容已过期）",
    "是否只引用了某一方的观点，忽略了其他视角",
]
```

**代码生成类任务的批评标准：**

```python
CODE_CRITERIA = [
    "代码是否在沙箱里实际执行过并验证了输出",
    "有没有假设了不存在的变量、函数或导入",
    "错误处理是否完整（边界情况、空值、异常）",
    "代码逻辑是否真的解决了原始问题，而不只是看起来像",
]
```

**分析报告类任务的批评标准：**

```python
ANALYSIS_CRITERIA = [
    "结论是否真的从数据中得出，还是先有结论再找数据支撑",
    "是否存在混淆相关性和因果性的推断",
    "分析是否覆盖了任务要求的所有维度",
    "建议是否具体可执行，还是停留在泛泛而谈",
]
```

---

## Reflection 的失效场景

Reflection 不是万能的，了解它的边界和了解它的能力同样重要。

### 模型对某类错误“无感知”

如果模型本身不具备识别某类错误的能力，让它审查自己的输出也没用。比如：

- 需要专业领域知识才能发现的事实错误（医学、法律、金融）
- 复杂数学推导中的计算错误
- 需要实际运行才能验证的代码问题

对于这类错误，Reflection 的作用有限，需要引入工具验证（执行代码、调用专业 API）或者人工审查。

### 自我一致性陷阱

模型审查自己的输出，存在一个根本性的偏差：它倾向于认为自己的输出是合理的，因为输出本身就来自它的推理。这种“自我一致性”会让它系统性地低估自己的错误率。

缓解方法：

- 在审查 prompt 里明确要求“假设这个输出是别人写的，你的任务是找到它的问题”
- 要求模型为每条标准给出具体的问题描述，而不是简单的“通过/不通过”
- 对高风险任务使用多 Agent 交叉审查，减少单一模型的自我一致性偏差

### 反思循环（Reflection Loop）

模型在审查后发现了“问题”，修正后再审查，又发现了新“问题”，如此循环，始终无法收敛到一个满意的输出。

```python
# 防止反思循环的安全边界
MAX_REFLECTION_ROUNDS = 2  # 最多审查 2 轮

# 只对严重问题触发重新执行
# 轻微问题直接接受，不触发修正
SEVERITY_THRESHOLD = "重要"  # 低于此严重程度的问题忽略
```

设置明确的轮次上限和严重程度阈值，是防止反思循环最直接的方法。

---

## 与其他范式的关系

把 Reflection 放进整个系列的范式图里：

![Reflection 在 Agent 范式中的位置图](reflection_paradigm_stack.svg)

*图 4：ReAct 解决“每一步怎么做”，Planning 解决“整体做什么”，Reflection 则负责在执行完成后检查“做得好不好”。*

四个范式的分工：

- **ReAct**：决定每一步怎么做（推理 + 行动的微观循环）
- **Planning**：决定整体做什么（任务分解和全局协调）
- **执行完成**：确认任务按计划走完了
- **Reflection**：确认完成的质量达标，发现隐性错误

Reflection 不替代前三个，它是在它们之上的质量保证层。当 Reflection 发现了严重问题，会触发回退——可能是回退到上一个检查点重新执行某些步骤，也可能是完全重新开始。

---

## 总结

执行完成和执行正确是两件事。ReAct 和 Planning 解决的是前者，Reflection 解决的是后者。

三种形态覆盖不同场景：输出后审查成本低、适用广，是默认选择；执行中自我纠错适合长任务，在错误早期介入；多 Agent 交叉审查成本高但效果最强，用于高风险场景。

Reflection 效果的上限是批评标准的质量。泛化的自我审查几乎没用，针对当前任务已知风险点的具体批评标准才有价值。要防止自我一致性偏差（模型倾向于认为自己是对的）和反思循环（无法收敛），需要在 prompt 设计和轮次控制上做明确的约束。

最后：Reflection 有成本。在决定是否引入之前，先问一个问题：这个任务的错误代价高吗？如果答案是否，直接输出就够了；如果答案是是，Reflection 的额外成本是值得的。

---

*下一篇：Coding Agent 实战——从零搭建一个能读代码、跑测试、修 bug 的 Agent*
