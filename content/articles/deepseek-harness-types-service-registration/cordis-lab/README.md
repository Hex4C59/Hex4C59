# 在真实 Cordis 中复现类型与服务注册

对应 DeepSeek Harness 0.2.1-alpha.2，使用该版本中的 Cordis 4.0.5-alpha.1 和 Cosmokit 1.8.6-alpha.1。脚本会检查源码 commit 与相关工作区状态。示例能力 `blogFiles` 由本文定义，内容只由字符串拼接生成，不是 dsh 的 FileSystem 或本地文件系统后端。

## 运行

需要 Git、npm 和符合 dsh 要求的 Node（^22.19.0 或 >=24）。本次实际验证环境为 macOS arm64、Node v25.9.0。先准备 DeepSeek Harness 源码，检出与版本对应的固定快照：

```sh
git clone https://github.com/deepseek-ai/deepseek-harness.git
git -C deepseek-harness switch --detach d743267388641bc76f17c45ce8b4c231aed1d32c
```

进入本实验目录，再运行：

```sh
npm ci --ignore-scripts
DSH_SOURCE=/path/to/deepseek-harness npm run verify
```

将 `/path/to/deepseek-harness` 替换成刚才的源码目录。不需要在 dsh 源码目录安装工作区依赖；脚本只读取它，在新建的系统临时目录构建。实验依赖通过 npm 安装；后续消费工程安装本次生成的 tarball 时使用 `--offline --ignore-scripts --legacy-peer-deps`，其中 `--legacy-peer-deps` 避免解析未参与实验的可选 Loader/include peer。Cordis/Cosmokit/示例包及 standard-schema 都显式安装，不依靠该参数隐藏缺少的运行依赖。

本实验固定 TypeScript 6.0.3、tsdown 0.22.2、@types/node 22.20.1、@standard-schema/spec 1.1.0，并附 package-lock.json。末行预期为 `13 checks passed`，其后报告实际 Node 与 TypeScript 版本。

## 实际执行的内容

- 使用原始 Cordis/Cosmokit tsconfig 与项目引用运行 `tsc -b`。在临时副本中将 manifest 的 `workspace:` 依赖替换为快照中对应包的版本；main/types/exports/files 保留原配置。
- 用 tsdown 将已发出的 JavaScript 打成两个 runtime 入口，保留 tsc 生成的声明。这里使用针对两个包的构建配置，没有运行根构建的 Typert 插件或完整 Host/Client 构建。
- 构建 `@dsh-blog/files` 与 `@dsh-blog/reader`，打包上述四个包以及 standard-schema，得到五个本地 tarball。只把这些 tarball 安装到独立消费工程，类型检查不使用源码 paths，且关闭 skipLibCheck。
- NodeNext 与 Bundler 分别检查：只导入 reader 时访问 `ctx.blogFiles` 报 TS2339；显式导入 files 类型入口后通过。reader 的 .d.ts 本身不保留空类型导入。
- 检查普通 inject 元数据与 @Inject 的类型约束。三个负例分别要求 TS2345、TS2322、TS2345，报错属于成功条件。
- 从安装后的包加载真实 Cordis。通过 provide/inject 驱动消费者等待、激活、清理与恢复；另一个服务域的消费者保持等待，根 Fiber 卸载后所有已激活的消费者资源完成清理。
- 运行 --explainFiles 和 --traceResolution，确认增强文件出现的原因以及 types 条件实际选择的文件。

`FiberState` 是这个快照的 const enum，因此运行案例先用 tsc 编译再执行；不能把它当成 JavaScript 的具名导出直接加载。

## 查看诊断和保留消费工程

默认把经过路径替换的日志和 `report.json` 写到本目录的 `reports/`，临时构建目录随后删除。可改报告目录：

```sh
DSH_SOURCE=/path/to/deepseek-harness npm run verify -- --report-dir ./reports
```

要手动排障，可加 `--keep-workspace`。脚本会输出消费工程的实际目录；它保留本次创建的临时目录，便于检查 node_modules、声明和 tsconfig。

```sh
DSH_SOURCE=/path/to/deepseek-harness npm run verify -- --keep-workspace
node node_modules/typescript/bin/tsc -p /path/to/consumer/without-contract-Bundler.json --explainFiles --pretty false
node node_modules/typescript/bin/tsc -p /path/to/consumer/with-contract-Bundler.json --traceResolution --pretty false
```

第二条命令预期非零退出并给出 TS2339。将 `/path/to/consumer` 替换成脚本输出的路径。检查完成后，可删除脚本输出目录的父目录，它是本次创建的 `dsh-types-cordis-` 临时目录；不要删除其他目录。也可以不保留工程，直接阅读 reports 下的两个 explain 日志和 trace-resolution.log。

## 验证边界

这是源码快照的局部构建、本地打包消费与真实 Cordis 行为实验。它没有验证 npm 上官方发布的 tarball、真实 dsh-fs/dsh-fs-local 产物、完整 Host/Client 工程、Loader/HMR、真实文件 IO、模型请求或跨平台行为。类型与运行用例分别控制自己的文件集合，不能把某个通过的用例当成整套 dsh 的验收。
