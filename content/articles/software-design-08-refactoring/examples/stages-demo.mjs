import { versions } from "./versions.mjs";
import { runMigrationChecks } from "./migration-checks.mjs";

for (const [name, createTaskList] of versions) {
  await runMigrationChecks(createTaskList);
  const taskList = createTaskList(function saveSnapshot() {});
  const result = await taskList.completeTask("t1");
  console.log(name + "：检查通过；" + JSON.stringify(result));
}
console.log("直接把 Map 转为 JSON：", JSON.stringify(new Map([
  ["t1", { id: "t1", title: "写周报", completed: true }],
])));
