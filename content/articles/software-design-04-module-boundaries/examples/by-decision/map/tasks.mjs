import { defaultTasks } from "../../initial-tasks.mjs";

// 每次创建一份独立的演示数据。initialTasks 须已满足任务数据约定。
export function createTaskList(initialTasks = defaultTasks) {
  const tasks = new Map();
  for (const task of initialTasks) {
    tasks.set(task.id, { id: task.id, title: task.title, completed: task.completed });
  }

  function completeTask(id) {
    if (typeof id !== "string" || id.trim() === "") {
      return { ok: false, reason: "invalid-id" };
    }

    const task = tasks.get(id);

    if (task === undefined) {
      return { ok: false, reason: "not-found" };
    }

    const changed = task.completed === false;
    task.completed = true;

    return {
      ok: true,
      changed,
      task: {
        id: task.id,
        title: task.title,
        completed: task.completed,
      },
    };
  }

  function listTasks() {
    const result = [];
    for (const task of tasks.values()) {
      result.push({ id: task.id, title: task.title, completed: task.completed });
    }
    return result;
  }

  return { completeTask, listTasks };
}
