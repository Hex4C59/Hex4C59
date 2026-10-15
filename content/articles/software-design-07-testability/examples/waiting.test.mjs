import test from "node:test";
import assert from "node:assert/strict";
import { createAsyncTaskList } from "./async-task-list.mjs";
import { createControlledSave } from "./controlled-save.mjs";

test("保存未结束时保留旧数据，成功后才采用", async function () {
  const saving = createControlledSave();
  const taskList = createAsyncTaskList(saving.saveSnapshot);
  const pending = taskList.completeTask("t1");
  try {
    assert.equal(saving.calls.length, 1);
    assert.deepEqual(taskList.listTasks(), [
      { id: "t1", title: "写周报", completed: false },
      { id: "t2", title: "整理笔记", completed: false },
    ]);
    assert.equal(saving.calls[0].tasks[0].completed, true);
    saving.calls[0].succeed();
    assert.deepEqual(await pending, {
      ok: true, changed: true,
      task: { id: "t1", title: "写周报", completed: true },
    });
    assert.deepEqual(taskList.listTasks().map(task => task.completed), [true, false]);
  } finally {
    for (const call of saving.calls) call.succeed();
    await Promise.allSettled([pending]);
  }
});
