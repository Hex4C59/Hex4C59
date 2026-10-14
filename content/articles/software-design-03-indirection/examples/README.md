# 按名称选择任务操作

与《间接调用与依赖：程序怎样按名称选择要做的事》配套。

验证环境：2026-10-14，macOS arm64，Node.js 25.9.0。使用 Node.js 自带功能，无第三方依赖，无需运行 npm install。

在解压后的 software-design-03-examples 目录运行：

```sh
node function-value.mjs
node demo.mjs
node pitfalls.mjs
node --test dispatch.test.mjs
```

- `tasks.mjs`：与上一篇相同的任务实现，每次创建独立数据；初始数据须有唯一非空编号、字符串标题和布尔完成标记。
- `by-branch.mjs`：用条件分支选择功能。
- `by-table.mjs`：把操作名与处理函数放进 Map，查找后执行。
- `function-value.mjs`：保存函数不会执行，调用后计数才增加。
- `demo.mjs`：两种方案处理相同请求，分别展示列出、完成、重复完成和失败结果。
- `pitfalls.mjs`：提前调用、普通对象的继承属性与 Map 同名覆盖。提前调用的 TypeError 在演示中被捕获，命令仍正常结束。
- `extended.mjs`：两种方案新增 count-open 后的独立完整快照。
- `dispatch.test.mjs`：22 项检查，包括输入与名称拒绝、参数传递、结果与状态保持、创建时不执行、异常传出及统计扩展。

请求是程序自己构造的普通对象，或从 JSON 文本解析得到的数据；任务操作对象由示例代码提供，不检查任意外部 JavaScript 对象的特殊行为。

入口按原样匹配 action；空白名称被拒绝，两侧有空白的非空名称不会被修正；多余字段被忽略。只登记 list 与 complete，扩展版另有 count-open。未知名称（包括 toString、constructor、__proto__）返回 unknown-action。

list 返回 `{ ok: true, tasks }`；complete 按原样交回任务函数的成功或失败结果。缺失或非法编号为 invalid-id，不存在为 not-found，重复完成成功且 changed 为 false。入口没有保存文件、权限检查、网络通信或界面；意外抛出的异常继续向调用者传出。

统计扩展可以在同一目录运行：

```sh
node --input-type=module -e '
import { createTaskList } from "./tasks.mjs";
import { createExtendedTableDispatcher } from "./extended.mjs";
const dispatch = createExtendedTableDispatcher(createTaskList());
console.log(dispatch({ action: "count-open" }));
dispatch({ action: "complete", id: "t1" });
console.log(dispatch({ action: "count-open" }));
'
```

预期先为 `{ ok: true, count: 2 }`，再为 `{ ok: true, count: 1 }`。测试通过只覆盖这些例子，不证明其他运行时或产品功能已经验证。
