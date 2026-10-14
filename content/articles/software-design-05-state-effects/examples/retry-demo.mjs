import { copyTasks } from "./copy-tasks.mjs";
import { createUnsafeTaskList } from "./unsafe-save.mjs";
import { createSavedTaskList } from "./save-before-adopt.mjs";

for (const [name, create] of [
  ["先改当前数据再保存", createUnsafeTaskList],
  ["先保存新数据再采用", createSavedTaskList],
]) {
  let calls = 0;
  const saved = [];
  function saveSnapshot(tasks) {
    calls += 1;
    if (calls === 1) throw new Error("合成的首次保存失败");
    saved.push(copyTasks(tasks));
  }
  const taskList = create(saveSnapshot);
  console.log(name);
  console.log("第一次：", JSON.stringify(taskList.completeTask("t1")));
  console.log("失败后当前数据：", taskList.listTasks()[0].completed);
  console.log("再次尝试：", JSON.stringify(taskList.completeTask("t1")));
  console.log("保存调用次数：", calls);
  console.log("成功保存份数：", saved.length);
}
