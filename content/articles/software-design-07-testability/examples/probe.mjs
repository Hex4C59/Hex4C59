import { createAsyncTaskList } from "./async-task-list.mjs";
import { createAsyncTaskList as earlyAdopt } from "./faults/early-adopt.mjs";
import { createAsyncTaskList as ignoreRejection } from "./faults/ignore-rejection.mjs";
import { createAsyncTaskList as allowOverlap } from "./faults/allow-overlap.mjs";
import { runContractChecks } from "./contract-checks.mjs";

const versions = new Map([
  ["correct", createAsyncTaskList],
  ["early-adopt", earlyAdopt],
  ["ignore-rejection", ignoreRejection],
  ["allow-overlap", allowOverlap],
]);
const name = process.argv[2] ?? "correct";
const createTaskList = versions.get(name);
if (!createTaskList) {
  console.error("未知比较版本");
  process.exitCode = 2;
} else {
  try {
    await runContractChecks(createTaskList);
    console.log(name + "：检查通过");
  } catch (error) {
    console.error(name + "：检查失败：" + error.message.split("\n")[0]);
    process.exitCode = 1;
  }
}
