import { open, rename, rm } from "node:fs/promises";
import { dirname, basename, join } from "node:path";
import { randomUUID } from "node:crypto";

export async function replaceFile(file, text, renameFile = rename) {
  const temporary = join(dirname(file), "." + basename(file) + "." + randomUUID() + ".tmp");
  // open 成功后，才知道这个临时文件属于本次调用。
  const handle = await open(temporary, "wx");
  try {
    try {
      await handle.writeFile(text, "utf8");
    } finally {
      await handle.close();
    }
    await renameFile(temporary, file);
  } catch (error) {
    try {
      await rm(temporary, { force: true });
    } catch {
      // 保留原错误；未清理的临时文件不会作为正式数据读取。
    }
    throw error;
  }
}
