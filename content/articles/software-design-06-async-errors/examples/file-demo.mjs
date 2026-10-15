import { mkdtemp, writeFile, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createAsyncTaskList } from "./async-task-list.mjs";

const directory = await mkdtemp(join(tmpdir(), "software-design-06-"));
try {
  const file = join(directory, "tasks.json");
  const taskList = createAsyncTaskList(function saveSnapshot(tasks) {
    return writeFile(file, JSON.stringify(tasks));
  });
  console.log("真实文件结果：", JSON.stringify(await taskList.completeTask("t1")));
  console.log("读回的 t1：", JSON.parse(await readFile(file, "utf8"))[0].completed);
  const failing = createAsyncTaskList(function saveSnapshot(tasks) {
    return writeFile(join(directory, "missing", "tasks.json"), JSON.stringify(tasks));
  });
  console.log("路径错误结果：", JSON.stringify(await failing.completeTask("t1")));
  console.log("失败后内存 t1：", failing.listTasks()[0].completed);
} finally {
  await rm(directory, { recursive: true, force: true });
}
