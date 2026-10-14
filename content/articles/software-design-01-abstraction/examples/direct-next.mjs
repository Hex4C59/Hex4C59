// 需求变化：版本值相同，内部存储改为嵌套结构。
export const appInfo = {
  release: { version: "1.0.0" },
  platform: {
    versions: { node: "node-demo", electron: "electron-demo" },
  },
  internalBuildTag: "demo-build",
};
