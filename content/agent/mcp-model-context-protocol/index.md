+++
title = "MCP：让 Agent 的工具生态不再各自为战"
date = 2026-03-23T20:00:00+08:00
draft = false
author = "Hex4C59"
description = "从工具集成的 N×M 问题出发，系统解析 MCP 的架构设计、核心原语、传输机制与安全模型，说明它为什么可能成为 Agent 工具层的基础协议。"
summary = "系统分析 Model Context Protocol（MCP）的设计动机、三层架构（Host-Client-Server）、三种原语（Tools / Resources / Prompts）、传输机制与安全边界，结合实际代码示例说明如何构建和接入 MCP Server。"
tags = ["Agent", "MCP", "Tool Use", "Protocol", "LLM"]
categories = ["Agent"]
series = ["agent-engineering"]
series_order = 11
difficulty = "intermediate"
article_type = "concept"
topics = ["mcp", "tool-use", "protocol", "architecture", "agent"]
frameworks = ["Anthropic", "OpenAI"]
ShowToc = true
+++

在 [Tool Use](/agent/tool-use-core-of-agent/) 那篇里，我在最后提到过 MCP：当 Tool Use 要走向规模化复用时，工具生态的标准化就成了绕不开的问题。在[工具接口设计](/agent/tool-interface-design/)那篇里，我们讨论了面向 Agent 的工具应该怎么设计——粒度、返回值、错误处理、状态管理。

但那两篇都有一个隐含假设：工具是你自己写的，集成逻辑也是你自己控的。

现实往往不是这样。你可能想让 Agent 同时用上 GitHub、Slack、数据库、本地文件系统、Jira、Notion——这些工具来自不同的提供方，每个都有自己的 API 风格、认证方式和数据格式。如果每个 Agent 框架都要自己写一遍这些适配层，整个生态就会陷入重复造轮子的困局。

MCP（Model Context Protocol）要解决的，就是这个问题。

---

## 先给结论

1. **MCP 的核心价值是把工具集成从 N×M 问题变成 N+M 问题。** N 个 Agent 客户端和 M 个工具提供方，不需要各写一遍适配，只要双方都遵守同一套协议，就能直接互通。
2. **MCP 是一个开放协议，不是一个框架。** 它定义的是 Host、Client、Server 三层之间的通信规范，不绑定任何特定模型或 Agent 框架。
3. **MCP 提供三种原语：Tools（工具）、Resources（资源）和 Prompts（提示模板）。** 其中 Tools 是最核心的——模型可以主动调用；Resources 是被动读取的数据源；Prompts 是可复用的交互模板。
4. **MCP 的安全模型基于信任边界分层。** Host 控制用户交互和授权策略，Client 负责与 Server 的协议通信，Server 只暴露能力不触碰模型——三层各司其职，权限不互相穿透。
5. **MCP 已经在主流 Agent 产品中落地。** Cursor、Claude Desktop、Windsurf、Claude Code 都已原生支持 MCP，生态在快速增长。

---

## 工具集成的 N×M 问题

在没有标准协议之前，每个 Agent 应用要接入一个外部工具，都需要自己写一套集成逻辑：理解工具的 API、处理认证、解析返回格式、包装成模型能理解的工具描述。

假设有 N 个 Agent 应用（Cursor、Claude Desktop、自研 Agent、其他 IDE 插件……），M 个工具提供方（GitHub、Slack、PostgreSQL、文件系统、搜索引擎……），那么需要的集成工作量是 N×M。

```text
Agent A ──┬── GitHub 适配层
          ├── Slack 适配层
          ├── PostgreSQL 适配层
          └── 文件系统适配层

Agent B ──┬── GitHub 适配层（重新写一遍）
          ├── Slack 适配层（重新写一遍）
          ├── PostgreSQL 适配层（重新写一遍）
          └── 文件系统适配层（重新写一遍）

Agent C ──┬── ...
```

这不仅浪费开发资源，还导致了一个更严重的问题：**工具的质量取决于谁来写适配层。** 同一个 GitHub API，不同 Agent 框架包装出来的工具描述、错误处理、返回格式可能完全不同。在[工具接口设计](/agent/tool-interface-design/)里讨论过的那些设计原则——粒度、返回值去噪、结构化错误——每个集成方都需要独立实现一遍，质量参差不齐。

MCP 的解法是在中间插入一层标准协议：

