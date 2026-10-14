import assert from "node:assert/strict";

const info = { runtime: { node: "before" } };
info.runtime.node = "after-const";
assert.equal(info.runtime.node, "after-const");
assert.throws(() => { info = {}; }, TypeError);

Object.freeze(info);
assert.throws(() => { info.runtime = {}; }, TypeError);
info.runtime.node = "after-freeze";
assert.equal(info.runtime.node, "after-freeze");
assert.equal(Object.isFrozen(info.runtime), false);

Object.freeze(info.runtime);
assert.throws(() => { info.runtime.node = "blocked"; }, TypeError);
console.log("const: binding fixed, nested write allowed");
console.log("freeze: outer write rejected, nested write allowed");
console.log("freeze nested: nested write rejected");
