+++
title = "DeepSeek Harness 源码解析（四）：CLI、Web、Desktop 与 SDK 如何组装同一套运行时"
date = 2026-10-14
lastmod = 2026-10-17
draft = false
author = "Hex4C59"
description = "沿 runCli、runProfile 与 Cordis Loader 追踪 DeepSeek Harness 的配置创建、分层覆盖、启动审查与退出，比较 Web、headless、Desktop 和 SDK 的任务通道，并解释 SDK 结果收集与 minimal 组合。"
summary = "dsh 的几个入口共享启动和 Agent 服务，却有不同的输入、传输、配置与退出方式。本文从 profile 如何变成插件树讲起，追踪浏览器、Electron 和 SDK 子进程怎样接入这棵树。"
tags = ["DeepSeek Harness", "Cordis", "应用架构"]
categories = ["ai"]
source_kind = "original"
series = ["DeepSeek Harness"]
series_order = 4
difficulty = "intermediate"
article_type = "concept"
topics = ["coding-agent", "plugin-architecture", "application-composition"]
frameworks = ["DeepSeek Harness", "Cordis"]
ShowToc = true
+++

[第三篇](/articles/deepseek-harness-source-map/)从 `read` 工具追到文件系统提供者，最后停在一个问题上：究竟是哪份配置，把这些插件放进了应用？

这个问题会直接影响你读到的行为。浏览器提交一条消息、终端执行一次任务、Python 调用一次 `run()`，都能驱动 Agent，但它们的启动者、通信方式和退出条件不同。只看 Agent 循环，解释不了为什么 Web 会监听端口、SDK 必须独占标准输出，也解释不了 Desktop 为什么要启动另一个进程。

**dsh 的共享部分是启动流程与底层服务；具体应用由有序配置层装配出来。** `dsh-base` 提供常用基础能力，Web、headless、完整 SDK 分别在它上面添加应用层。Desktop 通过共享 profile runner 启动完整 Web 应用。`sdk-minimal` 则使用一份独立的完整配置，不继承 base。

本文面向能阅读 TypeScript 导入、函数和 YAML 配置的开发者，沿“谁启动、装哪些插件、输入从哪里进入、何时就绪和退出”追踪入口。Agent 内部的 Turn、Step 和工具循环见[第二篇](/articles/deepseek-harness-request-lifecycle/)；这里着重解释循环外面如何形成一个可使用的应用。

