+++
title = "抽象的收益与代价：封装何时降低复杂度"
date = 2026-10-14T12:00:00+08:00
lastmod = 2026-10-14
draft = false
author = "Hex4C59"
description = "比较直接读取、查询函数和单纯转调，通过版本数据的结构变化，检查一层抽象隐藏了什么、保留了什么依赖，以及新增了什么成本。"
summary = "已有版本对象，再写查询函数是否多余？用两个调用者和一次内部结构变化，观察封装如何集中字段映射、何时只是增加跳转，并区分信息隐藏与对象冻结。"
tags = ["抽象", "信息隐藏"]
categories = ["engineering"]
source_kind = "original"
article_type = "concept"
series = ["software-design"]
series_role = "chapter"
series_order = 1
series_number = 1
series_part = "抽象、契约与依赖"
difficulty = "beginner"
ShowToc = true
+++

已有一个对象保存应用版本，再写一个查询函数，是否只是把一行代码变成了几行？

判断这层封装的收益，可以检查它集中处理了哪些细节，以及调用者是否因此少依赖一些会变化的决定。如果函数只为另一项操作增加了名称和跳转，当前需求下的收益就需要另找依据。这里用同一组版本数据比较三种实现，再改变内部数据结构，观察修改会传播到哪里。

本文面向能理解 JavaScript 对象、函数和模块导入的读者；函数值与调用的准备见[导读](/articles/software-design-00-reading-guide/)。案例没有文件读写、网络或跨进程通信。读完后，你应能为一层封装写出具体职责、维护代价和重新评估它的条件。

## 一份版本数据，两个调用者

假设演示应用“纸舟”需要一个关于页，显示 `纸舟 1.0.0`。之后又增加诊断导出，要求取得应用、Node.js 和 Electron 三个版本字段。诊断导出在这里仅生成对象，不写文件。

下面是 `direct.mjs` 的完整内容：

```js
export const appInfo = {
  version: "1.0.0",
  runtime: { node: "node-demo", electron: "electron-demo" },
  internalBuildTag: "demo-build",
};
```

这些值都是合成数据。`node-demo` 和 `electron-demo` 不代表本机版本，示例也没有加载 Electron。`export` 使其他模块可以导入 `appInfo`，所以调用者能直接访问它的属性。

初始需求只约定关于页文本和诊断对象中的三个字段，不约定两条路径返回同一个对象。后面比较查询方案时，会另外检查返回对象的身份和修改隔离，避免把“字段值相同”误写成“所有行为相同”。

### 直接读取

下面是从两个调用者文件摘出的相关代码；关于页函数位于 `about.mjs`，诊断函数位于 `diagnostics.mjs`，各文件都导入 `appInfo`：

```js
import { appInfo } from "./direct.mjs";

export function directAbout() {
  return `纸舟 ${appInfo.version}`;
}

export function directDiagnostics() {
  return {
    app: appInfo.version,
    node: appInfo.runtime.node,
    electron: appInfo.runtime.electron,
  };
}
```

只有关于页时，读取 `appInfo.version` 很容易理解。增加诊断调用者后，它也需要知道版本放在 `version` 与 `runtime` 下，还要把内部字段映射成要求的输出字段。

这套实现满足当前需求，源头也已经集中在一个对象里。暂时没有证据说明必须再加一层函数。需要继续检查的是：调用者共享了多少内部知识，这些知识是否值得集中管理。

### 由查询函数统一组装

下面是 `query.mjs` 的完整代码，和直接读取方案使用相同的数据：

```js
const appInfo = {
  version: "1.0.0",
  runtime: { node: "node-demo", electron: "electron-demo" },
  internalBuildTag: "demo-build",
};

export function getAppVersion() {
  return {
    app: appInfo.version,
    node: appInfo.runtime.node,
    electron: appInfo.runtime.electron,
  };
}
```

这个模块只导出 `getAppVersion`。通过正常的模块导入，调用者不能取得这里的 `appInfo` 绑定。它得到的是一个新组装的对象，字段名为 `app`、`node` 和 `electron`。

两个调用者的相关片段变为：

```js
import { getAppVersion } from "./query.mjs";

export function queryAbout() {
  return `纸舟 ${getAppVersion().app}`;
}

export function queryDiagnostics() {
  return getAppVersion();
}
```

诊断调用者省去了字段映射。关于页仍然要读取一个属性，还多调用了函数；对它而言，这层接口的价值主要取决于数据来源和结果约定能否保持分离。

维护者需要阅读 `getAppVersion` 的定义，理解它返回什么、何时读取数据、会不会失败；代码中多了一处需要命名和维护的实现。调用者能够忽略内部属性路径，但仍需知道公开的 `app` 等字段。

### 再包一层转调

假设又出现 `forward.mjs`：

```js
import { getAppVersion } from "./query.mjs";

export function queryVersion() {
  return getAppVersion();
}
```

