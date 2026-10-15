---
title: "DeepSeek Harness"
description: "按源码与调用链研究 DeepSeek Harness：从插件运行时、模型与工具，到会话、权限、多 Agent、界面及工程验证。"
lastmod: 2026-10-15
series_start: "/agent/deepseek-harness-agent-engineering/"
series_status: "连载中"
---

这个系列面向希望理解 Coding Agent 实现的开发者。先从背景与完整请求链路建立认识，再逐项阅读服务、事件、配置、状态和失败处理；各篇会记录对应的源码版本与验证边界。

## 从这里开始

从[开篇：从代码补全到仓库级 Agent](/agent/deepseek-harness-agent-engineering/)了解 Harness 的职责，再读[第二篇：一次用户请求如何经过整个 dsh 系统](/articles/deepseek-harness-request-lifecycle/)，沿输入、模型、工具、日志和输出追踪完整链路。随后读[第三篇：源码目录、包依赖与文档地图](/articles/deepseek-harness-source-map/)，学习怎样从一个调用点追到接口、实现和装配配置。接着读[第四篇：CLI、Web、Desktop 与 SDK 如何组装同一套运行时](/articles/deepseek-harness-application-entrypoints/)，比较配置层、应用启动、任务输入、就绪与退出边界。

[第五篇：Context、Service 与依赖注入如何协作](/articles/deepseek-harness-cordis-context-services/)开始阅读 Cordis 运行时，从工具插件缺少文件系统服务的情况出发，解释服务注册、依赖激活、服务域隔离和调用方 Context。

[第六篇：类型声明如何接上服务注册](/articles/deepseek-harness-types-service-registration/)接着解释编辑器怎样认识 `ctx.fs`，区分声明合并、类型导入、运行时挂载与发布声明，并用独立 TypeScript 实验核对它们的差异。

[第七篇：五种事件派发怎样执行监听器](/articles/deepseek-harness-event-dispatch/)比较 `emit`、`parallel`、`serial`、`bail` 与 `waterfall` 的执行、等待、返回值和异常处理，再追踪监听器过滤、派发快照与重入，并附固定源码的聚焦实验。

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

前七篇使用固定 commit `d743267388641bc76f17c45ce8b4c231aed1d32c` 进行静态分析，开篇于 2026-10-14 重写。后续按文章记录实际分析版本。结构分析、无密钥测试和真实模型实验分别标注，旧版本结果不作为新版本证据。
