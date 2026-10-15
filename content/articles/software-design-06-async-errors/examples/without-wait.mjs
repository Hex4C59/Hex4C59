import { defaultTasks } from "./initial-tasks.mjs";
import { copyTasks } from "./copy-tasks.mjs";
import { planCompletion } from "./plan-completion.mjs";

// 反例：把返回 Promise 的保存当作已经完成，提前采用新数据。
export function createWithoutWait(saveSnapshot, initialTasks = defaultTasks) {
  let tasks = copyTasks(initialTasks);
  function listTasks() { return copyTasks(tasks); }
  async function completeTask(id) {
    const proposal = planCompletion(tasks, id);
    if (proposal.result.ok === false || proposal.result.changed === false) {
      return proposal.result;
    }
    try {
      saveSnapshot(copyTasks(proposal.nextTasks));
    } catch {
      return { ok: false, reason: "save-failed" };
    }
    tasks = proposal.nextTasks;
    return proposal.result;
  }
  return { listTasks, completeTask };
}
