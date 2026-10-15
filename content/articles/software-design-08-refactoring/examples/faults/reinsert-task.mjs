// Deliberate fault: use the planner that moves an existing task.
import { defaultTasks } from "../initial-tasks.mjs";
import { copyTasks } from "../copy-tasks.mjs";
import { toTaskMap } from "../to-task-map.mjs";
import { planMapCompletion } from "./reinsert-plan.mjs";

export function createAsyncTaskList(saveSnapshot, initialTasks = defaultTasks) {
  if (typeof saveSnapshot !== "function") {
    throw new TypeError("需要提供保存函数");
  }
  let currentTasks = toTaskMap(initialTasks);
  let busy = false;
  function listTasks() {
    return copyTasks(currentTasks.values());
  }
  async function completeTask(id) {
    if (busy) {
      return { ok: false, reason: "busy" };
    }
    busy = true;
    try {
      const proposal = planMapCompletion(currentTasks, id);
      if (proposal.result.ok === false || proposal.result.changed === false) {
        return proposal.result;
      }
      try {
        const saveResult = await saveSnapshot(copyTasks(proposal.nextTasks.values()));
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
