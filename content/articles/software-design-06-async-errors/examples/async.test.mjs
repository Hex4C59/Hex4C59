import test from "node:test";
import assert from "node:assert/strict";
import { defaultTasks } from "./initial-tasks.mjs";
import { copyTasks } from "./copy-tasks.mjs";
import { createAsyncTaskList } from "./async-task-list.mjs";
import { createControlledSave } from "./controlled-save.mjs";
import { createWithoutWait } from "./without-wait.mjs";
import { createWithoutBusy } from "./without-busy.mjs";
import { regularFailure, asyncFailure, returnTaskFailure, returnWithoutAwait, returnWithAwait } from "./promise-basics.mjs";

test("创建时不保存，错误的保存接口在创建时同步抛出", () => {
  const saving = createControlledSave();
  createAsyncTaskList(saving.saveSnapshot);
  assert.equal(saving.calls.length, 0);
  assert.throws(() => createAsyncTaskList(null), TypeError);
});

test("完成函数始终返回 Promise，即使编号错误也要取得其中的结果", async () => {
  const list = createAsyncTaskList(() => {});
  const pending = list.completeTask("");
  assert.ok(pending instanceof Promise);
  assert.equal(pending.ok, undefined);
  assert.deepEqual(await pending, { ok: false, reason: "invalid-id" });
});

test("等待保存期间当前数据保留原样，保存结束后才采用", async () => {
  const saving = createControlledSave();
  const list = createAsyncTaskList(saving.saveSnapshot);
  const pending = list.completeTask("t1");
  assert.equal(saving.calls.length, 1);
  assert.equal(saving.calls[0].tasks[0].completed, true);
  assert.deepEqual(list.listTasks(), defaultTasks);
  saving.calls[0].succeed();
  assert.deepEqual(await pending, { ok: true, changed: true, task: { id: "t1", title: "写周报", completed: true } });
  assert.equal(list.listTasks()[0].completed, true);
  assert.equal(list.listTasks()[1].completed, false);
});

test("等待时拒绝第二次修改，busy 优先于编号检查，不再次保存", async () => {
  const saving = createControlledSave();
  const list = createAsyncTaskList(saving.saveSnapshot);
  const pending = list.completeTask("t1");
  for (const id of ["t2", "t1", "t9", "", undefined]) {
    assert.deepEqual(await list.completeTask(id), { ok: false, reason: "busy" });
  }
  assert.equal(saving.calls.length, 1);
  saving.calls[0].succeed();
  await pending;
});

test("第一项结束后重新提交第二项，基于新状态计算，不覆盖第一项", async () => {
  const saving = createControlledSave();
  const list = createAsyncTaskList(saving.saveSnapshot);
  const first = list.completeTask("t1");
  assert.equal((await list.completeTask("t2")).reason, "busy");
  saving.calls[0].succeed();
  await first;
  const second = list.completeTask("t2");
  assert.deepEqual(saving.calls[1].tasks.map(task => task.completed), [true, true]);
  saving.calls[1].succeed();
  await second;
  assert.deepEqual(list.listTasks().map(task => task.completed), [true, true]);
});

test("保存拒绝时返回 save-failed，保留旧状态并允许重试", async () => {
  const saving = createControlledSave();
  const list = createAsyncTaskList(saving.saveSnapshot);
  const first = list.completeTask("t1");
  saving.calls[0].fail(new Error("受控失败"));
  assert.deepEqual(await first, { ok: false, reason: "save-failed" });
  assert.deepEqual(list.listTasks(), defaultTasks);
  const retry = list.completeTask("t1");
  saving.calls[1].succeed();
  assert.equal((await retry).changed, true);
});

test("保存函数同步抛错也在同一处映射，忙碌状态会释放", async () => {
  let calls = 0;
  const list = createAsyncTaskList(() => { calls += 1; throw new Error("同步失败"); });
  assert.deepEqual(await list.completeTask("t1"), { ok: false, reason: "save-failed" });
  assert.deepEqual(await list.completeTask("t1"), { ok: false, reason: "save-failed" });
  assert.equal(calls, 2);
  assert.deepEqual(list.listTasks(), defaultTasks);
});

test("同步保存成功仍可使用，但采用发生在 await 之后", async () => {
  let calls = 0;
  const list = createAsyncTaskList(() => { calls += 1; });
  const pending = list.completeTask("t1");
  assert.equal(calls, 1);
  assert.equal(list.listTasks()[0].completed, false);
  assert.equal((await pending).ok, true);
  assert.equal(list.listTasks()[0].completed, true);
});

test("保存正常履行但返回额外数据，按接口拒绝且释放忙碌状态", async () => {
  const list = createAsyncTaskList(() => Promise.resolve("意外值"));
  assert.equal((await list.completeTask("t1")).reason, "save-failed");
  assert.equal((await list.completeTask("t2")).reason, "save-failed");
  assert.deepEqual(list.listTasks(), defaultTasks);
});

test("非法编号和未知任务不保存，并能继续接受后面的有效操作", async () => {
  let calls = 0;
  const list = createAsyncTaskList(() => { calls += 1; });
  for (const id of [undefined, null, "", "  ", 0, {}, []]) {
    assert.deepEqual(await list.completeTask(id), { ok: false, reason: "invalid-id" });
  }
  for (const id of ["t9", " t1 ", "T1"]) {
    assert.deepEqual(await list.completeTask(id), { ok: false, reason: "not-found" });
  }
  assert.equal(calls, 0);
  assert.deepEqual(list.listTasks(), defaultTasks);
  assert.equal((await list.completeTask("t1")).ok, true);
});

