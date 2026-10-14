---
title: "DeepSeek Harness"
description: "按源码与调用链研究 DeepSeek Harness：从插件运行时、模型与工具，到会话、权限、多 Agent、界面及工程验证。"
lastmod: 2026-10-14
series_start: "/agent/deepseek-harness-agent-engineering/"
series_status: "连载中"
---

这个系列面向希望理解 Coding Agent 实现的开发者。先从背景与完整请求链路建立认识，再逐项阅读服务、事件、配置、状态和失败处理；各篇会记录对应的源码版本与验证边界。

## 从这里开始

从[开篇：从代码补全到仓库级 Agent](/agent/deepseek-harness-agent-engineering/)了解 Harness 的职责，再读[第二篇：一次用户请求如何经过整个 dsh 系统](/articles/deepseek-harness-request-lifecycle/)，沿输入、模型、工具、日志和输出追踪完整链路。

## 阅读路线

后续篇章处于规划阶段，随源码研究继续拆分；已发布文章会加入本页目录。

| 篇章 | 主题 | 主要研究内容 |
|---|---|---|
| 01 | 导读与系统全貌 | 背景、请求链路、源码地图和应用入口 |
| 02 | Cordis 插件运行时 | 服务、事件、依赖、生命周期与配置 |
| 03 | Agent 与模型调用 | Turn、Step、流式响应、重试与取消 |
| 04 | Prompt 与上下文 | 指令、引用、工作目录与上下文压缩 |
| 05 | 会话与持久化 | 事件、投影、存储、恢复与格式迁移 |
| 06 | 工具系统与文件操作 | 工具注册、执行、文件编辑与大输出 |
| 07 | 进程、终端与安全边界 | Shell、沙箱、审批、凭据与远程执行 |
| 08 | 外部能力与资源 | Web、MCP、Skill、浏览器、附件与交付 |
| 09 | 多 Agent 与任务执行 | Subagent、后台 Jobs、PTC 与 Workflow |
| 10 | 计划、目标与人机协作 | Plan、Todo、Goal、Schedule 与用户交互 |
| 11 | Web Host 与客户端 | 远程调用、通信、状态、渲染与设置 |
| 12 | 应用、SDK 与原生运行时 | CLI、Desktop、SDK、原生组件与分发 |
| 13 | 实验能力 | Agent Teams、Hooks、Worktree 与实验运行时 |
| 14 | 验证、扩展与工程维护 | 测试、构建、文档同步、扩展与故障复盘 |

## 阅读时注意版本

开篇的历史资料源于 2026-08-16 的研究。后续源码文章从固定 commit `d743267388641bc76f17c45ce8b4c231aed1d32c` 开始，按文章记录实际分析版本。结构分析、无密钥测试和真实模型实验分别标注，旧版本结果不作为新版本证据。