调用者改用 `queryVersion()`，得到的仍是 `getAppVersion()` 新建的结果。这个包装没有增加字段选择、输入检查或错误处理；排查查询行为时，又多了一个需要追踪的函数。

对当前案例，我会保留字段组装的位置，省去这层转调。如果应用后来确实需要一个长期稳定的公共入口，而内部查询函数会独立替换，`queryVersion` 就可能承担边界职责。那时还要检查导出路径和实际依赖，确认调用者通过这个入口取得能力。判断这样的短函数时，需要具体说明它负责稳定哪条边界。

## 改变内部结构，看看谁必须跟着改

现在假设版本数据的内部组织发生变化：应用版本放进 `release`，运行时版本移到 `platform.versions`。版本值和对外需求保持不变。完整的新对象见 `direct-next.mjs`：

```js
export const appInfo = {
  release: { version: "1.0.0" },
  platform: {
    versions: { node: "node-demo", electron: "electron-demo" },
  },
  internalBuildTag: "demo-build",
};
```

原来的直接访问路径失效。关于页仍读 `appInfo.version`，会得到文本 `纸舟 undefined`；诊断函数继续读取 `appInfo.runtime.node`，因为 `runtime` 不再存在而抛出 `TypeError`。两个调用者都需要修改属性路径。

查询方案中，内部对象同样调整，但公开结果仍保持原样。`query-next.mjs` 中的函数改为：

```js
export function getAppVersion() {
  return {
    app: appInfo.release.version,
    node: appInfo.platform.versions.node,
    electron: appInfo.platform.versions.electron,
  };
}
```

这段摘录依赖同文件中的新对象定义。调用者仍然取得 `app`、`node`、`electron`，所以关于页和诊断函数不需要调整。转调方案也得到相同结果，因为底层查询函数已经处理了变化。

| 比较项 | 直接读取 | 查询函数组装 | 查询函数加转调 |
| --- | --- | --- | --- |
| 调用者依赖的结构 | 内部对象的属性路径 | 查询结果的字段 | 同样的查询结果字段 |
| 字段映射的位置 | 需要这些字段的调用者 | `getAppVersion` | 仍在 `getAppVersion` |
| 本次布局变化要修改哪里 | 数据源、关于页、诊断调用者 | 查询模块内的数据与映射 | 查询模块内的数据与映射 |
| 定位取值过程要追踪什么 | 调用者与数据源 | 调用者、查询函数与私有数据 | 还需经过 `queryVersion` |

这个比较只描述给定源码中的依赖和修改位置。它没有测量阅读时间，也没有把多一次调用换算成性能损失。

对于这项已经明确的内部布局变化，查询函数把属性路径调整集中到了一个模块。如果版本数据一直稳定，而且只有一处读取，集中处理带来的收益就小得多。调用者数量增加，本身也不足以证明需要封装；还要看它们是否共同依赖了值得隐藏的决定。

## 这层接口具体隐藏了什么

这里的**信息隐藏**，指把某项设计决定留在负责它的模块内部，让其他模块通过约定的能力工作。本例隐藏的是版本数据的内部路径，以及把这些路径转换成公开字段的规则。

