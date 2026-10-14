import { defaultTasks } from "./initial-tasks.mjs";

// 反例：返回内部数组，使用者可以绕过任务操作直接修改数据。
export function createLeakyStore() {
  const tasks = [];
  for (const task of defaultTasks) {
    tasks.push({ id: task.id, title: task.title, completed: task.completed });
  }
  function getTasks() {
    return tasks;
  }
  return { getTasks };
}
