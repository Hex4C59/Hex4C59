# Loader、配置与完成边界实验

本目录是《DeepSeek Harness 源码解析（九）》的可重跑实验，不包含 dsh vendor 源码。

## 版本与运行

- deepseek-harness：`d743267388641bc76f17c45ce8b4c231aed1d32c`。
- TypeScript：6.0.3；js-yaml：4.1.1。package.json 固定直接依赖版本，package-lock.json 固定完整依赖与校验值。
- 运行时需要支持 Promise.withResolvers()；本次实际运行 Node v25.9.0、macOS 27.0.1 arm64，未建立其他平台验证。
- 按上游许可证另行取得固定源码；五个 vendor 源码目录必须干净，脚本会检查。

在本目录执行：

```sh
npm ci --ignore-scripts --no-audit --no-fund
DSH_SOURCE=/path/to/deepseek-harness npm run verify
```

可复用外部已安装的固定工具，避免重复安装：`DSH_LOADER_TYPESCRIPT` 指向 TypeScript 6.0.3 的 `lib/typescript.js`，`DSH_LOADER_YAML_PACKAGE` 指向 js-yaml 4.1.1 的 `package.json`。未设置时从本目录依赖解析。

`run.mjs` 校验 commit 与源目录状态，转译真实 cosmokit、Cordis、Schemastery、Loader、Include，复制固定 YAML 运行依赖进入独立临时目录，执行 28 组 scenarios 后清理。只检查转译语法诊断，不代表全仓库语义类型检查。每组使用新的 Context，最后等待 root Fiber 清理已持有的资源。Include 只读写本次临时文件。

成功时输出 28 行 `PASS` 和含 commit、Node、工具版本及各组观察的 JSON。失败时 Node 返回非零。

## 核对范围

28 组覆盖：原始/有效表达式与字面字符串；Group 延迟求值；相同配置；普通重启；internal/update 消费；Fiber.update 等待边界；volatile 引用/先提交/本地事件；无效候选；混合更新；普通有效表达式变化；对象默认值；PENDING 延迟解析；禁用/重启；禁用 Group；同标签服务域；true 本地域；移动条目；intercept 映射；移除后等待边界；活 entry 的 name 变化；Include YAML 表达式/子树 id；坏文件刷新恢复；Include patch 更新；patch 插入/输入隔离；entry 写回保留标签；Fiber 写回保存解析值；主动卸载反写 disabled；Loader await 拦截门控。

清理时序使用受控 Promise，不使用固定延时。这些是聚焦 Loader 实现的真实运行检查；**没有运行文件监听、Node HMR 缓存替换、完整 app boot、真实工具或模型网络请求**。文章 HMR 部分来自固定源码分析，不能将此实验报告为 HMR 或整个 dsh 通过。
