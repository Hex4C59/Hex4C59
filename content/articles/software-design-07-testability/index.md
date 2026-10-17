+++
title = "可测试性：怎样写出能发现问题的检查"
date = 2026-10-15T00:00:00+08:00
lastmod = 2026-10-17
draft = false
author = "Hex4C59"
description = "沿任务保存例子解释测试、断言和测试替身，从行为约定推导检查，用三个故意改错的版本检验检查，再接上真实文件说明验证范围。"
summary = "最后返回成功，不能证明等待期间的数据正确。先学会控制保存何时结束、观察哪些结果，再让同一组检查面对提前采用、吞掉失败和允许重叠修改的版本，理解测试为什么有用、又有哪些事情没有被证明。"
tags = ["软件测试", "可测试性", "接口设计"]
categories = ["engineering"]
source_kind = "original"
article_type = "concept"
series = ["software-design"]
series_role = "chapter"
series_order = 7
series_number = 7
series_part = "模块、状态与行为保持"
difficulty = "beginner"
ShowToc = true
+++

待办事项程序完成一条任务，保存成功后返回 `ok: true`。我们运行了一遍，看到了成功结果，能说“先保存，再采用新数据”已经做对了吗？

还不能。有一份写错的代码会先修改内存，再等待保存。只要这次保存最后成功，它也会返回相同的结果。两份代码的差别出现在等待期间，只看最后一行输出就会错过。

本文要解决的问题是：**怎样把行为约定写成可重复运行的检查，让程序做错时，检查确实能够发现。** 我们会先控制保存何时结束，检查等待前后的任务，再故意改坏三个地方，看相同的检查能否指出问题。最后接上真实文件，补上模拟保存没有覆盖的部分。

**软件测试**是在指定条件下运行程序，并比较实际行为和预期行为。**可测试性**指我们有多容易安排这些条件、执行操作并观察结果。例如，能不能让保存确定地失败，能不能在保存尚未结束时读取任务，而不用碰运气等一次磁盘故障。

读者需要能阅读简单 JavaScript。本文使用的 `await` 表示等待一项操作交回结果；Promise 是表示这项操作最终结果的对象。[上一篇](/articles/software-design-06-async-errors/)已经解释了它们，本篇只补充检查需要的写法。完整代码延续上一章的任务实现，加入检查和比较，没有增加任务功能。

## 1. 先说清楚，我们准备检查什么

任务有三个字段：`id` 是编号，`title` 是标题，`completed` 表示是否完成。初始数据是：

```js
[
  { id: "t1", title: "写周报", completed: false },
  { id: "t2", title: "整理笔记", completed: false },
]
```

调用 `completeTask("t1")`，表示完成写周报。调用者等待它的结果；任务模块负责管理当前数据，保存函数负责把准备好的数据交给外部存储。

这里的**契约**是这些代码共同遵守的约定：什么输入有效，成功或失败时返回什么，哪些数据会改变。我们沿用前两篇已经选定的规则：

| 条件 | 调用者取得的结果 | 当前任务与保存行为 |
| --- | --- | --- |
| 编号无效，且没有其他修改在等待 | `invalid-id` | 不修改，不保存 |
| 编号不存在 | `not-found` | 不修改，不保存 |
| 任务已经完成 | `ok: true, changed: false` | 不再次保存 |
| 有效修改正在等待保存 | 第一项操作还没有最终结果 | 读取仍得到旧任务 |
| 保存正常结束 | `ok: true, changed: true` | 采用新任务 |
| 保存抛错或 Promise 拒绝 | `ok: false, reason: "save-failed"` | 保留旧任务 |
| 同一任务对象已有修改在等待 | `ok: false, reason: "busy"` | 第二项修改不保存 |

`ok` 表示操作成功与否，`changed` 表示这一次有没有改变任务；表格中只写原因名称的失败结果，都有 `ok: false` 和相应的 `reason`。

