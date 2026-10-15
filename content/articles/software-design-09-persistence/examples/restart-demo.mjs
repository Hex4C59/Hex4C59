import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = await mkdtemp(join(tmpdir(), "software-design-09-restart-"));
try {
  const file = join(root, "tasks.json");
  const app = fileURLToPath(new URL("./app.mjs", import.meta.url));
  for (const [command, label, id] of [
    ["init", "创建文件", undefined],
    ["complete", "完成并退出", "t1"],
    ["list", "新进程读回", undefined],
  ]) {
    const args = ["--unhandled-rejections=strict", app, command, file];
    if (id !== undefined) args.push(id);
    const child = spawnSync(process.execPath, args, { encoding: "utf8", timeout: 10_000 });
    if (child.error) throw child.error;
    if (child.status !== 0) throw new Error(child.stderr || child.stdout);
    console.log(label + "：" + child.stdout.trim());
  }
} finally {
  await rm(root, { recursive: true, force: true });
}
