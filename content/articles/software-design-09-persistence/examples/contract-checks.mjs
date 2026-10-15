import assert from "node:assert/strict";
import { createControlledSave } from "./controlled-save.mjs";

export async function checkBeforeAdopt(createTaskList) {
  const saving = createControlledSave();
  const taskList = createTaskList(saving.saveSnapshot);
  let pending;
  try {
    pending = taskList.completeTask("t1");
    assert.equal(saving.calls.length, 1, "有效修改应发起一次保存");
    assert.deepEqual(taskList.listTasks(), [
      { id: "t1", title: "写周报", completed: false },
      { id: "t2", title: "整理笔记", completed: false },
    ], "保存结束前应保留原任务");
    assert.deepEqual(saving.calls[0].tasks, [
      { id: "t1", title: "写周报", completed: true },
      { id: "t2", title: "整理笔记", completed: false },
    ], "保存应收到准备好的新任务");
    saving.calls[0].succeed();
    assert.deepEqual(await pending, {
      ok: true, changed: true,
      task: { id: "t1", title: "写周报", completed: true },
    }, "保存结束后应报告本次修改");
    assert.equal(taskList.listTasks()[0].completed, true);
  } finally {
    for (const call of saving.calls) call.succeed();
    if (pending) await Promise.allSettled([pending]);
  }
}

export async function checkRejection(createTaskList) {
  const saving = createControlledSave();
  const taskList = createTaskList(saving.saveSnapshot);
  let pending;
  try {
    pending = taskList.completeTask("t1");
    assert.equal(saving.calls.length, 1);
    saving.calls[0].fail(new Error("受控的保存失败"));
    assert.deepEqual(await pending, { ok: false, reason: "save-failed" },
      "保存拒绝应返回 save-failed");
    assert.deepEqual(taskList.listTasks(), [
      { id: "t1", title: "写周报", completed: false },
      { id: "t2", title: "整理笔记", completed: false },
    ], "保存失败后应保留原任务");
  } finally {
    for (const call of saving.calls) call.succeed();
    if (pending) await Promise.allSettled([pending]);
  }
}

export async function checkBusy(createTaskList) {
  const saving = createControlledSave();
  const taskList = createTaskList(saving.saveSnapshot);
  const pending = [];
  try {
    pending.push(taskList.completeTask("t1"));
    pending.push(taskList.completeTask("t2"));
    assert.equal(saving.calls.length, 1, "等待时第二次修改不应再次保存");
    assert.deepEqual(await pending[1], { ok: false, reason: "busy" },
      "等待时第二次修改应报告 busy");
    saving.calls[0].succeed();
    await pending[0];
    assert.deepEqual(taskList.listTasks().map(task => task.completed), [true, false]);
  } finally {
    for (const call of saving.calls) call.succeed();
    await Promise.allSettled(pending);
  }
}

export async function runContractChecks(createTaskList) {
  await checkBeforeAdopt(createTaskList);
  await checkRejection(createTaskList);
  await checkBusy(createTaskList);
}
