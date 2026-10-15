import test from "node:test";
import assert from "node:assert/strict";
import { versions } from "./versions.mjs";
import { checkBeforeAdopt, checkRejection, checkBusy } from "./contract-checks.mjs";
import { checkSnapshotArray, checkTaskOrder, checkBusyPriority } from "./migration-checks.mjs";

const checks = [
  ["保存结束前保留旧任务，结束后才采用", checkBeforeAdopt],
  ["保存拒绝返回失败并保留旧任务", checkRejection],
  ["等待中的第二次修改不再次保存", checkBusy],
  ["保存方仍收到数组", checkSnapshotArray],
  ["完成任务仍保留列表顺序", checkTaskOrder],
  ["等待期间先报告 busy", checkBusyPriority],
  ["无效编号、不存在与重复完成不额外保存", async function (createTaskList) {
    const saved = [];
    const taskList = createTaskList(function saveSnapshot(tasks) { saved.push(tasks); });
    for (const id of [undefined, null, 1, "", "  "]) {
      assert.deepEqual(await taskList.completeTask(id), { ok: false, reason: "invalid-id" });
    }
    for (const id of ["t9", " t1 "]) {
      assert.deepEqual(await taskList.completeTask(id), { ok: false, reason: "not-found" });
    }
    assert.equal(saved.length, 0);
    await taskList.completeTask("t1");
    assert.deepEqual(await taskList.completeTask("t1"), {
      ok: true, changed: false,
      task: { id: "t1", title: "写周报", completed: true },
    });
    assert.equal(saved.length, 1);
  }],
  ["同步保存抛错或异步拒绝后均可重试", async function (createTaskList) {
    for (const asynchronous of [false, true]) {
      let calls = 0;
      const taskList = createTaskList(function saveSnapshot() {
        calls += 1;
        if (calls === 1) {
          if (asynchronous) return Promise.reject(new Error("受控拒绝"));
          throw new Error("受控抛错");
        }
      });
      assert.deepEqual(await taskList.completeTask("t1"), { ok: false, reason: "save-failed" });
      assert.deepEqual(taskList.listTasks().map(task => task.completed), [false, false]);
      assert.deepEqual(await taskList.completeTask("t1"), {
        ok: true, changed: true,
        task: { id: "t1", title: "写周报", completed: true },
      });
      assert.equal(calls, 2);
    }
  }],
  ["保存返回其他正常值仍按失败处理并释放忙碌", async function (createTaskList) {
    for (const asynchronous of [false, true]) {
      let calls = 0;
      const taskList = createTaskList(function saveSnapshot() {
        calls += 1;
        const value = calls === 1 ? false : undefined;
        return asynchronous ? Promise.resolve(value) : value;
      });
      assert.deepEqual(await taskList.completeTask("t1"), { ok: false, reason: "save-failed" });
      assert.deepEqual(taskList.listTasks().map(task => task.completed), [false, false]);
      assert.equal((await taskList.completeTask("t1")).ok, true);
    }
  }],
  ["外部修改初始数据、列表和返回任务不会改内部任务", async function (createTaskList) {
    const initial = [
      { id: "t1", title: "写周报", completed: false },
      { id: "t2", title: "整理笔记", completed: false },
    ];
    const taskList = createTaskList(function saveSnapshot() {}, initial);
    initial[0].title = "外部初始修改";
    const view = taskList.listTasks();
    view[0].title = "外部列表修改";
    view.pop();
    const result = await taskList.completeTask("t1");
    result.task.title = "外部结果修改";
    assert.deepEqual(taskList.listTasks(), [
      { id: "t1", title: "写周报", completed: true },
      { id: "t2", title: "整理笔记", completed: false },
    ]);
  }],
  ["保存方修改收到的副本也不会修改候选任务", async function (createTaskList) {
    const taskList = createTaskList(function saveSnapshot(tasks) {
      tasks[0].title = "保存方修改";
      tasks[0].completed = false;
      tasks.pop();
    });
    assert.deepEqual(await taskList.completeTask("t1"), {
      ok: true, changed: true,
      task: { id: "t1", title: "写周报", completed: true },
    });
    assert.deepEqual(taskList.listTasks(), [
      { id: "t1", title: "写周报", completed: true },
      { id: "t2", title: "整理笔记", completed: false },
    ]);
  }],
  ["创建对象时缺少保存函数仍同步抛出 TypeError", async function (createTaskList) {
    assert.throws(function () { createTaskList(null); }, TypeError);
  }],
];

for (const [name, createTaskList] of versions) {
  for (const [description, check] of checks) {
    test(name + "：" + description, async function () { await check(createTaskList); });
  }
}
