let calls = 0;
function completeTask(id) {
  calls += 1;
  return { ok: true, id };
}

const savedFunction = completeTask;
console.log("保存函数后：", calls);
const savedResult = completeTask("t1");
console.log("立即调用后：", calls, typeof savedResult);
savedFunction("t2");
console.log("调用保存的函数后：", calls);
