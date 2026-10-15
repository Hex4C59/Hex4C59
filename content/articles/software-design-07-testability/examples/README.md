# 可测试性：从行为约定写出检查

与《可测试性：怎样写出能发现问题的检查》配套。

验证环境：2026-10-15，macOS arm64，Node.js 25.9.0。仅使用 Node.js 自带模块，无需安装第三方依赖。

在解压的 software-design-07-examples 目录执行：

```sh
node --test planning.test.mjs waiting.test.mjs contracts.test.mjs file.test.mjs
node fault-demo.mjs
node file-demo.mjs
```

完整测试为 20 项通过、无跳过或取消；其中 4 项检查真实临时文件，4 项在独立进程里核对正确版本与三个错误版本的判断及退出码。

- initial-tasks.mjs、copy-tasks.mjs、plan-completion.mjs、async-task-list.mjs、controlled-save.mjs：与第六篇逐字节相同。正式实现没有新增任务功能。
- planning.test.mjs：按约定写出明确预期，检查计算结果、无效输入、重复完成及数据副本。
- waiting.test.mjs：展开一项完整的等待检查，包括主动完成保存与 finally 清理。
- contract-checks.mjs：可复用的采用顺序、保存拒绝和忙碌策略检查；预期不由被检查实现计算。
- contracts.test.mjs：检查正式实现、失败后重试、不额外保存、busy 优先级，以及独立进程反例。
- json-file-save.mjs、file.test.mjs：真实 JSON 保存与读回、缺失父目录失败、正常返回却没有写文件的对照。
- faults/early-adopt.mjs：人为提前采用新数据，等待检查应失败。
- faults/ignore-rejection.mjs：人为把保存失败报告成任务成功，失败结果检查应失败。
- faults/allow-overlap.mjs：人为移除忙碌拒绝，保存次数检查应失败。
- probe.mjs：对所选版本执行同一组约定检查。参数可为 correct、early-adopt、ignore-rejection、allow-overlap，默认 correct。
- fault-demo.mjs：启动四个比较进程，核对正确版本退出 0，三个错误版本各自退出 1。
- file-demo.mjs：演示真实保存、文件读回与缺失父目录失败，只操作本次临时目录。

注意：faults 中三个版本是故意写错的教学材料。单独运行 node probe.mjs early-adopt，应打印检查失败并以退出码 1 结束；另外两个错误版本同理。不要为了得到通过结果而删除对应断言。fault-demo 自己退出 0，只表示它观察到了预期的通过和失败。

初始任务须合法、编号唯一，title 为字符串、completed 为布尔值。只复制 id、title、completed 三个字段。completeTask 返回 Promise；invalid-id、not-found、busy、save-failed 都是正常交回的失败结果对象。

保存正常结束须给出 undefined；保存同步抛错或 Promise 拒绝会转换为 save-failed。其他正常返回值也被正式实现拒绝。保存方须正确保存传入副本，不能内部等待同一任务对象的另一项修改，并应最终结束。

busy 检查先于编号检查，只负责同一任务对象，不排队、不协调其他对象或进程。受控保存由检查主动完成或拒绝，不使用固定睡眠猜测完成时间。各项检查新建数据和保存记录；真实文件使用各自临时目录，等待操作结束后清理。

20 项通过只说明列出的检查条件成立。受控保存不写文件，正常结束的模拟函数不能证明任何文件存在。真实文件检查没有覆盖磁盘满、部分写入、断电、崩溃恢复、页面或多个进程。保存已改过外部数据再失败，不会自动恢复文件；保留旧内存不等于文件未变。

正文另外给出可另存运行的 first-check.test.mjs 与 real-file.test.mjs。它们用于展开解释，不属于上述 20 项的计数。修改标题和新增错误版本是读者练习，未作为本次功能实现。
