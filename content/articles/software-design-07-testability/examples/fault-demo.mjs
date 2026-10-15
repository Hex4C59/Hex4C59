import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const probe = fileURLToPath(new URL("./probe.mjs", import.meta.url));
for (const [name, expected] of [
  ["correct", 0], ["early-adopt", 1], ["ignore-rejection", 1], ["allow-overlap", 1],
]) {
  const run = spawnSync(process.execPath, ["--unhandled-rejections=strict", probe, name], {
    encoding: "utf8", timeout: 10000,
  });
  if (run.error || run.status !== expected) {
    throw new Error(name + " 没有得到预期退出结果");
  }
  console.log((run.stdout + run.stderr).trim());
}
