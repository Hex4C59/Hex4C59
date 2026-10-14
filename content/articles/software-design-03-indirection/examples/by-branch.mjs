export function createBranchDispatcher(taskList) {
  function dispatch(request) {
    if (typeof request !== "object" || request === null || Array.isArray(request)) {
      return { ok: false, reason: "invalid-request" };
    }
    if (typeof request.action !== "string" || request.action.trim() === "") {
      return { ok: false, reason: "invalid-action" };
    }

    if (request.action === "list") {
      return { ok: true, tasks: taskList.listTasks() };
    }
    if (request.action === "complete") {
      return taskList.completeTask(request.id);
    }
    return { ok: false, reason: "unknown-action" };
  }
  return dispatch;
}
