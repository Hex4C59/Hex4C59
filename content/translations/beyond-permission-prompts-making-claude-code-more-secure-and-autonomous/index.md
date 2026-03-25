+++
title = "超越权限提示：让 Claude Code 更安全、更自主"
date = 2026-03-25T12:00:00+08:00
lastmod = 2026-03-25T12:00:00+08:00
draft = false
author = "Hex4C59"
description = "介绍 Claude Code 的权限模型与审批疲劳，以及基于操作系统能力的沙箱：文件系统隔离、网络隔离、沙箱化 bash，与云端 Claude Code 的凭据隔离设计。"
summary = "用原生沙箱在固定边界内放手让 Claude 干活，减少反复点「批准」的同时降低 prompt injection 风险。"
tags = []
categories = ["Translations"]
topics = ["claude-code", "security", "sandboxing"]
translation_category = "安全"
original_title = "Beyond permission prompts: making Claude Code more secure and autonomous"
original_url = "https://claude.com/blog/beyond-permission-prompts-making-claude-code-more-secure-and-autonomous"
original_author = "Anthropic"
original_date = "2025-10-08"
original_site = "Claude Blog"
ShowToc = true
+++

> **译文信息**  
> - 原文：[Beyond permission prompts: making Claude Code more secure and autonomous](https://claude.com/blog/beyond-permission-prompts-making-claude-code-more-secure-and-autonomous)  
> - 作者：Anthropic  
> - 原文发布：2025-10-08  
> - 翻译发布：2026-03-25（东八区）

在 Claude Code 里，Claude 会与你一起编写、测试和调试代码：浏览代码库、编辑多个文件、运行命令验证结果。把这么大的权限交给 Claude 会带来风险，尤其是在 **prompt injection（提示注入）** 场景下——例如误删你本不想删的文件。

为缓解这一问题，我们在 Claude Code 中推出了两项基于 **沙箱（sandboxing）** 的新能力：既给开发者更安全的作业空间，也让 Claude 在更少权限弹窗的前提下更自主地运行。这两项能力是 **原生沙箱（native sandboxing）** 的示例：预先划定 Claude 可自由行动的边界，在边界内提升安全性与能动性。

## 我们当前如何保障用户安全

Claude Code 采用 **基于权限的模型**：默认偏只读，在修改文件或执行命令前会征求许可。也有例外：我们用静态分析自动放行 `echo`、`cat` 等相对安全的命令，但大多数操作仍需要用户明确批准。

不断点击「批准」会拖慢开发，还可能带来 **审批疲劳（approval fatigue）**——用户不再仔细看清自己点了什么。我们希望在更安全的同时也更高效，因此需要更好的办法。

## 沙箱：更安全、也更自主的路线

沙箱通过 **预定义边界**，让 Claude 在边界内更自由地工作，而不必为每个动作都弹一次权限。

随着 Claude Code 的更新，我们正在转向这一思路。沙箱实现依托 **操作系统级能力**，并支撑上述两项新能力；边界上可以概括为两件大事：

1. **文件系统隔离（Filesystem isolation）**：Claude 只能访问或修改指定目录。这对防止被注入的 Claude 改动敏感系统文件尤其关键。
2. **网络隔离（Network isolation）**：Claude 只能连接经批准的远端。这能降低被注入的 Claude **外泄敏感信息** 或 **下载恶意软件** 的风险。

值得强调：**有效的沙箱需要文件系统隔离与网络隔离同时具备**。没有网络隔离，被攻陷的 agent 可能把 SSH 密钥等敏感文件外传；没有文件系统隔离，被攻陷的 agent 可能轻易逃出沙箱并获得网络访问。两者一起用，才能为 Claude Code 用户提供更安全的 agent 体验。

### Claude Code 中的两项沙箱能力

#### 沙箱化 bash：更少权限提示下的安全命令执行

我们发布了一个新的 **沙箱运行时**（目前为 **research preview**），让你精确指定 agent 可访问的目录与网络主机，而无需起停完整容器。它可用于沙箱化任意进程、agent 与 MCP 服务器；并以开源研究预览形式发布：[anthropic-experimental/sandbox-runtime](https://github.com/anthropic-experimental/sandbox-runtime)。

在 Claude Code 中，我们用该运行时 **沙箱化 bash 工具**：Claude 在你设定的限制内执行命令。这些命令默认更安全、需要的用户授权更少，因此 Claude 能更自主地运行。若 Claude 试图访问 **沙箱外** 的资源，你会立刻收到通知，并可选择是否允许。

实现上，我们基于 **Linux [bubblewrap](https://github.com/containers/bubblewrap)** 与 **macOS Seatbelt** 等 OS 级原语在系统层落实限制；覆盖范围不仅包括 Claude Code 的直接操作，也包括命令所启动的脚本、程序与子进程。

如上所述，该沙箱同时落实：

1. **文件系统隔离**：允许对当前工作目录读写，但 **禁止修改其外的文件**。
2. **网络隔离**：仅允许通过 **Unix 域套接字** 连接沙箱外运行的代理来访问互联网。该代理限制进程可连接的域名，并对 **新请求的域名** 处理用户确认。若你需要更高安全级别，还可以 **自定义该代理**，对出站流量施加任意规则。

两部分均可配置：你可以按需放行或拒绝特定路径或域名。

沙箱保证：即便发生成功的 prompt injection，影响也被 **完全隔离**，不会波及用户整体安全。这样，被攻陷的 Claude Code 难以窃取你的 SSH 密钥，也难以向攻击者控制的服务器「回拨」。

启用方式：运行 `claude --sandbox`。安全模型与配置的更多技术说明见官方文档：[Claude Code 沙箱（Sandboxing）](https://docs.claude.com/en/docs/claude-code/sandboxing)。

为方便其他团队构建更安全的 agent，我们已将相关沙箱能力 **开源**（见上文仓库）。我们也希望更多 AI 公司能在自家 agent 中采用类似技术，以提升整体安全态势。

#### Claude Code on the web：在云端安全运行 Claude Code

我们还发布了 **Claude Code on the web**，让用户在云端隔离沙箱中运行 Claude Code。每次会话在独立沙箱中执行，在设计上既能安全地使用其所需的服务器侧能力，又避免把敏感凭据暴露给不可信代码。

沙箱设计目标之一是：**敏感凭据（如 git 凭据、签名密钥等）不进入与不可信代码同处的沙箱环境**。这样，即便沙箱内运行的代码被攻陷，用户仍可避免进一步损失。

Claude Code on the web 使用 **自定义代理服务** 透明处理所有 git 操作。沙箱内的 git 客户端用 **定制、受限的凭据** 向该服务认证；代理校验凭据与 git 操作内容（例如确保只推送到配置的 branch），再在发往 GitHub 等远端前附上正确的认证 token。

## 上手

沙箱化 bash 与 Claude Code on the web 在 **安全性** 与 **效率** 上对使用 Claude 做工程的开发者都有明显提升。

可以这样开始：

1. 运行 `claude --sandbox`，并阅读 [沙箱配置文档](https://docs.claude.com/en/docs/claude-code/sandboxing)。
2. 打开 [claude.com/code](https://claude.com/code) 体验 Claude Code on the web。

若你在自研 agent，也可以研究上述开源沙箱代码，并考虑集成进自己的工作流。我们期待看到你基于这些能力做出的产品。

## 译注

- 英文原文页面在个别句子与链接处存在明显草稿痕迹（如合并词句、占位链接）；译文按 **通顺语义** 整理，并为开源仓库与文档补充了当前公开的官方链接；若与日后官网修订不一致，**以英文原文页面为准**。

## 转载与版权

本文为 [Anthropic](https://www.anthropic.com/) 旗下 [Claude 官方博客](https://claude.com/blog/) 文章的**非官方中文译文**，仅用于技术学习与讨论；著作权与最终解释权归原作者及 Anthropic 所有。
