import { openTaskApp } from "./open-task-app.mjs";
import { openWithReset } from "./faults/reset-on-error.mjs";
import { checkRejectBrokenFile } from "./startup-check.mjs";

const name = process.argv[2] ?? "correct";
const openApp = name === "correct" ? openTaskApp : name === "reset" ? openWithReset : undefined;
if (!openApp) {
  console.error("未知比较版本：" + name);
  process.exitCode = 2;
} else {
  try {
    await checkRejectBrokenFile(openApp);
    console.log(name + "：检查通过");
  } catch (error) {
    console.error(name + "：检查失败：" + error.message.split("\n")[0]);
    process.exitCode = 1;
  }
}
