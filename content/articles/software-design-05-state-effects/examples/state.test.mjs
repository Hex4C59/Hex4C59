import test from "node:test";
import assert from "node:assert/strict";
import { defaultTasks } from "./initial-tasks.mjs";
import { copyTasks } from "./copy-tasks.mjs";
import { planCompletion } from "./plan-completion.mjs";
import { createTaskList } from "./task-list.mjs";
import { createTaskList as createMutableTaskList } from "./mutable-tasks.mjs";
import { createSavedTaskList } from "./save-before-adopt.mjs";
import { createUnsafeTaskList } from "./unsafe-save.mjs";

test("计算可以接收冻结的任务数据，并且不修改输入", () => {
  const input = copyTasks(defaultTasks);
  for (const task of input) Object.freeze(task);
  Object.freeze(input);
  const proposal = planCompletion(input, "t1");
  assert.equal(input[0].completed, false);
  assert.equal(proposal.nextTasks[0].completed, true);
  assert.deepEqual(proposal.result, { ok: true, changed: true, task: { id: "t1", title: "写周报", completed: true } });
});

test("非法编号和未知任务没有下一份数据，原数据不变", () => {
  const input = copyTasks(defaultTasks);
  for (const id of [undefined, null, "", "  ", 4, {}, []]) {
    assert.deepEqual(planCompletion(input, id), { result: { ok: false, reason: "invalid-id" }, nextTasks: null });
  }
  assert.deepEqual(planCompletion(input, "t9"), { result: { ok: false, reason: "not-found" }, nextTasks: null });
  assert.deepEqual(input, defaultTasks);
});

test("重复完成无需采用新数据，但结果仍交回副本", () => {
  const first = planCompletion(defaultTasks, "t1");
  const repeated = planCompletion(first.nextTasks, "t1");
  assert.equal(repeated.result.changed, false);
  assert.equal(repeated.nextTasks, null);
  repeated.result.task.completed = false;
  assert.equal(first.nextTasks[0].completed, true);
});

test("相同输入得到相同字段内容，两次计算不共享新数组", () => {
  const first = planCompletion(defaultTasks, "t1");
  const second = planCompletion(defaultTasks, "t1");
  assert.deepEqual(first, second);
  assert.notEqual(first.nextTasks, second.nextTasks);
  first.nextTasks[0].title = "修改一次计算";
  assert.equal(second.nextTasks[0].title, "写周报");
});

test("交回的任务结果和建议采用的数据互不共享任务对象", () => {
  const proposal = planCompletion(defaultTasks, "t1");
  proposal.result.task.completed = false;
  assert.equal(proposal.nextTasks[0].completed, true);
});

test("计算本身不记住前一次执行，下一次输入决定下一次结果", () => {
  const first = planCompletion(defaultTasks, "t1");
  assert.equal(planCompletion(defaultTasks, "t1").result.changed, true);
  assert.equal(planCompletion(first.nextTasks, "t1").result.changed, false);
});

for (const [name, create] of [["原地修改版", createMutableTaskList], ["先计算再采用版", createTaskList]]) {
  test(`${name}：完成与重复完成保留原来的任务规则`, () => {
    const list = create();
    assert.equal(list.completeTask("t1").changed, true);
    assert.equal(list.completeTask("t1").changed, false);
    assert.deepEqual(list.listTasks(), [{ ...defaultTasks[0], completed: true }, defaultTasks[1]]);
  });
  test(`${name}：错误输入、精确编号和未知任务不改数据`, () => {
    const list = create();
    for (const id of [undefined, null, "", "  ", {}, [], 4]) {
      assert.deepEqual(list.completeTask(id), { ok: false, reason: "invalid-id" });
    }
    for (const id of ["t9", " t1 ", "T1"]) {
      assert.deepEqual(list.completeTask(id), { ok: false, reason: "not-found" });
    }
    assert.deepEqual(list.listTasks(), defaultTasks);
  });
  test(`${name}：返回结果与列表副本不能改写当前任务`, () => {
    const list = create();
    list.listTasks()[0].title = "外部修改";
    list.completeTask("t1").task.completed = false;
    assert.deepEqual(list.listTasks()[0], { id: "t1", title: "写周报", completed: true });
  });
  test(`${name}：初始数据复制、顺序与独立实例继续成立`, () => {
    const initial = [{ id: "10", title: "先", completed: false }, { id: "2", title: "后", completed: true }];
    const first = create(initial);
    const second = create(initial);
    initial[0].title = "修改初始数据";
    first.completeTask("10");
    assert.deepEqual(first.listTasks().map(task => task.id), ["10", "2"]);
    assert.equal(first.listTasks()[0].title, "先");
    assert.equal(second.listTasks()[0].completed, false);
    assert.equal(initial[0].completed, false);
  });
}

