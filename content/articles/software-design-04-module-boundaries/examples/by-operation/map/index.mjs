import { defaultTasks } from "../../initial-tasks.mjs";
import { createState } from "./state.mjs";
import { listTasks } from "./list-tasks.mjs";
import { completeTask } from "./complete-task.mjs";

export function createTaskList(initialTasks = defaultTasks) {
  const state = createState(initialTasks);
  return {
    listTasks() {
      return listTasks(state);
    },
    completeTask(id) {
      return completeTask(state, id);
    },
  };
}
