import test from "node:test";
import assert from "node:assert/strict";
import { readFile, writeFile, readdir } from "node:fs/promises";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { inTemporaryDirectory, runCli } from "./test-helpers.mjs";

const initial = [
  { id: "t1", title: "写周报", completed: false },
  { id: "t2", title: "整理笔记", completed: false },
];

test("顺序新进程完成两项任务，后一次读取保留前次修改", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    assert.deepEqual(runCli("init", file), { status: 0, result: { ok: true, created: true } });
    assert.deepEqual(runCli("complete", file, "t1"), {
      status: 0, result: { ok: true, changed: true, task: { id: "t1", title: "写周报", completed: true } },
    });
    assert.deepEqual(runCli("list", file), {
      status: 0, result: { ok: true, format: "v1", tasks: [
        { id: "t1", title: "写周报", completed: true }, initial[1],
      ] },
    });
    assert.equal(runCli("complete", file, "t2").status, 0);
    const after = runCli("list", file);
    assert.equal(after.status, 0);
    assert.deepEqual(after.result.tasks.map(task => task.completed), [true, true]);
  });
});
test("缺失文件的命令失败，不自动初始化", async function () {
  await inTemporaryDirectory(async function (root) {
    assert.deepEqual(runCli("complete", join(root, "tasks.json"), "t1"), {
      status: 1, result: { ok: false, reason: "missing-file" },
    });
    assert.deepEqual(await readdir(root), []);
  });
});
test("损坏文件上的修改与重新初始化都失败，原文保留", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    const text = '{"version":1,"tasks":';
    await writeFile(file, text);
    assert.deepEqual(runCli("complete", file, "t1"), {
      status: 1, result: { ok: false, reason: "invalid-json" },
    });
    assert.deepEqual(runCli("init", file), { status: 1, result: { ok: false, reason: "already-exists" } });
    assert.equal(await readFile(file, "utf8"), text);
  });
});
test("旧格式能经命令读取，成功修改才升级", async function () {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    const text = JSON.stringify(initial);
    await writeFile(file, text);
    assert.deepEqual(runCli("list", file), { status: 0, result: { ok: true, format: "legacy-array", tasks: initial } });
    assert.equal(await readFile(file, "utf8"), text);
    assert.equal(runCli("complete", file, "t1").status, 0);
    assert.equal(runCli("list", file).result.format, "v1");
  });
});
test("未知命令和缺少路径直接失败，不创建文件", async function () {
  await inTemporaryDirectory(async function (root) {
    assert.deepEqual(runCli("delete-all", join(root, "tasks.json")), {
      status: 1, result: { ok: false, reason: "unknown-command" },
    });
    assert.deepEqual(runCli("list"), { status: 1, result: { ok: false, reason: "invalid-arguments" } });
    assert.deepEqual(await readdir(root), []);
  });
});
for (const [name, status, message] of [["correct", 0, "检查通过"], ["reset", 1, "损坏文件应拒绝启动"]]) {
  test("损坏启动约定的独立比较：" + name, function () {
    const child = spawnSync(process.execPath, [
      "--unhandled-rejections=strict", fileURLToPath(new URL("./probe.mjs", import.meta.url)), name,
    ], { encoding: "utf8", timeout: 10_000 });
    assert.ifError(child.error);
    assert.equal(child.status, status, child.stderr);
    assert.ok((child.stdout + child.stderr).includes(message));
  });
}
