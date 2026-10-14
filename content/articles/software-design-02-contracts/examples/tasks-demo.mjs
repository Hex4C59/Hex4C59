import { createTaskList } from "./tasks.mjs";

const { completeTask, listTasks } = createTaskList();
console.log("初始任务：", JSON.stringify(listTasks()));
console.log("第一次完成 t1：", JSON.stringify(completeTask("t1")));
console.log("再次完成 t1：", JSON.stringify(completeTask("t1")));
console.log("查询不到 t9：", JSON.stringify(completeTask("t9")));
console.log("传入空编号：", JSON.stringify(completeTask("")));
console.log("最终任务：", JSON.stringify(listTasks()));
