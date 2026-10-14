import { createTaskList } from "./tasks.mjs";

const { completeTask } = createTaskList();
const result = completeTask("t9");
console.log("实际结果：", JSON.stringify(result));
console.log("旧写法直接判断整个结果：", result ? "显示完成" : "显示失败");
console.log("新写法检查 ok：", result.ok ? "显示完成" : "显示失败");
