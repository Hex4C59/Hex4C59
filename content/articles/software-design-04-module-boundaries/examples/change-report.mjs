import { readFileSync } from "node:fs";

export function changedFiles() {
  const byOperation = [];
  for (const name of ["state.mjs", "list-tasks.mjs", "complete-task.mjs", "index.mjs"]) {
    const before = readFileSync(new URL("./by-operation/array/" + name, import.meta.url));
    const after = readFileSync(new URL("./by-operation/map/" + name, import.meta.url));
    if (!before.equals(after)) byOperation.push(name);
  }
  const byDecision = [];
  const before = readFileSync(new URL("./by-decision/array/tasks.mjs", import.meta.url));
  const after = readFileSync(new URL("./by-decision/map/tasks.mjs", import.meta.url));
  if (!before.equals(after)) byDecision.push("tasks.mjs");
  return { byOperation, byDecision };
}