Parnas 在 1972 年的论文[《On the Criteria To Be Used in Decomposing Systems into Modules》](https://www.cs.lafayette.edu/~gexia/cs301/resources/parnas.html)中比较两种模块划分。在 “The Criteria” 和结论部分，他提出围绕难以决定或可能变化的设计决定组织模块，让接口尽量少透露内部工作方式。本文把这个分析视角用于一个小例子：先指定内部布局变化，再追踪哪些模块知道这套布局。论文中的系统与本例规模不同，不能据此断言某个真实项目的每个查询函数都值得保留。

如果模块一边导出查询函数，一边继续导出原始 `appInfo`，调用者仍然可以依赖内部路径。是否形成了这条边界，需要继续检查实际导入和使用；仅增加函数还不足以说明已经隔离变化。示例中的查询模块因此只导出操作。

John Ousterhout 在 2008 年的公开讲义[“Designing Abstractions”](https://web.stanford.edu/~ouster/CS349W/lectures/abstraction.html)中，用简单接口能够隐藏多少实现复杂度来讨论抽象的价值，也指出接口本身会增加需要理解的内容。本例据此检查两处新增函数：`getAppVersion` 承担字段选择和映射，`queryVersion` 在当前需求中只转交结果。这个判断针对所列职责；给后者增加实际的兼容或权限边界后，需要重新比较。

接口也留下了新的依赖。假如需求把公开字段 `app` 改为 `application`，关于页和诊断结果的使用者仍要检查和修改。假如读取改为网络请求，原来的同步返回是否还能保持，也要重新约定。查询函数可以限制内部结构变化的传播，但公开结果与调用方式仍属于调用双方共同依赖的部分。下一篇会沿着这些约定讨论契约。

## 不直接暴露数据，还要检查对象是否共享

查询函数每次创建新对象，当前返回的三个字段都是字符串。调用者修改结果中的 `app`，不会改写内部版本数据。下面的片段在 `query.mjs` 旁运行：

```js
import { getAppVersion } from "./query.mjs";

const first = getAppVersion();
const second = getAppVersion();
console.log(first === second); // false

first.app = "caller-edit";
console.log(getAppVersion().app); // 1.0.0
```

这个结果对象可以修改。它与内部数据分离，依赖的是重新组装结果和返回字符串值；这里没有冻结对象。

如果函数改为直接 `return appInfo`，调用者拿到的就是内部对象。若改为 `return { runtime: appInfo.runtime }`，新建的外层对象仍然引用原来的嵌套对象。此时“返回一个对象”这句话无法说明修改是否会互相影响，需要沿引用继续检查。

`const` 也不禁止修改对象属性。下面的完整例子可以独立运行：

```js
const info = { runtime: { node: "before" } };
info.runtime.node = "after-const";

Object.freeze(info);
info.runtime.node = "after-freeze";
console.log(info.runtime.node); // after-freeze
```

`const` 限制 `info` 绑定重新赋值。`Object.freeze(info)` 固定的是 `info` 自身的属性；这里并没有递归冻结它所引用的 `runtime`。冻结与模块导出分别影响可写性和访问方式，需要分开核对。示例包的 `freeze.mjs` 还检查了外层写入被拒绝，以及单独冻结 `runtime` 后嵌套写入被拒绝的情况。

这些语义可对照 ECMAScript 工作稿的[不可变绑定操作](https://tc39.es/ecma262/multipage/executable-code-and-execution-contexts.html#sec-declarative-environment-records-setmutablebinding-n-v-s)、[`Object.freeze`](https://tc39.es/ecma262/multipage/fundamental-objects.html#sec-object.freeze) 与 [`SetIntegrityLevel`](https://tc39.es/ecma262/multipage/abstract-operations.html#sec-setintegritylevel)。截至 2026-10-14，在线页眉标为 ECMAScript 2027 工作稿；这里引用具体算法，并用下述运行环境检查本例行为。

## 运行完整比较

下载[第 01 篇完整示例包](software-design-01-examples.zip)，解压得到 `software-design-01-examples` 目录。在它的上一级目录执行：

```sh
cd software-design-01-examples
node --version
node demo.mjs
node --test check.test.mjs
node freeze.mjs
```

核验环境为 2026-10-14、macOS arm64、Node.js v25.9.0。代码仅使用 Node.js 内置模块，无第三方依赖；未验证其他 Node.js 版本。

`demo.mjs` 的实际输出为：

```text
direct {"about":"纸舟 1.0.0","diagnostics":{"app":"1.0.0","node":"node-demo","electron":"electron-demo"}}
query {"about":"纸舟 1.0.0","diagnostics":{"app":"1.0.0","node":"node-demo","electron":"electron-demo"}}
forward {"about":"纸舟 1.0.0","diagnostics":{"app":"1.0.0","node":"node-demo","electron":"electron-demo"}}
```

`node --test check.test.mjs` 运行 6 项检查，本次全部通过。检查覆盖初始输出、查询模块的导出、同步结果与对象身份、修改返回字段后的隔离，以及内部布局变化后的调用行为。迁移检查把文件复制到独立临时目录，替换为两个 `*-next.mjs` 数据模块，确认查询调用者和转调文件保持原样；直接访问的两个调用者出现前述失败，分别调整属性路径后恢复预期结果。临时目录在测试结束后清理。

`freeze.mjs` 输出三行：

```text
const: binding fixed, nested write allowed
freeze: outer write rejected, nested write allowed
freeze nested: nested write rejected
```

测试入口和判定方式见[对应版本的 Node.js 测试运行器文档](https://nodejs.org/download/release/v25.9.0/docs/api/test.html)。这些检查提供给定案例的行为证据。异步来源、外部坏输入、真实 Electron 集成和性能均未覆盖。

## 给选择写出条件

在当前案例中，如果只需要一处读取稳定的版本对象，我会采用直接访问。已明确需要隔离内部布局变化、并统一多个调用者的字段映射时，我会让查询模块只导出 `getAppVersion`，保留同步返回和三个公开字段的约定。对于只转调的 `queryVersion`，目前没有额外职责支撑保留它。

可以用一个变式检查自己是否掌握了这个判断方法：增加“复制应用版本”按钮，它只需要应用版本字符串。先用直接读取实现，再用查询结果实现；随后把内部版本移到 `release.version`，记录各自的修改位置。最后写一段选择说明：你希望隐藏哪项决定，新增调用者仍需知道什么，以及什么需求会让你改变方案。

如果按钮需要的字符串格式和诊断导出的字段开始独立变化，继续检查现有查询函数是否同时承担了两类不同约定。[第 02 篇：接口与契约](/articles/software-design-02-contracts/)将继续讨论输入、结果、错误和副作用各自需要说明到什么程度。
