+++
title = "错误传播与异步边界：需要等待时，成功和失败怎样交回来"
date = 2026-10-15T00:00:00+08:00
lastmod = 2026-10-15
draft = false
author = "Hex4C59"
description = "沿用任务保存例子，解释 Promise、async、await 与错误传播，比较正常失败结果和拒绝、缺少等待与局部捕获，并处理等待期间的第二次修改。"
summary = "保存函数返回以后，文件操作可能还没结束。先分清 Promise 与任务结果，再追踪等待、拒绝、错误转换和状态采用，观察为什么只补 await 仍可能覆盖任务，以及 busy、finally 分别承担什么。"
tags = ["异步编程", "Promise", "错误处理"]
categories = ["engineering"]
source_kind = "original"
article_type = "concept"
series = ["software-design"]
series_role = "chapter"
series_order = 6
series_number = 6
series_part = "模块、状态与行为保持"
difficulty = "beginner"
ShowToc = true
+++

待办事项程序准备好一份新任务数据，保存正常结束后，再把它作为当前数据。[上一篇](/articles/software-design-05-state-effects/)用这条顺序解释了状态与副作用，也指出保存失败时，内存没有改变，不代表文件必然没有改变。

当时还有一个条件：保存函数在返回之前完成所有工作。现在改用另一种文件接口，它先交回一个表示未来结果的对象，文件工作结束后再报告成功或失败。原来的几行调用还能保留“保存后才采用”的顺序吗？

本文的选择是：让完成任务的接口明确返回 Promise，调用者等待其中的操作结果；任务模块在保存结束之后才采用新数据，并规定等待期间怎样处理第二次修改。保存错误只在负责转换它的位置转换，其他错误继续交给能够处理它的代码。

**异步操作**指结果不一定能在发起调用时取得，需要通过之后的通知继续处理。JavaScript 的 **Promise** 是用来表示一项操作最终结果的对象。**异步边界**在本文中指一处使用方式的变化：调用者从这里开始，需要等待结果，或把后续处理交给 Promise，而不能继续把函数的直接返回值当成最终任务结果。

我们继续使用写周报和整理笔记两条任务，编号为 `t1`、`t2`，初始都未完成。`completed` 表示完成状态，结果中的 `ok` 表示操作是否成功，`changed` 表示本次是否改变任务。正文先解释必要写法，再比较错误、等待和第二次请求，最后用完整实现、受控保存与真实临时文件检查行为。

## 上一篇的顺序，依靠了什么条件

上一篇保存代码的关键部分是：

```js
const saveResult = saveSnapshot(copyTasks(proposal.nextTasks));
if (saveResult !== undefined) {
  return { ok: false, reason: "save-failed" };
}
tasks = proposal.nextTasks;
```

这是上一章实现中的局部片段，不是独立文件。`proposal.nextTasks` 是计算产生的新任务数据，`copyTasks` 为保存函数准备副本，`tasks` 是所有者认可的当前数据。

当时约定保存成功不交回额外数据，也就是返回 `undefined`；保存失败抛出错误，由外面的 `catch` 转成 `save-failed`。保存返回后，才执行最后一行采用。

如果新的保存函数交回 Promise，上一章的额外返回值检查会拒绝它。这反映了接口约定已经不同。直接删掉检查也不够：后面的采用语句会继续执行，无法凭调用顺序证明文件已经保存。

函数调用仍然是一次调用，但“这次调用已经交回”和“它发起的保存已经结束”成为了两件事。我们需要说明怎样取得第二件事的结果。

## Promise 交回时，里面的结果可能还没有确定

Promise 有三个需要认识的状态：

| Promise 的状态 | 在这里怎样理解 |
| --- | --- |
| `pending`，待定 | 尚未报告最终结果 |
| `fulfilled`，已履行 | 正常结束，提供一个结果值 |
| `rejected`，已拒绝 | 以错误原因结束 |

这里“履行”只说明 Promise 正常交回了某个值，并不自动说明任务操作成功。那个值可能正是 `{ ok: false, reason: "not-found" }`。

Promise 最终状态一旦确定，就不会再从履行改成拒绝，或者反过来。后面登记的处理可以读取这个结果；Promise 本身并不是一份会不断更新的任务列表。

