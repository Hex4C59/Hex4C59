# 第 01 篇示例：抽象的收益与代价

这是虚构应用“纸舟”的教学代码。数据中的 `node-demo` 和 `electron-demo` 是字符串，代码没有加载 Electron，也没有读取本机版本。

核验环境：2026-10-14，macOS arm64，Node.js v25.9.0。仅使用 Node.js 内置模块，无第三方依赖；没有进行其他 Node.js 版本的兼容性验证。

解压后在本目录执行：

```sh
node --version
node demo.mjs
node --test check.test.mjs
node freeze.mjs
```

`demo.mjs` 按 direct、query、forward 打印相同的关于页文本和诊断字段。测试共 6 项；布局迁移在系统临时目录执行，结束后清理，不改写本目录。`freeze.mjs` 检查绑定、外层冻结与嵌套冻结，输出三行观察结果。

`direct.mjs` 暴露内部对象，`query.mjs` 只导出查询操作，`forward.mjs` 增加一层转调。`about.mjs` 和 `diagnostics.mjs` 是两个调用者；每个调用者并列展示三种调用路径。两个 `*-next.mjs` 文件模拟内部结构变化，保持版本值相同。

观察范围是给定的字段值、同步返回、结果对象身份与修改隔离、布局变化后的调用行为。测试不测阅读时间、性能或真实应用兼容性。尚未覆盖异步数据源、坏输入、持久化或跨进程调用。
