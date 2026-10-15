// 故意错误：把所有读取失败都替换成默认任务。
import { createAsyncTaskList } from "../task-list.mjs";
import { defaultTasks } from "../initial-tasks.mjs";

export async function openWithReset(store) {
  const loaded = await store.load();
  return {
    ok: true,
    format: loaded.ok ? loaded.format : "fallback",
    taskList: createAsyncTaskList(store.saveSnapshot, loaded.ok ? loaded.tasks : defaultTasks),
  };
}
