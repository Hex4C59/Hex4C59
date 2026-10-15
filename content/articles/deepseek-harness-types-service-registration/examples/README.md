# 类型声明与实例属性：最小语言实验

这是第六篇博客的独立 TypeScript 实验，不加载 Cordis，也不模拟 inject、服务域或插件生命周期。`Context` 是一个空类；`mountFs()` 通过普通对象赋值添加示意能力，只用于观察类型声明与运行对象的区别。这里的 FileSystem 不是 dsh 的完整接口。

需要 Node.js 22 或以上、TypeScript 6.0.3。在本目录运行：

```sh
npm install --ignore-scripts
npm run verify
```

脚本检查 8 组条件：包含与缺少声明合并、冲突合并、宽松重载、类型导入的 JavaScript 擦除、声明保留位置和外部消费方的类型入口，以及导入提供方不等于挂载、只挂载一个实例的结果。预期出现 8 条 PASS；末行报告 8 checks passed、实际 Node 版本和 TypeScript 6.0.3。

`tsconfig.missing.json` 与 `tsconfig.conflict.json` 是预期失败用例，由脚本分别确认 TS2339 和 TS2717；不要把它们当作待修复的构建错误。`permissive-overloads.ts` 刻意保留 any 重载，验证其边界，不建议业务代码因此放弃类型检查。

编译产物放在系统临时目录，检查后清理。若已有同版本编译器，可以通过 `DSH_TYPES_TSC` 环境变量传入其入口路径；正常阅读与复现使用上面的 npm 命令即可。
