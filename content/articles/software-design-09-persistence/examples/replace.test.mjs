import test from "node:test";
import assert from "node:assert/strict";
import { readFile, writeFile, readdir, rename } from "node:fs/promises";
import { join } from "node:path";
import { defaultTasks } from "./initial-tasks.mjs";
import { encodeTaskFile } from "./task-file-codec.mjs";
import { replaceFile } from "./replace-file.mjs";
import { createFileStore } from "./file-store.mjs";
import { openTaskApp } from "./open-task-app.mjs";
import { inTemporaryDirectory } from "./test-helpers.mjs";

const completedTasks = [
  { id: "t1", title: "写周报", completed: true },
  { id: "t2", title: "整理笔记", completed: false },
];

test("真实替换后读取新内容，临时路径已消失", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    await writeFile(file, "old");
    await replaceFile(file, "new");
    assert.equal(await readFile(file, "utf8"), "new");
    assert.deepEqual(await readdir(root), ["tasks.json"]);
  });
});
test("合成的替换前失败保留原文件并清理本次临时文件", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    await writeFile(file, "old");
    await assert.rejects(replaceFile(file, "new", async function failBeforeRename(temporary, target) {
      assert.equal(target, file);
      assert.equal(await readFile(temporary, "utf8"), "new");
      assert.equal(await readFile(file, "utf8"), "old");
      throw new Error("合成的替换前失败");
    }), /合成的替换前失败/);
    assert.equal(await readFile(file, "utf8"), "old");
    assert.deepEqual(await readdir(root), ["tasks.json"]);
  });
});
test("父目录缺失时拒绝，不创建其他文件", async function () {
  await inTemporaryDirectory(async function (root) {
    await assert.rejects(replaceFile(join(root, "missing", "tasks.json"), "new"), { code: "ENOENT" });
    assert.deepEqual(await readdir(root), []);
  });
});
test("非法保存数据在写入前被拒绝", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    await writeFile(file, "old");
    assert.throws(function () { createFileStore(file).saveSnapshot(null); }, TypeError);
    assert.equal(await readFile(file, "utf8"), "old");
    assert.deepEqual(await readdir(root), ["tasks.json"]);
  });
});
test("替换生效后人为报错：内存旧值不能代表磁盘旧值", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    const store = createFileStore(file);
    await store.initialize(defaultTasks);
    const opened = await openTaskApp({
      load: store.load,
      saveSnapshot(tasks) {
        return replaceFile(file, encodeTaskFile(tasks), async function failAfterRename(temporary, target) {
          await rename(temporary, target);
          throw new Error("合成的替换后错误");
        });
      },
    });
    assert.deepEqual(await opened.taskList.completeTask("t1"), { ok: false, reason: "save-failed" });
    assert.deepEqual(opened.taskList.listTasks(), defaultTasks);
    assert.deepEqual(JSON.parse(await readFile(file, "utf8")), { version: 1, tasks: completedTasks });
    assert.deepEqual(await readdir(root), ["tasks.json"]);
  });
});
