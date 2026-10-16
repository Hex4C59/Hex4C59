# Preset、Persona 与默认模型实验

配合 DeepSeek Harness 系列第十一篇。分析版本为 **0.2.1-alpha.2**，固定源码提交 `d743267388641bc76f17c45ce8b4c231aed1d32c`。

## 运行

需要 Node、npm、Git 和固定提交的 deepseek-harness checkout。解压后，在本实验目录执行：

```sh
npm ci --ignore-scripts --no-audit --no-fund
DSH_SOURCE=/path/to/deepseek-harness npm run verify
```

本次实际环境为 macOS 27.0.1 arm64、Node v25.9.0。没有建立其他操作系统和 Node 版本的验证矩阵。

TypeScript 6.0.3、zod 4.4.3、js-yaml 4.3.2、semver 7.8.5、resolve.exports 2.0.3 及完整性校验由 package-lock.json 固定。如需复用已安装工具，可分别设置 `DSH_PRESET_TYPESCRIPT` 为 TypeScript 的 lib/typescript.js 路径，`DSH_PRESET_ZOD_PACKAGE`、`DSH_PRESET_YAML_PACKAGE`、`DSH_PRESET_SEMVER_PACKAGE`、`DSH_PRESET_EXPORTS_PACKAGE` 为相应 package.json 路径。

## 实际执行什么

run.mjs 检查源码 HEAD 和可达工作区包的状态，沿静态运行 import/export 转译真实源码到独立临时目录，再加载这些模块运行 scenarios.mjs。当前闭包为 35 个工作区包、144 个模块。它不向 dsh checkout 安装依赖；成功或失败均清理自己创建的临时目录。只检查转译语法，不代表完整语义类型检查，也不提供任意动态插件打包器。

30 组断言运行真实 Loader、AgentPresetRegistry、AgentPreset 声明插件、Persona、SystemPrompt、AgentDefaultModelConfig、Session、SessionProjection、AgentRegistry、AgentLoop 和 API Session AgentController。主线中的 Agent 是真实驱动器。子 Scope 修订继承案例使用真实 composeFrom 和 Scope，没有执行子 Agent 的模型循环。

测试的工具贡献是合成工具；未执行工具业务。配置保存用受控 ConfigEditor 接口，只验证顺序、字段捕获及失败后的继续。模型名称是合成值，组装和 request/pre-step waterfall 直接调用真实实现；不配置 adapter，不发送模型请求。

## 输出和证据边界

成功输出 30 行 PASS，以及包括版本提交、依赖、运行闭包和各组观察的 JSON；任何断言失败返回非零状态。等待边界使用受控 Promise，没有固定 sleep。

覆盖默认 Preset 与显式选择、共享与保留修订、错误诊断和 PENDING 恢复、服务隔离、只读租约、空白会话切换及日志、Turn 锁定、Persona 作用域/空文本/严格插值/complete、默认模型 volatile 及保存队列、会话 pending/历史/default 的关系、快照与 request、模型变化说明。

未验证完整 Web 或 IPC 产品启动、真实模型与 adapter、真实工具执行、磁盘配置文件、日志后端持久性、崩溃恢复、HMR watcher 和跨进程行为。正文中 launcher 身份与实际 bundle 配置的说明来自静态源码核对。

实验代码用于解释固定版本；上游实现按其仓库 MIT 许可证使用，转译副本不随下载包分发。
