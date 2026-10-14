import { defaultTasks } from "./initial-tasks.mjs";
import { copyTasks } from "./copy-tasks.mjs";
import { createSavedTaskList } from "./save-before-adopt.mjs";

let saved = copyTasks(defaultTasks);
function saveSnapshot(tasks) {
  saved = copyTasks(tasks);
}
const first = createSavedTaskList(saveSnapshot);
const second = createSavedTaskList(saveSnapshot);
first.completeTask("t1");
console.log("第一份列表保存后：", JSON.stringify(saved.map(task => task.completed)));
second.completeTask("t2");
console.log("第二份列表保存后：", JSON.stringify(saved.map(task => task.completed)));
console.log("第一份列表仍认为 t1 已完成：", first.listTasks()[0].completed);
