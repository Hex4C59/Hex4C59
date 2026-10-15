import { createAsyncTaskList } from "./async-task-list.mjs";
import { createWithoutWait } from "./without-wait.mjs";
import { createControlledSave } from "./controlled-save.mjs";

const wrongSave = createControlledSave();
let ignoredPromise;
const wrong = createWithoutWait(function saveSnapshot(tasks) {
  ignoredPromise = wrongSave.saveSnapshot(tasks);
  return ignoredPromise;
});
const wrongResult = wrong.completeTask("t1");
// 演示从外面观察反例丢弃的 Promise，避免产生未处理拒绝。
const observedFailure = ignoredPromise.catch(function observe(error) { return error.message; });
console.log("缺少等待时提前交回：", JSON.stringify(await wrongResult));
console.log("保存尚未结束时的任务：", wrong.listTasks()[0].completed);
wrongSave.calls[0].fail(new Error("稍后才报告的失败"));
console.log("单独观察到的保存失败：", await observedFailure);
console.log("失败后已采用的数据：", wrong.listTasks()[0].completed);

const saving = createControlledSave();
const taskList = createAsyncTaskList(saving.saveSnapshot);
const first = taskList.completeTask("t1");
saving.calls[0].fail(new Error("受控的保存失败"));
console.log("等待后的失败：", JSON.stringify(await first));
console.log("失败后的 t1：", taskList.listTasks()[0].completed);
const retry = taskList.completeTask("t1");
saving.calls[1].succeed();
console.log("重试结果：", JSON.stringify(await retry));
