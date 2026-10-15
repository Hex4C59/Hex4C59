# Cordis 事件派发聚焦实验

对应《DeepSeek Harness 源码解析（七）：五种事件派发怎样执行监听器》。

## 准备与运行

需要 Git、Node.js 22 或以上和 npm。本次实际验证使用 Node v25.9.0、TypeScript 6.0.3；未逐一验证所有 Node 版本。

1. 单独准备 deepseek-harness 的 checkout，并切换到 commit `d743267388641bc76f17c45ce8b4c231aed1d32c`。保留已有工作时，使用单独的 checkout，避免覆盖修改。
2. 将本实验包解压到独立目录，进入该目录。
3. 安装固定的 TypeScript，并传入源码目录。下面 `/path/to/deepseek-harness` 是占位路径。

```sh
npm install --ignore-scripts
DSH_SOURCE=/path/to/deepseek-harness npm run verify
```

PowerShell 可先设置 `$env:DSH_SOURCE = "C:/path/to/deepseek-harness"`，然后运行 `npm run verify`。

脚本要求 HEAD 精确匹配上述 commit，且 `vendor/cordis`、`vendor/cosmokit` 没有工作区修改。不要求安装 dsh 的工作区依赖，也不改写 dsh 源文件。

若已有独立安装的 TypeScript 6.0.3，可通过 `DSH_EVENTS_TYPESCRIPT` 指向其 `lib/typescript.js`，不必在实验目录再次安装。该选项不改变版本断言。

## 实际执行了什么

`run.mjs` 将固定 checkout 中 Cordis 与 cosmokit 的 `.ts` 实现转译到新建的系统临时目录，加载其中真实的 Context 与 EventsService。没有手写替代事件循环，也没有运行仓库完整 build/typecheck；`transpileModule` 不做完整语义类型检查。程序退出前通过 finally 删除自己创建的转译目录。

`scenarios.mjs` 包含 18 组断言，覆盖停止值、异步等待与错误、waterfall、监听器快照、once 重入、过滤、撤销和诊断模式。受控 Promise 由脚本主动放行，不依赖 sleep。

`figure-fixtures.mjs` 另断言 10 组配图输入：五种派发分别在正常输入和 A 同步抛错时的轨迹。前四种正常输入为 A 返回受控 Promise（最终 undefined）、B 返回 0、C 返回 last；waterfall 使用独立的 next 包装函数。它们是演示输入，不是 dsh 业务事件的真实运行日志。

成功时先输出 18 条用例 PASS，再输出 `PASS 10 figure fixtures`，最后输出含源码 commit、实际 Node/TypeScript 版本、观察结果与图示轨迹的 JSON。断言失败时进程非零退出，每组 Context 在 finally 中释放。

## 证据边界

本实验没有启动 dsh 应用、真实文件工具或模型网络请求，不能证明完整依赖组合、取消、权限、持久化、进程故障和性能已经通过。`once` 的嵌套派发结果及 parallel 的诊断 mode 属于上述固定版本的观察，不外推到其他 Cordis 版本。
