import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { inTemporaryDirectory } from "./test-helpers.mjs";
import { createFileStore } from "./file-store.mjs";

export async function checkRejectBrokenFile(openApp) {
  await inTemporaryDirectory(async function (root) {
    const file = join(root, "tasks.json");
    const text = '{"version":1,"tasks":';
    await writeFile(file, text);
    assert.deepEqual(await openApp(createFileStore(file)), {
      ok: false, reason: "invalid-json",
    }, "损坏文件应拒绝启动");
    assert.equal(await readFile(file, "utf8"), text);
  });
}