```text
Agent A ─┐                ┌── GitHub MCP Server
Agent B ─┤── MCP 协议 ──├── Slack MCP Server
Agent C ─┘                ├── PostgreSQL MCP Server
                          └── 文件系统 MCP Server
```

工具提供方只需要实现一个 MCP Server，所有兼容 MCP 的 Agent 客户端就能直接接入。集成工作量从 N×M 降到 N+M。

这和 USB 解决外设连接问题的逻辑是一样的。在 USB 之前，每种外设都需要专用接口；有了 USB，设备只要遵守同一个协议标准，就能即插即用。MCP 想成为 AI Agent 工具层的"USB"。

---

## MCP 的三层架构

MCP 把整个系统分成三个角色：Host、Client 和 Server。

```text
┌─────────────────────────────────────────┐
│  Host（宿主应用）                         │
│  例如：Cursor、Claude Desktop            │
│                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Client A│ │ Client B│ │ Client C│   │
│  └────┬────┘ └────┬────┘ └────┬────┘   │
└───────┼───────────┼───────────┼─────────┘
        │           │           │
   MCP 协议     MCP 协议     MCP 协议
        │           │           │
   ┌────┴────┐ ┌────┴────┐ ┌────┴────┐
   │ Server A│ │ Server B│ │ Server C│
   │ (GitHub)│ │ (Slack) │ │  (DB)   │
   └─────────┘ └─────────┘ └─────────┘
```

### Host

Host 是面向用户的应用程序，比如 Cursor、Claude Desktop、你自己写的 Agent 应用。它负责：

- 创建和管理 Client 实例
- 控制用户交互和授权策略（比如"这个工具调用需要用户确认"）
- 把 Client 发现的工具注册到模型的上下文里
- 执行安全策略，决定哪些工具可以自动执行、哪些需要人工批准

Host 是信任链的最上层。用户信任 Host，Host 信任（或不信任）各个 Server。

### Client

Client 是 Host 内部的协议层，负责和 Server 建立连接、维护协议状态。每个 Client 实例和一个 Server 保持一对一的连接。

Client 的职责是纯粹的协议通信：

- 发送 `initialize` 请求，完成能力协商
- 调用 Server 暴露的 Tools / Resources / Prompts
- 处理 Server 端的通知和状态更新
- 维护连接的生命周期

Client 不直接面向用户，也不直接和模型交互。它是 Host 和 Server 之间的桥梁。

### Server

Server 是工具或数据的实际提供方。每个 Server 封装一组特定的能力：

- 一个 GitHub MCP Server 可能暴露 `create_issue`、`list_pull_requests`、`get_file_contents` 等工具
- 一个 PostgreSQL MCP Server 可能暴露 `query`、`list_tables`、`describe_table` 等工具
- 一个文件系统 MCP Server 可能暴露 `read_file`、`write_file`、`list_directory` 等工具

Server 不需要知道谁在调用它，也不需要知道上游是什么模型。它只需要实现 MCP 协议规定的接口，暴露自己的能力描述和执行逻辑。

这种分层的好处是职责清晰：**Server 只管"我能做什么"，Client 只管"怎么通信"，Host 只管"要不要执行、怎么展示给用户"。** 三层各自独立演进，互不依赖。

---

## 三种核心原语

MCP 定义了三种原语（Primitive），对应 Agent 在与外部世界交互时的三种基本需求。

### Tools：模型主动调用的能力

Tools 是 MCP 里最核心的原语。它和我们在 [Tool Use](/agent/tool-use-core-of-agent/) 里讨论的概念完全一致：模型在推理过程中判断需要调用外部能力，生成一个结构化的调用请求，系统执行后把结果回传给模型。

MCP 规范中，一个 Tool 的描述长这样：

```json
{
  "name": "create_issue",
  "description": "Create a new issue in a GitHub repository. Use this when you need to report a bug, request a feature, or track a task.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "repo": {
        "type": "string",
        "description": "Repository in owner/repo format, e.g. 'anthropics/mcp'"
      },
      "title": {
        "type": "string",
        "description": "Issue title, should be concise and descriptive"
      },
      "body": {
        "type": "string",
        "description": "Issue body in Markdown format"
      },
      "labels": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Labels to apply, e.g. ['bug', 'priority:high']"
      }
    },
    "required": ["repo", "title"]
  }
}
```

这个结构和 OpenAI 的 function calling 定义很像，但 MCP 把它标准化了——无论是哪个 Server 提供的工具，描述格式都是一样的。Host 拿到这些描述后，可以直接转换成任何模型 API 能理解的 tools 参数。

