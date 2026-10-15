import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createAsyncTaskList } from "./async-task-list.mjs";
import { createJsonFileSave } from "./json-file-save.mjs";

const directory = await mkdtemp(join(tmpdir(), "software-design-07-"));
try {
  const file = join(directory, "tasks.json");
  const taskList = createAsyncTaskList(createJsonFileSave(file));
  console.log("真实保存结果：", JSON.stringify(await taskList.completeTask("t1")));
  console.log("读回文件的完成标记：", JSON.stringify(JSON.parse(await readFile(file, "utf8")).map(task => task.completed)));
  const failing = createAsyncTaskList(createJsonFileSave(join(directory, "missing", "tasks.json")));
  console.log("真实路径失败：", JSON.stringify(await failing.completeTask("t1")));
  console.log("失败后的完成标记：", JSON.stringify(failing.listTasks().map(task => task.completed)));
} finally {
  await rm(directory, { recursive: true, force: true });
}
