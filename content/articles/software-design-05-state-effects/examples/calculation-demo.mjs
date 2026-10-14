import { defaultTasks } from "./initial-tasks.mjs";
import { planCompletion } from "./plan-completion.mjs";
import { createTaskList } from "./task-list.mjs";

const proposal = planCompletion(defaultTasks, "t1");
console.log("计算后的原数据：", defaultTasks[0].completed);
console.log("建议采用的新数据：", proposal.nextTasks[0].completed);
const taskList = createTaskList();
console.log("采用前：", taskList.listTasks()[0].completed);
console.log("完成结果：", JSON.stringify(taskList.completeTask("t1")));
console.log("采用后：", taskList.listTasks()[0].completed);
