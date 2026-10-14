import { createTaskList } from "./tasks.mjs";

const taskList = createTaskList();
const wrongHandlers = new Map();
wrongHandlers.set("complete", taskList.completeTask("t1"));
console.log("错误登记后 t1 已完成：", taskList.listTasks()[0].completed);
console.log("表里保存的类型：", typeof wrongHandlers.get("complete"));
try {
  const handler = wrongHandlers.get("complete");
  handler("t1");
} catch (error) {
  console.log("尝试调用保存的结果：", error.name);
}

const objectHandlers = { list: function handleList() { return "任务列表"; } };
console.log("普通对象查到 toString：", typeof objectHandlers["toString"]);
console.log("toString 是明确登记的属性：", Object.hasOwn(objectHandlers, "toString"));
const mapHandlers = new Map();
console.log("空 Map 查到 toString：", mapHandlers.get("toString"));

function first() { return "第一次登记"; }
function second() { return "第二次登记"; }
mapHandlers.set("list", first);
mapHandlers.set("list", second);
console.log("同名登记后执行：", mapHandlers.get("list")());
