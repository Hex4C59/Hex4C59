import assert from "node:assert/strict";
import { createControlledSave } from "./controlled-save.mjs";
import { runContractChecks } from "./contract-checks.mjs";

export async function checkSnapshotArray(createTaskList) {
  let received;
  const taskList = createTaskList(function saveSnapshot(tasks) {
    received = tasks;
  });
  assert.equal((await taskList.completeTask("t1")).ok, true);
  assert.ok(Array.isArray(received), "保存方应收到数组");
  assert.equal(received.length, 2);
}

export async function checkTaskOrder(createTaskList) {
  const taskList = createTaskList(function saveSnapshot() {});
  await taskList.completeTask("t1");
  assert.deepEqual(taskList.listTasks().map(task => task.id), ["t1", "t2"],
    "完成任务应保留原列表顺序");
}

export async function checkBusyPriority(createTaskList) {
  const saving = createControlledSave();
  const taskList = createTaskList(saving.saveSnapshot);
  const pending = taskList.completeTask("t1");
  try {
    assert.deepEqual(await taskList.completeTask(""), { ok: false, reason: "busy" },
      "等待时应先报告 busy");
    assert.equal(saving.calls.length, 1);
  } finally {
    for (const call of saving.calls) call.succeed();
    await Promise.allSettled([pending]);
  }
}

export async function runMigrationChecks(createTaskList) {
  await checkSnapshotArray(createTaskList);
  await checkTaskOrder(createTaskList);
  await checkBusyPriority(createTaskList);
  await runContractChecks(createTaskList);
}
