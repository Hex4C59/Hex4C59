+++
title = "工具接口设计：让 Agent 用得好，比让 Agent 用得上更难"
date = 2026-03-23T11:00:00+08:00
draft = false
author = "Hex4C59"
description = "解释为什么 Agent 时代的工具接口不能只追求人类可用，并从粒度、返回值、错误处理与状态管理四个维度给出可落地的设计原则。"
summary = "系统分析面向 Agent 的工具接口设计，说明为什么粒度、返回格式、错误信息和显式状态会直接决定 Agent 的决策质量与恢复能力。"
tags = ["Agent", "Tool Design", "Tool Use", "Interface Design", "LLM"]
categories = ["Agent"]
series = ["agent-engineering"]
series_order = 9
difficulty = "intermediate"
article_type = "concept"
topics = ["tool-use", "tool-design", "agent", "mcp", "interface-design"]
frameworks = ["OpenAI", "Anthropic"]
ShowToc = true
+++

在 [Tool Use](/agent/tool-use-core-of-agent/) 那篇里，我们讨论了工具是 Agent 与外部世界的接口层，以及工具描述写得好不好对调用决策的影响。

但那篇文章有一个盲区：它假设工具本身是现成的，重点在于如何描述工具、如何在 system prompt 里写调用规则。

现实工程里更常见的问题是：**你需要自己设计工具**。你要决定工具的粒度、参数结构、返回格式、错误处理方式。这些决策直接决定了 Agent 能不能用好这个工具——而不只是能不能调用它。

