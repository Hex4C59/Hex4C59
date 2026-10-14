import { changedFiles } from "./change-report.mjs";
const report = changedFiles();
console.log("按操作拆分，发生变化的文件：", report.byOperation.join(", "));
console.log("集中隐藏表示，发生变化的文件：", report.byDecision.join(", "));
