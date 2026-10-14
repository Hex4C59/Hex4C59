import { createTaskList } from "./tasks.mjs";
import { createBranchDispatcher } from "./by-branch.mjs";
import { createTableDispatcher } from "./by-table.mjs";

for (const [name, createDispatcher] of [
  ["条件分支", createBranchDispatcher],
  ["处理器表", createTableDispatcher],
]) {
  const dispatch = createDispatcher(createTaskList());
  console.log(name);
  for (const request of [
    { action: "list" },
    { action: "complete", id: "t1" },
    { action: "complete", id: "t1" },
    { action: "complete", id: "t9" },
    { action: "complete" },
    { action: "toString" },
  ]) {
    console.log(JSON.stringify(request), "=>", JSON.stringify(dispatch(request)));
  }
}
