import { defaultTasks } from "./initial-tasks.mjs";
import { copyTasks } from "./copy-tasks.mjs";
import { planCompletion } from "./plan-completion.mjs";

// 反例：等待保存，却允许同一所有者同时计算两份基于旧状态的修改。
export function createWithoutBusy(saveSnapshot, initialTasks = defaultTasks) {
  let tasks = copyTasks(initialTasks);
  function listTasks() { return copyTasks(tasks); }
  async function completeTask(id) {
    const proposal = planCompletion(tasks, id);
    if (proposal.result.ok === false || proposal.result.changed === false) {
      return proposal.result;
    }
    try {
      const saveResult = await saveSnapshot(copyTasks(proposal.nextTasks));
      if (saveResult !== undefined) return { ok: false, reason: "save-failed" };
    } catch {
      return { ok: false, reason: "save-failed" };
    }
    tasks = proposal.nextTasks;
    return proposal.result;
  }
  return { listTasks, completeTask };
}
