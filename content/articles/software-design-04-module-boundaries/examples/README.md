# 模块边界与任务表示

与《模块边界与信息隐藏：哪些代码应该放在一起》配套。

验证环境：2026-10-15，macOS arm64，Node.js 25.9.0。只使用 Node.js 自带功能，无第三方依赖，无需运行 npm install。

解压后进入 software-design-04-examples 目录，运行：

```sh
node demo.mjs
node compare.mjs
node mixed-demo.mjs
node leak-demo.mjs
node --test contracts.test.mjs
```

四个完整比较版本：

| 目录 | 组织方式 | 内部表示 |
| --- | --- | --- |
| by-operation/array | 状态、列出、完成、组装各有文件 | 数组 |
| by-operation/map | 同样的操作划分 | Map |
| by-decision/array | 集中维护任务数据和操作 | 数组 |
| by-decision/map | 集中维护任务数据和操作 | Map |

每个版本对外提供 createTaskList，返回 listTasks 与 completeTask。集中数组版函数体与上一章保持相同，只移动演示初始数据；request-entry.mjs 与上一章的处理器表入口相同。四个版本共用 consumer.mjs，demo.mjs 输出的四份结果应完全一致。

compare.mjs 读取实际比较文件：按操作拆分有 state.mjs、list-tasks.mjs、complete-task.mjs 三个文件变化，index.mjs 不变；集中维护表示的 tasks.mjs 一处文件变化。这是当前快照的文件差异，不是程序质量分数。

mixed-demo.mjs 故意把 Map 状态与旧数组完成代码混用：t1 存在，却返回 not-found，任务没有完成。leak-demo.mjs 展示只返回内部数组也会让外部改写标题；返回副本则保留原来的写周报标题。

28 项测试覆盖相同结果、成功与失败、重复完成、返回副本、初始数据复制、保留输入顺序、独立实例、请求拒绝、文件变化和两个反例。

初始任务须已经合法：编号为唯一非空字符串，标题为字符串，completed 为布尔值。示例不验证损坏初始数据；重复编号可能让数组和 Map 行为不同。任务操作按原样匹配编号，不修正两侧空白；返回的数组和任务对象是当前三个简单字段的副本。

本篇固定按初始放入顺序列出任务。所有操作都在调用返回前完成，并只使用程序运行期间的数据；没有真实页面、文件保存、网络或权限实现。测试结果只支持所列输入与当前实现，不作为性能或产品验收证据。

正文的内部 completed 改名为 done 是读者练习，下载包未预先实现。
