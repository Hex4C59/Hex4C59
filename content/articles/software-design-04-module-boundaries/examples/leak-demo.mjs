import { createLeakyStore } from "./leaky-store.mjs";
import { createTaskList } from "./by-decision/array/tasks.mjs";

const leaky = createLeakyStore();
leaky.getTasks()[0].title = "外部改写";
console.log("返回内部数组后：", leaky.getTasks()[0].title);
const taskList = createTaskList();
taskList.listTasks()[0].title = "外部改写";
console.log("返回任务副本后：", taskList.listTasks()[0].title);
