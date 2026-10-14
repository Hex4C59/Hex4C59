import { defaultTasks } from "./initial-tasks.mjs";
import { createTaskList } from "./mutable-tasks.mjs";

// 反例：已修改当前任务，再尝试保存。失败返回值不能撤销之前的修改。
export function createUnsafeTaskList(saveSnapshot, initialTasks = defaultTasks) {
  if (typeof saveSnapshot !== "function") {
    throw new TypeError("需要提供在返回前完成的保存函数");
  }
  const taskList = createTaskList(initialTasks);
  function completeTask(id) {
    const result = taskList.completeTask(id);
    if (result.ok === false || result.changed === false) {
      return result;
    }
    try {
      const saveResult = saveSnapshot(taskList.listTasks());
      if (saveResult !== undefined) {
        return { ok: false, reason: "save-failed" };
      }
    } catch {
      return { ok: false, reason: "save-failed" };
    }
    return result;
  }
  return { listTasks: taskList.listTasks, completeTask };
}
