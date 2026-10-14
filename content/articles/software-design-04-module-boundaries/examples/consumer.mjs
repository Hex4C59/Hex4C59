import { createTableDispatcher } from "./request-entry.mjs";

export function runScenario(taskList) {
  const dispatch = createTableDispatcher(taskList);
  const results = [];
  for (const request of [
    { action: "list" },
    { action: "complete", id: "t1" },
    { action: "complete", id: "t1" },
    { action: "complete", id: "t9" },
    { action: "complete" },
    { action: "toString" },
  ]) {
    results.push(dispatch(request));
  }
  return { results, tasks: taskList.listTasks() };
}