test("重复完成成功但不再保存，返回结果仍为副本", async () => {
  let calls = 0;
  const list = createAsyncTaskList(() => { calls += 1; });
  await list.completeTask("t1");
  const result = await list.completeTask("t1");
  assert.equal(result.changed, false);
  result.task.completed = false;
  assert.equal(calls, 1);
  assert.equal(list.listTasks()[0].completed, true);
});

test("保存得到的副本、列表副本和完成结果均不能改写当前任务", async () => {
  let retained;
  const list = createAsyncTaskList(tasks => { retained = tasks; });
  const result = await list.completeTask("t1");
  retained[0].title = "保存函数改写";
  result.task.completed = false;
  list.listTasks()[0].completed = false;
  assert.deepEqual(list.listTasks()[0], { id: "t1", title: "写周报", completed: true });
});

test("初始数据复制、列表顺序和独立实例保持不变", async () => {
  const initial = [{ id: "10", title: "先", completed: false }, { id: "2", title: "后", completed: false }];
  const first = createAsyncTaskList(() => {}, initial);
  const second = createAsyncTaskList(() => {}, initial);
  initial[0].title = "改初始数据";
  await first.completeTask("10");
  assert.deepEqual(first.listTasks().map(task => task.id), ["10", "2"]);
  assert.equal(first.listTasks()[0].title, "先");
  assert.equal(second.listTasks()[0].completed, false);
});

test("保存函数修改外部快照后拒绝，内存不采用也不会撤销外部修改", async () => {
  let external;
  const list = createAsyncTaskList(tasks => { external = copyTasks(tasks); return Promise.reject(new Error("改后拒绝")); });
  assert.equal((await list.completeTask("t1")).ok, false);
  assert.equal(list.listTasks()[0].completed, false);
  assert.equal(external[0].completed, true);
});

test("保存已经解决但等待代码尚未恢复时，当前状态仍忙碌", async () => {
  const saving = createControlledSave();
  const list = createAsyncTaskList(saving.saveSnapshot);
  const pending = list.completeTask("t1");
  saving.calls[0].succeed();
  const rejectedWhileResuming = list.completeTask("t2");
  assert.equal((await rejectedWhileResuming).reason, "busy");
  await pending;
  assert.equal(list.listTasks()[0].completed, true);
});

test("没有 await 的反例提前报告成功，并丢失稍后的保存拒绝", async () => {
  const saving = createControlledSave();
  let ignored;
  const list = createWithoutWait(tasks => { ignored = saving.saveSnapshot(tasks); return ignored; });
  const pending = list.completeTask("t1");
  const observed = ignored.catch(error => error.message);
  assert.equal((await pending).ok, true);
  assert.equal(list.listTasks()[0].completed, true);
  saving.calls[0].fail(new Error("稍后失败"));
  assert.equal(await observed, "稍后失败");
  assert.equal(list.listTasks()[0].completed, true);
});

test("只有 await 没有 busy：两份基于旧数据的结果会互相覆盖", async () => {
  const saving = createControlledSave();
  const list = createWithoutBusy(saving.saveSnapshot);
  const first = list.completeTask("t1");
  const second = list.completeTask("t2");
  assert.equal(saving.calls.length, 2);
  saving.calls[0].succeed();
  await first;
  assert.deepEqual(list.listTasks().map(task => task.completed), [true, false]);
  saving.calls[1].succeed();
  await second;
  assert.deepEqual(list.listTasks().map(task => task.completed), [false, true]);
});

test("普通函数抛错由同步调用位置收到", () => {
  assert.throws(regularFailure, /普通函数错误/);
});

test("async 函数在首次 await 前抛错也表现为拒绝，不从同步调用处抛出", async () => {
  let pending;
  assert.doesNotThrow(() => { pending = asyncFailure(); });
  assert.ok(pending instanceof Promise);
  await assert.rejects(pending, /异步函数错误/);
});

test("返回 ok:false 是正常履行，then 能收到，拒绝处理不会执行", async () => {
  let caught = false;
  const result = await returnTaskFailure().then(value => value).catch(() => { caught = true; });
  assert.deepEqual(result, { ok: false, reason: "not-found" });
  assert.equal(caught, false);
});

test("Promise 本身作为条件为真，它的 ok 不是任务结果的 ok", async () => {
  const pending = returnTaskFailure();
  assert.equal(Boolean(pending), true);
  assert.equal(pending.ok, undefined);
  assert.equal((await pending).ok, false);
});

test("直接 return Promise 不会让局部 catch 收到稍后的拒绝", async () => {
  const error = new Error("保存拒绝");
  await assert.rejects(returnWithoutAwait(() => Promise.reject(error)), actual => actual === error);
});

test("return await 会在局部等待位置接收拒绝，再由 catch 转换", async () => {
  assert.equal(await returnWithAwait(() => Promise.reject(new Error("保存拒绝"))), "这里捕获了错误");
});

test("直接 return 情形仍能捕获调用保存函数时立即抛出的同步错误", async () => {
  assert.equal(await returnWithoutAwait(() => { throw new Error("立即抛错"); }), "这里捕获了错误");
});

test("await 已履行的 Promise 仍会先交还执行机会", async () => {
  const order = [];
  async function run() { order.push("开始"); await Promise.resolve(); order.push("恢复"); }
  const pending = run();
  order.push("调用之后");
  assert.deepEqual(order, ["开始", "调用之后"]);
  await pending;
  assert.deepEqual(order, ["开始", "调用之后", "恢复"]);
});

test("所有 await 完成之后的显示代码抛错，任务已经保存并采用", async () => {
  const list = createAsyncTaskList(() => {});
  const result = await list.completeTask("t1");
  assert.equal(result.ok, true);
  assert.throws(() => { throw new Error("显示失败"); }, /显示失败/);
  assert.equal(list.listTasks()[0].completed, true);
});
