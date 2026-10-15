import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { defaultTasks } from "./initial-tasks.mjs";
import { createAsyncTaskList } from "./async-task-list.mjs";

async function withTemporaryFile(check) {
  const directory = await mkdtemp(join(tmpdir(), "software-design-06-test-"));
  const file = join(directory, "tasks.json");
  try {
    await writeFile(file, JSON.stringify(defaultTasks));
    await check({ directory, file });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

test("真实异步文件：等待保存后任务数据与文件一致", async () => {
  await withTemporaryFile(async ({ file }) => {
    const list = createAsyncTaskList(tasks => writeFile(file, JSON.stringify(tasks)));
    assert.equal((await list.completeTask("t1")).changed, true);
    assert.deepEqual(JSON.parse(await readFile(file, "utf8")), list.listTasks());
  });
});

test("真实路径拒绝：ENOENT 映射为 save-failed，原内存和已有文件保持", async () => {
  await withTemporaryFile(async ({ directory, file }) => {
    let code;
    const list = createAsyncTaskList(async function saveSnapshot(tasks) {
      try { await writeFile(join(directory, "missing", "tasks.json"), JSON.stringify(tasks)); }
      catch (error) { code = error.code; throw error; }
    });
    assert.equal((await list.completeTask("t1")).reason, "save-failed");
    assert.equal(code, "ENOENT");
    assert.deepEqual(list.listTasks(), defaultTasks);
    assert.deepEqual(JSON.parse(await readFile(file, "utf8")), defaultTasks);
  });
});

test("真实文件顺序修改：第一项结束后提交第二项，文件保留两项完成", async () => {
  await withTemporaryFile(async ({ file }) => {
    const list = createAsyncTaskList(tasks => writeFile(file, JSON.stringify(tasks)));
    await list.completeTask("t1");
    await list.completeTask("t2");
    assert.deepEqual(JSON.parse(await readFile(file, "utf8")).map(task => task.completed), [true, true]);
  });
});

test("合成写入后拒绝：Promise 被观察不代表文件修改被撤销", async () => {
  await withTemporaryFile(async ({ file }) => {
    const list = createAsyncTaskList(async function saveSnapshot(tasks) {
      await writeFile(file, JSON.stringify(tasks));
      throw new Error("合成的完整写入后报告失败");
    });
    assert.equal((await list.completeTask("t1")).reason, "save-failed");
    assert.equal(list.listTasks()[0].completed, false);
    assert.equal(JSON.parse(await readFile(file, "utf8"))[0].completed, true);
  });
});
