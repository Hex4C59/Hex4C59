import test from "node:test";
import assert from "node:assert/strict";
import { createAsyncTaskList } from "./task-list.mjs";
import { checkBeforeAdopt, checkRejection, checkBusy } from "./contract-checks.mjs";

test("原约定：保存后才采用", async function () { await checkBeforeAdopt(createAsyncTaskList); });
test("原约定：保存拒绝返回失败", async function () { await checkRejection(createAsyncTaskList); });
test("原约定：等待时拒绝第二次修改", async function () { await checkBusy(createAsyncTaskList); });
test("创建任务对象仍为同步接口", function () {
  assert.throws(function () { createAsyncTaskList(null); }, TypeError);
});
