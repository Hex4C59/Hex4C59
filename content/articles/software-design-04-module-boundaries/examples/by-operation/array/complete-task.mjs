export function completeTask(state, id) {
  if (typeof id !== "string" || id.trim() === "") {
    return { ok: false, reason: "invalid-id" };
  }

  let task;
  for (const item of state.tasks) {
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
