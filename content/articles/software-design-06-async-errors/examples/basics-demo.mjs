import { regularFailure, asyncFailure, returnTaskFailure, returnWithoutAwait, returnWithAwait } from "./promise-basics.mjs";

try { regularFailure(); } catch (error) { console.log("普通调用外层：", error.message); }
let pending;
try {
  pending = asyncFailure();
  console.log("异步调用已交回 Promise：", pending instanceof Promise);
} catch {
  console.log("这个同步 catch 不会执行");
}
try { await pending; } catch (error) { console.log("等待时收到：", error.message); }
const resultPromise = returnTaskFailure();
console.log("直接读取 Promise.ok：", resultPromise.ok);
console.log("Promise 作为条件：", Boolean(resultPromise));
const result = await resultPromise;
console.log("等待后的任务结果：", JSON.stringify(result));
await returnTaskFailure().then(function onResult(value) {
  console.log("then 收到的 ok：", value.ok);
});
const failLater = function saveSnapshot() { return Promise.reject(new Error("保存拒绝")); };
try { await returnWithoutAwait(failLater); } catch (error) { console.log("直接 return 的拒绝到外层：", error.message); }
console.log("return await 的局部结果：", await returnWithAwait(failLater));
