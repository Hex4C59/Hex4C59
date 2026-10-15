import { defaultTasks } from "./initial-tasks.mjs";
import { copyTasks } from "./copy-tasks.mjs";
import { planCompletion } from "./plan-completion.mjs";

export function createAsyncTaskList(saveSnapshot, initialTasks = defaultTasks) {
  if (typeof saveSnapshot !== "function") {
    throw new TypeError("需要提供保存函数");
  }
  let currentTasks = copyTasks(initialTasks);
  let busy = false;
  function listTasks() {
    return copyTasks(currentTasks);
  }
  async function completeTask(id) {
    if (busy) {
      return { ok: false, reason: "busy" };
    }
    busy = true;
    try {
      const proposal = planCompletion(currentTasks, id);
      if (proposal.result.ok === false || proposal.result.changed === false) {
        return proposal.result;
      }
      try {
        const saveResult = await saveSnapshot(copyTasks(proposal.nextTasks));
        if (saveResult !== undefined) {
          return { ok: false, reason: "save-failed" };
        }
      } catch {
        return { ok: false, reason: "save-failed" };
      }
      currentTasks = proposal.nextTasks;
      return proposal.result;
    } finally {
      busy = false;
    }
  }
  return { listTasks, completeTask };
}
