# 第 02 篇：两段代码怎样可靠地配合工作

主体是待办事项的完成操作，版本查询是独立的补充练习。所有数据都由演示构造，不读取真实任务或本机版本。

## 待办事项

在本目录执行：

```sh
node tasks-demo.mjs
node contract-change.mjs
node --test tasks.test.mjs check.test.mjs
```

tasks-demo.mjs 展示第一次完成、重复完成、找不到任务和错误编号；contract-change.mjs 展示失败对象被旧的布尔判断误当作成功。任务部分 11 项测试，版本查询部分 5 项，共 16 项。

tasks.mjs 中 createTaskList 每次建立独立数据，交回 completeTask 和 listTasks。完成任务只修改目标任务的 completed；成功返回 ok、changed 与任务副本，失败返回 ok 和 reason。编号不是非空字符串时，原因是 invalid-id；精确匹配不到编号时，原因是 not-found。失败时数据保持原样，再次完成仍成功但 changed 为 false。

初始任务应当已满足编号唯一、标题为字符串、completed 为布尔值的条件。创建和读取损坏数据、文件保存、保存失败、网络请求与任务时间均未实现。修改返回的任务或列表，不会改变内部数据；当前只复制编号、标题和完成标记。

## 版本查询练习

```sh
node before.mjs
node demo.mjs
```

before.mjs 输出 1.0.0 和 undefined。demo.mjs 展示名称检查后的版本查询、错误提示与再次查询。

可选的 TypeScript 检查只针对版本查询，不给任务实现提供静态类型证明：

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run check:types
npm run check:invalid
```

check:types 检查 typed.ts，应当通过。check:invalid 检查故意写错的 invalid.ts，预期报告参数 appp 不符合要求并以非零状态退出。也可运行 npm test 执行全部 16 项行为检查，无需先安装编译器。

核验环境：2026-10-14，Apple Silicon Mac 上的 macOS、Node.js v25.9.0；可选检查使用 npm 11.12.1、固定 TypeScript 5.9.3。编译命令只检查，不生成文件。未核验其他版本组合。
