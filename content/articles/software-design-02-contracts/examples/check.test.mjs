import assert from "node:assert/strict";
import test from "node:test";
import { getVersion } from "./get-version.mjs";

test("app 和 node 返回各自的演示版本", () => {
  assert.equal(getVersion("app"), "1.0.0");
  assert.equal(getVersion("node"), "node-demo");
});

test("拼错或未知的名称在查询时被拒绝", () => {
  for (const name of ["appp", "browser", "toString"]) {
    assert.throws(() => getVersion(name), Error);
  }
});

test("缺少参数或传入其他类型时被拒绝", () => {
  for (const value of [undefined, null, 3, {}, []]) {
    assert.throws(() => getVersion(value), Error);
  }
});

test("从 JSON 文本读出的错误名称也会被拒绝", () => {
  const request = JSON.parse('{"component":"appp"}');
  assert.throws(() => getVersion(request.component), Error);
});

test("查询失败不会改变后续的合法查询", () => {
  const before = getVersion("app");
  assert.throws(() => getVersion("appp"), Error);
  assert.equal(getVersion("app"), before);
  assert.equal(getVersion("node"), "node-demo");
});