这些是本例的选择。其他程序可以排队，可以把保存失败交给调用者处理，但要先确定自己的规则，再据此写检查。如果约定还在争论，测试只能记录其中一个选择，不能替人决定哪种产品行为更合适。

本例还要求初始任务合法、编号唯一，保存函数最终给出结果；正常保存以 `undefined` 表示成功，失败通过抛错或拒绝报告。本文不会用测试悄悄扩大这些前提。

## 2. 打印结果和断言有什么不同

调试时，我们经常写：

```js
// 示意片段：taskList 是已经创建好的任务对象。
console.log(await taskList.completeTask("t1"));
```

它帮人看结果，但打印本身没有说什么结果才正确。即使打印出 `save-failed`，脚本也可能正常退出，需要人一直盯着终端。

**断言**把“应当如此”写进代码。条件不成立时，它报告错误，让这一次检查失败。下面两行的意思分别是：“实际值应当等于 `true`”“实际对象的字段和值应当与预期对象一致”：

```js
// 断言写法示意；actualFlag、actualResult 代表程序运行得到的值。
assert.equal(actualFlag, true);
assert.deepEqual(actualResult, { ok: false, reason: "save-failed" });
```

本文从 `node:assert/strict` 导入 `assert`，使用 Node.js 自带的严格比较规则。`equal` 用于这里的布尔值、数量等简单值；`deepEqual` 用于比较对象和数组中的内容。只写 `actualResult === expectedResult`，比较的是两个对象是否为同一个对象，不能代替我们要检查的字段和值。[1]

把“运行程序”和“判断结果”分开之后，检查才不依赖读者记住上一次的终端输出。

## 3. 从最容易确定的计算开始

前两篇已经把完成任务拆成两步。`planCompletion(tasks, id)` 先计算结果和准备采用的新数据，不保存文件；`createAsyncTaskList` 创建管理当前任务的对象，负责调用保存并决定何时采用。

先检查前一个函数，因为输入和结果都很清楚。下面是可独立运行的完整检查，可另存为示例目录里的 `first-check.test.mjs`：

```js
import test from "node:test";
import assert from "node:assert/strict";
import { planCompletion } from "./plan-completion.mjs";

test("完成指定任务，原数组仍保持原值", function () {
  const original = [
    { id: "t1", title: "写周报", completed: false },
    { id: "t2", title: "整理笔记", completed: false },
  ];
  const proposal = planCompletion(original, "t1");

  assert.deepEqual(proposal.result, {
    ok: true, changed: true,
    task: { id: "t1", title: "写周报", completed: true },
  });
  assert.deepEqual(proposal.nextTasks, [
    { id: "t1", title: "写周报", completed: true },
    { id: "t2", title: "整理笔记", completed: false },
  ]);
  assert.deepEqual(original, [
    { id: "t1", title: "写周报", completed: false },
    { id: "t2", title: "整理笔记", completed: false },
  ]);
});
```

在示例目录执行：

```sh
node --test first-check.test.mjs
```

`test` 给一项检查命名，并交给 Node.js 的测试运行器执行。运行器负责收集通过、失败等结果。**退出码**是程序结束时交给操作系统的数字；这套运行器用 `0` 表示正常通过，有测试失败时用 `1`，其他工具也能据此判断失败。[2]

这项检查观察三个不同的东西：返回给调用者的结果、准备保存的新任务、传入的原任务。最后一个断言不能因为“前面已经看到了新数组”而省掉。某份实现完全可能一边返回正确新数组，一边错误地修改原数组。

## 4. 预期结果应当从哪里来

上面的预期数组，是按任务约定写下来的：编号 `t1` 变为完成，`t2` 保持原样，原输入仍未完成。

一种容易写出的检查却是：

```js
// 有问题的检查示意：同一次计算方式产生实际值和预期值。
const expected = planCompletion(original, "t1");
const actual = planCompletion(original, "t1");
assert.deepEqual(actual, expected);
```

