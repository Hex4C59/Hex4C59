import test from "node:test";
import assert from "node:assert/strict";
import { toTaskMap } from "./to-task-map.mjs";
import { planMapCompletion } from "./map-plan-completion.mjs";

function initialMap() {
  return toTaskMap([
    { id: "t1", title: "写周报", completed: false },
    { id: "t2", title: "整理笔记", completed: false },
  ]);
}

test("Map 计算返回新建议，原数据未改变", function () {
  const original = initialMap();
  const proposal = planMapCompletion(original, "t1");
  assert.deepEqual(proposal.result, {
    ok: true, changed: true,
    task: { id: "t1", title: "写周报", completed: true },
  });
  assert.deepEqual([...proposal.nextTasks.values()], [
    { id: "t1", title: "写周报", completed: true },
    { id: "t2", title: "整理笔记", completed: false },
  ]);
  assert.deepEqual([...original.values()], [
    { id: "t1", title: "写周报", completed: false },
    { id: "t2", title: "整理笔记", completed: false },
  ]);
});

test("Map 计算保留无效编号与未知编号的区别", function () {
  for (const [id, reason] of [["", "invalid-id"], ["t9", "not-found"], [" t1 ", "not-found"]]) {
    assert.deepEqual(planMapCompletion(initialMap(), id), {
      result: { ok: false, reason }, nextTasks: null,
    });
  }
});

test("Map 计算不再次修改已完成任务", function () {
  const tasks = initialMap();
  tasks.get("t1").completed = true;
  assert.deepEqual(planMapCompletion(tasks, "t1"), {
    result: {
      ok: true, changed: false,
      task: { id: "t1", title: "写周报", completed: true },
    }, nextTasks: null,
  });
});

test("完成第二条任务也不改变列表顺序", function () {
  const proposal = planMapCompletion(initialMap(), "t2");
  assert.deepEqual([...proposal.nextTasks.values()], [
    { id: "t1", title: "写周报", completed: false },
    { id: "t2", title: "整理笔记", completed: true },
  ]);
});

test("构造 Map 和返回操作结果都隔开外部修改", function () {
  const initial = [{ id: "t1", title: "写周报", completed: false }];
  const current = toTaskMap(initial);
  initial[0].title = "外部修改";
  const proposal = planMapCompletion(current, "t1");
  proposal.result.task.title = "结果修改";
  assert.equal(current.get("t1").title, "写周报");
  assert.equal(proposal.nextTasks.get("t1").title, "写周报");
});
