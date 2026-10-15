import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { createAsyncTaskList } from "./async-task-list.mjs";
import { createControlledSave } from "./controlled-save.mjs";
import { checkBeforeAdopt, checkRejection, checkBusy } from "./contract-checks.mjs";

test("保存前后采用数据的约定", async function () {
  await checkBeforeAdopt(createAsyncTaskList);
});
test("保存拒绝后的结果与数据约定", async function () {
  await checkRejection(createAsyncTaskList);
});
test("等待中的第二次修改约定", async function () {
  await checkBusy(createAsyncTaskList);
});

test("保存失败后可以重新发起同一修改", async function () {
  const saving = createControlledSave();
  const taskList = createAsyncTaskList(saving.saveSnapshot);
  const pending = [];
  try {
    pending.push(taskList.completeTask("t1"));
    saving.calls[0].fail(new Error("第一次保存失败"));
    assert.deepEqual(await pending[0], { ok: false, reason: "save-failed" });
    pending.push(taskList.completeTask("t1"));
    assert.equal(saving.calls.length, 2);
    saving.calls[1].succeed();
    assert.deepEqual(await pending[1], {
      ok: true, changed: true,
      task: { id: "t1", title: "写周报", completed: true },
    });
  } finally {
    for (const call of saving.calls) call.succeed();
    await Promise.allSettled(pending);
  }
});

test("编号失败与重复完成都不额外保存", async function () {
  const calls = [];
  const taskList = createAsyncTaskList(async function saveSnapshot(tasks) {
    calls.push(tasks);
  });
  assert.deepEqual(await taskList.completeTask(""), { ok: false, reason: "invalid-id" });
  assert.deepEqual(await taskList.completeTask("t9"), { ok: false, reason: "not-found" });
  assert.equal(calls.length, 0);
  await taskList.completeTask("t1");
  assert.deepEqual(await taskList.completeTask("t1"), {
    ok: true, changed: false,
    task: { id: "t1", title: "写周报", completed: true },
  });
  assert.equal(calls.length, 1);
});

test("busy 检查优先于无效编号检查", async function () {
  const saving = createControlledSave();
  const taskList = createAsyncTaskList(saving.saveSnapshot);
  const first = taskList.completeTask("t1");
  try {
    assert.deepEqual(await taskList.completeTask(""), { ok: false, reason: "busy" });
    assert.equal(saving.calls.length, 1);
  } finally {
    for (const call of saving.calls) call.succeed();
    await Promise.allSettled([first]);
  }
});

const probes = [
  ["correct", 0, "检查通过"],
  ["early-adopt", 1, "保存结束前应保留原任务"],
  ["ignore-rejection", 1, "保存拒绝应返回 save-failed"],
  ["allow-overlap", 1, "等待时第二次修改不应再次保存"],
];
for (const [subject, expectedStatus, message] of probes) {
  test("独立进程检查：" + subject, function () {
    const run = spawnSync(process.execPath, [
      "--unhandled-rejections=strict",
      fileURLToPath(new URL("./probe.mjs", import.meta.url)), subject,
    ], { encoding: "utf8", timeout: 10_000 });
    assert.ifError(run.error);
    assert.equal(run.status, expectedStatus, run.stderr);
    assert.ok((run.stdout + run.stderr).includes(message));
  });
}
