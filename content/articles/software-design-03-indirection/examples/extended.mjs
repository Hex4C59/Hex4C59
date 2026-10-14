// 独立比较快照：只增加 count-open，保留原有操作和失败约定。
export function createExtendedBranchDispatcher(taskList) {
  function countOpenTasks() {
    let count = 0;
    for (const task of taskList.listTasks()) {
      if (task.completed === false) {
        count += 1;
      }
    }
    return { ok: true, count };
  }

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
    if (request.action === "count-open") {
      return countOpenTasks();
    }
    return { ok: false, reason: "unknown-action" };
  }
  return dispatch;
}

export function createExtendedTableDispatcher(taskList) {
  function handleList() {
    return { ok: true, tasks: taskList.listTasks() };
  }
  function handleComplete(request) {
    return taskList.completeTask(request.id);
  }

  function countOpenTasks() {
    let count = 0;
    for (const task of taskList.listTasks()) {
      if (task.completed === false) {
        count += 1;
      }
    }
    return { ok: true, count };
  }

  const handlers = new Map();
  handlers.set("list", handleList);
  handlers.set("complete", handleComplete);
  handlers.set("count-open", countOpenTasks);

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
