import { createAsyncTaskList } from "./async-task-list.mjs";
import { createControlledSave } from "./controlled-save.mjs";

const saving = createControlledSave();
const taskList = createAsyncTaskList(saving.saveSnapshot);
const pending = taskList.completeTask("t1");
console.log("调用已交回 Promise：", pending instanceof Promise);
console.log("等待时 t1：", taskList.listTasks()[0].completed);
console.log("等待时完成 t2：", JSON.stringify(await taskList.completeTask("t2")));
saving.calls[0].succeed();
console.log("t1 的最终结果：", JSON.stringify(await pending));
console.log("保存后当前标记：", JSON.stringify(taskList.listTasks().map(task => task.completed)));
const second = taskList.completeTask("t2");
saving.calls[1].succeed();
await second;
console.log("再次提交 t2 后：", JSON.stringify(taskList.listTasks().map(task => task.completed)));
