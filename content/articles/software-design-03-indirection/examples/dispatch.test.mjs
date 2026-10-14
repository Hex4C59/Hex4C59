import test from "node:test";
import assert from "node:assert/strict";
import { createTaskList } from "./tasks.mjs";
import { createBranchDispatcher } from "./by-branch.mjs";
import { createTableDispatcher } from "./by-table.mjs";
import { createExtendedBranchDispatcher, createExtendedTableDispatcher } from "./extended.mjs";

for (const [name, createDispatcher] of [
  ["条件分支", createBranchDispatcher],
  ["处理器表", createTableDispatcher],
]) {
  test(`${name}：创建入口时不执行任何任务操作`, () => {
    let calls = 0;
    createDispatcher({
      listTasks() { calls += 1; },
      completeTask() { calls += 1; },
    });
    assert.equal(calls, 0);
  });

  test(`${name}：列出任务，然后完成 t1，再次完成不再修改`, () => {
    const taskList = createTaskList();
    const dispatch = createDispatcher(taskList);
    assert.deepEqual(dispatch({ action: "list" }), { ok: true, tasks: taskList.listTasks() });
    assert.deepEqual(dispatch({ action: "complete", id: "t1" }), {
      ok: true, changed: true, task: { id: "t1", title: "写周报", completed: true },
    });
    assert.equal(dispatch({ action: "complete", id: "t1" }).changed, false);
    assert.equal(taskList.listTasks()[1].completed, false);
  });

  test(`${name}：未知操作及对象常见属性名均被拒绝，不修改任务`, () => {
    const taskList = createTaskList();
    const dispatch = createDispatcher(taskList);
    const before = taskList.listTasks();
    for (const action of ["delete", "toString", "constructor", "__proto__", "Complete", " complete "]) {
      assert.deepEqual(dispatch({ action, id: "t1" }), { ok: false, reason: "unknown-action" });
    }
    assert.deepEqual(taskList.listTasks(), before);
  });

  test(`${name}：请求形状和操作名称格式错误时没有执行业务`, () => {
    let calls = 0;
    const dispatch = createDispatcher({
      listTasks() { calls += 1; },
      completeTask() { calls += 1; },
    });
    for (const request of [undefined, null, "complete", 7, true, [], () => {}]) {
      assert.deepEqual(dispatch(request), { ok: false, reason: "invalid-request" });
    }
    for (const action of [undefined, null, "", "  ", 7, {}, []]) {
      assert.deepEqual(dispatch({ action }), { ok: false, reason: "invalid-action" });
    }
    assert.equal(calls, 0);
  });

  test(`${name}：任务编号错误和任务不存在，保留任务函数原有结果`, () => {
    const taskList = createTaskList();
    const dispatch = createDispatcher(taskList);
    const before = taskList.listTasks();
    for (const id of [undefined, null, "", "  ", 12]) {
      assert.deepEqual(dispatch({ action: "complete", id }), { ok: false, reason: "invalid-id" });
    }
    assert.deepEqual(dispatch({ action: "complete", id: "t9" }), { ok: false, reason: "not-found" });
    assert.deepEqual(taskList.listTasks(), before);
  });

  test(`${name}：每次只执行选中的功能，并原样传入编号`, () => {
    const calls = [];
    const dispatch = createDispatcher({
      listTasks() { calls.push("list"); return []; },
      completeTask(id) { calls.push(["complete", id]); return { ok: false, reason: "not-found" }; },
    });
    dispatch({ action: "list", id: "ignored" });
    dispatch({ action: "complete", id: " t1 " });
    dispatch({ action: "missing", id: "t1" });
    assert.deepEqual(calls, ["list", ["complete", " t1 "]]);
  });

  test(`${name}：入口交回的数据仍是副本`, () => {
    const taskList = createTaskList();
    const dispatch = createDispatcher(taskList);
    dispatch({ action: "list" }).tasks[0].title = "外部修改";
    dispatch({ action: "complete", id: "t1" }).task.completed = false;
    assert.deepEqual(taskList.listTasks()[0], { id: "t1", title: "写周报", completed: true });
  });

  test(`${name}：多余字段被忽略，合法操作只按约定字段执行`, () => {
    const dispatch = createDispatcher(createTaskList());
    assert.equal(dispatch({ action: "list", unused: true }).ok, true);
    assert.equal(dispatch({ action: "complete", id: "t1", completed: false }).task.completed, true);
  });

  test(`${name}：意外抛出的异常继续交给使用入口的代码`, () => {
    const error = new Error("演示中的程序错误");
    const dispatch = createDispatcher({
      listTasks() { throw error; },
      completeTask() { throw error; },
    });
    assert.throws(() => dispatch({ action: "list" }), (actual) => actual === error);
    assert.throws(() => dispatch({ action: "complete", id: "t1" }), (actual) => actual === error);
  });
}

test("同一组请求，两种安排产生相同结果和最终任务", () => {
  const left = createTaskList();
  const right = createTaskList();
  const branch = createBranchDispatcher(left);
  const table = createTableDispatcher(right);
  for (const request of [
    { action: "list" }, { action: "complete", id: "t1" },
    { action: "complete", id: "t1" }, { action: "complete", id: "t9" },
    { action: "complete" }, { action: "toString" }, {}, null,
  ]) {
    assert.deepEqual(branch(request), table(request));
    assert.deepEqual(left.listTasks(), right.listTasks());
  }
});

test("两个独立创建的任务列表互不影响", () => {
  const first = createTableDispatcher(createTaskList());
  const second = createTableDispatcher(createTaskList());
  first({ action: "complete", id: "t1" });
  assert.equal(second({ action: "list" }).tasks[0].completed, false);
});

for (const [name, createDispatcher] of [
  ["增加分支", createExtendedBranchDispatcher],
  ["增加表项", createExtendedTableDispatcher],
]) {
  test(`${name}：count-open 随完成操作变化，并保留原有失败约定`, () => {
    const taskList = createTaskList();
    const dispatch = createDispatcher(taskList);
    assert.deepEqual(dispatch({ action: "count-open" }), { ok: true, count: 2 });
    assert.equal(dispatch({ action: "complete", id: "t1" }).ok, true);
    assert.deepEqual(dispatch({ action: "count-open" }), { ok: true, count: 1 });
    assert.equal(dispatch({ action: "list" }).tasks.length, 2);
    assert.deepEqual(dispatch({ action: "toString" }), { ok: false, reason: "unknown-action" });
    assert.deepEqual(dispatch({ action: "complete", id: "t9" }), { ok: false, reason: "not-found" });
  });
}
