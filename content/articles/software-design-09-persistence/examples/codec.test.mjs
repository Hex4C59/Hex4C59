import test from "node:test";
import assert from "node:assert/strict";
import { defaultTasks } from "./initial-tasks.mjs";
import { copyTasks } from "./copy-tasks.mjs";
import { decodeTaskFile, encodeTaskFile } from "./task-file-codec.mjs";

function versionOne(tasks) { return JSON.stringify({ version: 1, tasks }); }

test("版本一编码与读取保留合法任务", function () {
  assert.deepEqual(decodeTaskFile(encodeTaskFile(defaultTasks)), {
    ok: true, format: "v1", tasks: defaultTasks,
  });
});
test("旧数组格式仍能读取且标记其来源", function () {
  assert.deepEqual(decodeTaskFile(JSON.stringify(defaultTasks)), {
    ok: true, format: "legacy-array", tasks: defaultTasks,
  });
});
test("空任务是合法数据，不回退到默认任务", function () {
  for (const text of ["[]", versionOne([])]) {
    const decoded = decodeTaskFile(text);
    assert.equal(decoded.ok, true);
    assert.deepEqual(decoded.tasks, []);
  }
});
test("不能解析的文本报告 invalid-json", function () {
  for (const text of ["", "{", '{"version":1,"tasks":']) {
    assert.deepEqual(decodeTaskFile(text), { ok: false, reason: "invalid-json" });
  }
});
test("未知整数版本先报告 unsupported-version", function () {
  assert.deepEqual(decodeTaskFile('{"version":2,"rows":[]}'), {
    ok: false, reason: "unsupported-version",
  });
});
test("根结构及版本类型不符合约定时拒绝", function () {
  for (const value of [null, 1, "tasks", {}, { version: "1", tasks: [] }, { version: 1.5, tasks: [] }]) {
    assert.deepEqual(decodeTaskFile(JSON.stringify(value)), { ok: false, reason: "invalid-data" });
  }
});
test("任务集合必须为数组", function () {
  for (const tasks of [null, {}, "tasks", 1]) {
    assert.deepEqual(decodeTaskFile(versionOne(tasks)), { ok: false, reason: "invalid-data" });
  }
});
test("每一项必须包含三个约定字段", function () {
  for (const task of [null, [], 1, {}, { id: "t1", title: "写周报" }]) {
    assert.deepEqual(decodeTaskFile(versionOne([task])), { ok: false, reason: "invalid-data" });
  }
});
test("编号、标题与完成标记类型都需要验证", function () {
  for (const field of [{ id: " " }, { id: 1 }, { title: 1 }, { completed: "false" }]) {
    const tasks = copyTasks(defaultTasks);
    Object.assign(tasks[0], field);
    assert.deepEqual(decodeTaskFile(versionOne(tasks)), { ok: false, reason: "invalid-data" });
  }
});
test("重复编号会被拒绝，不进入 Map", function () {
  const tasks = copyTasks(defaultTasks);
  tasks[1].id = "t1";
  assert.deepEqual(decodeTaskFile(versionOne(tasks)), { ok: false, reason: "invalid-data" });
});
test("未知字段被拒绝，避免读入后悄悄丢弃", function () {
  const tasks = copyTasks(defaultTasks);
  tasks[0].note = "尚不支持的字段";
  for (const value of [{ version: 1, tasks }, { version: 1, tasks: defaultTasks, extra: true }]) {
    assert.deepEqual(decodeTaskFile(JSON.stringify(value)), { ok: false, reason: "invalid-data" });
  }
});
test("写出时也不接受非法任务", function () {
  assert.throws(function () { encodeTaskFile([{ id: "t1", title: "写周报", completed: "false" }]); }, TypeError);
});
