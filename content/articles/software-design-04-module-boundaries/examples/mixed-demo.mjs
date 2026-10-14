import { defaultTasks } from "./initial-tasks.mjs";
import { createState } from "./by-operation/map/state.mjs";
import { completeTask } from "./by-operation/array/complete-task.mjs";

const state = createState(defaultTasks);
console.log("新表示中确实存在 t1：", state.tasks.has("t1"));
console.log("只换状态文件，仍用旧完成代码：", JSON.stringify(completeTask(state, "t1")));
console.log("t1 的完成标记：", state.tasks.get("t1").completed);
