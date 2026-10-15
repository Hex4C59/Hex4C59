# 重构中的行为保持

与《重构中的行为保持：换一种实现，怎样确认功能没变》配套。

验证环境：2026-10-15，macOS arm64，Node.js 25.9.0。只使用 Node.js 自带功能，无第三方依赖，无需安装包。

在解压后的 software-design-08-examples 目录执行：

```sh
node --test behavior.test.mjs map.test.mjs file.test.mjs faults.test.mjs
node stages-demo.mjs
node fault-demo.mjs
```

完整测试为 65 项通过，无跳过或取消：12 项共同约定应用到 4 个版本，共 48 项；Map 计算 5 项；真实临时文件 8 项；独立进程比较 4 项。重复运行相同约定，不代表覆盖了 48 种不同需求。

按阶段观察同一组行为与文件检查，每个命令匹配 14 项：

```sh
node --test --test-name-pattern "^00-original" behavior.test.mjs file.test.mjs
node --test --test-name-pattern "^01-rename" behavior.test.mjs file.test.mjs
node --test --test-name-pattern "^02-map-bridge" behavior.test.mjs file.test.mjs
node --test --test-name-pattern "^03-map-direct" behavior.test.mjs file.test.mjs
```

- 00-original.mjs：与第七篇的 async-task-list.mjs 逐字节相同，作为数组版本基线。
- 01-rename.mjs：只把所有者的 tasks 局部变量改为 currentTasks，容器和控制流程不变。
- 02-map-bridge.mjs：当前数据改用 Map，原数组计算前转数组，保存后转回 Map。这里的转换是迁移期间的连接。
- 03-map-direct.mjs：采用 Map 计算，移除计算前后的临时转换，读取和保存参数仍为数组副本。
- initial-tasks.mjs、copy-tasks.mjs、plan-completion.mjs、controlled-save.mjs、contract-checks.mjs、json-file-save.mjs：与第七篇逐字节相同。旧计算仅供前三个阶段使用，最终所有者不再导入它。
- to-task-map.mjs：先复制外部任务，再按编号构造 Map。
- map-plan-completion.mjs：根据 Map 计算新建议，不修改当前任务；未变化任务可以内部共享，修改目标创建新对象。
- versions.mjs：登记四个阶段，供演示与共同测试使用。
- migration-checks.mjs：检查保存参数仍是数组、列表顺序、busy 优先级，再执行第七篇原约定检查。
- behavior.test.mjs：四个阶段共同接受的 12 项检查，覆盖保存、错误、重试、数据副本及同步创建失败。
- map.test.mjs：计算结果、编号、重复完成、顺序及副本检查。
- file.test.mjs：每个阶段各检查真实内容读回与缺失父目录失败；只操作自己创建的临时目录，等待操作与清理结束。
- faults/reinsert-plan.mjs、faults/reinsert-task.mjs：人为删除已有键后重插，改变原列表顺序。
- faults/save-map.mjs：人为把私有 Map 直接交给保存方，改变原数组参数。
- faults/validate-first.mjs：人为提前验证编号，改变等待中无效编号的返回原因。
- probe.mjs、fault-demo.mjs：以相同检查比较正确版本和三个偏离约定的版本；正确版本退出 0，三个反例各自退出 1。
- stages-demo.mjs：四个阶段执行相同迁移检查，并输出相同的正常完成结果；最后展示默认 JSON.stringify(Map) 在当前环境得到 {}。

注意：faults 中的代码是对照材料。node probe.mjs save-map 预期失败并退出 1，另外两个错误参数为 reinsert-task、validate-first。fault-demo 自己退出 0，只表示它核对了这些预期通过和失败。提前验证编号未必永远不合适，它违反的是本次要保留的 busy 优先约定。

任务须合法、编号唯一，只包含 id、title、completed 三个简单字段；不支持通过初始重复编号测试推断数组与 Map 等价。外部不能取得内部 Map，列表和保存仍接收数组副本。创建函数仍同步返回对象，缺少保存函数同步抛出 TypeError；completeTask 仍返回 Promise。

busy 检查先于编号判断，只管同一个对象。保存函数须正确保存副本并最终结束，成功值为 undefined，接受同步成功或异步正常完成。保存抛错或拒绝变为正常的 save-failed 结果；其他正常返回值也按保存失败处理。保存函数不应内部等待同一个对象的另一项修改。

内部 new Map 复制键值对应，不复制所有任务对象；未变化任务内部共享但不修改。修改的任务、交回的结果、列表和保存参数各按代码建立副本，不能直接推广到任意嵌套对象。

这里没有性能测量、产品页面、排队、取消、期限、多对象或多进程写入协调、启动加载和崩溃恢复。文件检查不模拟磁盘满或部分写入。保留旧内存不等于外部文件未变。改变排序和额外函数提取为读者练习。

四份阶段代码是教学快照，不是四个真实 Git 提交；产品中无需长期维护四套实现。正式调用可从 03-map-direct.mjs 导入 createAsyncTaskList，再传入保存函数。若要保持原数组实现，可以选择 00-original.mjs。