**关键特征：Tools 的控制权在模型侧。** 模型决定要不要调用、调用哪个、传什么参数。Host 可以加一层确认（比如有副作用的操作弹窗让用户批准），但调用的发起者始终是模型。

### Resources：被动读取的数据源

Resources 代表 Server 可以提供的数据——文件内容、数据库 schema、API 文档、配置信息等。和 Tools 不同，Resources 通常不是模型主动调用的，而是由 Host 或用户主动选择后注入到模型的上下文里。

```json
{
  "uri": "file:///workspace/src/main.py",
  "name": "main.py",
  "description": "Application entry point",
  "mimeType": "text/x-python"
}
```

Resources 的 URI 可以是文件路径、数据库标识、API 端点等。Host 通过 `resources/list` 获取可用资源列表，通过 `resources/read` 读取具体内容。

**Resources 和 Tools 的区别在于控制权：** Tools 由模型决定是否调用，Resources 由应用层或用户决定是否加载到上下文。这个区分很重要——它意味着 Resources 不会被模型"过度调用"，也不需要在 system prompt 里花费 token 来描述每个 Resource。

一个典型场景：用户在 Cursor 里用 `@` 符号引用了一个数据库的表结构，Cursor 通过 MCP 的 Resources 接口读取这个结构，注入到模型的上下文里。模型不需要主动调用任何工具就能看到这些信息。

### Prompts：可复用的交互模板

Prompts 是预定义的提示模板，由 Server 提供，用户可以选择使用。

```json
{
  "name": "code_review",
  "description": "Review code for bugs, security issues, and best practices",
  "arguments": [
    {
      "name": "code",
      "description": "The code to review",
      "required": true
    },
    {
      "name": "focus",
      "description": "Specific area to focus on: security, performance, readability",
      "required": false
    }
  ]
}
```

当用户选择一个 Prompt 模板时，Server 会根据参数生成一组完整的消息（可能包含 system message、user message、甚至预填的 assistant message），直接注入到对话中。

Prompts 的使用频率不如 Tools 和 Resources，但它在某些场景下很有价值：比如一个安全审计 MCP Server 可以提供标准化的审计流程模板，确保每次审计都遵循相同的检查清单。

### 三种原语的对比

| | Tools | Resources | Prompts |
|---|---|---|---|
| 控制方 | 模型（LLM 决定是否调用） | 应用/用户（主动选择加载） | 用户（主动选择使用） |
| 典型用途 | 执行操作、查询数据 | 提供上下文信息 | 标准化交互流程 |
| 对上下文的影响 | 每次调用都产生结果消息 | 注入一次，持续可见 | 生成完整消息序列 |
| 是否有副作用 | 可能有（写数据、发消息） | 通常没有（只读） | 没有（只生成消息） |

---

## 传输机制

MCP 是一个基于 JSON-RPC 2.0 的协议，支持两种主要的传输方式。

### stdio（标准输入输出）

Client 以子进程方式启动 Server，通过 stdin/stdout 通信。

```text
Host 进程
  └── 启动子进程: python server.py
        ├── stdin  ← Client 发请求
        └── stdout → Client 收响应
```

这是本地场景下最常见的方式。Cursor、Claude Desktop 接入本地 MCP Server 时默认用 stdio。优势是简单、无需网络配置、进程隔离天然提供了安全边界。

配置通常长这样：

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxx"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/projects"]
    }
  }
}
```

### Streamable HTTP

远程场景下使用 HTTP 传输。Client 通过 HTTP POST 发送 JSON-RPC 请求，Server 可以返回普通 JSON 响应，也可以升级为 SSE（Server-Sent Events）流式推送进度。

```text
Client ──HTTP POST──→ Server
Client ←──SSE 流────── Server（可选，用于流式进度）
```

Streamable HTTP 适合 Server 运行在远程服务器上的场景——比如企业内部的数据库 MCP Server 部署在内网，多个开发者的 Agent 客户端远程接入。

两种传输方式在协议层面是透明的：同一个 Server 实现可以同时支持 stdio 和 HTTP，Client 不需要关心底层用的是哪种传输。

---

## 连接生命周期

一次 MCP 连接从建立到关闭，经历三个阶段。

### 1. 初始化：能力协商

Client 发送 `initialize` 请求，告诉 Server 自己支持哪些协议版本和能力：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-03-26",
    "capabilities": {
      "roots": { "listChanged": true }
    },
    "clientInfo": {
      "name": "Cursor",
      "version": "1.0.0"
    }
  }
}
```

