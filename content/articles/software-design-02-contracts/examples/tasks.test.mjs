import assert from "node:assert/strict";
import test from "node:test";
import { createTaskList } from "./tasks.mjs";

test("第一次完成任务，返回结果和任务数据都符合约定", () => {
  const { completeTask, listTasks } = createTaskList();
  assert.deepEqual(completeTask("t1"), {
    ok: true,
    changed: true,
    task: { id: "t1", title: "写周报", completed: true },
  });
  assert.equal(listTasks()[0].completed, true);
});

test("再次完成同一任务仍成功，但不再改变任务数据", () => {
  const { completeTask, listTasks } = createTaskList();
  completeTask("t1");
  const before = listTasks();
  assert.deepEqual(completeTask("t1"), {
    ok: true,
    changed: false,
    task: { id: "t1", title: "写周报", completed: true },
  });
  assert.deepEqual(listTasks(), before);
});

test("找不到任务时说明原因，并且不修改任何任务", () => {
  const { completeTask, listTasks } = createTaskList();
  const before = listTasks();
  assert.deepEqual(completeTask("t9"), { ok: false, reason: "not-found" });
  assert.deepEqual(listTasks(), before);
});

test("空编号和其他类型得到输入错误，任务保持不变", () => {
  const { completeTask, listTasks } = createTaskList();
  const before = listTasks();
  for (const id of [undefined, null, 3, "", "   ", {}, []]) {
    assert.deepEqual(completeTask(id), { ok: false, reason: "invalid-id" });
    assert.deepEqual(listTasks(), before);
  }
});

test("完成 t1 只改变 t1，不改标题和其他任务", () => {
  const { completeTask, listTasks } = createTaskList();
  const before = listTasks();
  completeTask("t1");
  const after = listTasks();
  assert.equal(after[0].title, before[0].title);
  assert.equal(after[0].id, before[0].id);
  assert.deepEqual(after[1], before[1]);
});

test("修改返回的任务副本不会改变内部任务", () => {
  const { completeTask, listTasks } = createTaskList();
  const result = completeTask("t1");
  result.task.completed = false;
  result.task.title = "调用者改过的文字";
  assert.deepEqual(listTasks()[0], { id: "t1", title: "写周报", completed: true });
});

test("修改 listTasks 返回的数据也不会改变内部任务", () => {
  const { listTasks } = createTaskList();
  const snapshot = listTasks();
  snapshot[0].completed = true;
  snapshot.push({ id: "extra", title: "外部添加", completed: false });
  assert.equal(listTasks().length, 2);
  assert.equal(listTasks()[0].completed, false);
});

test("创建时复制合法初始数据，后续操作不会改写传入的数据", () => {
  const initial = [{ id: "t1", title: "写周报", completed: false }];
  const { completeTask } = createTaskList(initial);
  completeTask("t1");
  assert.deepEqual(initial, [{ id: "t1", title: "写周报", completed: false }]);
});

test("编号按原样精确匹配，不自动去掉两侧空格", () => {
  const { completeTask } = createTaskList();
  assert.deepEqual(completeTask(" t1 "), { ok: false, reason: "not-found" });
});

test("读入的请求仍要经过编号检查和存在性检查", () => {
  const { completeTask } = createTaskList();
  assert.deepEqual(completeTask(JSON.parse('{"id":3}').id), { ok: false, reason: "invalid-id" });
  assert.deepEqual(completeTask(JSON.parse('{"id":"t9"}').id), { ok: false, reason: "not-found" });
});

test("失败结果对象不能当作旧接口的 false 使用", () => {
  const { completeTask } = createTaskList();
  const result = completeTask("t9");
  assert.equal(Boolean(result), true);
  assert.equal(result.ok, false);
});
