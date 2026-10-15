export function regularFailure() {
  throw new Error("普通函数错误");
}
export async function asyncFailure() {
  throw new Error("异步函数错误");
}
export async function returnTaskFailure() {
  return { ok: false, reason: "not-found" };
}
export async function returnWithoutAwait(saveSnapshot) {
  try {
    return saveSnapshot();
  } catch {
    return "这里捕获了错误";
  }
}
export async function returnWithAwait(saveSnapshot) {
  try {
    return await saveSnapshot();
  } catch {
    return "这里捕获了错误";
  }
}
