// Deliberate fault: delete then insert the existing key.
export function planMapCompletion(currentTasks, id) {
  if (typeof id !== "string" || id.trim() === "") {
    return { result: { ok: false, reason: "invalid-id" }, nextTasks: null };
  }
  const target = currentTasks.get(id);
  if (target === undefined) {
    return { result: { ok: false, reason: "not-found" }, nextTasks: null };
  }
  const changed = target.completed === false;
  const completedTask = { id: target.id, title: target.title, completed: true };
  const result = { ok: true, changed, task: { ...completedTask } };
  if (changed === false) {
    return { result, nextTasks: null };
  }
  const nextTasks = new Map(currentTasks);
  nextTasks.delete(id);
  nextTasks.set(id, completedTask);
  return { result, nextTasks };
}