Server 返回自己的能力声明：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-03-26",
    "capabilities": {
      "tools": { "listChanged": true },
      "resources": { "subscribe": true },
      "prompts": { "listChanged": true }
    },
    "serverInfo": {
      "name": "github-mcp-server",
      "version": "0.5.0"
    }
  }
}
```

能力协商的作用是双方对齐预期。如果 Server 声明了 `tools` 能力，Client 就知道可以调用 `tools/list` 和 `tools/call`。如果 Server 没有声明 `resources`，Client 就不会尝试读取资源。

### 2. 正常操作

初始化完成后，双方进入正常通信阶段。典型的调用流程：

```text
Client → tools/list          获取可用工具列表
Client ← [工具描述数组]

Client → tools/call           调用某个工具
         { name: "create_issue", arguments: {...} }
Client ← { content: [...] }  工具执行结果
```

这个阶段 Server 也可以主动发送通知，比如工具列表发生了变化（`notifications/tools/list_changed`），Client 收到后重新拉取工具列表。

### 3. 关闭

Client 发送 `close` 通知，或者直接断开连接（对于 stdio，就是终止子进程）。Server 清理资源。

整个生命周期设计得相当克制——没有复杂的状态机，没有心跳机制，连接模型是简单的请求-响应。这让实现一个 MCP Server 的门槛很低。

---

## 动手写一个 MCP Server

理论讲得再多，不如看一个完整例子。下面用 Python 的官方 MCP SDK 实现一个简单的笔记管理 MCP Server。

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("notes")

notes: dict[str, str] = {}


@mcp.tool()
def add_note(name: str, content: str) -> str:
    """
    Add a new note or update an existing one.

    Use this when the user wants to save information for later reference.
    The name should be descriptive, e.g. 'meeting-notes-2026-03-23'.

    Args:
        name: Unique identifier for the note (lowercase, hyphens allowed)
        content: The note content in plain text or Markdown
    """
    notes[name] = content
    return f"Note '{name}' saved ({len(content)} characters)"


@mcp.tool()
def get_note(name: str) -> str:
    """
    Retrieve a note by name.

    Use this when you need to recall previously saved information.
    If the note doesn't exist, returns a list of available notes.

    Args:
        name: The name of the note to retrieve
    """
    if name in notes:
        return notes[name]

    available = list(notes.keys()) if notes else []
    return (
        f"Note '{name}' not found. "
        f"Available notes: {available if available else '(none)'}"
    )


@mcp.tool()
def list_notes() -> str:
    """
    List all saved notes with their sizes.

    Use this to check what notes are available before trying to retrieve one.
    """
    if not notes:
        return "No notes saved yet."

    lines = [f"- {name} ({len(content)} chars)" for name, content in notes.items()]
    return f"Saved notes ({len(notes)} total):\n" + "\n".join(lines)


@mcp.resource("notes://list")
def notes_index() -> str:
    """All notes as a browsable index"""
    if not notes:
        return "No notes yet."
    return "\n".join(f"- {name}: {content[:80]}..." for name, content in notes.items())


if __name__ == "__main__":
    mcp.run()
```

这段代码做了几件事：

1. **用 `@mcp.tool()` 装饰器注册了三个工具。** 函数的 docstring 会自动变成工具描述，类型标注会变成参数 schema。这和在 [Tool Use](/agent/tool-use-core-of-agent/) 里讨论的工具描述设计完全对应——描述里说明了什么时候该用、什么时候不该用、参数格式是什么。
2. **`get_note` 的错误处理遵循了[工具接口设计](/agent/tool-interface-design/)里的原则。** 没有抛出一个空洞的 "not found" 错误，而是返回了可用笔记的列表，给模型一个明确的恢复路径。
3. **用 `@mcp.resource()` 暴露了一个 Resource。** Host 或用户可以主动读取这个资源，把笔记索引注入到上下文里。

要让 Cursor 或 Claude Desktop 接入这个 Server，只需要在配置里加一行：

```json
{
  "mcpServers": {
    "notes": {
      "command": "python",
      "args": ["notes_server.py"]
    }
  }
}
```

这就是 MCP 降低工具接入成本的直观体现：Server 开发者不需要知道上游是 Cursor 还是 Claude Desktop，不需要适配不同的 API 格式，只要遵守 MCP 协议就行。

---

## MCP 和直接 Function Calling 的区别

