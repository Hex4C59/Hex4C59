+++
title = "什么是 Model Context Protocol？让 AI 连接你的世界"
date = 2026-03-25T12:00:00+08:00
lastmod = 2026-03-25T12:00:00+08:00
draft = true
author = "Hex4C59"
description = "介绍 Model Context Protocol（MCP）：开放标准如何统一 LLM 与外部系统的连接方式，以及 Connectors、开发者与企业场景的适用性。"
summary = "把 MCP 比作 LLM 的 USB-C：一端 MCP Client、一端 MCP Server，减少重复集成，让 agent 能读写真实工具与数据。"
tags = []
categories = ["Translations"]
topics = ["mcp", "model-context-protocol", "claude", "agents", "integrations"]
translation_category = "AI 与工具"
original_title = "What is Model Context Protocol? Connect AI to your world"
original_url = "https://claude.com/blog/what-is-model-context-protocol"
original_author = "Anthropic"
original_date = "2025-10-31"
original_site = "Claude Blog"
ShowToc = true
+++

> **译文信息**  
> - 原文：[What is Model Context Protocol? Connect AI to your world](https://claude.com/blog/what-is-model-context-protocol)  
> - 作者：Anthropic  
> - 原文发布：2025-10-31  
> - 翻译发布：2026-03-25（东八区）

AI 模型能发挥多大作用，取决于你给了它多少上下文。像 [Claude](https://claude.ai/) 这样的 AI 助手可以回答问题、完成许多复杂任务，但如果拿不到需要的数据或工具，能替你做的事就会受限。你通常会在各个标签页之间复制、粘贴上下文——无论是在 Google Drive 里改文档、在 Slack 里回帖，还是在 IDE 里改代码。这个过程慢、费手，还容易漏掉关键信息。

**Model Context Protocol（MCP）** 提供了一种开放、可在各类 AI 应用与助手中广泛采用的方案。本文将介绍 MCP 是什么、如何运作、为何重要、适合谁，并给出在 Claude 中的 Connectors 示例，以及如何开始接入或自建 MCP。

## 什么是 Model Context Protocol（MCP）？

**Model Context Protocol** 是一项开放标准，规定 LLM 如何与外部系统通信。

可以把 MCP 理解为 **面向 LLM 的 USB-C**。正如 USB-C 为手机、笔记本等设备提供统一接口，MCP 为 LLM 连接外部系统提供统一格式。在 USB-C 普及之前，每种设备往往各用各的线：iPhone 用 Lightning，Android 用 micro-USB，相机还有专有接口。随着更多设备采用 USB-C，整个生态里的连接变得顺畅。

MCP 为 AI 集成带来同样的简化。在 MCP 之前，每个应用、每个数据库往往都要写一套定制代码才能接到 LLM：Google Drive 一套、Slack 一套、Figma 又一套。现在，MCP 用单一、标准化的方式，把这些工具接到 Claude 及其他 AI 应用上。

## MCP 从何而来？

MCP 由 Anthropic 的 David Sorria Para 与 Justin Spahr-Summers 创建。起因是 David 在 Claude Desktop 与 IDE 之间反复拷贝代码感到厌烦。他意识到这是典型的 **M×N 问题**（多种应用 × 多种集成），于是向 Justin 提议做一套协议来解决。他们参考了广泛使用的 Language Server Protocol 进行设计，并于 2024 年 11 月在 Anthropic 支持下将其开源，以便整个 AI 生态都能受益。

## MCP 如何工作？

MCP 采用 **双边** 模型：Claude 等 AI agent 与聊天机器人实现 **MCP Client**，从而连接 Notion、Canva、Figma 等通过 **MCP Server** 暴露工具与数据的应用。

实现 **MCP Client** 后，AI agent 与聊天机器人可以接入社区构建的成千上万台 MCP Server，以直接路径扩展能力。实现 **MCP Server** 后，公司与开发者可以让产品更容易被 AI 调用，开辟新的价值场景。

MCP 是开源的，任何人都可以实现 Server 或 Client。

## 为什么 MCP 重要？

MCP 让 LLM 不局限于「聊天」，而能执行真实世界任务：读完邮件线程并回复、访问代码库并部署更新、阅读设计简报并生成初稿。该协议为 LLM 连接外部系统、工具与应用、获取数据并执行操作打下基础。它带来：

### 对 AI 的通用兼容

**AI 助手能接入成千上万种工具** — 一旦某助手实现了 MCP（通过 MCP client），即可即时连接大量 MCP 兼容应用，从专用编程工具到企业工作流平台，而无需为每个产品各写一套定制集成。

**工具与应用一次对接、多端 AI 共用** — Notion、Figma、Asana 等公司只需维护 **一个** MCP server，即可服务所有实现了 MCP client 的 AI 助手。开发者做一次集成，即可覆盖多种 AI 连接场景。

### 开放、AI 原生的生态

**任何人都可以构建与分享** — 作为开放标准，开发者或公司发布的 MCP server 可与任意 MCP client 互通。这种开放性催生了大量社区 server，加快了 AI 助手可用工具与应用的丰富度。

**让软件从设计上就便于 AI 使用** — 传统软件主要为人类和网页界面而造。MCP 提供面向 AI 交互的并行接口，使应用能真正 **AI-native**，从而带来 AI 模型与人们日常工具之间更好、更可靠的集成。

### Agent 的基础协议

MCP 为 AI agent 访问任意数量的服务与工具提供基础设施，支撑端到端任务自动化。随着更多应用采用该协议，AI agent 独立处理复杂多步工作流的设想会变得越来越可行。

## MCP 适合谁？

开发者可以用统一标准做一次集成，在任意兼容的 AI 上复用。企业可获得可扩展、可由 IT 管控的安全 AI 连接。普通用户无需技术背景，即可把常用工具接到 AI 上。

### 面向开发者：连接 AI 与应用的单一标准

开发者只需遵循同一套标准，即可把外部产品接到你们的 AI 应用与 agent 上。这能简化集成建设、增加可连接产品数量，并提升生态里连接方式的整体质量与安全。

在搭一个要接很多应用的 agent？还是在做一个要接很多 agent 的应用？MCP 让你进入兼容工具生态，并以更轻量的方式完成集成。

### 面向企业：组织内安全、可扩展的 AI 连接

企业能更高效地推动内部采用 AI 工具与应用，因为 MCP 简化了自有系统与 AI 的对接。这有助于让 AI 在组织内更「连成网」，扩展员工可用能力与场景。

### 面向消费者：一键接入常用工具

MCP 让终端用户在自己偏好的 AI 助手与工作工具之间无缝衔接，更容易自动化任务、少在标签页间复制粘贴。简而言之，MCP 让 AI 对你数字世界的访问与连接能力更强。

在 [Claude](https://claude.ai/) 中，你可以快速连接 MCP Server，在产品里称为 [**Connectors**](https://claude.com/partners/mcp)，从而把 Claude 接到常用工作应用上。

## Connectors（MCP）实战

当你用日常工具看到 MCP 落地时，价值最直观。下面是 Claude 中由 MCP 驱动的集成示例（即 **Connectors**）：

### Claude 中的 Canva

Canva Connector 让 Claude 直接在 Canva 里生成新设计。通过 MCP，Claude 可以调用 Canva 提供的工具，在画布上生成设计。

### Claude 中的 Notion 与 Linear

通过 Notion 与 Linear Connectors，Claude 可以读取你在 Notion 中的页面，并据此更新 Linear 中的工单。这里 MCP 把非结构化上下文顺畅转入另一套项目管理里的结构化工单。

### Claude Code 中的 Figma

Figma Connector 让 Claude 访问 Figma 中的设计，从而使 Claude Code 能基于 Figma 稿做出网站、应用或界面的可运行原型。

### 可用的 Claude Connectors

Claude Connectors 包括但不限于：

- **Notion**：工作区文档  
- **Linear**：问题跟踪  
- **Stripe**：支付相关数据  
- **Canva** 与 **Figma**：设计辅助  
- **HubSpot**：CRM 自动化  
- **Sentry**：错误追踪  
- ……还有更多  

每个 Connector 通常只需数秒即可完成配置，进入 Claude 的工作上下文。在 Claude 之外，开源生态里还有 [MCP Registry](https://modelcontextprotocol.io/) 上的大量 MCP server。

## 开始探索 MCP

可按需求选两条路径。

### Claude 中的 Connectors

[Connectors](https://claude.com/partners/mcp) 为预置集成，让 Claude 即时访问工具、数据库与应用，并为你扩展能力边界。打开 [Claude](https://claude.ai/directory)，浏览可用 Connectors，点击即可添加。

### 自建 MCP 连接

MCP 开源，任何人都可以采用它来把 AI 接到应用上。[Model Context Protocol 文档](https://modelcontextprotocol.io/) 说明了如何基于 MCP 构建。

## 上手建议

若想试用 MCP，可以先在 Claude 里找一个能立刻启用的 Connector。

若还没有现成的 MCP server，自建需要一些工作量；若熟悉 TypeScript 或 Python，难度并不高。[Model Context Protocol quickstart](https://modelcontextprotocol.io/quickstart) 提供可改写的示例。

## 常见问题

### MCP 只能用于 Claude 吗？

不是。MCP 是开源协议。虽然 Claude 较早推动 MCP 落地，其他 AI 提供商也已采用同一协议，从而可以接入同一套 MCP server 生态。

### 使用 MCP 需要会编程吗？

使用 [Connectors](https://claude.com/partners/mcp) 不需要：浏览、安装、完成认证即可。自建 MCP server 需要 TypeScript 或 Python 能力，但不断增长的 [Connector 库](https://claude.com/partners/mcp) 已覆盖多数主流工具。

### MCP 的安全模型是怎样的？

每个 server 会请求具体权限以允许 Claude 访问。你可以批准或拒绝访问，并随时撤销授权。

### MCP 性能如何？

MCP 使用高效的传输方式：本地 server 可用 stdio，开销很小；远端 server 可用 SSE（Server-Sent Events）与 Streamable HTTP 维持长连接。响应流式传输有助于在大数据操作上避免超时。协议还支持分页、过滤与部分响应，以便高效处理大数据集。
