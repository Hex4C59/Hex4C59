import assert from "node:assert/strict";

const appInfo = { version: "1.0.0", internalBuildTag: "demo-build" };

function getAppVersion() {
  return { app: appInfo.version };
}

const query = getAppVersion;
const first = query();
const second = query();
assert.equal(first.app, "1.0.0");
assert.equal(second.app, "1.0.0");
assert.notStrictEqual(first, second);
console.log(first.app);
console.log(first === second);
