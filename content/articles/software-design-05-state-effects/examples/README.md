# 状态、计算与保存顺序

与《状态与副作用：谁能修改数据，失败后保留什么》配套。

验证环境：2026-10-15，macOS arm64，Node.js 25.9.0。无第三方依赖，无需 npm install。在解压的 software-design-05-examples 目录运行：

```sh
node calculation-demo.mjs
node retry-demo.mjs
node file-demo.mjs
node two-owners-demo.mjs
node --test state.test.mjs file.test.mjs
```

- initial-tasks.mjs / copy-tasks.mjs：演示初始数据与三个简单字段的副本。
- mutable-tasks.mjs：上一章集中数组版，创建函数体相同，仅调整 import 路径。
- plan-completion.mjs：根据当前数据与编号计算，不修改输入；交回 result 和 nextTasks，没有需要采用的数据时 nextTasks 为 null。
- task-list.mjs：所有者在计算成功且有变化时采用新数据，保留原有内存任务接口。
- unsafe-save.mjs：反例，先改当前数据，再保存；失败后数据已改，重试可能跳过保存。
- save-before-adopt.mjs：先计算，再保存，正常返回后才采用；失败不采用新数据。
- calculation-demo.mjs：观察计算与采用的区别。
- retry-demo.mjs：首次保存故意失败，后续模拟保存成功，比较两种顺序。
- file-demo.mjs：创建本次独立临时目录，展示正常文件写入、真实路径错误和合成的部分写入后报错，finally 清理本次目录。
- two-owners-demo.mjs：两个独立列表共同写同一个外部快照变量，后一次覆盖前一次进度；不写真实文件。
- state.test.mjs / file.test.mjs：29 项检查，包括真实临时文件的正常保存、ENOENT、部分写入后主动抛错，以及完整写入后主动抛错。

初始数据须已合法：编号为唯一非空字符串，标题为字符串，completed 为布尔值。只复制当前三个简单字段，不验证坏初始数据或任意嵌套对象。

保存函数接收任务副本，必须在返回前完成，成功返回 undefined，失败抛错；不得在执行期间重新调用同一列表的修改接口。额外返回值被视为 save-failed。创建列表不自动保存，输入错误、不存在和重复完成不保存。保存函数须正确保存传入内容；提供副本只保护内存，不证明外部内容正确。

先保存再采用保证的是本例条件下失败不接受新内存数据，不保证外部文件未被修改。合成的部分写入和完整写入后抛错，都能导致外部数据与内存不同；这不等于实测操作系统中途故障或断电。示例没有实现后台等待、多进程协作、完整文件恢复或抗崩溃保存。

file-demo 和 file.test 仅操作本次创建的临时目录；正常结束清理，不读取用户现有任务文件。正文的标题修改与失败恢复版是读者练习，下载包未实现。