假如 `planCompletion` 错把 `t2` 也标记完成，两次都会产生相同错误。比较通过，只说明两次结果一致。

我们需要一个独立的判断依据。对两条任务来说，把预期数据直接写出就足够，不必再写一套通用任务算法来计算它。否则那套“预期算法”也需要检查，问题又绕了回来。

**独立**不表示人写的预期永远正确。它表示预期有自己的来源，可以回到“应当只完成指定编号”这条约定核对，而不是把被检查函数的输出重新当作答案。需求理解有误、预期抄错，都仍然可能让检查给出错误判断。

## 5. 为什么只检查 `ok` 不够

接下来检查带保存的完整操作。一个很短的检查可能是：

```js
// 不充分的检查示意：保存立即报告成功，只检查最终结果。
const taskList = createAsyncTaskList(async function saveSnapshot() {});
const result = await taskList.completeTask("t1");
assert.equal(result.ok, true);
```

它能发现某些问题，例如有效任务一律失败；它看不到新数据是什么时候成为当前数据的，也没有检查保存收到的内容。

把“采用新数据”错误地移到保存前面，这项检查照样通过。因为它直到 `await` 结束后才看结果，而两份代码到那时都可能已经成功完成。

想检查顺序，就必须安排一个保存尚未结束的时刻，并在那个时刻观察。为此，我们需要控制外部工作的完成时间。

## 6. 用一个小函数控制保存

任务模块需要调用保存，才能完成自己的工作。这里的保存就是它的一个**依赖**：完成当前功能时必须借助的另一段代码。

平时传入写文件的函数；检查时，可以传入下面的函数，先不写文件，只记录调用，并把完成或失败的开关交给检查：

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

这是 `controlled-save.mjs` 的完整代码。`calls` 记录每次传进来的任务；`succeed()` 让那一次 Promise 正常完成，`fail(error)` 让它拒绝。在检查主动选择以前，它保持等待。

例如 `saving.calls[0].succeed()`，就是完成第一次保存。这里的 `0` 是数组第一项的位置，没有任务编号的含义。

**测试替身**指检查时用来替代真实协作部分的代码。这个保存函数就是替身：保留任务模块需要的调用形式，提供容易控制的结果。这个总称不要求使用专门框架，几行普通 JavaScript 也可以做到。[3]

它没有保存文件，也没有模拟磁盘内部怎样工作。我们只借它提出一个问题：“如果保存此刻还没完成，任务模块会怎么办？”

## 7. 这是不是为了测试，硬给程序加一个参数

本例原来就需要传入 `saveSnapshot`。任务模块负责算任务变化，保存函数负责外部写入；这个分工让检查可以换掉保存，也让同一个任务模块可以选择不同保存位置。

把依赖从外部交进来，常被称为**依赖注入**。在这里，它就是调用 `createAsyncTaskList(saveSnapshot)` 时传一个函数，没有额外容器，也没有自动寻找实现的机制。

这个选择有成本。创建任务对象的代码必须知道要用哪个保存函数；保存的成功值、失败方式、是否会一直等待，也都需要约定。函数参数变多、组合关系变散时，阅读负担仍会增加。

是否值得，要看我们是否确实需要分开管理任务行为和外部保存。本例既要处理保存失败，又要观察等待期间的状态，分开后有明确用途。若只是检查一个简单加法，凭空增加三层可替换对象，并不会让问题更清楚。

也不用为了方便检查，把所有内部变量都导出。本文通过 `listTasks()` 观察当前任务，通过保存函数收到的参数观察待写数据，已经能回答关心的问题。

## 8. 一项完整的等待检查

下面是 `waiting.test.mjs`，可以在示例目录直接运行。先阅读 `try` 中的主体，后面再解释清理：

