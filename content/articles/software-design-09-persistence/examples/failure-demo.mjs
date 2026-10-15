import { mkdtemp, readFile, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { defaultTasks } from "./initial-tasks.mjs";
import { createFileStore } from "./file-store.mjs";
import { openTaskApp } from "./open-task-app.mjs";
import { openWithReset } from "./faults/reset-on-error.mjs";

const root = await mkdtemp(join(tmpdir(), "software-design-09-failure-"));
try {
  const broken = join(root, "broken.json");
  const brokenText = '{"version":1,"tasks":';
  await writeFile(broken, brokenText);
  const store = createFileStore(broken);
  console.log("损坏文件启动：", JSON.stringify(await openTaskApp(store)));
  console.log("再次初始化：", JSON.stringify(await store.initialize(defaultTasks)));
  console.log("原内容保留：", await readFile(broken, "utf8") === brokenText);

  const legacy = join(root, "legacy.json");
  await writeFile(legacy, JSON.stringify(defaultTasks));
  const old = await openTaskApp(createFileStore(legacy));
  if (!old.ok) throw new Error(old.reason);
  console.log("旧格式读取：", old.format);
  await old.taskList.completeTask("t1");
  const reopened = await openTaskApp(createFileStore(legacy));
  if (!reopened.ok) throw new Error(reopened.reason);
  console.log("修改后格式：", reopened.format);
  console.log("重新读取标记：", JSON.stringify(reopened.taskList.listTasks().map(task => task.completed)));

  const unsafeFile = join(root, "unsafe.json");
  await writeFile(unsafeFile, brokenText);
  const unsafe = await openWithReset(createFileStore(unsafeFile));
  await unsafe.taskList.completeTask("t1");
  console.log("错误默认值版保留原内容：", await readFile(unsafeFile, "utf8") === brokenText);
} finally {
  await rm(root, { recursive: true, force: true });
}
