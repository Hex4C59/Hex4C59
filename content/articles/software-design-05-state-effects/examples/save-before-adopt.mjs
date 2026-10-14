import { defaultTasks } from "./initial-tasks.mjs";
import { copyTasks } from "./copy-tasks.mjs";
import { planCompletion } from "./plan-completion.mjs";

export function createSavedTaskList(saveSnapshot, initialTasks = defaultTasks) {
  if (typeof saveSnapshot !== "function") {
    throw new TypeError("需要提供在返回前完成的保存函数");
  }
  let tasks = copyTasks(initialTasks);
  function listTasks() {
    return copyTasks(tasks);
  }
  function completeTask(id) {
    const proposal = planCompletion(tasks, id);
    if (proposal.result.ok === false || proposal.result.changed === false) {
      return proposal.result;
    }
    try {
      const saveResult = saveSnapshot(copyTasks(proposal.nextTasks));
      if (saveResult !== undefined) {
        return { ok: false, reason: "save-failed" };
      }
    } catch {
      return { ok: false, reason: "save-failed" };
    }
    tasks = proposal.nextTasks;
    return proposal.result;
  }
  return { listTasks, completeTask };
}