```js
import test from "node:test";
import assert from "node:assert/strict";
import { createAsyncTaskList } from "./async-task-list.mjs";
import { createControlledSave } from "./controlled-save.mjs";

test("保存未结束时保留旧数据，成功后才采用", async function () {
  const saving = createControlledSave();
  const taskList = createAsyncTaskList(saving.saveSnapshot);
  const pending = taskList.completeTask("t1");
  try {
    assert.equal(saving.calls.length, 1);
    assert.deepEqual(taskList.listTasks(), [
      { id: "t1", title: "写周报", completed: false },
      { id: "t2", title: "整理笔记", completed: false },
    ]);
    assert.equal(saving.calls[0].tasks[0].completed, true);
    saving.calls[0].succeed();
    assert.deepEqual(await pending, {
      ok: true, changed: true,
      task: { id: "t1", title: "写周报", completed: true },
    });
    assert.deepEqual(taskList.listTasks().map(task => task.completed), [true, false]);
  } finally {
    for (const call of saving.calls) call.succeed();
    await Promise.allSettled([pending]);
  }
});
```

```sh
node --test waiting.test.mjs
```

这项检查依次观察：保存被调用一次；当前任务仍未完成；交给保存的新任务已经完成；我们允许保存成功；操作返回成功；当前任务才变成新的状态。

注意第一次读取当前任务时，没有先 `await pending`。如果先等操作全部完成，就再也看不到这一次操作的等待过程了。

这里也没有等固定的十毫秒或一百毫秒。检查掌握保存的完成开关，所以可以直接安排“还没完成”和“已经完成”两个条件。机器运行快慢不负责决定它看到哪一种状态。

## 9. 为什么这段检查自己也要等待

传给 `test` 的函数写了 `async`，内部等待 `pending`。测试运行器才能等这些断言和清理结束，再确定这一项的结果。[2]

如果启动操作后直接退出测试函数，把判断丢在一个没有返回、也没有等待的 Promise 后面，测试函数可能已经结束，操作和断言却还没结束。晚到的错误可能成为额外异步错误，而不是按你以为的顺序完成当前检查。

检查里的 `finally` 处理另一件事：如果中途某个断言失败，也要让已经发起的受控保存结束，并观察已经取得的 Promise。`Promise.allSettled` 等待这些操作各自结束，正常或拒绝都会记录下来；这里用它清理，不把它当作成功证明。

这样，断言抛出的问题仍会报告，清理也不会故意留下一个等待开关。它不是产品里的取消功能，更不会修复一个永远不结束的任意保存实现。我们只对本例自己创建并掌握开关的操作做收尾。

## 10. 失败检查要分清两种“失败”

保存函数的 Promise 拒绝了，表示保存操作没成功。任务模块捕获这项拒绝后，会正常返回一个失败结果对象。

因此检查任务模块，应当等待结果并比较这个对象：

```js
// 核心片段，完整清理与其他断言见 contract-checks.mjs。
const saving = createControlledSave();
const taskList = createAsyncTaskList(saving.saveSnapshot);
const pending = taskList.completeTask("t1");
saving.calls[0].fail(new Error("受控的保存失败"));
assert.deepEqual(await pending, { ok: false, reason: "save-failed" });
```

随后还要读当前任务，确认仍是两条未完成任务。只检查失败对象，漏掉的是“虽然报告失败，却已经修改数据”的另一种错误。

检查保存函数本身时，如果它的约定就是拒绝，则可以使用 `await assert.rejects(...)`，要求 Promise 真的拒绝。[1] 同一次调用究竟应该“正常交回失败对象”还是“拒绝”，要由接口约定确定，不能因为中文都叫失败，就混用两种断言。

错误原因也应按所检查接口的约定判断。任务模块承诺交回 `save-failed`，就不必要求错误提示包含某个操作系统的完整文件路径。后面直接检查真实文件接口时，才核对文件接口提供的错误代码。

