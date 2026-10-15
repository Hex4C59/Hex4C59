import { createWithoutBusy } from "./without-busy.mjs";
import { createControlledSave } from "./controlled-save.mjs";

const saving = createControlledSave();
const taskList = createWithoutBusy(saving.saveSnapshot);
const first = taskList.completeTask("t1");
const second = taskList.completeTask("t2");
saving.calls[0].succeed();
await first;
console.log("第一项保存结束：", JSON.stringify(taskList.listTasks().map(task => task.completed)));
saving.calls[1].succeed();
await second;
console.log("第二项保存结束：", JSON.stringify(taskList.listTasks().map(task => task.completed)));
