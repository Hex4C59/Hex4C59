import { createAsyncTaskList } from "./task-list.mjs";

export async function openTaskApp(store) {
  const loaded = await store.load();
  if (loaded.ok === false) return loaded;
  return {
    ok: true,
    format: loaded.format,
    taskList: createAsyncTaskList(store.saveSnapshot, loaded.tasks),
  };
}
