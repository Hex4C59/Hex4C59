import { copyTasks } from "./copy-tasks.mjs";

export function toTaskMap(tasks) {
  const byId = new Map();
  for (const task of copyTasks(tasks)) {
    byId.set(task.id, task);
  }
  return byId;
}
