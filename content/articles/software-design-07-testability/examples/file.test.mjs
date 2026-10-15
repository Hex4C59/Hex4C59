import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createAsyncTaskList } from "./async-task-list.mjs";
import { createJsonFileSave } from "./json-file-save.mjs";

async function inTemporaryDirectory(check) {
  const root = await mkdtemp(join(tmpdir(), "software-design-07-test-"));
  try {
    await check(root);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}

test("真实保存函数写入可读回的 JSON，成功值为 undefined", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    const saveSnapshot = createJsonFileSave(file);
    assert.equal(await saveSnapshot([
      { id: "t1", title: "写周报", completed: true },
    ]), undefined);
    assert.deepEqual(JSON.parse(await readFile(file, "utf8")), [
      { id: "t1", title: "写周报", completed: true },
    ]);
  });
});

test("任务所有者与真实保存函数组合后，文件包含修改结果", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    const taskList = createAsyncTaskList(createJsonFileSave(file));
    assert.deepEqual(await taskList.completeTask("t1"), {
      ok: true, changed: true,
      task: { id: "t1", title: "写周报", completed: true },
    });
    assert.deepEqual(JSON.parse(await readFile(file, "utf8")), [
      { id: "t1", title: "写周报", completed: true },
      { id: "t2", title: "整理笔记", completed: false },
    ]);
  });
});

test("真实保存函数对不存在的父目录拒绝，任务所有者转换失败", async function () {
  await inTemporaryDirectory(async function (root) {
    const saveSnapshot = createJsonFileSave(join(root, "missing", "tasks.json"));
    await assert.rejects(saveSnapshot([]), { code: "ENOENT" });
    const taskList = createAsyncTaskList(saveSnapshot);
    assert.deepEqual(await taskList.completeTask("t1"), {
      ok: false, reason: "save-failed",
    });
    assert.deepEqual(taskList.listTasks(), [
      { id: "t1", title: "写周报", completed: false },
      { id: "t2", title: "整理笔记", completed: false },
    ]);
  });
});

test("正常返回的模拟保存不能证明文件存在", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "never-written.json");
    const taskList = createAsyncTaskList(async function pretendSave() {});
    assert.equal((await taskList.completeTask("t1")).ok, true);
    await assert.rejects(readFile(file, "utf8"), { code: "ENOENT" });
  });
});
