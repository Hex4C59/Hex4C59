import { copyTasks } from "./copy-tasks.mjs";
import { isValidTasks } from "./validate-tasks.mjs";

export function decodeTaskFile(text) {
  let value;
  try {
    value = JSON.parse(text);
  } catch {
    return { ok: false, reason: "invalid-json" };
  }
  if (Array.isArray(value)) {
    if (!isValidTasks(value)) return { ok: false, reason: "invalid-data" };
    return { ok: true, format: "legacy-array", tasks: copyTasks(value) };
  }
  if (value === null || typeof value !== "object" || !Number.isInteger(value.version)) {
    return { ok: false, reason: "invalid-data" };
  }
  if (value.version !== 1) return { ok: false, reason: "unsupported-version" };
  const keys = Object.keys(value);
  if (keys.length !== 2 || !keys.every(key => ["version", "tasks"].includes(key))) {
    return { ok: false, reason: "invalid-data" };
  }
  if (!isValidTasks(value.tasks)) return { ok: false, reason: "invalid-data" };
  return { ok: true, format: "v1", tasks: copyTasks(value.tasks) };
}

export function encodeTaskFile(tasks) {
  if (!isValidTasks(tasks)) throw new TypeError("任务数据不符合文件格式");
  return JSON.stringify({ version: 1, tasks: copyTasks(tasks) }, null, 2) + "\n";
}
