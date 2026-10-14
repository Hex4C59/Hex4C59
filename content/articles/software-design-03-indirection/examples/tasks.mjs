const defaultTasks = [
  { id: "t1", title: "写周报", completed: false },
  { id: "t2", title: "整理笔记", completed: false },
];

// 每次创建一份独立的演示数据。initialTasks 须已满足任务数据约定。
export function createTaskList(initialTasks = defaultTasks) {
  const tasks = [];
  for (const task of initialTasks) {
    tasks.push({ id: task.id, title: task.title, completed: task.completed });
  }

  function completeTask(id) {
    if (typeof id !== "string" || id.trim() === "") {
      return { ok: false, reason: "invalid-id" };
    }

    let task;
    for (const item of tasks) {
      if (item.id === id) {
        task = item;
        break;
      }
    }

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
    for (const task of tasks) {
      result.push({ id: task.id, title: task.title, completed: task.completed });
    }
    return result;
  }

  return { completeTask, listTasks };
}
