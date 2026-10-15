# 异步完成任务与错误传播

与《错误传播与异步边界：需要等待时，成功和失败怎样交回来》配套。

验证环境：2026-10-15，macOS arm64，Node.js 25.9.0。使用 Node.js 自带功能，无第三方依赖，无需 npm install。

在解压的 software-design-06-examples 目录执行：

```sh
node basics-demo.mjs
node waiting-demo.mjs
node failure-demo.mjs
node overlap-demo.mjs
node file-demo.mjs
node --test async.test.mjs file.test.mjs
```

- initial-tasks.mjs、copy-tasks.mjs、plan-completion.mjs：与第五篇逐字节相同。
- async-task-list.mjs：正式异步所有者，等待保存后采用，等待期间拒绝新修改，finally 释放忙碌状态。
- controlled-save.mjs：为演示与测试保存每次调用，显式 succeed / fail，不依赖固定延时。
- without-wait.mjs：故意丢弃保存 Promise 的反例；failure-demo 从外部观察被丢弃的拒绝，避免未处理拒绝。
- without-busy.mjs：等待保存却允许两份基于旧状态的建议覆盖。
- promise-basics.mjs、basics-demo.mjs：普通抛错、异步拒绝、ok:false 正常结果与 return await 对照。
- waiting-demo.mjs、failure-demo.mjs、overlap-demo.mjs：等待、重试与覆盖路径。
- file-demo.mjs：真正的 fs/promises 写入与路径拒绝，finally 等待清理本次临时目录。
- async.test.mjs、file.test.mjs：30 项检查，包含 4 项真实临时文件检查。

初始任务须已合法、编号唯一，标题为字符串、completed 为布尔值；只复制这三个简单字段。读取列表仍同步返回副本，完成操作总是返回 Promise。预期失败（invalid-id / not-found / busy / save-failed）是正常履行的结果对象，需要 await 后检查 ok。

忙碌检查先于编号检查。等待期间的新修改直接返回 busy，不排队或自动重试；列表读取保持旧状态。busy 只管同一个对象，不协调其他所有者或进程。保存结果一直待定时，busy 也不会自动释放。

保存函数须正确保存传入副本，返回正常结果为 undefined 的 Promise，也接受同步返回 undefined。同步抛错和 Promise 拒绝都在保存附近转成 save-failed；额外正常结果也被拒绝。保存函数不能内部等待同一所有者的另一项修改。其他位置的未处理错误继续表现为完成 Promise 拒绝。

等待和错误转换不撤销外部写入。文件测试中“完整写入后抛错”是合成失败，不是系统中途故障实测；正常演示只操作本次创建的临时目录，不读取用户文件。没有页面、取消、超时、队列、多所有者写入协调或抗崩溃恢复。排队与标题修改是读者练习。
