export function createControlledSave() {
  const calls = [];
  function saveSnapshot(tasks) {
    return new Promise(function createPending(resolve, reject) {
      calls.push({ tasks, succeed: resolve, fail: reject });
    });
  }
  return { calls, saveSnapshot };
}
