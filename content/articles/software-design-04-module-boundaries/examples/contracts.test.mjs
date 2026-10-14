import test from "node:test";
import assert from "node:assert/strict";
import { createTaskList as operationArray } from "./by-operation/array/index.mjs";
import { createTaskList as operationMap } from "./by-operation/map/index.mjs";
import { createTaskList as decisionArray } from "./by-decision/array/tasks.mjs";
import { createTaskList as decisionMap } from "./by-decision/map/tasks.mjs";
import { createTableDispatcher } from "./request-entry.mjs";
import { runScenario } from "./consumer.mjs";
import { changedFiles } from "./change-report.mjs";
import { createLeakyStore } from "./leaky-store.mjs";
import { defaultTasks } from "./initial-tasks.mjs";
import { createState as createMapState } from "./by-operation/map/state.mjs";
import { completeTask as completeWithArray } from "./by-operation/array/complete-task.mjs";

const implementations = [
  ["按操作拆分 / 数组", operationArray],
  ["按操作拆分 / Map", operationMap],
  ["集中隐藏表示 / 数组", decisionArray],
  ["集中隐藏表示 / Map", decisionMap],
];

for (const [name, createTaskList] of implementations) {
  test(`${name}：完成目标、重复完成和其他任务保持原有约定`, () => {
    const taskList = createTaskList();
    assert.deepEqual(taskList.listTasks(), defaultTasks);
    const first = taskList.completeTask("t1");
    assert.deepEqual(first, { ok: true, changed: true, task: { id: "t1", title: "写周报", completed: true } });
    assert.deepEqual(taskList.completeTask("t1"), { ...first, changed: false });
    assert.deepEqual(taskList.listTasks()[1], defaultTasks[1]);
  });

  test(`${name}：非法编号和找不到任务时不改变数据`, () => {
    const taskList = createTaskList();
    const before = taskList.listTasks();
    for (const id of [undefined, null, "", "  ", 0, {}, []]) {
      assert.deepEqual(taskList.completeTask(id), { ok: false, reason: "invalid-id" });
    }
    for (const id of ["t9", " t1 ", "T1"]) {
      assert.deepEqual(taskList.completeTask(id), { ok: false, reason: "not-found" });
    }
    assert.deepEqual(taskList.listTasks(), before);
  });

  test(`${name}：列出和完成返回的副本不能改写内部数据`, () => {
    const taskList = createTaskList();
    const listed = taskList.listTasks();
    listed[0].title = "外部改写";
    listed.push({ id: "t9", title: "外部增加", completed: false });
    const completed = taskList.completeTask("t1");
    completed.task.completed = false;
    assert.deepEqual(taskList.listTasks(), [
      { id: "t1", title: "写周报", completed: true }, defaultTasks[1],
    ]);
  });

  test(`${name}：复制合法初始数据、保留顺序、不同实例互不影响`, () => {
    const seed = [
      { id: "10", title: "先放入", completed: false },
      { id: "2", title: "后放入", completed: true },
    ];
    const first = createTaskList(seed);
    const second = createTaskList(seed);
    assert.deepEqual(first.listTasks().map(task => task.id), ["10", "2"]);
    seed[0].title = "修改传入对象";
    first.completeTask("10");
    assert.equal(first.listTasks()[0].title, "先放入");
    assert.equal(second.listTasks()[0].completed, false);
    assert.equal(seed[0].completed, false);
  });

  test(`${name}：对共同调用者只提供两项任务操作`, () => {
    const taskList = createTaskList();
    assert.deepEqual(Object.keys(taskList).sort(), ["completeTask", "listTasks"]);
    assert.equal(typeof taskList.completeTask, "function");
    assert.equal(typeof taskList.listTasks, "function");
    assert.equal(taskList.tasks, undefined);
    assert.equal(taskList.state, undefined);
  });

  test(`${name}：沿用上一章请求入口时，任务结果和请求拒绝继续成立`, () => {
    const taskList = createTaskList();
    const dispatch = createTableDispatcher(taskList);
    assert.deepEqual(dispatch({ action: "list" }), { ok: true, tasks: defaultTasks });
    assert.equal(dispatch({ action: "complete", id: "t1" }).changed, true);
    assert.equal(dispatch({ action: "complete", id: "t1" }).changed, false);
    assert.deepEqual(dispatch({ action: "complete", id: "t9" }), { ok: false, reason: "not-found" });
    assert.deepEqual(dispatch({ action: "complete" }), { ok: false, reason: "invalid-id" });
    for (const action of ["toString", "constructor", "__proto__", "missing"]) {
      assert.deepEqual(dispatch({ action }), { ok: false, reason: "unknown-action" });
    }
    assert.deepEqual(dispatch(null), { ok: false, reason: "invalid-request" });
    assert.deepEqual(dispatch({}), { ok: false, reason: "invalid-action" });
  });
}

test("同一份调用者和请求入口使用四个完整版本，观察结果一致", () => {
  const expected = runScenario(decisionArray());
  for (const [, createTaskList] of implementations) {
    assert.deepEqual(runScenario(createTaskList()), expected);
  }
});

test("本次表示变化的快照确实分别修改三个文件和一个文件", () => {
  assert.deepEqual(changedFiles(), {
    byOperation: ["state.mjs", "list-tasks.mjs", "complete-task.mjs"],
    byDecision: ["tasks.mjs"],
  });
});

test("只替换状态表示、仍使用旧完成代码，会把存在的任务判断为不存在", () => {
  const state = createMapState(defaultTasks);
  assert.equal(state.tasks.has("t1"), true);
  assert.deepEqual(completeWithArray(state, "t1"), { ok: false, reason: "not-found" });
  assert.equal(state.tasks.get("t1").completed, false);
});

test("不直接导出数组、却通过函数返回内部数组，仍可被外部改写", () => {
  const leaky = createLeakyStore();
  leaky.getTasks()[0].title = "外部改写";
  assert.equal(leaky.getTasks()[0].title, "外部改写");
});
