import test from "node:test";
import assert from "node:assert/strict";
import { planCompletion } from "./plan-completion.mjs";

// 每次调用都新建数据，检查之间不共用可以修改的数组。
function initialTasks() {
  return [
    { id: "t1", title: "写周报", completed: false },
    { id: "t2", title: "整理笔记", completed: false },
  ];
}

test("完成指定任务，原数组仍保持原值", function () {
  const original = initialTasks();
  const proposal = planCompletion(original, "t1");
  assert.deepEqual(proposal.result, {
    ok: true, changed: true,
    task: { id: "t1", title: "写周报", completed: true },
  });
  assert.deepEqual(proposal.nextTasks, [
    { id: "t1", title: "写周报", completed: true },
    { id: "t2", title: "整理笔记", completed: false },
  ]);
  assert.deepEqual(original, [
    { id: "t1", title: "写周报", completed: false },
    { id: "t2", title: "整理笔记", completed: false },
  ]);
});

test("无效编号没有待采用的新数据", function () {
  for (const id of [undefined, null, 1, "", "  "]) {
    assert.deepEqual(planCompletion(initialTasks(), id), {
      result: { ok: false, reason: "invalid-id" }, nextTasks: null,
    });
  }
});

test("未知编号与有空格的不同编号都不匹配已有任务", function () {
  for (const id of ["t9", " t1 "]) {
    assert.deepEqual(planCompletion(initialTasks(), id), {
      result: { ok: false, reason: "not-found" }, nextTasks: null,
    });
  }
});

test("已经完成的任务不提出再次修改", function () {
  const tasks = initialTasks();
  tasks[0].completed = true;
  assert.deepEqual(planCompletion(tasks, "t1"), {
    result: {
      ok: true, changed: false,
      task: { id: "t1", title: "写周报", completed: true },
    },
    nextTasks: null,
  });
});

test("修改返回结果不会改动原输入或待保存数据", function () {
  const tasks = initialTasks();
  const proposal = planCompletion(tasks, "t1");
  proposal.result.task.title = "外部修改";
  assert.equal(tasks[0].title, "写周报");
  assert.equal(proposal.nextTasks[0].title, "写周报");
});
