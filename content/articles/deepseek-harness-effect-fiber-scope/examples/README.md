# Cordis effect / Fiber / Scope 生命周期实验

对应《DeepSeek Harness 源码解析（八）：effect、Fiber 与 Scope 怎样清理资源》。

## 准备

需要 Git、Node.js 22 或以上、npm，以及独立的 deepseek-harness checkout。实际验证环境为 macOS 27.0.1 arm64、Node v25.9.0、TypeScript 6.0.3；未逐一验证所有 Node 版本。

将源码准备在 commit `d743267388641bc76f17c45ce8b4c231aed1d32c`。脚本要求 HEAD 精确匹配，并拒绝 `vendor/cordis`、`vendor/cosmokit`、`packages/core/scope` 中已有修改的情况。保留自己的工作时使用独立 checkout，避免覆盖修改。

解压后进入 `resource-lifecycle-lab`，执行：

```sh
npm install --ignore-scripts
DSH_SOURCE=/path/to/deepseek-harness npm run verify
```

上面的源码目录是占位路径。PowerShell 可以先设置 `$env:DSH_SOURCE = "C:/path/to/deepseek-harness"`，再运行 `npm run verify`。

若已有独立安装的 TypeScript 6.0.3，可将 `DSH_LIFECYCLE_TYPESCRIPT` 指向它的 `lib/typescript.js`，直接执行 `node run.mjs`。脚本仍会检查编译器版本。

## 检查如何执行

`run.mjs` 将固定源码中的 cosmokit、Cordis 与 dsh-scope 的实现文件转译到本次创建的系统临时目录，加载真实 Context、Fiber 与 Scope，并调用 `scenarios.mjs`。它不替换框架实现，不写入源码，不安装 dsh 工作区依赖。`transpileModule` 仅转译，不做完整语义类型检查。

每组检查有独立根 Context，结束时清理自己持有的资源。根 Fiber 的 dispose 在该版本中是 restart，不能把这项清理描述为根实例的永久销毁。最外层 finally 删除本次创建的临时转译目录。

## 22 组断言

1. 立即初始化与公开清理入口单次执行。
2. 单个生成器 effect 内逆序等待。
3. Fiber 的兄弟 effect 逆序开始并异步重叠。
4. yield 确切 Scope rawDispose 后按组合顺序清理。
5. 新包装函数留下并行兄弟，tail 可先于 Scope 结束。
6. await effect 等初始化并取得清理入口；插件异步主体显式等待时维持 LOADING。
7. 异步初始化迟到的资源仍被释放。
8. 同步初始化重入 owner 卸载。
9. 同步初始化失败的回滚仍可被 owner 等待。
10. 异步初始化拒绝后释放已经 yield 的资源。
11. 无效初始化结果抛 TypeError。
12. 一份组合清理失败会截断更早成员，兄弟 effect 仍清理并记录错误。
13. 公开重复调用返回 undefined，确切的组合持有者加入在途清理。
14. PENDING 插件也可能拥有内部观察者登记的资源。
15. 装载中撤销阻止过期插件主体运行。
16. 依赖丢失卸载，提供方替换后同一 Fiber 再激活。
17. 父插件等待子清理，而自己的清理可重叠；显式等待子插件已装载后再开始。
18. Scope 路由祖先不会重排兄弟 Fiber 的所有权。
19. rawDispose 已启动时，Scope.dispose 仍共享一份完成 Promise。
20. extend 继续共享原 Fiber。
21. restart 保留 uid、普通 dispose 终止实例、根 dispose 为 restart。
22. registry.delete 启动清理并返回 runtime，不是完成屏障。

异步顺序由受控 Promise 和开始/结束信号确定，不用 sleep。第 13 组检查外层较早清理不能在子清理未完成时执行，避免只凭一瞬间的布尔值推断等待。成功时输出 22 条 PASS，随后 JSON 报告 commit、实际 Node/TypeScript 版本和每组观察结果。断言失败会以非零状态退出。

配图使用第 3、4、5 组已断言轨迹；节点中间状态是对应轨迹的解释，完成帧包含对 owner 卸载的等待，不声称采样了每次 Fiber.state 变化。

## 范围

实验使用合成资源，不执行真实文件工具、Agent 应用或模型网络请求。没有完成 dsh 全量构建、语义类型检查、所有插件组合、进程故障或真实产品退出验收。业务取消、持久化与退出顺序需要另外检查实际调用方。错误处理组使用正常工作的默认 logger；不外推到 logger 本身抛错的情况。
