import { readFile, writeFile } from "node:fs/promises";
import { decodeTaskFile, encodeTaskFile } from "./task-file-codec.mjs";
import { isValidTasks } from "./validate-tasks.mjs";
import { replaceFile } from "./replace-file.mjs";

export function createFileStore(file) {
  async function load() {
    let text;
    try {
      text = await readFile(file, "utf8");
    } catch (error) {
      return { ok: false, reason: error.code === "ENOENT" ? "missing-file" : "read-failed" };
    }
    return decodeTaskFile(text);
  }
  async function initialize(tasks) {
    if (!isValidTasks(tasks)) return { ok: false, reason: "invalid-data" };
    const text = encodeTaskFile(tasks);
    try {
      await writeFile(file, text, { encoding: "utf8", flag: "wx" });
      return { ok: true, created: true };
    } catch (error) {
      return { ok: false, reason: error.code === "EEXIST" ? "already-exists" : "create-failed" };
    }
  }
  function saveSnapshot(tasks) {
    return replaceFile(file, encodeTaskFile(tasks));
  }
  return { load, initialize, saveSnapshot };
}
