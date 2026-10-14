import { appInfo } from "./direct.mjs";
import { getAppVersion } from "./query.mjs";
import { queryVersion } from "./forward.mjs";

export function directDiagnostics() {
  return {
    app: appInfo.version,
    node: appInfo.runtime.node,
    electron: appInfo.runtime.electron,
  };
}

export function queryDiagnostics() {
  return getAppVersion();
}

export function forwardedDiagnostics() {
  return queryVersion();
}