## 11. 等待中的第二次修改，也有可观察的结果

本例的忙碌策略很明确：同一任务对象正在保存时，再完成另一条任务，应当得到 `busy`，不能再次调用保存。

所以检查至少观察三件事：第二次调用交回 `busy`，保存调用数量仍是一次，第一项保存结束后第二条任务仍未完成。

为什么连保存次数都要看？因为一份写错的实现可能先发起第二次保存，再返回 `busy`。调用者看到了拒绝修改的结果，外部写入却已经发生了。对本例来说，“不保存第二项修改”本来就是约定的一部分。

但不用继续要求某个内部辅助函数被调用两次、局部变量必须叫 `busy`、源代码必须分成几个文件。那些不属于调用者的承诺。只要公开行为符合约定，内部可以换一种实现。

这里有一个判断方法：**如果改变这件事，会不会改变调用者或保存方能观察到的承诺？** 会，就可能值得检查；只是把一个循环换成另一个循环，通常不必把代码形状固定进测试。

## 12. 让检查面对一份确实写错的实现

写了断言以后，还可以反过来问：“我关心的错误出现时，这些断言会失败吗？”

下载包保留三个故意改错的版本，放在 `faults/`。它们都是教学比较，不能作为推荐实现使用。正式的 `async-task-list.mjs` 沿用上一章，这三处人为错误只放在反例文件中。

| 比较版本 | 人为改动 | 相同约定检查应当发现什么 |
| --- | --- | --- |
| `early-adopt` | 在等待保存前就采用新任务 | 保存未结束时，读取已经变成完成 |
| `ignore-rejection` | 捕获保存失败，却返回成功结果 | 保存拒绝后没有返回 `save-failed` |
| `allow-overlap` | 删除等待期间拒绝新修改的判断 | 第二次修改又发起一次保存 |

每一份都用同样的初始任务和受控保存。检查不根据版本名称放宽条件，也不专门给错误实现换一个“正确答案”。

这种办法让检查的价值更容易观察：它不只是对一份程序说“通过”，还对具体错误说“这里违背了约定”。不过三个反例只覆盖三种错误，不能推导出其他所有错误都会被发现。

## 13. 同一组检查怎样复用

`contract-checks.mjs` 把三个检查分别写成函数：`checkBeforeAdopt`、`checkRejection`、`checkBusy`。每个函数接收一个“创建任务对象”的函数。

因此，换实现时只换创建函数，其余输入和预期保持一致。下面是调用关系的删节示意：

```js
// 示意：各检查的完整实现见 contract-checks.mjs。
export async function runContractChecks(createTaskList) {
  await checkBeforeAdopt(createTaskList);
  await checkRejection(createTaskList);
  await checkBusy(createTaskList);
}
```

这也是为什么任务模块的接口约定有用。检查只需要知道怎样创建对象、怎样完成任务、怎样读取任务，就能比较几个实现。不必知道它们内部把数据放在哪个局部变量里。

这次提取还有一个具体收益：`node:test` 的正常检查和演示反例的命令都调用这些函数，不各写一份“差不多相同”的规则。否则一份补了等待检查，另一份忘了补，比较本身就容易失真。

我们仍保留一项展开写的 `waiting.test.mjs` 供阅读。它展示完整过程；复用的三个函数负责对不同实现执行同一组约定判断。

## 14. 实际运行：正确版本通过，错误版本退出失败

在示例目录运行：

```sh
node fault-demo.mjs
```

本次运行得到：

```text
correct：检查通过
early-adopt：检查失败：保存结束前应保留原任务
ignore-rejection：检查失败：保存拒绝应返回 save-failed
allow-overlap：检查失败：等待时第二次修改不应再次保存
```

还可以单独运行：

```sh
node probe.mjs early-adopt
```

它会以退出码 `1` 结束。这是预期现象：我们要求一份提前采用数据的实现遵守“等待时保留旧数据”，它违反了要求。

