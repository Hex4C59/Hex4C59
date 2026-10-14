// 仅导出查询函数，调用者不直接取得内部对象。
const appInfo = {
  version: "1.0.0",
  runtime: { node: "node-demo", electron: "electron-demo" },
  internalBuildTag: "demo-build",
};

export function getAppVersion() {
  return {
    app: appInfo.version,
    node: appInfo.runtime.node,
    electron: appInfo.runtime.electron,
  };
}
