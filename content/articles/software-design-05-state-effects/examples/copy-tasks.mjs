export function copyTasks(tasks) {
  const copies = [];
  for (const task of tasks) {
    copies.push({ id: task.id, title: task.title, completed: task.completed });
  }
  return copies;
}
