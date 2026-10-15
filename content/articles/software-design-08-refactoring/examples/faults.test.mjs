import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

for (const [name, status, message] of [
  ["correct", 0, "检查通过"],
  ["reinsert-task", 1, "完成任务应保留原列表顺序"],
  ["save-map", 1, "保存方应收到数组"],
  ["validate-first", 1, "等待时应先报告 busy"],
]) {
  test("独立进程：" + name, function () {
    const run = spawnSync(process.execPath, [
      "--unhandled-rejections=strict",
      fileURLToPath(new URL("./probe.mjs", import.meta.url)), name,
    ], { encoding: "utf8", timeout: 10_000 });
    assert.ifError(run.error);
    assert.equal(run.status, status, run.stderr);
    assert.ok((run.stdout + run.stderr).includes(message));
  });
}
