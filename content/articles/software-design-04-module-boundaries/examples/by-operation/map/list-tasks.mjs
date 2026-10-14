export function listTasks(state) {
  const result = [];
  for (const task of state.tasks.values()) {
    result.push({ id: task.id, title: task.title, completed: task.completed });
  }
  return result;
}
