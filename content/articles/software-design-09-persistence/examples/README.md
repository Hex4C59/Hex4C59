# 持久化与设计演化

与《持久化与设计演化：任务保存后，怎样重新读回来》配套。

验证环境：2026-10-15，macOS arm64，Node.js 25.9.0。仅使用 Node.js 自带模块，不依赖第三方包，无需安装依赖。

在解压的 software-design-09-examples 目录执行：

```sh
node --test owner.test.mjs codec.test.mjs store.test.mjs replace.test.mjs process.test.mjs
node restart-demo.mjs
node failure-demo.mjs
```

完整测试为 40 项通过，无跳过或取消：原任务约定 4 项，编码与验证 12 项，存储与启动 12 项，临时替换 5 项，独立进程 7 项。源目录与解压包均以 --unhandled-rejections=strict 运行过这些检查和演示。

逐条操作的命令为：

```sh
mkdir -p demo-data
node app.mjs init demo-data/tasks.json
node app.mjs complete demo-data/tasks.json t1
node app.mjs list demo-data/tasks.json
```

init 固定创建两条演示任务，路径已存在时返回 already-exists，不覆盖；缺失父目录不会自动建立。文件模块的 initialize([]) 已支持并检查空数组，当前命令行没有空任务初始化选项。命令正常结果打印 JSON；ok:false 对应退出码 1，成功为 0。

- task-list.mjs：与第八篇 03-map-direct.mjs 逐字节相同，仍负责当前任务、busy、等待、错误转换和采用。
- initial-tasks.mjs、copy-tasks.mjs、to-task-map.mjs、map-plan-completion.mjs、controlled-save.mjs、contract-checks.mjs：与第八篇逐字节相同。
- validate-tasks.mjs：验证三字段任务、字段类型、非空白编号及编号唯一；拒绝未知字段，接受空数组。
- task-file-codec.mjs：解析并验证旧数组与版本一，所有新保存写 {version:1,tasks:[...]}。版本二不支持。
- replace-file.mjs：同目录独占创建临时文件，写完并关闭后替换目标。失败时尽力清理本次已创建的临时路径，不把临时内容自动当成正式数据。
- file-store.mjs：路径、读取、显式初始化与保存；读取失败不重置，不隐式创建。
- open-task-app.mjs：先读取验证，成功后才创建任务对象。format 表示本次读取格式，不会随之后保存自动变化。
- app.mjs：init / list / complete 命令。每次启动读取，操作完成后退出。
- restart-demo.mjs：在自己创建的临时目录中，依次启动真实独立进程初始化、完成、重新读取，等待前一个退出后再启动后一个。
- failure-demo.mjs：正确拒绝损坏启动和覆盖、旧格式升级，以及错误默认值后续覆盖的对照。只操作本次临时文件。
- faults/reset-on-error.mjs：故意错误，把所有读取失败替换为默认任务，启动后继续保存可能覆盖原文件。
- startup-check.mjs、probe.mjs：对正常与错误启动器执行同一损坏文件约定。node probe.mjs correct 退出 0；node probe.mjs reset 预期检查失败并退出 1。
- owner.test.mjs：保留既有任务约定。
- codec.test.mjs：文件结构、格式、字段、唯一性和编码验证。
- store.test.mjs：真实初始化、损坏拒绝、读取、保留原字节及升级时机。
- replace.test.mjs：真实替换、合成替换前失败、非法数据、缺失目录及合成替换后错误。
- process.test.mjs：真实命令行退出与重新读取、错误退出、迁移和反例；各进程顺序运行，未验证并发写入。
- test-helpers.mjs：为检查创建并清理独立目录，启动命令时不用 shell 拼接输入。

正式读取只接受合法旧数组，或 {version:1,tasks:[...]}，且对象字段与任务字段不得包含未知项目。未知整数版本返回 unsupported-version，损坏文本返回 invalid-json，字段错误返回 invalid-data。读取失败时没有 taskList；缺失路径为 missing-file，其他读取错误为 read-failed。

旧数组只读取不重写，第一次成功保存实际任务修改才升级；重复完成 changed:false 不保存、不升级。丢弃未知字段或自动把空数组换成默认任务均不属于本例行为。

同一时刻每个文件只能有一个任务所有者，使用普通本地文件且父目录已存在，不处理外部编辑、多个对象或进程间写入冲突。替换仍不是完整故障恢复；保存失败保留旧内存不保证正式文件没变。replace.test 中替换前失败和替换后报错是代码主动制造的条件，不是系统中途故障、磁盘满、崩溃或断电实测。

临时清理是尽力执行，失败可能残留文件；启动不扫描临时文件自动恢复。新文件替换没有实现保留旧文件权限等额外属性的逻辑。初始化使用 wx 只阻止覆盖已存在路径，不保证创建过程中失败绝不留下新内容。未验证不同系统、网络文件系统、性能、页面、取消或期限。

添加空任务初始化选项和单独格式升级命令为读者练习，当前未实现。正常测试通过不表示 faults 中的错误版本已经修复。