本文分析 [DeepSeek Harness `0.2.1-alpha.2`](https://github.com/deepseek-ai/deepseek-harness/tree/d743267388641bc76f17c45ce8b4c231aed1d32c)，核对日期为 2026-10-14。本文依据该版本的实现和配置作静态分析，没有启动 dsh、发送模型请求或验证安装后的产品行为。

## 先把启动通道与任务通道分开

在终端输入 `dsh web`，产生的是应用启动：加载配置、安装插件、监听本地端口。浏览器随后提交“解释这个项目”，才产生任务输入。两件事可以相隔很久，也有不同的失败位置。

SDK 也一样。启动子进程后，客户端先执行 `initialize` 握手，再发送 `session/prompt`。子进程已经存在，不代表配置树已经准备好；一条 prompt 已被接收，也不代表模型已经完成回答。

下图把两条通道分别画出。切换入口时，观察启动调用方和任务传输如何变化，以及哪些部分仍由 `runProfile`、Loader 和 Agent 服务承担。图中的“共享 Agent 服务”是对 Agent、Session、Tools、LLM 等能力的合并表示，具体提供者与策略仍由所选配置决定。

{{< interactive-diagram src="entrypoints.html" title="切换 Web、headless、Desktop 与 SDK，比较应用启动、任务输入和共享 Agent 服务之间的关系" height="1440" compact-height="1940" mobile-height="1980" >}}

这里的连线只表达图中命名的关系。Desktop 的 IPC（进程间通信）承担就绪与控制信息，Web 的连接层承担应用请求和流；不能把所有跨进程通信都归到同一条消息通道上。

## profile、bundle 和 patch 各负责什么

### profile 保存一次应用组合

在该版本中，profile 是 Harness home 中的一份命名配置。它的 `package.json` 通过 `dsh.profile.bundles` 指定要叠加的 bundle，同时可以记录安装在此 profile 中的外部插件依赖。用户修改放在 `cordis.patch.yml` 中。

一个简化的 manifest 如下。这里省略了其他字段，只展示 Web 模板的 bundle 顺序，不是可直接用于安装的完整文件：

```json
{
  "dsh": {
    "profile": {
      "bundles": [
        "@deepseek-ai/dsh-base",
        "@deepseek-ai/dsh-web-app"
      ]
    }
  }
}
```

这个列表的意思是先应用 base 的配置，再应用 Web 的配置。它没有要求你为 Web 复制一套 Agent 实现。

[`PROFILE_TEMPLATES`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/app-boot/src/profile.ts#L179)定义了五个随仓库提供的模板：

| profile | bundle 顺序 | 应用用途 |
|---|---|---|
| `web` | `dsh-base` → `dsh-web-app` | 浏览器界面与后端服务 |
| `headless` | `dsh-base` → `dsh-headless` | 执行一次任务并退出 |
| `sdk` | `dsh-base` → `dsh-sdk-app` | 通过标准输入输出服务 SDK 客户端 |
| `sdk-minimal` | 仅 `dsh-sdk-minimal` | 显式定义的小型 SDK 运行时 |
| `acp` | `dsh-base` → `dsh-acp-app` | 自动化 ACP 协议入口 |

表中的短名都省略了 `@deepseek-ai/` 前缀。Desktop 使用由 Electron 管理的保留 profile，后文单独说明；它不在这个普通模板表中。ACP（Agent Client Protocol）属于另一种自动化协议组合，本文只定位其入口，不展开协议细节。

### 第一次启动会创建文件，以后启动复用它们

[`loadProfile()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/app-boot/src/profile.ts#L788)先定位 `$DSH_HOME/profiles/<name>`。如果缺少 manifest，且名称属于仓库模板，就调用 `initProfile()`；未知名称则报错，要求先建立对应 profile。

[`initProfile()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/app-boot/src/profile.ts#L261)创建 manifest、空的用户 patch 和 pnpm workspace 设置，只补缺失文件，不覆盖已有文件。`prepareProfile()` 随后写入启动用的空根 `cordis.yml`。下面只列出这次组合涉及的路径，home 层 patch 是可选的：

```text
$DSH_HOME/
├── cordis.patch.yml              # 可选：整个 home 的用户层
└── profiles/
    └── web/
        ├── package.json         # bundle 顺序与外部插件依赖
        ├── pnpm-workspace.yaml  # profile 插件的包管理设置
        ├── cordis.patch.yml     # 这个 profile 的用户层
        └── cordis.yml           # 启动器重写为 [] 的根文件
```

持久修改应放在 `cordis.patch.yml`。`cordis.yml` 被重写为空列表，是为了防止 Loader 写回的合成配置在下次启动时再次叠加 bundle，造成重复插入。这也意味着，程序重启和恢复出厂组合是不同的操作。

若想基于 Web 模板创建独立名称，可以使用 [`initializeProfileFromDefault()` 对应的参数](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/apps/cli/src/profile-boot.ts#L101)。下面只展示语法，本次没有执行：

```sh
# 首次创建：复制模板的 bundle 列表，然后启动。
dsh rescue --from-default-profile web --no-open

# 后续复用：启动已经存在的 rescue。
dsh rescue --no-open
```

创建分支要求目标名称不是内置模板名、目标目录尚不存在。它复制的是模板中的 bundle 列表，不复制另一份 Web profile 的本地状态，也不保存一条以后自动继承那个 profile 的关系；对已存在目录再次使用 `--from-default-profile` 会被拒绝。

profile 名称主要划分组合与包依赖。默认 base 的会话存储仍指向 [`dshHomePath('sessions')`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/base/cordis.patch.yml#L133)，所以改名为 `rescue` 并没有顺便隔离全部持久数据。若需要另一套会话、设置与凭据，应该同时检查 Harness home 和具体存储配置；工作目录、profile 与数据根各自负责不同的范围。

### bundle 将配置行与实现一起交付

bundle 的 manifest 通过 `dsh.bundle.patch` 指向它携带的配置文件。比如 [`dsh-web-app/package.json`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/web-app/package.json)指向同包中的 `cordis.patch.yml`。

打开这份 patch，会看到三类动作：给已有配置行换配置、禁用某些行、插入新行。Web 给 base 已有的系统提示词等行设置应用值，并加入 Web server、连接、API 与界面插件。完整 SDK 则加入标准输入输出的 JSON-RPC 服务。

因此，bundle 名称并不等于只有一个插件。`dsh-web-app` 既提供组合配置，也包含 Web 应用自己的运行时代码；它的 [`src/index.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/web-app/src/index.ts)负责静态前端、应用 URL、浏览器打开等胶合工作。理解一个 bundle，至少要看 manifest、patch 和 patch 挂载的实现。

### patch 有顺序，而且会替换整份 config

[`readProfilePatches()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/app-boot/src/profile-context.ts#L63)收集的顺序如下，后面的层可以改变前面的配置：

| 顺序 | 配置来源 | 适合放什么 |
|---|---|---|
| 1 | manifest 中各 bundle 的 patch，按列表顺序 | 应用分发的组合 |
| 2 | profile 自己的 `cordis.patch.yml` | 这个 profile 的持久修改 |
| 3 | `$DSH_HOME/cordis.patch.yml` | 同一个 Harness home 的公共偏好 |
| 4 | 本次启动的 `--patch` 文件，按参数顺序 | 这次调用的覆盖 |
| 5 | 满足条件时生成的遥测关闭 patch | 启动环境中的关闭开关 |

第五层要求 `DSH_TELEMETRY_DISABLED` 非空，且合成树已有相应会话遥测行，才生成关闭设置。这里检查的是非空字符串，`"0"` 或 `"false"` 也会触发关闭；它不会插入一套新的遥测插件。前三个应用 profile 的默认组合由各自的 bundle 决定，用户层仍能继续改变它们。

这些配置叠加在一个空列表 `[]` 上。CLI 的 [`PROFILE_ROOT_CONFIG`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/apps/cli/src/profile-boot.ts#L80)就是这个空根；它的职责是承载组合，不是另一份需要手工同步的默认配置。

还有一个容易出错的细节：**patch 定位一行后，会替换这一行的整个 `config`。** 它不会按你想象的方式递归补齐旧字段。[Web patch 的开头注释](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/web-app/cordis.patch.yml#L1)专门说明了这一点。

假设前一层给某行设置了 `{ host, port, tls }`，后一层只写 `{ port }`，就不能假定旧 `host` 和 `tls` 仍保留在那份 config 中。最终行为还要结合插件 schema 的默认值与校验来判断。这是解释合成规则的假设例子，不是建议照抄的部署配置。

### 列进 manifest 的 bundle，也可能没有进入配置树

[`resolveBundleDir()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/app-boot/src/profile.ts#L713)先从运行中的 dsh 安装位置查找 bundle，找不到再查 profile 的包环境。这解释了内置组合怎样使用安装自带的包，以及外部 bundle 为什么需要安装到 profile。这个顺序描述 bundle 定位，不能直接当作所有模块导入的通用覆盖规则。

找到包以后，[`loadProfileDirectory()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/app-boot/src/profile.ts#L739)还会读取 bundle 声明、检查它的 DSH peer 兼容范围，再读取 patch。peer 范围说明该包声明兼容哪些 Harness 版本；不兼容且没有对应豁免时，这一 bundle 不被采纳。

这个阶段按 bundle 捕获错误，把失败项与原因放进 `skippedBundles`，继续读取其他 bundle。runner 再输出诊断。普通的不可读或不兼容 bundle 被跳过时，它的 manifest 选择不会因此被删除；与旧版本退休 bundle 的专门迁移规则要分开理解。

因此，排查时要比较“manifest 选择了什么”和“这次实际加载了哪些 layer”。用户 patch 或 profile manifest 本身损坏仍会抛错，不能从 bundle 的跳过机制推断所有配置错误都会被忽略。

## CLI 如何把参数变成插件树

### `runCli()` 先决定运行哪一种命令

[`apps/cli/src/bin.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/apps/cli/src/bin.ts#L27)中的 `runCli()` 调用 `parseDshArgs()`，得到一个分派结果。启动 profile 只是其中一种：它还可以执行插件管理、输出合成配置、输出配置 schema。

因此，读取 CLI 时不要从 `process.argv` 直接跳到 Agent。中间还有命令分派；配置输出模式就没有进入正常应用启动。

参数也分两层。启动器解析 `--profile`、`--patch` 等自己拥有的参数，把剩余应用参数作为 `args` 交给配置树。应用插件随后解析自己的参数。下面两条命令用来说明语法；本文没有实际执行它们，也没有调用模型：

```sh
# 启动器选择 web；Web 的参数解析器处理 --no-open。
dsh --profile web --no-open

# 启动器选择 headless；headless 的参数解析器处理任务与 --json。
dsh --profile headless --json "解释当前目录的项目结构"
```

[`args.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/apps/cli/src/args.ts#L1)规定：第一个不由启动器识别的 token 会开启内部参数部分，所以启动器参数应放在应用参数前面。`dsh web` 是 `dsh --profile web` 的简写；`dsh web --help` 交给 Web 应用打印自己的帮助。

### `runProfile()` 提供各应用共同的启动准备

进入 [`runProfile()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/apps/cli/src/profile-boot.ts#L244) 后，程序先安装基于启动环境快照的 HTTP 代理处理，再准备 profile、包解析环境和额外 patch。它还建立清理与退出控制，监听进程信号。

在配置行挂载前，`runProfile()` 向根 Context 提供这些启动事实：

- `profileContext`：本次 profile 的名称、目录、Harness home、已启动 bundle 与覆盖配置等。
- 启动环境快照：让插件取得同一次启动的环境值。
- `PluginPackages`：按已解析的安装位置和 profile 包环境解析插件。
- `cmdlineArgs`、`appExit`、`appReady`：应用参数、退出请求和启动完成通知。

这几项说明了为什么 Web 的参数解析和 SDK 的输入生命周期都可以写成普通插件。它们拿到所需服务后执行自己的工作；启动器只需要提供共同事实。

[`composeProfile()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/apps/cli/src/profile-boot.ts#L197)还接受应用传入的 `resolvedProfile` 和 `installAnchor`。`installAnchor` 指向本次运行时安装的包位置，供包解析使用。Desktop 正是通过这条路径，将自己的打包运行时交给共享 runner。

### `boot()` 创建 Context，再让 Loader 挂载配置

[`boot()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/app-boot/src/index.ts#L975)创建 Cordis 根 Context、安装 Loader、执行上述准备函数，随后挂载根 include 与 patch。

Context 可以先理解成插件共享服务与事件的运行环境。Loader 根据配置加载插件，插件声明的注入关系决定它依赖哪些服务。YAML 中行的排列提供组合输入，不能当作所有插件 `apply()` 严格串行执行的保证。

挂载后，`boot()` 等待 Loader 当前树完成处理，再审查启动条目的状态。`runProfile()` 只有在启动未被信号取消、根 fiber 仍处于 `ACTIVE`、Loader 仍存在时，才提交 `appReady`。这里的 fiber 是 Cordis 管理一项插件及其生命周期的对象。

这就区分了几件事：进程存在、某个插件已经激活、整棵树处理完毕、应用启动审查通过。某一个局部动作成功，不能替代后面的条件。

### Loader 等待结束后，还要判断哪些失败会阻止启动

`loader.await()` 等待当前树的导入和生命周期工作处理完毕，可能得到成功、失败和等待依赖的不同条目。随后 [`auditStartupEntries()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/app-boot/src/index.ts#L928)按启动策略审查这些结果。

该版本有一份按配置行 id 维护的[必需条目集合](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/app-boot/src/index.ts#L748)，包括 `agent-loop`、`webserver`、`web-runtime`、`modules`、`connection`、`headless-runner`、`acp` 和 `sdk-jsonrpc-server`。根 include 也必须成功激活，因为没有它就无法可靠加载配置树。

| 失败或状态 | 此版本的启动处理 |
|---|---|
| profile manifest 或用户 patch 读取失败 | 在准备配置时抛错 |
| 某个 bundle 无法读取或不兼容 | 记入跳过诊断，继续处理其他 bundle |
| 根 include 未激活 | 启动失败，释放已挂载的树 |
| 树中已启用的必需条目导入、配置或激活失败 | 启动失败，诊断同时包含其他失败项 |
| 只有普通条目失败或等待注入服务 | 警告；成功的兄弟插件继续运行 |
| 必需 id 没有出现在树中，或对应行明确禁用 | 不作为这个审查的失败项 |
| `disabled` 表达式自己抛错 | 记作条目失败，不能当作明确禁用 |

最后两行限制了“就绪”的含义：审查确认的是这棵配置树符合当前启动策略，并没有证明完整产品能力都已出现。假设整个 Web bundle 被跳过，不能仅凭必需集合里写着 `webserver`，就推断缺失的 Web 行一定会被这次审查拦住。

后续 HMR 也有自己的处理方式。[启动与重载失败说明](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/boot/app-boot/README.md#startup-and-reload-failures)区分了启动审查与运行中的配置更新：后者不会重新执行整套必需启动审查，也不会遇到任意失败就回滚整棵树。某项配置修正后能否重新激活，要继续看 Loader 与重载协调逻辑。

插件自行启动、却未纳入 `apply()` 返回 Promise 的异步工作，若产生未处理的拒绝，还会进入共享的致命错误处理。普通条目启动失败可以只警告，不意味着所有后台异常都可以被当作可选能力缺失。

### 正常结束与进程信号共享清理控制

`runProfile()` 在启动窗口就安装信号处理，不必等所有插件准备好。该实现将 `SIGTERM` 视为监督方的停止请求，使用退出码 0；将 `SIGINT` 视为用户中断，使用退出码 130。退出码 0 在这里表示停止方式，不能当作某次 Agent 任务已经成功的证明。

[`createProcessShutdown()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/apps/cli/src/process-shutdown.ts#L22)把多次正常退出请求合并到同一个清理过程，默认给予 5 秒。清理失败或超过期限会强制退出；清理过程中再次收到中断也会升级为强制退出。应用的退出请求通过 `appExit` 进入这个控制器。

这个期限属于共享启动器的退出控制。SDK server 的协议 `shutdown` 还有自己的“先回响应、再释放根 Context”路径，客户端也有关闭期限；它们各管一段生命周期，不能把 5 秒当作所有入口和工具执行的统一超时。

## Web：启动插件树，再由浏览器通过连接层使用它

### Web 参数先成为一个服务

Web 的 [`startup.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/web-app/src/startup.ts#L17)注入 `cmdlineArgs`，解析参数后提供 `webStartup`。Web server 和 Web runtime 的配置行都声明需要这个服务，之后才能计算引用它的配置表达式。

例如，[Web server 行](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/web-app/cordis.patch.yml#L179)从 `webStartup` 读取 host、port 和 TLS，缺省 host 与 port 分别为 `127.0.0.1` 和 `3080`。这也解释了为什么帮助流程不会正常提供 `webStartup`：相关应用服务不会沿普通运行路径启动。

应用参数的归属到这里已经很清楚：`--port` 由 Web 参数插件解释，再通过服务进入配置；`--patch` 则在前面的启动器层处理。

### 前端插件与后端插件有各自的运行环境

Web 的配置除了 Agent 能力，还加入 Web server、静态前端、`client-modules`、`connection`、`api-remotes` 与界面插件。

[`client-modules` 的 Node 部分](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/client/modules/src/index.ts#L1)扫描 Host Loader 中声明 `dsh.client` 的条目，生成浏览器需要的 `window.__DSH_BOOT__` 图，并提供对应客户端 bundle。浏览器的模块系统根据这些启动信息建立客户端插件环境。

因此，同一个配置组合可以同时决定后端服务与浏览器插件名单，但浏览器没有取得 Node 根 Context 的对象引用。跨这条运行环境边界，要使用传输和远程接口。

[`connection` 配置行](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/web-app/cordis.patch.yml#L229)同时对应 Node 与浏览器两端：Node 端将网关绑定到 `/api`，浏览器端负责 fetch 与 SSE。SSE（Server-Sent Events，服务器发送事件）用于把服务端事件持续推送到客户端；应用请求则通过相应接口发出。

消息越过连接层和远程 API 后，才进入共享 Agent 服务。后续 inbox、Turn、Step、模型和工具链路沿用第二篇的分析。浏览器组件负责收集输入与呈现状态，后端 Agent 执行模型与工具循环。

### 公开展示的 URL 不会自动改变信任策略

Web runtime 的 `publicUrl` 决定对外打印、打开以及提供给模型上下文的应用地址。它没有自动配置反向代理路由或认证；Connection 的请求检查仍依据监听地址与 `trustedHosts` 等规则。

这两类设置由 [`web-app` 的配置定义](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/web-app/src/index.ts#L42)和 Web patch 中的 Connection 行分别说明。修改 URL 时，需要继续检查实际监听与请求信任配置；不能从“页面打印了一个公网地址”推断外部访问已经正确配置。

## headless：命令行的一次任务由直接驱动插件执行

`headless` 的默认组合是 base 加 [`dsh-headless/cordis.patch.yml`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/headless/cordis.patch.yml)。这个应用层没有挂载 Web Host、HTTP server 或浏览器插件。它加入参数提供者与直接驱动 Agent 的 runner，并关闭默认配置 HMR。

HMR（Hot Module Replacement，热替换）在这里指配置变化后的重载协调；是否启用由配置行决定。默认 Web 继承 base 的配置 HMR，headless 与完整 SDK 则在各自 patch 中禁用它。用户 patch 仍能覆盖默认值。

[`headless/startup.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/headless/src/startup.ts#L37)处理任务、`--session-id` 和 `--json`，发布 `headlessStartup`。runner 的配置等待这个服务，再取得任务文本与运行选项。

真正的一次任务发生在 [`run()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/headless/src/index.ts#L311)中：

1. 等待 Loader 树处理完成，取得 Agent registry、默认模型和 Session 服务。
2. 从参数或标准输入取得非空任务，选择默认模型。
3. 创建新 Agent；如果指定 `--session-id`，采用符合条件的既有 Session。
4. 通过 `agent.followup()` 投递用户消息，等待根 Agent 和相关子任务达到代码定义的完成边界。
5. 刷新会话记录，整理本次结果，写出文本或 JSON 事件，再请求应用退出。

其中，`--session-id` 表示继续已有会话；未知 id 会报错，不会顺手创建同名新会话。这一分支可以从 [`resolveAgent()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/headless/src/index.ts#L276)继续读。

headless 复用的是 Agent 与会话服务，输入端用命令行任务替换浏览器，输出端用标准输出替换界面。它的 `--json` 是这一应用定义的逐行事件输出；SDK 的标准输出则是 JSON-RPC 协议，两种格式不能互换。

## Desktop：Electron 管窗口，Node 子进程运行 Web 后端

### 为什么 Desktop 还要单独启动 Host

[`DesktopHostProcess.start()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/apps/desktop/src/host-process.ts#L186)用 Electron 可执行文件启动私有 `dsh-desktop-host` 入口。其环境通过 [`desktopNodeEnvironment()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/apps/desktop/src/node-environment.ts#L12)设置 `ELECTRON_RUN_AS_NODE=1`，使这个子进程以 Node 模式运行。

主进程仍管理窗口和原生交互；子进程承载应用后端。这是实际进程边界，需要通信与退出控制，不能只用“桌面版复用网页”一句话略过。

[`apps/desktop-host/src/index.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/apps/desktop-host/src/index.ts#L18)从 Desktop 打包运行时定位安装锚点，加载已经准备好的 profile，然后调用同一个 `runProfile()`。它传入：

- 名称为 `desktop` 的应用 profile，以及已经解析的 profile 对象。
- Desktop 打包运行时中的 `@deepseek-ai/dsh/package.json` 作为 `installAnchor`。
- `--no-open --host 127.0.0.1 --port 0` 作为应用参数。

默认 `port 0` 让操作系统分配空闲端口；后续 profile 配置仍可以覆盖它。`--no-open` 避免再打开普通浏览器窗口。

Desktop profile 的初始 bundle 来自 Web 模板，见 [`project-manager.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/apps/desktop/src/project-manager.ts)。普通 CLI 的 [`rejectElectronProfile()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/apps/cli/src/args.ts#L83)限制直接启动保留的 `desktop` profile。Desktop 通过 runner API 提供受管理的组合，并非让用户把 `desktop` 当作普通模板随意启动。

### 本地文档、HTTP 与 IPC 分别传什么

根据 [Desktop 架构说明](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/docs/architecture.md#desktop-application)，窗口立即加载打包的 `dsh-app://app/` 文档，等 Host 的启动注入到达后，在同一个文档中激活客户端插件。

应用 HTTP 请求经过桌面载体转发到已认证的本地 Web Host。实现入口为 [`forwardWebRequest()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/apps/desktop/src/web-document.ts#L77)。WebSocket 连接也指向该 Host，并受桌面应用窗口的凭据附加规则约束。

Node IPC 则传递启动注入、ready、致命错误和关闭等控制信息。子进程就绪后发送实际 URL 与注入内容，主进程接收它们，完成窗口与 Host 的连接。

因此可以分别检查两种故障：Host 启动失败，先查 runner 和 ready/fatal 控制消息；界面已经启动但应用请求失败，再查本地转发、认证和 Web 连接层。两者最终都使用 Web 应用，但出错的位置不同。

这个进程安排说明了代码的组织与通信方式。它本身没有证明工具执行被安全隔离；工具权限仍要查所选 sandbox、策略和实际运行环境。

## SDK：客户端启动运行时，再通过 stdio JSON-RPC 驱动它

### TypeScript 与 Python 都将 Agent 留在运行时进程里

TypeScript 的 [`resolveDshLaunch()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/sdk/client/src/launch.ts#L128)默认选择 `sdk` profile，解析同版本 dsh 的入口，再添加 `--profile` 与有序 `--patch` 参数。客户端用 `process.execPath` 启动这个 Node 入口，并建立标准输入、输出和错误管道。

Python 的 [`_default_launch_args()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/python/sdk/src/deepseek_harness/client.py#L476)同样组织 profile 和 patch 参数。默认可执行入口来自配套 runtime 包；调用方也可以指定 `dsh_bin`。

Python 这一实现要求显式 `dsh_home` 或非空 `DSH_HOME`，不会隐式落到 `~/.dsh`。不要把这个要求直接当成 TypeScript SDK 的相同默认行为：TypeScript 启动选项中的 `dshHome` 是可选的。

两种语言的客户端都负责进程与协议，Agent 继续在所启动的 dsh 运行时中执行。更换 Python 调用层，并没有新建一套 Python Agent 循环。

### 启动完成需要一次 `initialize` 握手

完整 [`sdk` patch](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/sdk-app/cordis.patch.yml)先挂载 `sdk-app-startup`，再让 JSON-RPC server 注入 `sdkAppStartup` 和 Loader。参数解析成功才发布 startup 服务；帮助路径不会按普通运行方式占用协议传输。

[`sdk-jsonrpc-server`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/sdk/server/src/index.ts#L76)处理 `initialize` 时，等待 Loader 当前树处理完毕。这样，异步加载的兄弟能力也能在第一条 prompt 前完成初始装配。

随后 [`HarnessSdkJsonRpcServer.initialize()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/sdk/server/src/server.ts#L154)解析工作目录，检查 provider/model 路由和可选推理强度、输出上限，成功后记录初始化状态。对于缺失的默认官方 provider，它还有挂载对应适配器的兼容分支；不能简化成“所有 provider 缺失都会以同一种方式失败”。

标准输出在这里属于协议帧，普通诊断写到标准错误。若额外插件往 stdout 打印调试文本，就会污染协议通道；即使传输实现会忽略部分畸形行，也不能将这种日志当成有效协议数据。这个限制会改变你为 SDK 组合插件时的日志选择。

### prompt 回执、运行结果和关闭是三个边界

[`prompt()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/sdk/server/src/server.ts#L195)取得或创建目标 Session 的 Agent，检查对象仍属于活跃 registry，构造用户消息，再调用 `followup()`。返回值是 `messageId`。

这个回执表明消息已被接收；后续执行通过 `session.event` 和 `session.status` 等通知继续报告。高层 [`DeepSeekHarness` API](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/sdk/client/src/api.ts)在协议上组织一次运行，等待相应的活动区间完成，再得到最终响应等结果。不能收到 prompt 回执就关闭子进程。

正常关闭时，客户端请求 `shutdown`。server 先刷出协议响应，再释放根 Context，使所拥有的 Agent、订阅与持久化资源进入停止状态，最后退出。SDK 应用层还将 stdin EOF 连接到共享退出请求；客户端关闭管道也有对应的生命周期处理。

SDK 子进程可以在多次运行之间保留。会话是否延续，还要看使用的 Session id 与持久数据位置；“复用进程”“复用会话”“复用 Harness home”分别影响运行时、对话身份和持久资源，不能混成一个开关。

### 高层 `run()` 怎样确定这一轮该收集哪些结果

以 TypeScript 的 [`HarnessSession.run()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/sdk/client/src/api.ts#L195)为例，它先完成初始化、建立通知订阅，再发送 prompt。建立订阅早于投递，可以保留紧接着出现的通知。

拿到 `messageId` 后，客户端在通知流里等待根 Session 的 `agent/inbox/spliced`，确认其中的 `inserted` 列表包含这条消息。它从这个入队事实开始收集，直到收到该根 Session 的 `idle` 状态。这里使用的是消息身份与 Session 状态，无法用“收到第一个 assistant chunk”代替完成条件。

收集时还有两个范围：`events` 只保存根 Session 的持久事件；`notifications` 可以包含根与已发现后代的通知。[`finalResponse()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/sdk/client/src/api.ts#L323)从根事件中倒序寻找最后一个 `assistant/message`，拼接其文本块。因此，子 Agent 的消息可以出现在通知中，却不会直接替换根 Agent 的最终文本。

Python 的 [`Session.run()`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/python/sdk/src/deepseek_harness/api.py#L149)采用相同的入队回执到 idle 区间，但两种语言的返回对象字段并不完全相同：

| 结果内容 | TypeScript | Python |
|---|---|---|
| 会话身份 | `sessionId` | `session_id` |
| 根会话最后一条 assistant 文本 | `finalResponse` | `final_response` |
| 根会话事件 | `events` | `events` |
| 根与已发现后代的通知 | `notifications` | `notifications` |
| 最后一个根 `turn/end` 的 kind | 此版本没有独立结果字段，从事件读取 | `finish_reason`，没有结束事件时为 `None` |

TypeScript 的字段以 [`RunResult` 定义](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/sdk/client/src/types.ts#L70)为准，Python 的结束类型由 `finish_reason()` 从根事件提取。不能把一个 SDK 的便利字段推成另一个 SDK 在此版本也有的 API。

如果直接使用低层协议，[`session/wait`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/sdk/server/src/server.ts#L221)观察一个已经存在、由 SDK 管理的根 Agent 及其后代活动；它不会创建未知 Session。高层 `run()` 上述实现通过通知区间收集结果，并非简单发送一次 `session/wait` 后就把它的响应当作最终文本。

## `sdk-minimal` 改变的是整份能力组合

[`sdk-minimal/cordis.patch.yml`](https://github.com/deepseek-ai/deepseek-harness/blob/d743267388641bc76f17c45ce8b4c231aed1d32c/packages/bundle/sdk-minimal/cordis.patch.yml)以一个完整 insert 明确列出 SDK 应用、模型适配器、Agent 核心、本地文件系统与进程服务、持久 shell、工作目录和 JSONL 会话持久化等行。它没有先加载 base 再逐项关掉。

因此，这两个 SDK profile 共享协议入口，但默认提供给 Agent 的能力不同：

| 比较项 | 完整 `sdk` | `sdk-minimal` |
|---|---|---|
| 配置来源 | base 上叠加 SDK 应用层 | 独立完整树 |
| 默认能力范围 | base 的工具、设置、凭据与策略等，再加 SDK 传输 | 显式列出的核心与本地执行能力 |
| 默认模型可用工具 | 取决于 base 的完整组合与覆盖 | 未配置 MCP 时，平台持久 shell 与 `working_directory` |
| 文件系统 | 继承 base 的提供者组合 | 挂载本地 fs 服务；没有因此自动注册 `read`、`edit` 等文件工具 |
| 会话存储 | 继承 base 组合 | 未压缩 JSONL |
| 配置 HMR | SDK patch 禁用 base 的 HMR 行 | 默认树不挂载 HMR |
| 额外修改 | profile、home 与启动 patch | 同样接受这些上层 patch |

“文件系统服务”和“模型能调用的文件工具”在第三篇已经区分。minimal 需要本地 fs 为运行时提供能力，不意味着它向模型公布了 `tool-fs` 的工具名单。类似地，看到某个内部服务行，也不能推断完整的产品功能与控制工具都已启用。

这份配置还将 `sandbox-policy` 的 `mode` 设置为 `danger-full-access`。小型组合并不代表更小的执行权限；shell 能访问什么，取决于进程本身可访问的资源和实际环境。它适合需要明确掌握配置内容的调用方，但不能仅凭 minimal 这个名称推断其有更强隔离。

## 沿入口排查问题，可以从哪里开始

假设同一条任务在 Web 中可以运行，而 SDK 在第一条 prompt 前失败。先区分失败发生在哪个边界，再决定读哪部分代码：

| 可观察现象 | 优先检查的边界 | 源码入口 |
|---|---|---|
| 程序将一个选项判为未知参数 | 启动器参数与应用参数的划分 | `apps/cli/src/args.ts` 与应用 startup |
| 某插件或服务没有出现 | manifest 选择、实际 layer、跳过诊断与包解析 | `profile-boot.ts`、`profile-context.ts` |
| Web 没有监听，或启动审查失败 | Web startup、依赖服务、Loader 审查 | `web-app/startup.ts`、`app-boot` |
| Desktop 窗口存在，Host 尚未 ready | 子进程启动与 Node IPC | `host-process.ts`、`desktop-host` |
| SDK 子进程存在，初始化失败 | 树处理结果、模型路由与协议握手 | SDK server 的 `initialize` 分支 |
| 任务进入 Agent 后才失败 | Turn、Step、模型与工具执行 | 第二篇中的请求链路 |

这些是由代码边界得到的排查顺序，没有测量各种故障出现的频率。实际还要结合错误内容与本次合成配置。

如果已经安装了对应版本，可以用 `--dump-default-config` 和 `--dump-config` 比较默认层与叠加后的配置行；输出中的 `!!js` 表达式尚未按启动上下文求值。它们不启动应用插件树，但准备 profile 仍可能创建或更新配置文件，所以不要把配置输出当作绝无写入的只读操作。`--dump-config-schema` 还会导入插件声明的 schema，也不能替代对未知插件的审查。

本次源码阅读采用下面的只读检索。工作目录为固定版本的仓库根目录；只需 Git 和 ripgrep，不需要模型凭据。它们分别找到模板、合成顺序、应用共享启动与传输实现：

```sh
git rev-parse HEAD
rg -n 'PROFILE_TEMPLATES' packages/boot/app-boot/src/profile.ts
rg -n 'readProfilePatches|context.overlays|telemetryPatch' packages/boot/app-boot/src/profile-context.ts
rg -n 'runProfile|provideCmdline|appReady.commit' apps/cli/src/profile-boot.ts
rg -n 'runProfile|resolvedProfile|args:' apps/desktop-host/src/index.ts
rg -n 'initialize|loader|shutdown' packages/sdk/server/src/index.ts
```

这些命令已在本文基线执行，核对到对应定义与调用位置。它们证明的是代码位置和组合关系，不是 Web、Desktop 或 SDK 已在本机成功运行。

## 接下来读 Context、Service 与依赖注入

入口追踪到这里，会反复遇到同一组操作：`new Context()`、`ctx.plugin()`、`ctx.provide()`、`inject`、`loader.await()` 和 `fiber.dispose()`。应用将配置交给它们，插件也靠它们取得依赖、等待启动与释放资源。

下一篇从 Context 与 Service 讲起：服务由谁注册，怎样在作用域中被找到，以及插件声明依赖后如何等待提供者。这样才能继续解释“配置行已经存在，为什么服务还不能用”。
