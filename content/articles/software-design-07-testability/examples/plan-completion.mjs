import { copyTasks } from "./copy-tasks.mjs";

export function planCompletion(tasks, id) {
  if (typeof id !== "string" || id.trim() === "") {
    return { result: { ok: false, reason: "invalid-id" }, nextTasks: null };
  }

  const nextTasks = copyTasks(tasks);
  let target;
  for (const task of nextTasks) {
    if (task.id === id) {
      target = task;
      break;
    }
  }
  if (target === undefined) {
    return { result: { ok: false, reason: "not-found" }, nextTasks: null };
  }

  const changed = target.completed === false;
  target.completed = true;
  const result = {
    ok: true,
    changed,
    task: { id: target.id, title: target.title, completed: target.completed },
  };
  if (changed === false) {
    return { result, nextTasks: null };
  }
  return { result, nextTasks };
}