`fault-demo.mjs` 负责启动各个比较进程，并核对正确版本退出 `0`，三个错误版本各自退出 `1`。整段演示正常结束，表示它观察到了预期的四种判断；不表示那三个错误实现修好了。

这里把“被检查程序失败”和“演示是否按预期工作”分开，避免为了让终端全显示通过，就删掉能够指出真实问题的断言。

## 15. 测试通过的数量，回答不了所有问题

如果一百项检查都只在保存结束后看 `ok`，它们仍可能一起漏掉提前采用数据。反过来，一项位置合适的等待检查，就能发现这个具体错误。

数量告诉我们运行了多少项命名检查，不直接告诉我们条件安排得是否合适、预期是否独立、观察是否足够。

有些工具还统计**代码覆盖率**，即运行检查时，哪些代码位置确实执行过。[2]它能帮人找出没有走到的分支，但一行执行过，不表示这一行的结果被断言检查过。本例没有运行覆盖率统计，也不报告覆盖率数字。

三个错误版本也不能变成另一种漂亮分数。“三份都被发现”只对这三项人为改动成立。新增了文件加载、超时或取消功能，仍要先解释它们的约定，再设计相应的条件和观察点。

## 16. 模拟保存通过了，文件就一定写好了吗

不会。我们传入一个空的异步函数，它也能正常交回 `undefined`。任务模块会据此采用新数据，但没有任何文件因此出现。

这不是任务模块可以凭空识别的问题。它依赖保存方遵守“正常结束表示数据已经保存”的约定。检查任务模块时，我们用替身安排这种通知；要验证真正的保存方是否履行约定，就得检查保存方。

本章增加一个很短的真实保存适配函数。**适配**在这里指把任务模块需要的“接收任务并报告保存结果”，接到 Node.js 的文件写入接口上：

```js
import { writeFile } from "node:fs/promises";

export function createJsonFileSave(file) {
  return function saveSnapshot(tasks) {
    return writeFile(file, JSON.stringify(tasks));
  };
}
```

这是 `json-file-save.mjs` 的完整代码。`file` 指定路径，`JSON.stringify` 把任务变成文本，`writeFile` 返回表示文件写入结果的 Promise。[4]

路径由外部提供，因此检查能选择自己刚创建的临时目录，演示也不需要覆盖读者的真实任务文件。传入路径在这里有运行用途，不是为了让检查读到任务模块的内部变量。

## 17. 接上真实文件，观察写入之后的内容

“调用过写入函数”和“文件能读回正确任务”是两项不同观察。前者可以由替身记录；后者必须真正写入并重新读取。

下面是完整的独立文件检查，可以在示例目录另存为 `real-file.test.mjs`。示例包的 `file.test.mjs` 还有组合与失败检查：

```js
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createAsyncTaskList } from "./async-task-list.mjs";
import { createJsonFileSave } from "./json-file-save.mjs";

test("完成任务后，真实文件可以读回新数据", async function () {
  const root = await mkdtemp(join(tmpdir(), "software-design-07-"));
  try {
    const file = join(root, "tasks.json");
    const taskList = createAsyncTaskList(createJsonFileSave(file));
    assert.equal((await taskList.completeTask("t1")).ok, true);
    assert.deepEqual(JSON.parse(await readFile(file, "utf8")), [
      { id: "t1", title: "写周报", completed: true },
      { id: "t2", title: "整理笔记", completed: false },
    ]);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
```

```sh
node --test real-file.test.mjs
```

`mkdtemp` 新建一处临时目录，`readFile` 读回文本，`JSON.parse` 把文本还原为数据。`finally` 在通过或失败后清理本次目录；清理也要等待，不能发起删除后就把检查结束。[4]

这里的预期仍然直接来自任务约定，没有通过“把刚读回的文件再写一遍”来证明自己。

