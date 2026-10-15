import { writeFile } from "node:fs/promises";

export function createJsonFileSave(file) {
  return function saveSnapshot(tasks) {
    return writeFile(file, JSON.stringify(tasks));
  };
}
