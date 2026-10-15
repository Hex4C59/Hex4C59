import test from "node:test";
import assert from "node:assert/strict";
import { readFile, writeFile, readdir } from "node:fs/promises";
import { join } from "node:path";
import { defaultTasks } from "./initial-tasks.mjs";
import { copyTasks } from "./copy-tasks.mjs";
import { createFileStore } from "./file-store.mjs";
import { openTaskApp } from "./open-task-app.mjs";
import { inTemporaryDirectory } from "./test-helpers.mjs";

const completedTasks = [
  { id: "t1", title: "写周报", completed: true },
  { id: "t2", title: "整理笔记", completed: false },
];

test("缺失文件拒绝启动且不创建文件", async function () {
  await inTemporaryDirectory(async function (root) {
    const store = createFileStore(join(root, "tasks.json"));
    assert.deepEqual(await openTaskApp(store), { ok: false, reason: "missing-file" });
    assert.deepEqual(await readdir(root), []);
  });
});
test("显式初始化创建版本一文件", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    const store = createFileStore(file);
    assert.deepEqual(await store.initialize(defaultTasks), { ok: true, created: true });
    assert.deepEqual(JSON.parse(await readFile(file, "utf8")), { version: 1, tasks: defaultTasks });
    assert.deepEqual(await store.load(), { ok: true, format: "v1", tasks: defaultTasks });
  });
});
test("已有正常文件也不能再次初始化覆盖", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    const store = createFileStore(file);
    await store.initialize(completedTasks);
    const before = await readFile(file, "utf8");
    assert.deepEqual(await store.initialize(defaultTasks), { ok: false, reason: "already-exists" });
    assert.equal(await readFile(file, "utf8"), before);
  });
});
test("已有损坏文件拒绝读取及重新初始化，原字节保留", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    const text = '{"version":1,"tasks":';
    await writeFile(file, text);
    const store = createFileStore(file);
    assert.deepEqual(await openTaskApp(store), { ok: false, reason: "invalid-json" });
    assert.deepEqual(await store.initialize(defaultTasks), { ok: false, reason: "already-exists" });
    assert.equal(await readFile(file, "utf8"), text);
  });
});
test("未知版本拒绝启动且保留原文件", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    const text = '{"version":2,"rows":[]}';
    await writeFile(file, text);
    assert.deepEqual(await openTaskApp(createFileStore(file)), { ok: false, reason: "unsupported-version" });
    assert.equal(await readFile(file, "utf8"), text);
  });
});
test("重复编号拒绝进入任务所有者", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    const tasks = copyTasks(defaultTasks);
    tasks[1].id = "t1";
    const text = JSON.stringify({ version: 1, tasks });
    await writeFile(file, text);
    assert.deepEqual(await openTaskApp(createFileStore(file)), { ok: false, reason: "invalid-data" });
    assert.equal(await readFile(file, "utf8"), text);
  });
});
test("读取旧数组不自动重写", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    const text = JSON.stringify(defaultTasks);
    await writeFile(file, text);
    const opened = await openTaskApp(createFileStore(file));
    assert.equal(opened.format, "legacy-array");
    assert.deepEqual(opened.taskList.listTasks(), defaultTasks);
    assert.equal(await readFile(file, "utf8"), text);
  });
});
test("旧格式第一次成功修改后升级为版本一", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    await writeFile(file, JSON.stringify(defaultTasks));
    const opened = await openTaskApp(createFileStore(file));
    assert.deepEqual(await opened.taskList.completeTask("t1"), {
      ok: true, changed: true, task: completedTasks[0],
    });
    assert.deepEqual(JSON.parse(await readFile(file, "utf8")), { version: 1, tasks: completedTasks });
    const reopened = await openTaskApp(createFileStore(file));
    assert.equal(reopened.format, "v1");
    assert.deepEqual(reopened.taskList.listTasks(), completedTasks);
  });
});
test("旧格式重复完成不保存，也不偷偷升级", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    const text = JSON.stringify(completedTasks);
    await writeFile(file, text);
    const opened = await openTaskApp(createFileStore(file));
    assert.equal((await opened.taskList.completeTask("t1")).changed, false);
    assert.equal(await readFile(file, "utf8"), text);
  });
});
test("读回空数组后仍为空，缺省任务不会出现", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    const store = createFileStore(file);
    await store.initialize([]);
    const opened = await openTaskApp(store);
    assert.deepEqual(opened.taskList.listTasks(), []);
    assert.deepEqual(await opened.taskList.completeTask("t1"), { ok: false, reason: "not-found" });
  });
});
test("读取目录在本次系统上报告 read-failed，不创建默认任务", async function () {
  await inTemporaryDirectory(async function (root) {
    assert.deepEqual(await openTaskApp(createFileStore(root)), { ok: false, reason: "read-failed" });
  });
});
test("初始化失败或数据非法都不伪装成成功", async function () {
  await inTemporaryDirectory(async function (root) {
    assert.deepEqual(await createFileStore(join(root, "missing", "tasks.json")).initialize(defaultTasks), {
      ok: false, reason: "create-failed",
    });
    assert.deepEqual(await createFileStore(join(root, "tasks.json")).initialize(null), {
      ok: false, reason: "invalid-data",
    });
    assert.deepEqual(await readdir(root), []);
  });
});
