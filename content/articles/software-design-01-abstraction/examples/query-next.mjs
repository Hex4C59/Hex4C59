// 内部结构改变，公开的字段、同步返回和结果所有权保持不变。
const appInfo = {
  release: { version: "1.0.0" },
  platform: {
    versions: { node: "node-demo", electron: "electron-demo" },
  },
  internalBuildTag: "demo-build",
};

export function getAppVersion() {
  return {
    app: appInfo.release.version,
    node: appInfo.platform.versions.node,
    electron: appInfo.platform.versions.electron,
  };
}
