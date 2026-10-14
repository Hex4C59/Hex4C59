export function createTableDispatcher(taskList) {
  function handleList() {
    return { ok: true, tasks: taskList.listTasks() };
  }
  function handleComplete(request) {
    return taskList.completeTask(request.id);
  }

  const handlers = new Map();
  handlers.set("list", handleList);
  handlers.set("complete", handleComplete);

  function dispatch(request) {
    if (typeof request !== "object" || request === null || Array.isArray(request)) {
      return { ok: false, reason: "invalid-request" };
    }
    if (typeof request.action !== "string" || request.action.trim() === "") {
      return { ok: false, reason: "invalid-action" };
    }

    const handler = handlers.get(request.action);
    if (handler === undefined) {
      return { ok: false, reason: "unknown-action" };
    }
    return handler(request);
  }
  return dispatch;
}
