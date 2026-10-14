import { appInfo } from "./direct.mjs";
import { getAppVersion } from "./query.mjs";
import { queryVersion } from "./forward.mjs";

export function directAbout() {
  return `纸舟 ${appInfo.version}`;
}

export function queryAbout() {
  return `纸舟 ${getAppVersion().app}`;
}

export function forwardedAbout() {
  return `纸舟 ${queryVersion().app}`;
}
