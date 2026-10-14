import { getVersion } from "./get-version.mjs";

console.log("查询 app：", getVersion("app"));
console.log("查询 node：", getVersion("node"));

try {
  getVersion("appp");
} catch (error) {
  console.log("查询 appp 失败：", error.message);
}

console.log("再次查询 app：", getVersion("app"));
