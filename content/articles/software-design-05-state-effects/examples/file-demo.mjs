import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { defaultTasks } from "./initial-tasks.mjs";
import { createSavedTaskList } from "./save-before-adopt.mjs";

const directory = mkdtempSync(join(tmpdir(), "software-design-05-"));
const file = join(directory, "tasks.json");
try {
  writeFileSync(file, JSON.stringify(defaultTasks));
  const normal = createSavedTaskList(function saveSnapshot(tasks) {
    writeFileSync(file, JSON.stringify(tasks));
  });
  console.log("正常保存：", JSON.stringify(normal.completeTask("t1")));
  console.log("读回文件中的完成标记：", JSON.parse(readFileSync(file, "utf8"))[0].completed);

  writeFileSync(file, JSON.stringify(defaultTasks));
  const missingPath = createSavedTaskList(function saveSnapshot(tasks) {
    writeFileSync(join(directory, "missing", "tasks.json"), JSON.stringify(tasks));
  });
  console.log("真实路径错误：", JSON.stringify(missingPath.completeTask("t1")));
  console.log("路径错误后当前数据：", missingPath.listTasks()[0].completed);

  // 合成外部修改后才报错的保存函数，不声称操作系统真的发生了中途故障。
  const partial = createSavedTaskList(function saveSnapshot() {
    writeFileSync(file, '[{"id":');
    throw new Error("合成的写入部分内容后失败");
  });
  console.log("写入部分内容后报错：", JSON.stringify(partial.completeTask("t1")));
  console.log("报错后当前数据：", partial.listTasks()[0].completed);
  let valid = true;
  try { JSON.parse(readFileSync(file, "utf8")); } catch { valid = false; }
  console.log("文件仍为合法 JSON：", valid);
} finally {
  rmSync(directory, { recursive: true, force: true });
}
