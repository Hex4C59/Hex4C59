export function createState(initialTasks) {
  const tasks = new Map();
  for (const task of initialTasks) {
    tasks.set(task.id, { id: task.id, title: task.title, completed: task.completed });
  }
  return { tasks };
}