字节技术团队在一篇关于 Agentic Coding 实践的文章（[原文链接](https://mp.weixin.qq.com/s/Zlwn42KyfjgwfX6lp-JthQ)）里提出了一个值得深思的观点：

> 当我们观察 Agent 使用现有命令行工具时的困惑和迷失，这强烈表明：我们现有工具的信息架构对 LLM 来说是不够的。LLM 是在我们现有的 CLI 工具上训练的，所以它们知道如何使用这些工具。但这些工具是为人类设计的，它们的输出格式、错误信息、交互方式都假设用户是人类。

这句话指向了一个更根本的问题：为人设计的工具，不等于为 Agent 设计的工具。两者的需求有交集，但差异足够大，值得单独思考。

---

## 先给结论

1. **工具接口是 Agent 的感知质量上限。** Agent 做决策依赖工具的返回，工具返回的信息质量直接决定了 Agent 决策的质量上限，再好的模型也无法从垃圾输入里得到好结论。
2. **为人设计的工具有三个对 Agent 不友好的特点：** 输出面向人眼而非机器解析、错误信息模糊而非可操作、状态隐含而非显式。
3. **粒度是工具设计最关键的决策。** 太细需要太多调用轮次，消耗上下文；太粗灵活性差，无法适应多变的任务。分层设计（便捷函数 + 底层函数）是务实的解法。
4. **返回值应该为 Agent 的下一步决策服务，而不是为开发者的调试方便。** 这两个目标经常冲突。
5. **工具的错误信息是 prompt 的一部分。** Agent 会读取工具返回的错误内容，用它来决定下一步怎么做。错误信息写得好不好，直接影响 Agent 的错误恢复能力。

---

## 人类用的工具 vs Agent 用的工具

先把两类用户的需求差异说清楚，后面的所有设计原则都从这里出发。

人类使用工具时：
- 用眼睛扫描输出，能快速抓住关键信息，忽略噪音
- 遇到错误时，能结合上下文和经验判断原因
- 能在多次交互之间保持状态记忆
- 可以通过视觉层级（缩进、颜色、对齐）理解结构

Agent 使用工具时：
- 通过文本理解输出，需要明确的结构才能可靠解析
- 遇到错误时，完全依赖错误信息本身来判断下一步
- 每轮调用之间没有持久记忆，不知道“上次你查了什么”
- 对格式化字符（ANSI 颜色码、制表符对齐）是负担而非帮助

这不是说工具要在两类用户之间做取舍。很多时候可以同时满足两者，但设计时需要**有意识地为 Agent 考虑**，而不是默认“人类能看懂就行”。

---

## 粒度：最重要的设计决策

工具的粒度决定了 Agent 完成一个任务需要多少轮调用，而每一轮调用都有上下文成本。

### 太细的工具：调用链爆炸

```python
# 粒度太细的工具设计
tools = [
    "get_file_list",           # 获取目录文件列表
    "read_file",               # 读取单个文件
    "get_function_names",      # 获取文件中的函数名
    "get_function_body",       # 获取特定函数的代码
    "get_function_calls",      # 获取函数内的调用关系
]
```

要完成“找到 `process_order` 函数在哪里定义”这个任务：

```
调用 get_file_list → 返回 47 个文件
对每个文件调用 get_function_names → 47 次调用
找到目标文件后调用 get_function_body → 1 次调用
```

共 49 次调用，每次都往 context 里追加内容。而且这 49 次调用里有大量的中间结果是噪音——Agent 不需要知道其他 46 个文件里有哪些函数名。

### 太粗的工具：信息过载或灵活性丧失

```python
# 粒度太粗的工具
def analyze_codebase(query: str) -> str:
    """分析整个代码库，回答关于代码的任何问题"""
    # 把整个代码库塞进模型，让它自己找
```

这种设计把“理解代码库”的工作推给了工具本身，工具的返回结果高度依赖它内部的实现质量，Agent 失去了对信息收集过程的控制。

### 分层设计：便捷函数 + 底层函数

务实的解法是提供两层工具：

```python
# 第一层：便捷函数，覆盖 80% 的常见场景
@tool
def find_symbol(name: str, symbol_type: str = "any") -> dict:
    """
    在代码库中搜索符号（函数、类、变量）的定义位置。
    这是查找代码定义的首选方法。

    参数：
    - name: 符号名称，支持模糊匹配
    - symbol_type: "function" | "class" | "variable" | "any"

    返回符号的文件路径、行号、完整签名。
    如果找到多个匹配，返回最可能的前 3 个结果。
    """
    ...

# 第二层：底层函数，处理便捷函数覆盖不到的情况
@tool
def search_in_file(file_path: str, pattern: str,
                   context_lines: int = 3) -> dict:
    """
    在指定文件中搜索文本模式。

    仅当 find_symbol 无法找到目标时使用此工具。
    支持正则表达式。
    """
    ...
```

关键在于工具描述里**显式说明使用优先级**：“这是首选方法”、“仅当 X 无法找到时使用”。这样 Agent 在做工具选择时有了明确的决策依据，不会在两个功能重叠的工具之间随机选择。

分层设计带来的好处：
- 常见任务通过便捷函数一次完成，减少调用轮次
- 便捷函数内部可以做智能处理（去噪、聚合、格式化），不需要 Agent 自己处理
- 底层函数作为逃生舱口，保留了灵活性
- Agent 通过描述知道什么时候该用哪一层

---

## 返回值：为下一步决策服务

工具的返回值设计，最常见的错误是**把调试视角当成 Agent 视角**。

开发者调试时想看到完整的原始数据；Agent 在决策时需要的是“够用的、结构清晰的信息”。这两个目标经常冲突。

### 去噪：只返回 Agent 需要的

```python
# 返回了太多噪音
def get_pull_request(pr_number: int) -> dict:
    response = github_api.get(f"/pulls/{pr_number}")
    return response.json()  # 返回 GitHub API 的完整响应，60+ 个字段

# Agent 实际需要的
def get_pull_request(pr_number: int) -> dict:
    response = github_api.get(f"/pulls/{pr_number}")
    data = response.json()
    return {
        "number": data["number"],
        "title": data["title"],
        "state": data["state"],          # open / closed / merged
        "author": data["user"]["login"],
        "created_at": data["created_at"],
        "body": data["body"][:500],      # 截断过长的描述
        "files_changed": data["changed_files"],
        "additions": data["additions"],
        "deletions": data["deletions"],
        "labels": [l["name"] for l in data["labels"]],
    }
```

原始 GitHub API 响应包含 PR 的头像 URL、节点 ID、各种链接、内部 ID 等 Agent 永远不会用到的字段。把这些全部返回，只会稀释 context 里真正有用的信息密度。

### 元信息：帮助 Agent 判断结果质量

光有数据不够，Agent 还需要知道这份数据的**可靠性和完整性**：

```python
def search_documents(query: str, limit: int = 5) -> dict:
    results = vector_db.search(query, limit=limit)
    total_count = vector_db.count(query)

    return {
        "query": query,
        "total_matches": total_count,     # 告诉 Agent 总共找到多少
        "returned": len(results),          # 告诉 Agent 返回了多少
        "results": [
            {
                "title": r.title,
                "snippet": r.snippet,
                "relevance_score": round(r.score, 3),  # 相关度
                "source": r.source,
                "last_updated": r.updated_at,          # 时效性
            }
            for r in results
        ],
        # 引导 Agent 做出正确判断
        "note": (
            f"找到 {total_count} 条匹配，返回了相关度最高的 {len(results)} 条。"
            f"{'如果结果不满足需求，可以调整查询关键词。' if total_count == 0 else ''}"
        )
    }
```

`total_matches` 和 `returned` 的差值告诉 Agent：还有更多结果没有返回，如果当前结果不够用，可以调整策略。`relevance_score` 让 Agent 知道这些结果的可信度。`last_updated` 让 Agent 能判断信息是否可能已经过期。

这些元信息不是给开发者看的，是给 Agent 的决策依据。

### 截断：明确告知而不是静默截断

当返回内容过长时，截断是必要的，但截断方式很重要：

```python
def read_file(path: str, max_lines: int = 200) -> dict:
    with open(path) as f:
        lines = f.readlines()

    total_lines = len(lines)
    returned_lines = lines[:max_lines]
    was_truncated = total_lines > max_lines

    return {
        "path": path,
        "total_lines": total_lines,
        "content": "".join(returned_lines),
        "truncated": was_truncated,
        # 如果被截断，告诉 Agent 还剩多少，以及如何获取剩余内容
        "truncation_note": (
            f"文件共 {total_lines} 行，已返回前 {max_lines} 行。"
            f"如需查看后续内容，请使用 read_file_range(path, "
            f"start_line={max_lines+1}) 获取。"
        ) if was_truncated else None
    }
```

静默截断（只返回前 N 行，不说明）会让 Agent 误以为已经看到了完整内容，基于不完整信息做出错误判断。明确告知截断情况，Agent 才能决定是否需要继续读取。

---

## 错误信息：Agent 的决策输入

这是被低估最多的部分。工具的错误信息不只是给开发者看的日志，**它是 Agent 在工具调用失败时的唯一决策依据**。

### 典型的糟糕错误信息

```python
# 这些错误信息对 Agent 几乎没有帮助
raise Exception("操作失败")
raise Exception("无效输入")
raise ValueError("参数错误")
return {"error": True, "message": "Something went wrong"}
```

Agent 看到这些信息后，只知道“出错了”，但不知道为什么出错、是否可以重试、应该换什么参数。结果往往是：重试相同的调用（无效），或者直接放弃（过早）。

### 为 Agent 设计的错误信息

好的错误信息需要包含三个要素：**错误原因**（发生了什么）、**诊断信息**（具体的上下文）、**恢复建议**（下一步该怎么做）。

```python
class ToolError(Exception):
    def __init__(self, code: str, message: str,
                 context: dict = None, suggestion: str = None):
        self.code = code
        self.message = message
        self.context = context or {}
        self.suggestion = suggestion
        super().__init__(self.to_agent_message())

    def to_agent_message(self) -> str:
        parts = [f"[{self.code}] {self.message}"]
        if self.context:
            parts.append(f"上下文：{self.context}")
        if self.suggestion:
            parts.append(f"建议：{self.suggestion}")
        return "\n".join(parts)


# 实际使用
def query_database(sql: str, database: str) -> dict:
    if database not in AVAILABLE_DATABASES:
        raise ToolError(
            code="DATABASE_NOT_FOUND",
            message=f"数据库 '{database}' 不存在",
            context={
                "requested": database,
                "available": list(AVAILABLE_DATABASES.keys())
            },
            suggestion=(
                f"可用的数据库为：{list(AVAILABLE_DATABASES.keys())}。"
                f"请检查数据库名称是否正确，注意大小写。"
            )
        )

    try:
        result = db.execute(sql)
    except SyntaxError as e:
        raise ToolError(
            code="SQL_SYNTAX_ERROR",
            message="SQL 语句存在语法错误",
            context={"sql": sql, "error_detail": str(e)},
            suggestion=(
                "请检查 SQL 语法。常见问题：缺少引号、括号不匹配、"
                "列名或表名错误。可以先用 get_schema() 确认表结构。"
            )
        )
    except PermissionError:
        raise ToolError(
            code="PERMISSION_DENIED",
            message=f"当前凭证无权查询数据库 '{database}'",
            context={"database": database, "operation": "SELECT"},
            suggestion=(
                "此操作需要更高权限。如果你认为应该有此权限，"
                "请联系管理员，或尝试使用只读副本数据库 'readonly_replica'。"
            )
        )
```

Agent 看到 `DATABASE_NOT_FOUND` 错误，并且错误里列出了可用的数据库名，就能立即知道下一步是检查数据库名称，或者从可用列表里选一个。这比看到“操作失败”要有效得多。

### 错误码的价值

结构化的错误码（`DATABASE_NOT_FOUND`、`SQL_SYNTAX_ERROR`）让 Agent 可以做**模式匹配**而非文本理解。在 system prompt 里可以这样写：

```python
TOOL_FAILURE_HANDLING = """
工具调用失败时的处理策略：
- DATABASE_NOT_FOUND：检查数据库名称，使用返回的可用列表重试
- SQL_SYNTAX_ERROR：修正 SQL 语法后重试，可先调用 get_schema() 确认表结构
- PERMISSION_DENIED：换用权限更低的只读工具，或停止并告知用户
- RATE_LIMITED：等待 5 秒后重试，最多重试 3 次
- TIMEOUT：将任务拆分成更小的查询重试
"""
```

这样 Agent 对不同类型的错误有不同的处理策略，而不是对所有失败一视同仁地重试或放弃。

---

## 状态：显式优于隐式

为人设计的工具经常有隐含的状态：`client.connect()` 之后才能 `client.query()`，某个操作必须在另一个完成之后才有效。人类可以通过文档和经验维护这种状态，Agent 很难做到。

```python
# 有状态的 API：对 Agent 不友好
client = DatabaseClient()
client.connect(host, port)        # Agent 需要记住连接状态
client.authenticate(user, passwd) # Agent 需要记住认证状态
result = client.query(sql)        # 只有前两步都完成才有效

# 无状态的 API：对 Agent 友好
result = query_database(
    sql=sql,
    connection={"host": host, "port": port},
    auth={"user": user, "password": passwd}
)
```

无状态设计让每次工具调用都是完整的、独立的，Agent 不需要在多次调用之间维护隐含的状态机。这对 Agent 来说既更安全（不会因为忘记某个步骤导致错误），也更容易理解（每次调用的语义都是完整的）。

如果确实需要有状态的操作（比如长时间运行的任务），把状态显式化：

```python
# 显式状态管理
def start_analysis(config: dict) -> dict:
    """启动分析任务，返回任务 ID"""
    task_id = create_task(config)
    return {
        "task_id": task_id,
        "status": "running",
        "note": f"使用 get_analysis_status('{task_id}') 查询进度"
    }

def get_analysis_status(task_id: str) -> dict:
    """查询分析任务的进度和结果"""
    task = get_task(task_id)
    return {
        "task_id": task_id,
        "status": task.status,  # running / completed / failed
        "progress": task.progress,
        "result": task.result if task.status == "completed" else None,
        "error": task.error if task.status == "failed" else None,
    }
```

`task_id` 是显式的状态令牌，Agent 知道它的存在，并且通过工具描述知道如何使用它。

---

## 一个完整的设计评审清单

设计或评审一个工具接口时，可以对照这份清单：

```
粒度
□ 这个工具是否覆盖了最常见的使用场景，不需要多次调用？
□ 对于不常见的场景，是否有更底层的工具作为补充？
□ 工具描述里是否说明了使用优先级（首选 / 备选）？

返回值
□ 返回的字段 Agent 是否都会用到？有没有明显的噪音字段？
□ 如果内容被截断，是否明确告知了截断情况和获取剩余的方式？
□ 是否包含帮助 Agent 判断结果质量的元信息（总数、相关度、时效性）？

错误处理
□ 每种错误是否有对应的错误码？
□ 错误信息是否包含具体的上下文（而不只是“操作失败”）？
□ 错误信息是否包含恢复建议（下一步该怎么做）？

状态
□ 工具是否无状态？如果有状态，状态是否显式化？
□ 对于有副作用的操作，错误时是否说明了哪些操作已完成、哪些未完成？

描述
□ 工具描述是否明确说明了适用场景？
□ 是否明确说明了不适用的场景或限制？
□ 参数描述是否包含格式、示例、枚举值？
```

---

## 总结

工具接口设计是 Agent 工程里一个容易被忽视的杠杆点。开发者往往把精力集中在 prompt 设计和模型选择上，而把工具接口当成一个简单的“API 包装”来处理。

但工具的返回质量是 Agent 决策质量的上限，工具的错误信息是 Agent 错误恢复能力的直接决定因素。一个设计良好的工具接口，能让 Agent 用更少的调用轮次完成更复杂的任务；一个设计糟糕的工具接口，会把原本可以完成的任务拖垮。

核心原则用一句话总结：**工具是为 Agent 的下一步决策服务的，而不是为开发者的调试方便服务的。** 当这两个目标冲突时，优先考虑前者。

---

*参考：字节技术团队《Agentic Coding 实践》[原文](https://mp.weixin.qq.com/s/Zlwn42KyfjgwfX6lp-JthQ)（需微信登录）*

*下一篇：[多 Agent 协作：当一个 Agent 不够用时，如何让多个 Agent 分工合作](/agent/multi-agent-collaboration/)*
