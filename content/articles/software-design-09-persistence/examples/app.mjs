import { resolve } from "node:path";
import { defaultTasks } from "./initial-tasks.mjs";
import { createFileStore } from "./file-store.mjs";
import { openTaskApp } from "./open-task-app.mjs";

async function main() {
  const [command, file, id] = process.argv.slice(2);
  if (typeof file !== "string" || file.trim() === "") {
    return { ok: false, reason: "invalid-arguments" };
  }
  if (!["init", "list", "complete"].includes(command)) {
    return { ok: false, reason: "unknown-command" };
  }
  const store = createFileStore(resolve(file));
  if (command === "init") return store.initialize(defaultTasks);
  const opened = await openTaskApp(store);
  if (opened.ok === false) return opened;
  if (command === "list") {
    return { ok: true, format: opened.format, tasks: opened.taskList.listTasks() };
  }
  return opened.taskList.completeTask(id);
}

try {
  const result = await main();
  console.log(JSON.stringify(result));
  process.exitCode = result.ok ? 0 : 1;
} catch (error) {
  console.error(error);
  process.exitCode = 1;
}
