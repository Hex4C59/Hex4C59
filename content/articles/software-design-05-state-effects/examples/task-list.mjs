import { defaultTasks } from "./initial-tasks.mjs";
import { copyTasks } from "./copy-tasks.mjs";
import { planCompletion } from "./plan-completion.mjs";

export function createTaskList(initialTasks = defaultTasks) {
  let tasks = copyTasks(initialTasks);
  function listTasks() {
    return copyTasks(tasks);
  }
  function completeTask(id) {
    const proposal = planCompletion(tasks, id);
    if (proposal.result.ok && proposal.result.changed) {
      tasks = proposal.nextTasks;
    }
    return proposal.result;
  }
  return { listTasks, completeTask };
}