这项检查覆盖了任务模块、真实保存函数和本机文件接口之间的配合。但它没有启动页面，没有模拟断电，也没有启动第二个进程同时写同一路径。文件读回成功，不会自动扩展成这些条件下的证明。

## 18. 真实失败也要选能解释的条件

真实文件检查不必等到磁盘恰好出故障。我们在自己创建的临时目录下，选择一个父目录并不存在的路径，例如 `missing/tasks.json`，而不创建 `missing`。

在本次运行环境中，这个写入会拒绝，并提供 `ENOENT` 错误代码，表示相应路径项不存在。检查分两层观察：直接调用保存函数，要求它拒绝；把它交给任务模块，要求得到 `save-failed` 并保留原任务。

同时，示例包还有一项对照：传入什么也没写的模拟保存，完成任务会成功，但读取预定文件会因不存在而拒绝。它直接展示“模拟成功通知”和“真实文件存在”之间缺少的证据。

为什么不靠把文件设成只读来制造失败？文件权限、运行身份和环境配置可能改变这种例子的结果。这里选择不存在的父目录，是为了让条件能由示例明确建立并检查。我们仍然只报告实际观察到的这一类失败，没有测试磁盘已满或写入一半的故障。

## 19. 分开检查和组合检查各自负责什么

常见说法里，**单元测试**通常把一个较小部分单独检查；**集成测试**把几个部分接起来，检查它们怎样配合。项目对“多小才算单元”可能有不同口径，本文直接说明每项检查实际接了什么。

| 检查对象 | 可以安排或观察的事 | 仍然没有覆盖的事 |
| --- | --- | --- |
| 完成任务的计算 | 指定输入、结果、新旧数组 | 保存是否写入，等待期间行为 |
| 任务模块加受控保存 | 保存尚未结束、成功、拒绝、第二次修改 | 真实路径、实际写入内容 |
| 真实保存函数 | 文本写入与读回、路径错误 | 任务模块采用数据的顺序 |
| 任务模块加真实保存 | 一次完成操作后的文件结果、失败转换 | 页面、多个进程、崩溃恢复 |

受控保存让中间时刻容易观察，真实文件检查则确认任务代码交出的数据能否真正写入并读回。我们不用让所有检查都碰磁盘，也不能把所有文件工作换成空函数之后，就宣称文件保存完成了。

分开还有定位上的帮助。若计算检查已失败，可以先看任务规则；若受控保存检查通过，而真实文件检查失败，就有理由先检查路径和保存适配。它缩小排查范围，但仍要看具体错误，不能仅凭测试名称认定故障位置。

## 20. 每项检查都应当能单独重新运行

一项检查先完成 `t1`，另一项再用同一个对象检查“初始时两条任务都未完成”，结果就依赖执行顺序。单独运行后者可能通过，和前者一起运行却失败。

本例每项检查新建任务对象和受控保存记录。真实文件检查各自创建临时目录。前一个检查改过什么，不应该悄悄成为后一个检查的输入。

如果需要检查失败后重试，就把“失败，再重试”写在同一项检查里，因为那是我们有意安排的过程。示例中的重试检查会先拒绝第一次保存，确认 `save-failed`，再成功完成第二次保存，确认不再停留在 `busy`。

也不要通过“多等一会儿”修补没有结束的操作。先找出谁负责结束它，检查有没有等待它交回的 Promise。受控保存的开关应该属于这一项检查，而不是由上一项检查顺手完成。

## 21. 什么样的改动不应当逼你重写这些检查

假如下一篇把任务模块内部重新整理，公开输入、结果、保存时机和任务变化都保留，那么本篇的约定检查应当继续适用。

如果我们事先规定私有函数名称、局部变量顺序，甚至数组遍历必须调用某个具体方法，内部调整就会造成一批没有行为意义的失败。维护者忙着改测试，反而更难分辨真正的功能变化。

