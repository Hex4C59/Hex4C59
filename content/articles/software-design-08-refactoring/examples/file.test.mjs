import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { versions } from "./versions.mjs";
import { createJsonFileSave } from "./json-file-save.mjs";

async function inTemporaryDirectory(check) {
  const root = await mkdtemp(join(tmpdir(), "software-design-08-test-"));
  try { await check(root); }
  finally { await rm(root, { recursive: true, force: true }); }
}

for (const [name, createTaskList] of versions) {
  test(name + "：真实文件内容保留数组、字段与顺序", async function () {
    await inTemporaryDirectory(async function (root) {
      const file = join(root, "tasks.json");
      const taskList = createTaskList(createJsonFileSave(file));
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
  test(name + "：真实路径失败仍返回 save-failed 并保留任务", async function () {
    await inTemporaryDirectory(async function (root) {
      const taskList = createTaskList(createJsonFileSave(join(root, "missing", "tasks.json")));
      assert.deepEqual(await taskList.completeTask("t1"), { ok: false, reason: "save-failed" });
      assert.deepEqual(taskList.listTasks().map(task => task.completed), [false, false]);
    });
  });
}
