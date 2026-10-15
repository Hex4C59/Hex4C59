import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

for (const [name, expectedStatus] of [
  ["correct", 0], ["reinsert-task", 1], ["save-map", 1], ["validate-first", 1],
]) {
  const run = spawnSync(process.execPath, [
    "--unhandled-rejections=strict",
    fileURLToPath(new URL("./probe.mjs", import.meta.url)), name,
  ], { encoding: "utf8", timeout: 10_000 });
  if (run.error) throw run.error;
  if (run.status !== expectedStatus) throw new Error(name + " 的退出码不符合预期");
  console.log((run.stdout + run.stderr).trim());
}
