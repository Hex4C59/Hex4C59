# Agent、AgentHandle 与实例所有权实验

用于 DeepSeek Harness 系列第十篇。固定源码：`d743267388641bc76f17c45ce8b4c231aed1d32c`。

## 运行

本次实际环境 macOS 27.0.1 arm64、Node v25.9.0。实验用 TypeScript 6.0.3 与 zod 4.4.3，完整依赖和校验值由 package-lock.json 固定。没有建立其他平台或 Node 版本的验证矩阵。

在解压目录运行，需要 Node、npm、Git 及固定源码 checkout：

```sh
npm ci --ignore-scripts --no-audit --no-fund
DSH_SOURCE=/path/to/deepseek-harness npm run verify
```

已有工具可通过 `DSH_AGENT_TYPESCRIPT` 指向 TypeScript 6.0.3 的 `lib/typescript.js`，`DSH_AGENT_ZOD_PACKAGE` 指向 zod 4.4.3 的 package.json；不设置则使用实验目录依赖。

## 执行方式

脚本扫描仓库 package manifest，沿静态运行 import/export 找到工作区模块，检查固定 commit 和涉及包的干净状态，把真实源码转译到独立临时目录。当前入口闭包为 18 个包、82 个模块，额外复制固定 zod。结束或失败后删除临时目录，不向 dsh checkout 安装依赖。

只做转译语法诊断，不等于全仓库语义类型检查、完整产品打包或任意动态模块加载支持。每组实验用新 Context，释放本组受控 Promise 后等待根 Fiber 清理。成功输出 36 行 PASS，以及含 commit、运行环境、闭包与逐组观察的 JSON；断言失败时返回非零。

## 证据边界

36 组中，8 组 Registry 专项使用最小合成 Agent；其余挂载真实 LLM、Session、SessionProjection、SystemPrompt、Tools、AgentRegistry 与 AgentLoop，不调用模型。持久化场景用可控的内存接口适配器验证顺序和迟到 handle 关闭，不把这些结果报告为真实 JSONL/SQLite、文件锁、磁盘持久性或跨进程协议验证。

覆盖未发布 setup/commit、公告顺序与回滚、精确 entry、caller/factory 卸载、三种 parent 关系、initiator、重复清理、maintenance 等待、错误处理及恢复。受控 Promise 用于暴露等待边界，不使用固定 sleep。