正文有时使用 `pending` 作为变量名，表示正在等待的结果；有时一个 Promise 在变量被取得时已经确定，使用方式仍然相同。语言行为可以对照 TC39 的 [Promise 对象说明](https://tc39.es/ecma262/multipage/control-abstraction-objects.html#sec-promise-objects)。实际写作判断与本例结果仍通过后面的运行检查来验证。

## async 改变了函数交回结果的方式

`async` 写在函数前面，表示这个函数交回 Promise。函数正常 `return` 的值，成为这个 Promise 正常结束后的结果；函数内部没有处理的抛错，成为它的拒绝原因。

先看一个只返回任务失败的短例子：

```js
async function returnTaskFailure() {
  return { ok: false, reason: "not-found" };
}

const pending = returnTaskFailure();
console.log(pending.ok);
```

输出是 `undefined`。函数虽然在第一行就能算出失败结果，直接交回的仍然是 Promise。`pending` 上没有任务结果对象的 `ok` 字段。

把整个 Promise 放进 `if` 也不能判断操作成功。在本例中，它作为对象被当作真值，无论最终结果里的 `ok` 是 `true` 还是 `false`。这与第二篇提到的“把结果对象当布尔值”类似，现在又增加了等待结果这一步。

声明为 `async` 也不表示整个函数从调用第一刻就移到了别的线程。它会先执行到需要等待的位置，或直接结束。单纯增加这个关键字，不会把耗时计算自动移出当前执行过程。

## await 取得结果，拒绝时在等待位置交出错误

`await` 用在可等待的值前面，表示当前函数的后续步骤需要这个结果。Promise 正常履行时，取得其中的值；Promise 拒绝时，在等待位置产生错误，让周围的错误处理有机会接住它。

下面可以接在前面的短例子之后运行：

```js
const result = await pending;
console.log(result.ok);
```

此时输出 `false`。我们先取得任务结果，再根据结果决定提示什么。示例使用 `.mjs` 文件，Node.js 允许在这种模块的顶层使用 `await`；在普通函数内部需要先让该函数成为 `async`。

`await` 暂停的是当前函数后面的步骤，不是让整个程序都停止。等待保存时，其他调用仍可能读取列表，或者再次提出修改。这也是为什么后面必须讨论状态使用方式。

即使等的是已经正常履行的 Promise，或者当前同步函数返回的 `undefined`，`await` 后面的代码也会在让出执行机会后继续。语言规范通过 [Await 抽象操作](https://tc39.es/ecma262/multipage/control-abstraction-objects.html#await)描述这一过程。我们会用不依赖延迟时长的检查观察执行顺序。

## .then 怎样表达后续处理

不使用 `await` 时，也可以把后续函数交给 Promise 的 `.then`：

```js
returnTaskFailure().then(function handleResult(result) {
  console.log(result.ok);
});
```

`handleResult` 是之后接收正常结果的函数。它不是在登记 `.then` 时立即执行；等 Promise 正常结束后，才取得结果并执行。

这个例子同样打印 `false`。没有进入拒绝处理，是因为函数正常交回了一份任务失败结果。需要处理 Promise 拒绝时，可以使用 `.catch`，或者在 `await` 周围使用 `try`、`catch`。

`.then` 和 `.catch` 本身也交回 Promise，后续函数里如果又发起工作，仍要决定是否把那项工作交回、等待或单独管理。本篇主要使用 `await`，让保存、采用、清理的顺序能够沿着代码逐行阅读。

## 普通抛错与 async 函数的拒绝，在哪一处收到

先看两种函数：

```js
function regularFailure() {
  throw new Error("普通函数错误");
}
async function asyncFailure() {
  throw new Error("异步函数错误");
}
```

`throw` 让正常执行中断并交出错误，`new Error` 创建带说明文字的错误对象。使用普通函数时，外层同步 `try`、`catch` 能直接接到抛错：

```js
try {
  regularFailure();
} catch (error) {
  console.log(error.message);
}
```

但 `asyncFailure()` 把内部错误放进交回的 Promise。即使错误发生在第一个 `await` 之前，它也不会从这次普通调用位置同步抛出来。需要处理那个 Promise，或者等待它：

```js
const pendingFailure = asyncFailure();
try {
  await pendingFailure;
} catch (error) {
  console.log(error.message);
}
```

`promise-basics.mjs` 和 `basics-demo.mjs` 保留了完整对照。普通函数在调用处抛错，异步函数在等待处收到拒绝，这会改变调用者原来的错误处理位置。

这里要区分函数边界。创建任务列表的 `createAsyncTaskList` 是普通函数，传入错误的保存接口时，它会同步抛出 `TypeError`；返回对象中的 `completeTask` 才是异步函数。不能仅因为它们位于同一个文件，就把错误方式当作相同。

## 没有 await，catch 为什么没接住保存失败

下载包的 `without-wait.mjs` 是一个故意遗漏等待的反例。下面节选其完成操作的关键部分，假设新数据已经计算好：

```js
try {
  saveSnapshot(copyTasks(proposal.nextTasks));
} catch {
  return { ok: false, reason: "save-failed" };
}
tasks = proposal.nextTasks;
return proposal.result;
```

如果保存函数在调用当场就抛错，这个 `catch` 能接住。但保存函数交回 Promise、稍后才拒绝时，这段调用已经正常结束，代码也已经采用新数据并报告成功。

`failure-demo.mjs` 用手动控制的保存结果观察这件事：先让反例报告完成，再让保存拒绝。输出为：

```text
缺少等待时提前交回： {"ok":true,"changed":true,"task":{"id":"t1","title":"写周报","completed":true}}
保存尚未结束时的任务： true
单独观察到的保存失败： 稍后才报告的失败
失败后已采用的数据： true
```

这里的“单独观察”来自演示额外接到原保存 Promise 的 `.catch`。正式反例丢弃了这个 Promise，不能把这种额外观察算作它自身处理了错误。演示这样安排，是为了看清拒绝并让失败有明确去处。

没有等待的代码仍然按写下来的顺序执行了。问题在于保存调用交回 Promise 后，后面没有任何一步负责等它结束。`try` 的代码范围不能替一个被丢开的未来结果自动建立错误关系。

## 直接 return Promise，与 return await 的区别

有时函数最后一行只需要把另一项异步工作交给调用者。直接 `return` 那个 Promise，外层 Promise 会跟随它的最终结果，这可以满足单纯转交的需要。

但如果当前函数希望在本地捕获拒绝，就要检查错误处理与等待的位置。下面是两个完整的小函数，保留在 `promise-basics.mjs` 中：

```js
async function returnWithoutAwait(saveSnapshot) {
  try {
    return saveSnapshot();
  } catch {
    return "这里捕获了错误";
  }
}

async function returnWithAwait(saveSnapshot) {
  try {
    return await saveSnapshot();
  } catch {
    return "这里捕获了错误";
  }
}
```

假设 `saveSnapshot()` 交回一个会拒绝的 Promise。第一种写法在 `try` 里完成的是调用与转交，稍后的拒绝继续传到它的调用者，局部 `catch` 没有因此执行。第二种写法在 `try` 内等待，拒绝在等待位置产生错误，局部 `catch` 能转换它。

`basics-demo.mjs` 对这两种情况分别观察，得到：

```text
直接 return 的拒绝到外层： 保存拒绝
return await 的局部结果： 这里捕获了错误
```

如果保存函数根本没有交回 Promise，而是在调用时立即抛出同步错误，第一种局部 `catch` 仍然可以接住。比较时需要说明是哪一条错误路径，不能只记“有 `return` 就捕获不到”或者“加了 `async` 就能处理”。

同样，当前函数还有清理工作时，需要决定清理应发生在转交结果之后，还是等待结果结束之后。后面的任务实现选择等保存结束，再释放忙碌状态。

## 先明确异步任务接口新增了哪些规则

要保持上一篇的任务结果，需要把等待方式也写进契约。**契约**就是代码双方依靠的条件与行为约定；现在不仅要说明结果字段，还要说明何时取得它、错误怎样到达。

本例的 `listTasks()` 仍然立即交回当前任务副本，`completeTask(id)` 则总是交回 Promise。调用者通过 `await` 或 Promise 的后续处理取得任务操作结果。

| 情况 | 本例完成操作最终交回什么 |
| --- | --- |
| 空闲时编号非法 | 正常履行，值为 `invalid-id` 失败结果 |
| 空闲时任务不存在 | 正常履行，值为 `not-found` 失败结果 |
| 已经完成的任务 | 正常履行，成功且 `changed: false`，不保存 |
| 保存成功且结果符合保存接口 | 采用新任务，正常履行成功结果 |
| 保存抛错或其 Promise 拒绝 | 不采用新任务，正常履行 `save-failed` 失败结果 |
| 当前已有一项修改等待保存 | 正常履行 `busy` 失败结果，不接收第二项修改 |

表中 `invalid-id` 等名称简写了 `{ ok: false, reason: ... }`。这些预期失败都通过正常结果表达，所以调用者等待结果后仍须检查 `ok`，不能只处理 Promise 拒绝。

`busy` 表示当前所有者正在处理修改。我们选择先检查忙碌状态，因此等待期间再交入错误编号，也先得到 `busy`。这个检查顺序属于本例行为，新增后调用者需要理解它。

保存函数现在应返回正常结果为 `undefined` 的 Promise，表示等待结束且没有额外数据。为了兼容简单保存函数，立即返回 `undefined` 也可用。额外结果被拒绝；调用保存时抛出的错误与其 Promise 的拒绝，都转成 `save-failed`。

初始任务仍须合法且编号唯一。保存函数应正确保存副本，不在内部等待同一任务列表的另一项修改。我们没有让它处理任意外部对象、后台进度或多处写入，保存接口需要在这些条件下配合。

## 为什么只补 await 仍可能覆盖任务

等保存结束再采用新数据，解决了提前报告成功的问题。但等待让同一所有者有机会收到下一次请求，原来的内存数据在这期间仍然保留旧值。

`without-busy.mjs` 是第二个反例：它正确等待保存，却允许两项完成操作都开始计算。

第一项完成 `t1`，根据 `[false, false]` 准备 `[true, false]`；它还没结束时，第二项完成 `t2`，也根据旧数据准备 `[false, true]`。这里数组仅表示两条任务的完成标记。

如果两项保存依次结束，各自都采用自己准备的数据，输出会是：

```text
第一项保存结束： [true,false]
第二项保存结束： [false,true]
```

第一项确实一度完成，后来却被第二份基于旧状态的数据盖掉。没有同时执行两段 JavaScript 语句，也能出现这种逻辑上的重叠：两项工作在不同等待位置交错推进。

这类先后次序影响最终结果的问题，通常称为**竞态**。本例的具体问题是两份建议都依靠同一份旧数据，后来按各自结果完整覆盖当前状态。仅有 `await` 不会替任务所有者协调这项共享数据。

文件接口也需要考虑重叠写入。Node.js 的 [Promise 文件接口](https://nodejs.org/download/release/v25.9.0/docs/api/fs.html#promises-api)提醒调用者协调对同一数据的修改；文档不会自动替应用决定哪条任务进度才是当前版本。

## 本例先选择：等待时拒绝第二项修改

一种容易说明的策略，是一项修改未结束时，拒绝新修改，等前一项最终结果确定后再接受。我们用 `busy` 保存这个状态，不让第二项操作先计算旧任务。

`busy` 不是 JavaScript 提供的跨进程锁，只是同一个任务对象内部的布尔标记。它会在完成函数第一次等待前设为 `true`，其他调用进入同一个对象时就能观察到它。

读取列表仍然允许，返回的是尚未采用修改的旧任务。页面如果还需要显示“正在保存”，可以另外根据它发出的 Promise 是否已经结束来安排；本例没有实现真实页面。

被拒绝的请求不会自动排队，也不会后来自行重试。调用者收到 `busy` 后需要决定如何提示或何时再次提出请求。等第一项结束后重新提交，才会基于新状态计算第二项。

其他策略包括把请求排队、对更新附加版本检查，或让某类独立修改可以合并。它们都有新的规则与成本。本篇实现拒绝策略，是为了用短代码把等待期间的行为说完整，没有宣称它适合所有界面交互。

## 完整实现：等待保存，再采用并释放状态

`async-task-list.mjs` 保留上一篇的初始数据、复制函数和完成计算，只改变所有者怎样等待、采用和接受下一项操作。完整代码如下：

```js
import { defaultTasks } from "./initial-tasks.mjs";
import { copyTasks } from "./copy-tasks.mjs";
import { planCompletion } from "./plan-completion.mjs";

export function createAsyncTaskList(saveSnapshot, initialTasks = defaultTasks) {
  if (typeof saveSnapshot !== "function") {
    throw new TypeError("需要提供保存函数");
  }
  let tasks = copyTasks(initialTasks);
  let busy = false;
  function listTasks() {
    return copyTasks(tasks);
  }
  async function completeTask(id) {
    if (busy) {
      return { ok: false, reason: "busy" };
    }
    busy = true;
    try {
      const proposal = planCompletion(tasks, id);
      if (proposal.result.ok === false || proposal.result.changed === false) {
        return proposal.result;
      }
      try {
        const saveResult = await saveSnapshot(copyTasks(proposal.nextTasks));
        if (saveResult !== undefined) {
          return { ok: false, reason: "save-failed" };
        }
      } catch {
        return { ok: false, reason: "save-failed" };
      }
      tasks = proposal.nextTasks;
      return proposal.result;
    } finally {
      busy = false;
    }
  }
  return { listTasks, completeTask };
}
```

先看外层。完成函数检查 `busy`，接受操作时把它设为 `true`。无论后面是正常成功、输入失败，还是发生未处理错误，离开这次 `try` 时都执行 `finally`，把标记设回 `false`。

**finally** 是错误处理语法中的清理部分，在当前 `try` 离开前执行。这里依靠它避免某次保存失败以后，所有后续请求都一直得到忙碌结果。没有在 `finally` 里 `return`，以免覆盖原本要交回的结果或错误。

再看保存附近的内层 `try`。`await saveSnapshot(...)` 确保在取得保存结果前，不会走到 `tasks = proposal.nextTasks`。保存调用同步抛错，或 Promise 拒绝，都会在这处转成 `save-failed`。保存正常结果不是约定的 `undefined`，同样拒绝采用。

保存以外的计算和采用没有放进这个内层 `catch`。如果这些位置出现需要暴露的程序错误，它会让完成 Promise 拒绝，外层清理仍然执行。这样不会仅因为代码处在同一个函数里，就把任意错误都标成保存失败。

内层捕获也有范围：保存函数自己存在程序错误时，它的抛错或拒绝同样会在这里被转换，简单的 `reason` 不能说明根因。真实维护需要保留能够诊断的错误信息；本例集中展示给使用者的结果路径，没有实现日志系统。

## 沿一次调用，区分返回、等待与完成

`waiting-demo.mjs` 发起第一项修改，暂不让保存结束，然后立即观察列表和第二项请求。输出为：

```text
调用已交回 Promise： true
等待时 t1： false
等待时完成 t2： {"ok":false,"reason":"busy"}
t1 的最终结果： {"ok":true,"changed":true,"task":{"id":"t1","title":"写周报","completed":true}}
保存后当前标记： [true,false]
再次提交 t2 后： [true,true]
```

第一次调用先完成编号与任务计算，设置忙碌标记，发起保存，遇到 `await` 后把 Promise 交给调用者。此时内存还是旧数据，所以列表显示 `t1` 未完成。

第二次修改进入同一个所有者，看到 `busy` 就交回失败结果，不会调用保存。等演示明确报告第一次保存成功，先前等待的位置才继续，采用新数据、释放标记，第一项完成 Promise 也正常交回任务结果。

再次提交 `t2` 时，读到的已经是 `t1` 完成后的数据，因此得到 `[true, true]`。这与前面两项都基于旧数据计算的反例不同，改变的是接受操作的时机。

这套状态是同一个对象内部的选择。其他独立任务对象仍可能写向同一文件，别的进程也不会因为这个 `busy` 自动配合。第五篇里的两个所有者问题没有因此被解决。

## 调用者要同时处理结果失败与 Promise 拒绝

界面原来可能写 `const result = taskList.completeTask("t1")`，然后检查 `result.ok`。异步接口出现后，这里需要等待，并让外围代码知道这一等待会交出 Promise。

下面是使用方式的示意片段，假设位于一个 `async` 函数内，`taskList` 已经创建。它只打印提示，没有实现真实页面：

```js
let result;
try {
  result = await taskList.completeTask("t1");
} catch (error) {
  console.log("操作未能正常交回结果：", error.message);
  return;
}

if (result.ok === false) {
  console.log("任务未完成：", result.reason);
  return;
}
console.log("任务完成，是否有新变化：", result.changed);
```

等待正常结束之后，仍然可能得到 `busy`、`save-failed`、`not-found` 等失败结果。`catch` 处理的是 Promise 拒绝，它不会因为对象里的 `ok` 为 `false` 而自动执行。

提示代码放在等待的错误处理范围之外，也有具体含义：任务已经成功保存并采用，随后显示提示出错，不能把它重新说成保存失败。测试单独观察了这条路径，任务状态不会因后来的显示错误自动恢复。

如果外层还有请求分发函数，它也需要约定交回什么。可以继续把完成 Promise 返回给使用者；需要在本层转换拒绝、执行清理或检查最终结果时，则要在这里等待并安排错误范围。增加一个包装函数，不会自动完成这些决定。

## 用可控制的保存，观察顺序而不猜时间

为了检查等待期间的行为，示例没有依靠“过几十毫秒应该已经保存”这样的假设。`controlled-save.mjs` 返回一个保存函数，并把每次调用的完成按钮留给测试与演示。

```js
export function createControlledSave() {
  const calls = [];
  function saveSnapshot(tasks) {
    return new Promise(function createPending(resolve, reject) {
      calls.push({ tasks, succeed: resolve, fail: reject });
    });
  }
  return { calls, saveSnapshot };
}
```

`new Promise` 创建一个 Promise，同时执行用于安排结果的函数。这里的 `resolve`、`reject` 是构造过程交给我们的两个函数。在本例中，调用 `succeed()`，表示以 `undefined` 正常结束；调用 `fail(error)`，表示拒绝并交出错误。

`calls` 是演示记录，不属于正式任务接口。它保留每次保存收到的任务副本，供测试先查看输入，再决定什么时候报告成功或失败。保存不接真实文件，操作结果完全由这次检查控制。

例如测试先调用完成任务，确认旧数据仍在、第二项收到忙碌；再让保存结束，最后等待完成 Promise 并检查新数据。它检查的是顺序与状态，而不是机器快慢。

这种控制也能重复触发拒绝、重试和覆盖，不需要故意让磁盘或网络不稳定。它没有证明真实文件写入正确，所以本篇还保留了单独的文件检查。

## 接上真正的 Promise 文件接口

Node.js 的 `node:fs/promises` 提供返回 Promise 的文件操作。`file-demo.mjs` 在系统临时目录中创建本次专用目录，保存任务，再读回核对。

保存函数的核心片段如下；这里的 `file` 指向本次临时文件，完整导入与清理都在示例包中：

```js
const taskList = createAsyncTaskList(function saveSnapshot(tasks) {
  return writeFile(file, JSON.stringify(tasks));
});
const result = await taskList.completeTask("t1");
```

`JSON.stringify` 把任务数组转成 JSON 数据文本，`writeFile` 交回保存 Promise。任务所有者等待它结束后，才采用新任务。正常写入和缺少父目录的失败分别输出：

```text
真实文件结果： {"ok":true,"changed":true,"task":{"id":"t1","title":"写周报","completed":true}}
读回的 t1： true
路径错误结果： {"ok":false,"reason":"save-failed"}
失败后内存 t1： false
```

文件测试核对了真实路径错误代码 `ENOENT`，也检查等第一项结束再提交第二项时，文件中保留两条任务的完成状态。演示只操作自己新建的目录，正常结束在 `finally` 中等待删除，不读取使用者已有任务文件。

测试还主动构造“完整写入后再抛错”。等待能让所有者观察到拒绝，但文件已经改过，内存保留旧数据，二者仍可能不同。这是保存函数执行后再报告错误的合成情况，不是对系统中途故障的实测。

异步接口改变了如何等待与接收错误，没有自动增加第五篇尚未具备的文件恢复保证。目录、文件替换和重新读取的整体设计，仍需在持久化篇继续讨论。

## 错误沿哪一条路径交回

**错误传播**指一处工作失败后，错误或失败信息怎样沿着使用关系到达能够处理它的代码。在异步程序里，需要分清原始拒绝、等待位置收到的错误，以及模块选择交回的任务结果。

以真实路径不存在为例，可以沿四步读：文件接口的 Promise 拒绝；任务所有者在保存处等待，收到错误；局部 `catch` 把它转换为 `save-failed`；使用任务的代码正常取得这份失败结果，再决定怎样提示。

发生转换后，完成任务的 Promise 是正常履行的。外层只登记 `.catch`，不会收到已经转成正常值的 `save-failed`。这也解释了为什么语言层面的“正常结束”和功能层面的“成功完成”需要分别表达。

如果计算阶段在保存的 `try` 之外出现程序错误，路径就不同：完成 Promise 拒绝，调用者在自己的等待处收到错误。保存错误处理不应把它也改名为文件保存失败，因为执行位置和责任已经不同。

还可以观察转换之后的值。例如一个 `.catch` 处理函数只打印错误，没有重新抛出或交回失败信息，它正常结束时，后续 Promise 会以 `undefined` 正常履行。这个处理让拒绝结束了，却没有给下一段代码留下足够的任务结果。需要继续处理的工作，应当明确约定接下来取得什么。

本篇没有为任意错误建立统一包装。预期任务失败使用结果对象，保存接口的抛错或拒绝在保存附近转换，其他位置的错误继续传到调用者。能说明每种情况走哪条路径，比把所有错误都放进同一个大 `catch` 更容易判断执行到了哪里。

## 等待一直不结束时，finally 会不会自动释放

`finally` 在当前 `try` 离开时执行。保存 Promise 如果一直待定，代码就仍停留在等待中，尚未离开这次操作，忙碌状态也不会自动释放。

这是当前实现的实际条件：保存函数需要最终报告结果。`await` 不会自动附带期限，Promise 也不会仅因为调用者已经不想等，就撤销先前发起的文件操作。

假设以后给界面增加“等待超时”。界面先停止显示等待，与底层保存真的停止，是不同事实。如果仅在一段时间后释放 `busy`，原保存稍后仍然成功，先前那份任务建议可能再次参与状态采用，新的修改也可能正在执行。

所以，期限、取消和过期结果的处理需要共同设计：谁能要求停止、保存接口是否支持停止、报告超时后是否还接受旧结果。它们会改变本篇接口和状态规则，不能用一个提示文字代替。

本篇没有实现超时与取消，也没有用未结束 Promise 伪装成操作已经终止。只有在所列保存函数最终正常结束或拒绝的条件下，才会执行清理并允许下一项修改。

## 从同步改为异步，哪些使用代码需要一起改

数据结果里的字段可以保持相同，取得结果的方式却发生了变化。把原来普通函数直接改成 `async`，会影响依靠即时结果的使用者。

| 使用位置 | 需要重新检查什么 |
| --- | --- |
| 直接完成任务的代码 | 是否等待后才读 `ok`、`changed` 与任务字段 |
| 请求分发函数 | 是把 Promise 转交出去，还是需要在本层等待并处理结果 |
| 原来的 `try`、`catch` | 捕获的是同步抛错，还是已经观察异步拒绝 |
| 操作结束后的提示与读取 | 是否在保存及采用结束后执行 |
| 清理与忙碌标记 | 是否一直覆盖等待期间，所有结束路径是否释放 |
| 同一个所有者的新请求 | 等待时拒绝、排队还是采用其他策略 |

创建函数仍然可以保持同步，因为它只是准备数据和保存接口；读取列表也可以继续同步，因为本例把当前数据留在内存。异步关系不要求所有函数都加上 `async`。需要变化的是那些必须等到完成结果以后，才能履行自己职责的位置。

如果一个包装函数只是把完成 Promise 原样返回，调用者可以在更外层等待。中间不一定每层都写 `await`，但必须保留那条结果关系。丢弃 Promise、同时立即报告成功，会让调用者无法再依靠这次操作的最终状态。

异步接口的收益是允许保存工作等待外部完成，而当前执行过程可以继续处理别的事情。代价是调用者要维护等待与错误路径，所有者也需要明确交错执行时的状态规则。它不等于节省了文件工作本身，也不证明整体操作会更快。

## 运行完整示例，检查返回值、等待与状态

[下载完整示例包](software-design-06-examples.zip)，解压后进入 `software-design-06-examples` 目录。

验证日期为 **2026 年 10 月 15 日**，运行环境是 macOS arm64、Node.js **25.9.0**。示例只使用 Node.js 自带功能，没有第三方依赖，不需要安装依赖包。

```sh
node basics-demo.mjs
node waiting-demo.mjs
node failure-demo.mjs
node overlap-demo.mjs
node file-demo.mjs
node --test async.test.mjs file.test.mjs
```

`basics-demo.mjs` 比较普通抛错、异步拒绝、Promise 与结果对象，以及直接返回和等待后返回的局部错误处理。`waiting-demo.mjs` 观察等待期间的旧数据、忙碌拒绝与结束后的重新提交。`failure-demo.mjs` 比较遗漏等待和正确等待，`overlap-demo.mjs` 观察缺少忙碌策略的覆盖。

`file-demo.mjs` 使用真实临时文件，没有把受控保存当作文件系统验证。例子结束时等待清理自己创建的目录，不影响使用者已有文件。

最后一个命令运行 **30 项测试**，本次全部通过：

| 检查对象 | 实际观察 |
| --- | --- |
| Promise 与错误 | 普通抛错、异步拒绝、正常失败结果、局部捕获与等待顺序 |
| 保存与采用 | 等待时保留旧状态，成功才采用，拒绝后可以重试 |
| 同一个所有者 | 等待时拒绝新修改，结束后基于新状态计算下一项 |
| 既有任务约定 | 编号检查、不存在、重复完成、返回副本、初始数据复制与列表顺序 |
| 两个反例 | 遗漏等待提前报告成功，允许重叠导致旧数据覆盖 |
| 真实临时文件 | 正常保存、真实 `ENOENT`、顺序两项完成，以及合成的写入后拒绝 |

检查不使用固定延时判断“应该已经完成”，而是明确控制保存结果，再等待对应的完成 Promise。这样可以区分程序还没继续，与程序继续后做错了事情。

下载包包含 17 个文件。初始数据、任务复制与完成计算三个文件与第五篇逐字节相同，方便只比较新增的异步所有者。正式实现、两个反例、控制保存的辅助代码、五个演示和两份测试均包含在内。

测试只覆盖本例合法初始数据、同一个所有者和明确列出的保存接口。它没有验证真实页面、多个所有者共同写文件、取消、断电或完整恢复；相关限制会改变实际项目的接口选择，需要在需求出现时继续设计。

## 再加一项异步操作，检查边界有没有说完整

可以沿用上一章的标题修改练习，让保存也返回 Promise。先约定标题合法性与相同标题的结果，再检查等待时另一项完成请求应收到什么。

列出至少几条不同路径：正常保存、保存拒绝、调用保存函数时直接抛错、修改期间再收到请求、操作结束后提示失败。分别写出调用者拿到的是 Promise、任务结果还是错误，以及当前数据在哪一步改变。

还可以把 `busy` 策略改成排队。不要只保留第二份已经算好的任务建议，而应检查什么时候读取当前状态、什么时候执行下一项，以及某项失败后是否继续队列。这个变式是读者练习，下载包保留正文的拒绝策略，没有实现排队或取消。

能沿着一项请求说清“谁等待什么、在哪一处处理失败、什么时候采用数据”，就能继续检查异步代码的取舍。下一篇会围绕可测试性，讨论怎样控制输入与外部动作、哪些行为适合单独检查，以及什么地方仍然需要真实环境。

## 来源与结论范围

本篇核对了 TC39 在线 ECMAScript 规范中的 Promise 与 Await 规则，以及 Node.js 25.9.0 的 Promise 文件接口文档，资料访问日期为 **2026 年 10 月 15 日**。线上规范是持续更新的工作稿，引用用于说明相关语言行为。

任务失败结果、保存错误转换位置和忙碌拒绝策略，是本文对演示程序作出的选择。语言资料说明这些写法怎样执行，受控例子与真实临时文件说明当前实现发生了什么；它们不替所有应用决定该拒绝、排队还是接受另一种更新规则。