有人可能会问：我直接在 Agent 代码里定义 tools 传给模型 API 不就行了，为什么要绕一圈走 MCP？

对于简单场景，确实不需要 MCP。如果你的 Agent 只用到两三个自定义工具，直接写 function calling 是最简单的。MCP 解决的是另一类问题：

### 工具复用

你用 Python 写了一个很好用的 GitHub 工具集，但同事的 Agent 用的是 TypeScript。没有 MCP 的话，他要么自己重写一遍，要么想办法在 TypeScript 里调你的 Python 代码。有了 MCP，你只需要把它包装成 MCP Server，他的 TypeScript Agent 通过 MCP Client 就能直接用。

### 工具发现

Agent 在运行时不一定知道有哪些工具可用。MCP 的 `tools/list` 接口让 Agent 可以动态发现可用工具，而不是在编译时硬编码。Server 甚至可以在运行时增减工具，然后通过 `notifications/tools/list_changed` 通知 Client 更新。

### 关注点分离

直接写 function calling 时，工具的实现逻辑和 Agent 的调度逻辑混在一起。当工具数量增多、需要独立部署和维护时，这种耦合会变成负担。MCP 强制把工具实现（Server）和工具使用（Client/Host）分开，让两边可以独立迭代。

### 生态效应

这是最大的区别。当越来越多的工具提供方实现 MCP Server，越来越多的 Agent 框架支持 MCP Client，整个生态的网络效应就形成了。你今天为 Cursor 开发的 MCP Server，明天 Claude Desktop 的用户也能直接用。

```text
直接 Function Calling：
  Agent 代码 ←紧耦合→ 工具实现
  每换一个 Agent 框架就要重新适配

MCP：
  Agent (MCP Client) ←标准协议→ MCP Server ←→ 工具实现
  Server 写一次，所有 MCP 兼容的 Agent 都能用
```

当然，MCP 也引入了额外的复杂度：协议层的 overhead、Server 进程管理、连接状态维护。如果你的 Agent 是一个封闭的单体系统，不需要工具复用，直接 function calling 仍然是更简单的选择。

---

## 真实产品中的 MCP 落地

### Cursor

Cursor 是最早原生支持 MCP 的 IDE 级 Agent 之一。用户在项目的 `.cursor/mcp.json` 或全局配置中声明 MCP Server，Cursor 启动后自动连接，把 Server 暴露的 Tools 注册到 Agent 的工具列表里。

Cursor 的 MCP 集成有几个值得注意的设计：

- **自动发现**：Agent 在推理时可以看到所有已连接 MCP Server 的工具，像使用内置工具一样自然地调用
- **权限控制**：有副作用的工具调用（写文件、执行命令等）会弹窗请求用户确认
- **子 Agent 继承**：通过 Task 工具启动的子 Agent 可以继承父 Agent 的 MCP 工具集

### Claude Desktop

Claude Desktop 通过 `claude_desktop_config.json` 管理 MCP Server。配置方式和 Cursor 类似，支持 stdio 和 Streamable HTTP 两种传输。Claude Desktop 的 MCP 实现特别强调了 Resources 的使用——用户可以在对话中通过 UI 选择注入某个 Resource 的内容。

### Claude Code

Claude Code 除了支持标准的 MCP Server 配置，还利用 MCP 实现了一些更高级的功能。在[多 Agent 协作](/agent/multi-agent-collaboration/)里提到的 Agent Teams，每个 Teammate 都会加载项目配置的 MCP Server，这意味着所有 Agent 共享同一套外部工具集。

### 社区生态

MCP 的开源生态正在快速增长。官方维护了一批参考实现（GitHub、Slack、Google Drive、PostgreSQL、Puppeteer 等），社区也贡献了大量第三方 Server（Notion、Linear、Jira、各种数据库、云服务 API 等）。

这种增长是协议标准化带来的正反馈：可用的 Server 越多，Agent 客户端越有动力支持 MCP；支持 MCP 的 Agent 越多，工具提供方越有动力实现 MCP Server。

---

## 安全模型

工具能力越强，安全问题越重要。MCP 的安全设计基于几个层次。

### 信任边界

MCP 的三层架构天然定义了两道信任边界：

```text
用户 ──信任──→ Host ──有限信任──→ Server
                │
                └── Host 负责执行授权策略
```

- **用户信任 Host**：用户选择使用 Cursor 或 Claude Desktop，就意味着信任这个应用
- **Host 有限信任 Server**：Host 知道 Server 能做什么（通过能力协商），但不假设 Server 的行为一定安全
- **Server 不信任 Client 发来的内容**：Server 要做参数校验，不能把 Client 传来的内容直接当作可信输入执行

