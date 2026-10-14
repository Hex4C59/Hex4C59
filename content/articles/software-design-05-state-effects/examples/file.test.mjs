import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { defaultTasks } from "./initial-tasks.mjs";
import { createSavedTaskList } from "./save-before-adopt.mjs";

function withTemporaryFile(check) {
  const directory = mkdtempSync(join(tmpdir(), "software-design-05-test-"));
  const file = join(directory, "tasks.json");
  try {
    writeFileSync(file, JSON.stringify(defaultTasks));
    check({ directory, file });
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

test("真实临时文件：保存正常返回后，文件与当前任务相符", () => {
  withTemporaryFile(({ file }) => {
    const list = createSavedTaskList(function saveSnapshot(tasks) {
      writeFileSync(file, JSON.stringify(tasks));
    });
    assert.equal(list.completeTask("t1").ok, true);
    assert.deepEqual(JSON.parse(readFileSync(file, "utf8")), list.listTasks());
  });
});

test("真实路径错误：缺少父目录导致 ENOENT，保留当前任务和原文件", () => {
  withTemporaryFile(({ directory, file }) => {
    let code;
    const list = createSavedTaskList(function saveSnapshot(tasks) {
      try {
        writeFileSync(join(directory, "missing", "tasks.json"), JSON.stringify(tasks));
      } catch (error) {
        code = error.code;
        throw error;
      }
    });
    assert.deepEqual(list.completeTask("t1"), { ok: false, reason: "save-failed" });
    assert.equal(code, "ENOENT");
    assert.deepEqual(list.listTasks(), defaultTasks);
    assert.deepEqual(JSON.parse(readFileSync(file, "utf8")), defaultTasks);
  });
});

test("合成的部分写入后抛错：当前任务保持原样，文件却已经损坏", () => {
  withTemporaryFile(({ file }) => {
    const list = createSavedTaskList(function saveSnapshot() {
      writeFileSync(file, '[{"id":');
      throw new Error("合成的保存中途失败");
    });
    assert.equal(list.completeTask("t1").reason, "save-failed");
    assert.deepEqual(list.listTasks(), defaultTasks);
    assert.equal(readFileSync(file, "utf8"), '[{"id":');
    assert.throws(() => JSON.parse(readFileSync(file, "utf8")), SyntaxError);
  });
});

test("合成的完整写入后抛错：文件是新数据，当前任务仍是旧数据", () => {
  withTemporaryFile(({ file }) => {
    const list = createSavedTaskList(function saveSnapshot(tasks) {
      writeFileSync(file, JSON.stringify(tasks));
      throw new Error("合成的写入完成后报告失败");
    });
    assert.equal(list.completeTask("t1").reason, "save-failed");
    assert.equal(list.listTasks()[0].completed, false);
    assert.equal(JSON.parse(readFileSync(file, "utf8"))[0].completed, true);
  });
});
