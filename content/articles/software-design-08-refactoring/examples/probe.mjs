import { createAsyncTaskList as correct } from "./03-map-direct.mjs";
import { createAsyncTaskList as reinsert } from "./faults/reinsert-task.mjs";
import { createAsyncTaskList as saveMap } from "./faults/save-map.mjs";
import { createAsyncTaskList as validateFirst } from "./faults/validate-first.mjs";
import { runMigrationChecks } from "./migration-checks.mjs";

const subjects = new Map([
  ["correct", correct], ["reinsert-task", reinsert],
  ["save-map", saveMap], ["validate-first", validateFirst],
]);
const name = process.argv[2] ?? "correct";
const createTaskList = subjects.get(name);
if (!createTaskList) {
  console.error("未知比较版本：" + name);
  process.exitCode = 2;
} else {
  try {
    await runMigrationChecks(createTaskList);
    console.log(name + "：检查通过");
  } catch (error) {
    console.error(name + "：检查失败：" + error.message.split("\n")[0]);
    process.exitCode = 1;
  }
}