### 用户确认

对于有副作用的操作（写文件、发消息、执行命令），Host 应该在执行前请求用户确认。这是在 [Tool Use](/agent/tool-use-core-of-agent/) 里讨论过的"操作分级"原则在协议层的体现。

MCP 规范建议工具在描述中通过 `annotations` 标注自己的行为特征：

```json
{
  "name": "delete_file",
  "description": "Permanently delete a file from the filesystem",
  "inputSchema": { ... },
  "annotations": {
    "title": "Delete File",
    "readOnlyHint": false,
    "destructiveHint": true,
    "openWorldHint": false
  }
}
```

Host 可以根据这些标注决定授权策略：`readOnlyHint: true` 的工具自动执行，`destructiveHint: true` 的工具弹窗确认。

### 最小权限

每个 MCP Server 应该只暴露完成其职责所需的最小能力集。一个只做代码搜索的 Server 不应该暴露写文件的工具。这和在 [Tool Use](/agent/tool-use-core-of-agent/) 里讨论的最小权限原则完全一致。

### 数据隔离

MCP Client 不应该把不同 Server 的数据随意混在一起。一个 Server 的 Resource 内容不应该被发送给另一个 Server 的 Tool。Host 需要维护数据在不同 Server 之间的隔离。

---

## MCP 的局限与挑战

MCP 不是银弹。在实际使用中，它还面临一些真实的问题。

### 工具描述质量仍然参差不齐

MCP 标准化了工具描述的格式，但没有标准化描述的质量。一个 Server 开发者写的 `description` 是"Get data"还是精心设计的使用指南，完全取决于开发者自身的意识。而我们在[工具接口设计](/agent/tool-interface-design/)里讨论过，描述质量会直接影响模型的调用决策。

协议能保证格式统一，但保证不了语义质量。这一层仍然需要社区约定和最佳实践来推动。

### Server 质量和安全审计

任何人都可以发布一个 MCP Server，但用户很难判断一个第三方 Server 是否安全可靠。Server 可能存在安全漏洞、可能在工具调用时做了不该做的事、可能返回不准确的信息。

目前还没有一个成熟的 MCP Server 审计和信任评级机制。用户在使用第三方 Server 时需要自行评估风险。

### 状态管理

MCP 的连接模型是相对无状态的，但某些工具场景天然需要状态——比如数据库事务、多步骤文件编辑、长时间运行的任务。当前 MCP 的协议层对这些场景的支持还不够优雅，通常需要 Server 开发者自己在应用层实现状态管理。

### 性能开销

每次工具调用都要经过 JSON-RPC 序列化、进程间通信（stdio）或网络通信（HTTP）。对于高频工具调用场景（比如一个 Agent 在一轮推理中调用几十次文件系统操作），这些开销会累积起来。在延迟敏感的场景下，直接 function calling 仍然有优势。

---

## 总结

回到开头的问题：为什么 Agent 的工具生态需要 MCP？

因为工具集成的 N×M 问题，在 Agent 应用爆发式增长的背景下，已经成为整个生态的效率瓶颈。每个 Agent 框架各自实现一遍工具适配层，不仅浪费资源，还导致工具质量参差不齐、无法复用。

MCP 通过定义一套标准协议，把这个问题的复杂度从 N×M 降到 N+M：

- **三层架构**（Host-Client-Server）让职责清晰分离，各层独立演进
- **三种原语**（Tools-Resources-Prompts）覆盖了 Agent 与外部世界交互的核心需求
- **协议层的标准化**让工具写一次、到处可用，形成生态网络效应

但 MCP 也不是所有场景的最优解。对于简单、封闭的 Agent 系统，直接 function calling 仍然更轻量。MCP 的价值在规模化场景下才真正显现——当你需要接入多个第三方工具、当你希望工具能被不同 Agent 复用、当你想让工具生态像 npm 包一样即装即用时，MCP 提供的标准化价值是最大的。

从更长远的视角看，MCP 解决的不是某个单点能力问题，而是 Agent 工具层能不能形成真正的生态。协议有了，生态在增长，但工具描述质量、安全审计、性能优化这些工程问题，仍然需要社区持续推进。

---

*上一篇：[多 Agent 协作：当一个 Agent 不够用时，如何让多个 Agent 分工合作](/agent/multi-agent-collaboration/)*
