import assert from "node:assert/strict";
import { cp, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import * as query from "./query.mjs";
import { queryVersion } from "./forward.mjs";
import * as about from "./about.mjs";
import * as diagnostics from "./diagnostics.mjs";

const expected = {
  app: "1.0.0",
  node: "node-demo",
  electron: "electron-demo",
};

async function migratedExample(t) {
  const directory = await mkdtemp(join(tmpdir(), "software-design-01-"));
  t.after(() => rm(directory, { recursive: true, force: true }));
  for (const name of [
    "direct.mjs", "query.mjs", "forward.mjs", "about.mjs", "diagnostics.mjs",
  ]) {
    await cp(new URL(name, import.meta.url), join(directory, name));
  }
  await cp(new URL("direct-next.mjs", import.meta.url), join(directory, "direct.mjs"));
  await cp(new URL("query-next.mjs", import.meta.url), join(directory, "query.mjs"));
  return directory;
}

async function load(directory, name) {
  return import(pathToFileURL(join(directory, name)).href);
}

test("three paths meet the initial visible requirements", () => {
  for (const read of [about.directAbout, about.queryAbout, about.forwardedAbout]) {
    assert.equal(read(), "纸舟 1.0.0");
  }
  for (const read of [
    diagnostics.directDiagnostics,
    diagnostics.queryDiagnostics,
    diagnostics.forwardedDiagnostics,
  ]) {
    assert.deepEqual(read(), expected);
  }
});

test("query exposes only the operation and returns a fresh synchronous result", () => {
  assert.deepEqual(Object.keys(query), ["getAppVersion"]);
  const first = query.getAppVersion();
  const second = query.getAppVersion();
  assert.equal(first instanceof Promise, false);
  assert.notStrictEqual(first, second);
  assert.deepEqual(first, second);
  assert.equal(Object.isFrozen(first), false);
});

test("mutating a returned string field does not change later query results", () => {
  const result = query.getAppVersion();
  result.app = "caller-edit";
  assert.deepEqual(query.getAppVersion(), expected);
});

test("forwarding preserves the selected fields and result ownership", () => {
  const result = queryVersion();
  assert.deepEqual(result, expected);
  result.node = "caller-edit";
  assert.deepEqual(queryVersion(), expected);
});

test("source layout changes preserve query callers and expose direct dependencies", async (t) => {
  const directory = await migratedExample(t);
  const changedAbout = await load(directory, "about.mjs");
  const changedDiagnostics = await load(directory, "diagnostics.mjs");
  for (const name of ["queryAbout", "forwardedAbout"]) {
    assert.equal(changedAbout[name](), "纸舟 1.0.0");
  }
  for (const name of ["queryDiagnostics", "forwardedDiagnostics"]) {
    assert.deepEqual(changedDiagnostics[name](), expected);
  }
  assert.equal(changedAbout.directAbout(), "纸舟 undefined");
  assert.throws(() => changedDiagnostics.directDiagnostics(), TypeError);
  for (const name of ["about.mjs", "diagnostics.mjs", "forward.mjs"]) {
    assert.equal(
      await readFile(join(directory, name), "utf8"),
      await readFile(new URL(name, import.meta.url), "utf8"),
    );
  }
});

test("updating both direct callers restores the visible requirements", async (t) => {
  const directory = await migratedExample(t);
  for (const name of ["about.mjs", "diagnostics.mjs"]) {
    const source = await readFile(join(directory, name), "utf8");
    const updated = source
      .replaceAll("appInfo.version", "appInfo.release.version")
      .replaceAll("appInfo.runtime.", "appInfo.platform.versions.");
    assert.notEqual(updated, source);
    await writeFile(join(directory, name), updated);
  }
  assert.equal((await load(directory, "about.mjs")).directAbout(), "纸舟 1.0.0");
  assert.deepEqual((await load(directory, "diagnostics.mjs")).directDiagnostics(), expected);
});
