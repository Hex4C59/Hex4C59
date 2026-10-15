export function isValidTasks(tasks) {
  if (!Array.isArray(tasks)) return false;
  const ids = new Set();
  for (const task of tasks) {
    if (task === null || typeof task !== "object" || Array.isArray(task)) return false;
    const keys = Object.keys(task);
    if (keys.length !== 3 || !keys.every(key => ["id", "title", "completed"].includes(key))) {
      return false;
    }
    if (typeof task.id !== "string" || task.id.trim() === "" || ids.has(task.id)) return false;
    if (typeof task.title !== "string" || typeof task.completed !== "boolean") return false;
    ids.add(task.id);
  }
  return true;
}
