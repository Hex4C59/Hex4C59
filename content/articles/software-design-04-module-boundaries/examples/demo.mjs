import { createTaskList as operationArray } from "./by-operation/array/index.mjs";
import { createTaskList as operationMap } from "./by-operation/map/index.mjs";
import { createTaskList as decisionArray } from "./by-decision/array/tasks.mjs";
import { createTaskList as decisionMap } from "./by-decision/map/tasks.mjs";
import { runScenario } from "./consumer.mjs";

for (const [name, createTaskList] of [
  ["按操作拆分 / 数组", operationArray],
  ["按操作拆分 / Map", operationMap],
  ["集中隐藏表示 / 数组", decisionArray],
  ["集中隐藏表示 / Map", decisionMap],
]) {
  console.log(name);
  console.log(JSON.stringify(runScenario(createTaskList())));
}