test("两种内存实现接受同一组操作后，结果与当前数据一致", () => {
  const first = createMutableTaskList();
  const second = createTaskList();
  for (const id of ["t1", "t1", "t9", "", undefined, "t2"]) {
    assert.deepEqual(first.completeTask(id), second.completeTask(id));
    assert.deepEqual(first.listTasks(), second.listTasks());
  }
});

test("保存时当前状态仍是旧数据，正常返回后才采用新数据", () => {
  let list;
  let calls = 0;
  list = createSavedTaskList(function saveSnapshot(next) {
    calls += 1;
    assert.equal(list.listTasks()[0].completed, false);
    assert.equal(next[0].completed, true);
  });
  assert.equal(calls, 0);
  assert.equal(list.completeTask("t1").changed, true);
  assert.equal(list.listTasks()[0].completed, true);
  assert.equal(calls, 1);
});

test("保存抛错时返回保存失败，保留原来的当前数据", () => {
  const list = createSavedTaskList(function saveSnapshot() { throw new Error("合成失败"); });
  assert.deepEqual(list.completeTask("t1"), { ok: false, reason: "save-failed" });
  assert.deepEqual(list.listTasks(), defaultTasks);
});

test("首次失败后重试能再次计算、保存并采用", () => {
  let calls = 0;
  const saved = [];
  const list = createSavedTaskList(function saveSnapshot(next) {
    calls += 1;
    if (calls === 1) throw new Error("首次失败");
    saved.push(copyTasks(next));
  });
  assert.equal(list.completeTask("t1").ok, false);
  assert.equal(list.completeTask("t1").changed, true);
  assert.equal(calls, 2);
  assert.equal(saved.length, 1);
  assert.equal(list.listTasks()[0].completed, true);
});

test("反例先改后存：失败已改当前数据，重试会因没有新变化而跳过保存", () => {
  let calls = 0;
  const list = createUnsafeTaskList(function saveSnapshot() { calls += 1; throw new Error("保存失败"); });
  assert.deepEqual(list.completeTask("t1"), { ok: false, reason: "save-failed" });
  assert.equal(list.listTasks()[0].completed, true);
  assert.equal(list.completeTask("t1").changed, false);
  assert.equal(calls, 1);
});

test("保存函数改写或保留传入副本，不会改变后来采用的任务", () => {
  let retained;
  const list = createSavedTaskList(function saveSnapshot(next) {
    retained = next;
    next[0].title = "保存函数修改副本";
  });
  const result = list.completeTask("t1");
  retained[0].completed = false;
  result.task.title = "调用者修改结果";
  list.listTasks()[0].completed = false;
  assert.deepEqual(list.listTasks()[0], { id: "t1", title: "写周报", completed: true });
});

test("输入错误、任务不存在和重复完成都不会再次保存", () => {
  let calls = 0;
  const list = createSavedTaskList(function saveSnapshot() { calls += 1; });
  for (const id of [undefined, "", "t9"]) list.completeTask(id);
  assert.equal(calls, 0);
  list.completeTask("t1");
  list.completeTask("t1");
  assert.equal(calls, 1);
});

test("保存函数先修改外部数据再抛错，内存保留原样但外部修改不会自动撤销", () => {
  const saved = [];
  const list = createSavedTaskList(function saveSnapshot(next) {
    saved.push(copyTasks(next));
    throw new Error("已经修改外部数据后报错");
  });
  assert.equal(list.completeTask("t1").ok, false);
  assert.equal(list.listTasks()[0].completed, false);
  assert.equal(saved[0][0].completed, true);
});

test("不符合约定的保存返回值被拒绝，不采用新数据", () => {
  const list = createSavedTaskList(function saveSnapshot() { return "其他返回值"; });
  assert.deepEqual(list.completeTask("t1"), { ok: false, reason: "save-failed" });
  assert.equal(list.listTasks()[0].completed, false);
});

test("保存接口需要函数，创建列表不会自动保存已有完成任务", () => {
  assert.throws(() => createSavedTaskList(null), TypeError);
  let calls = 0;
  const initial = copyTasks(defaultTasks);
  initial[0].completed = true;
  const list = createSavedTaskList(function saveSnapshot() { calls += 1; }, initial);
  assert.equal(list.completeTask("t1").changed, false);
  assert.equal(calls, 0);
});

test("两个独立所有者写同一个外部快照，后一次会覆盖前一次的任务进度", () => {
  let saved = copyTasks(defaultTasks);
  function saveSnapshot(tasks) { saved = copyTasks(tasks); }
  const first = createSavedTaskList(saveSnapshot);
  const second = createSavedTaskList(saveSnapshot);
  first.completeTask("t1");
  assert.deepEqual(saved.map(task => task.completed), [true, false]);
  second.completeTask("t2");
  assert.deepEqual(saved.map(task => task.completed), [false, true]);
  assert.equal(first.listTasks()[0].completed, true);
});