另一方面，不能为了“测试不容易坏”，只剩下一个 `ok === true`。任务字段、失败原因、是否修改旧数据、等待时能否再保存，都是这份接口明确承担的行为，改变后应当提醒我们重新核对。

检查要固定多少细节，取决于承诺了多少细节。当前结果里承诺返回完整任务，本例就比较完整字段；若以后决定只返回编号，应当明确修改接口及对应预期，而不是让检查假装两种结果一样。

这也是测试对设计的反馈：某项行为若很难安排和观察，可能说明几个责任纠缠在一起；但“难检查”只是线索，还需要回到真实需求判断怎样拆分，不能自动推出要再加一层接口。

## 22. 下载、运行与这一次的验证范围

下载[第七篇完整示例](software-design-07-examples.zip)，解压后进入 `software-design-07-examples` 目录。示例不依赖第三方包，无需安装依赖：

```sh
node --version
node --test planning.test.mjs waiting.test.mjs contracts.test.mjs file.test.mjs
node fault-demo.mjs
node file-demo.mjs
```

本次在 macOS arm64、Node.js **25.9.0** 上运行，完整测试为 **20 项通过**，没有跳过或取消。其中 4 项使用真实临时文件；还有 4 项在独立进程里核对正确版本和三个错误版本的检查结果。命令中的退出码、文件结果和失败信息均按实际运行核对，未测量性能。

`node file-demo.mjs` 的输出为：

```text
真实保存结果： {"ok":true,"changed":true,"task":{"id":"t1","title":"写周报","completed":true}}
读回文件的完成标记： [true,false]
真实路径失败： {"ok":false,"reason":"save-failed"}
失败后的完成标记： [false,false]
```

包内 `README.md` 说明各文件用途和反例的预期失败。任务计算、任务所有者及受控保存沿用第六篇，新增约定检查、错误版本和文件适配。两个正文里可以另存运行的完整检查也已单独验证，不要求读者自己补 import。

这些检查针对当前两条任务及明确列出的条件。保存内部已经写入一部分数据后才拒绝，不会因为任务模块保留了旧内存就自动恢复文件；同一对象的 `busy` 也不负责多个对象或进程之间的写入协调。本篇没有增加启动加载、取消、期限或崩溃恢复。

若想继续练习，可以先给 `ignore-rejection` 增加一种错误：返回 `save-failed`，但仍然采用新任务。先想清楚现有哪一个断言应该发现它，再运行确认。另一项练习是增加“修改标题”，先写清保存失败后标题是否保留，再写预期；不要先复制实现算出答案。这两项是练习，不属于本次已实现的能力。

[下一篇进入重构](/articles/software-design-08-refactoring/)：沿数组到 Map 的分步迁移检查结果、保存与失败处理，区分内部整理和需要重新讨论的行为变化。返回[系列目录](/articles/software-design/)，可以查看前后各篇的阅读顺序。

## 参考资料

以下资料访问于 2026-10-15。测试行为以固定版本文档和本篇实际运行共同核对；本文的任务约定、反例选择及检查范围由示例定义。

1. [Node.js 25.9.0：严格断言、对象比较与拒绝检查](https://nodejs.org/download/release/v25.9.0/docs/api/assert.html)。用于核对 `node:assert/strict`、`deepEqual` 和 `rejects` 的使用。
2. [Node.js 25.9.0：测试运行器](https://nodejs.org/download/release/v25.9.0/docs/api/test.html)。用于核对异步测试、执行命令与失败退出码。
3. [Martin Fowler：Test Double](https://martinfowler.com/bliki/TestDouble.html)。用于说明测试替身作为替代协作代码的总称；本文没有展开各类替身的分类。
4. [Node.js 25.9.0：Promise 文件接口](https://nodejs.org/download/release/v25.9.0/docs/api/fs.html#promises-api)。用于核对写入、读取、临时目录与清理接口；文件检查没有覆盖所有系统故障。
