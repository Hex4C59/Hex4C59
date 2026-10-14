export function completeTask(state, id) {
  if (typeof id !== "string" || id.trim() === "") {
    return { ok: false, reason: "invalid-id" };
  }

  const task = state.tasks.get(id);

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
