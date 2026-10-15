import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

export async function inTemporaryDirectory(check) {
  const root = await mkdtemp(join(tmpdir(), "software-design-09-test-"));
  try { await check(root); }
  finally { await rm(root, { recursive: true, force: true }); }
}

export function runCli(command, file, id) {
  const args = ["--unhandled-rejections=strict", fileURLToPath(new URL("./app.mjs", import.meta.url)), command];
  if (file !== undefined) args.push(file);
  if (id !== undefined) args.push(id);
  const child = spawnSync(process.execPath, args, { encoding: "utf8", timeout: 10_000 });
  assert.ifError(child.error);
  assert.equal(child.stderr, "");
  return { status: child.status, result: JSON.parse(child.stdout) };
}
