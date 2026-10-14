export function createState(initialTasks) {
  const tasks = [];
  for (const task of initialTasks) {
    tasks.push({ id: task.id, title: task.title, completed: task.completed });
  }
  return { tasks };
}
