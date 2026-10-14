+++
title = "间接调用与依赖：程序怎样按名称选择要做的事"
date = 2026-10-14T12:00:00+08:00
lastmod = 2026-10-15
draft = false
author = "Hex4C59"
description = "沿用待办事项程序，解释直接调用、按操作名称分支和处理器表的工作过程，比较函数值、参数转换、修改范围与定位错误的成本。"
summary = "收到 complete 这样的操作名称后，程序怎样找到完成任务的代码？先讲清保存函数与执行函数的区别，再比较条件分支和处理器表，观察统一入口改变了哪些约定、依赖和阅读路径。"
tags = ["依赖关系", "函数", "路由表"]
categories = ["engineering"]
source_kind = "original"
article_type = "concept"
series = ["software-design"]
series_role = "chapter"
series_order = 3
series_number = 3
series_part = "抽象、契约与依赖"
difficulty = "beginner"
ShowToc = true
+++

待办事项程序已经有了两个函数：`listTasks` 列出任务，`completeTask` 完成任务。[上一篇](/articles/software-design-02-contracts/)讨论了它们应当遵守的约定，例如任务不存在时说明原因，重复完成同一条任务时不再修改数据。

现在增加一个需求：程序的一处入口会收到“列出任务”或“完成任务”这样的操作名称，再决定执行哪项功能。这个选择过程要怎样写？直接调用、条件分支、把函数存进一张表，分别解决什么问题？

先给出本文的选择：如果按钮已经明确知道要完成任务，直接调用完成任务函数就很清楚。确实需要按名称选择功能时，可以先用条件分支。操作之间具有相同的接收和返回方式，而且把名称与函数集中列出有助于维护时，再考虑处理器表。是否使用这张表，取决于它替我们集中处理了什么，以及它增加的查找过程是否值得。

按一个名称找到功能，再让它执行，本文称为**间接调用**。使用入口的代码仍须知道哪些名称可用、信息放在哪里。一段代码正常工作所依靠的其他功能、数据或约定，叫它的**依赖**。我们会追踪这次改写把依赖放到了哪些地方。

本文沿用两条演示任务，使用 JavaScript 和本地函数。阅读需要能看懂简单的对象与 `if` 判断；函数值、分发、处理器和依赖等概念会在用到时解释。读完后，你应该能沿着一次请求找到真正修改任务的代码，并说明新增操作时需要改哪里。文末提供完整示例、两种方案的行为检查，以及一个已经实现的扩展练习。

## 已经知道要做什么，就先直接调用

我们仍使用这两条任务：

```js
[
  { id: "t1", title: "写周报", completed: false },
  { id: "t2", title: "整理笔记", completed: false },
]
```

`id` 是任务编号，`title` 是标题，`completed` 表示是否已经完成。`false` 表示还没有完成，`true` 表示已经完成。对象里每个有名字的数据项叫**字段**。这些字段与上一篇相同。

完整示例中的 `tasks.mjs` 提供 `createTaskList`。执行一次这个函数，就创建一份独立的演示任务，并交回一个对象，里面有列出任务与完成任务的函数。下面的代码可以在示例目录中保存为另一个 `.mjs` 文件运行：

```js
import { createTaskList } from "./tasks.mjs";

const taskList = createTaskList();
const result = taskList.completeTask("t1");
console.log(result);
```

`import` 表示从另一个代码文件取得它提供的功能。`taskList.completeTask` 表示取出 `taskList` 对象里的完成任务函数；后面的 `("t1")` 让它执行，并把任务编号交给它。交给函数的这类信息叫**参数**，执行后交回的值叫**返回值**。让函数执行叫**调用**，发起调用的代码叫**调用者**。

如果列表页上的按钮就叫“完成任务”，按钮的处理代码知道自己要做什么。它交出任务编号，直接调用这个函数即可。详情页也可以这样使用。

额外写出一个操作名称，再把名称交给另一段代码查找，暂时没有替这个按钮省下什么信息。按钮原来知道 `completeTask`，现在可能改为知道字符串 `"complete"`，也就是用引号表示的一段文字，还需要约定任务编号放在哪里。我们需要先找到新增查找的实际用途。

## 当入口先收到一个操作名称

假设程序增加一个演示入口，用对象表示用户要做的事：

```js
{ action: "list" }
{ action: "complete", id: "t1" }
```

一个这样的对象叫一份**请求**：它描述希望程序执行的操作以及所需信息。这里的请求只是函数收到的普通数据，不涉及网络。

`action` 是我们为操作名称选定的字段。`"list"` 表示列出任务，`"complete"` 表示完成任务；完成任务还需要 `id`。这些英文名称是本例自己的约定，JavaScript 不会自动理解它们的含义。

一个明确的使用场景，是把几步操作写成数据，再由同一个演示入口依次执行。收到哪一份数据，执行哪项功能，就不能在入口里永远写死为完成任务。

这时需要一段选择代码：读出操作名称，找到对应功能，交出参数，最后把执行结果返回。这项工作通常叫**分发**。负责这项工作的函数可以叫 `dispatch`，中文可以理解为“按请求分派工作”。名字可以换，承担的工作需要讲清楚。

我们先用最容易逐行阅读的写法实现它。

## 用条件分支，把选择过程直接写出来

下面是示例包中 `by-branch.mjs` 的完整内容。它使用的 `taskList` 必须已经提供上一篇那两个函数。

```js
export function createBranchDispatcher(taskList) {
  function dispatch(request) {
    if (typeof request !== "object" || request === null || Array.isArray(request)) {
      return { ok: false, reason: "invalid-request" };
    }
    if (typeof request.action !== "string" || request.action.trim() === "") {
      return { ok: false, reason: "invalid-action" };
    }

    if (request.action === "list") {
      return { ok: true, tasks: taskList.listTasks() };
    }
    if (request.action === "complete") {
      return taskList.completeTask(request.id);
    }
    return { ok: false, reason: "unknown-action" };
  }
  return dispatch;
}
```

`export` 表示允许其他文件取得这个函数。`createBranchDispatcher` 接收一份任务操作对象，创建并交回 `dispatch`。它创建入口时，不会列出或完成任何任务。返回的 `dispatch` 以后执行时，仍能使用创建时传进来的那份 `taskList`。

读代码时，可以把创建和使用分开看：

```js
import { createTaskList } from "./tasks.mjs";
import { createBranchDispatcher } from "./by-branch.mjs";

const taskList = createTaskList();
const dispatch = createBranchDispatcher(taskList);
const result = dispatch({ action: "complete", id: "t1" });
console.log(result);
```

前两行是取得功能；接着创建任务数据，再创建使用这份数据的分发入口；最后一行调用 `dispatch` 时，才提出完成任务的请求。

入口先检查请求的基本形状。`typeof` 用来观察一个值的类型，`Array.isArray` 检查它是不是数组。由于 JavaScript 中 `typeof null` 的结果也是 `"object"`，代码还单独排除了 `null`。这里要求收到对象，并排除数组；调用范围是我们自己构造的普通对象，或从 JSON 文本读出的对象。JSON 是一种表示数据的文本格式。这里没有尝试检查任意 JavaScript 对象可能具有的特殊行为。

接着检查操作名称是不是非空字符串。`trim()` 产生去掉两端空白后的字符串，这里只借它判断名称是否全为空白，后面的匹配仍使用原来的名称。

`===` 比较两边是否严格相等。操作名是 `"list"`，执行列出任务；是 `"complete"`，执行完成任务。`if` 里面的代码只有在对应条件成立时执行，这种按条件选择不同代码的写法叫**条件分支**。

选择关系都能在这一个函数里看见。两项操作使用不同参数，也能在各自分支中直接处理。操作很少时，这通常足以满足需求。

## 新入口也需要自己的约定

上面的函数增加了一个接口，也就增加了调用者需要依靠的规则。**接口**是其他代码使用功能的方式，**契约**是双方在输入、结果与行为上共同遵守的约定。上一篇讲过这两个概念，这里把它们落到分发入口上。

| 收到的请求 | 本例的结果 | 是否执行任务操作 |
| --- | --- | --- |
| `null`、字符串或数组 | `invalid-request` | 否 |
| `{}` 或 `{ action: "  " }` | `invalid-action` | 否 |
| `{ action: "delete" }` | `unknown-action` | 否 |
| `{ action: "list" }` | `ok: true`，并带上任务数组 | 只执行列出任务 |
| `{ action: "complete", id: "t1" }` | 完成任务函数的原有结果 | 只执行完成任务 |
| `{ action: "complete" }` | `invalid-id` | 执行完成任务函数，由它检查编号 |

失败结果都保留 `ok: false` 和 `reason`，表中只简写了原因。检查顺序也属于行为：先确认收到可处理的请求，再检查操作名，最后处理选定操作需要的信息。

本例区分大小写，`"Complete"` 不等于 `"complete"`。`" complete "` 也不会自动变成 `"complete"`。多出来的字段会被忽略，例如列出任务时附带 `id` 不影响结果。这些都是当前示例的选择；如果产品要求自动修正名称或拒绝多余字段，需要明确修改规则和对应检查。

列出任务原来直接返回数组，入口把它包成 `{ ok: true, tasks: ... }`，方便使用入口的代码先查看 `ok`。完成任务原来已经返回带 `ok` 的对象，这里直接交回。成功时具体有哪些字段，仍然由操作决定：列出任务有 `tasks`，完成任务有 `task` 和 `changed`。统一入口没有把不同功能的所有结果变成同一种数据。

## 先分清：函数本身，与函数执行后的结果

考虑另一种安排之前，需要讲清楚一个 JavaScript 能力：**函数可以作为值保存，也可以交给另一段代码以后调用。**

可以先看一个更短的演示：

```js
let calls = 0;
function completeTask(id) {
  calls += 1;
  return { ok: true, id };
}

const savedFunction = completeTask;
console.log("保存函数后：", calls);
const savedResult = completeTask("t1");
console.log("立即调用后：", calls, typeof savedResult);
savedFunction("t2");
console.log("调用保存的函数后：", calls);
```

这里的 `completeTask` 只用来统计执行次数，不是任务列表中的真实实现。`calls += 1` 表示每执行一次就把计数加一。运行 `function-value.mjs` 得到：

```text
保存函数后： 0
立即调用后： 1 object
调用保存的函数后： 2
```

`const savedFunction = completeTask` 把函数交给一个新名字保存。右边没有调用括号，所以函数还没有执行，计数仍为零。后面写 `savedFunction("t2")`，就能通过保存的名字执行同一个函数。

`const savedResult = completeTask("t1")` 则立即执行了函数。它保存的是函数交回的对象，`typeof savedResult` 因而是 `"object"`。这个对象包含操作结果，不能拿它当作原来的函数调用。

“函数值”指的就是这里能够保存和传递的函数本身。JavaScript 的函数属于可以调用的对象，语言规范在[对象的内部方法说明](https://tc39.es/ecma262/multipage/ecmascript-data-types-and-values.html#sec-object-internal-methods-and-internal-slots)中区分了对象是否具有调用能力。本文只需要掌握上面这件可运行的事：函数可以先保存，稍后再加上括号执行。

## 把操作名称和函数放在一张表里

既然函数可以保存，就可以把“名称对应哪个函数”单独列出来。先用一个局部片段观察这个关系；这里假设两个处理函数已经定义好，完整代码在下一节。

```js
const handlers = new Map();
handlers.set("list", handleList);
handlers.set("complete", handleComplete);
```

`Map` 是 JavaScript 提供的一种保存对应关系的对象。这里左边的名称叫**键**，对应保存的函数叫**值**。`new Map()` 创建一张空表；`set` 放入一组对应关系；`get` 根据名称取出对应的值。

因此，`handlers.get("complete")` 会取出刚才保存的 `handleComplete` 函数。如果没有放入这个名称，`get` 返回 `undefined`，表示没有找到对应的值。规范中的 [Map 查找与保存规则](https://tc39.es/ecma262/multipage/keyed-collections.html#sec-map.prototype.get)给出了这两个操作的行为。

负责处理一项请求的函数，通常叫**处理器**。把操作名称与处理器对应起来的表，叫**处理器表**；按名称选择处理函数时，也经常称为**路由表**。“路由”在这里指选择请求要交给哪个函数，不要求程序连接网络。

上面两次 `set` 的工作叫**登记**或**注册**：让分发入口知道某个名称对应哪个处理函数。本例只是往表里保存函数，没有启动后台工作，也没有把任务标为完成。

名称与函数名还可以不同。`"complete"` 是交给调用者使用的操作名称，`handleComplete` 是代码里负责处理它的函数名。两者由这一行 `set` 联系起来，语言不会根据拼写自动匹配。

## 处理器表的完整实现

示例包的 `by-table.mjs` 如下。与条件分支版本相比，请求检查保持相同，选择功能的部分改成查表。

```js
export function createTableDispatcher(taskList) {
  function handleList() {
    return { ok: true, tasks: taskList.listTasks() };
  }
  function handleComplete(request) {
    return taskList.completeTask(request.id);
  }

  const handlers = new Map();
  handlers.set("list", handleList);
  handlers.set("complete", handleComplete);

  function dispatch(request) {
    if (typeof request !== "object" || request === null || Array.isArray(request)) {
      return { ok: false, reason: "invalid-request" };
    }
    if (typeof request.action !== "string" || request.action.trim() === "") {
      return { ok: false, reason: "invalid-action" };
    }

    const handler = handlers.get(request.action);
    if (handler === undefined) {
      return { ok: false, reason: "unknown-action" };
    }
    return handler(request);
  }
  return dispatch;
}
```

使用时仍然是先创建任务列表，再创建入口：

```js
import { createTaskList } from "./tasks.mjs";
import { createTableDispatcher } from "./by-table.mjs";

const taskList = createTaskList();
const dispatch = createTableDispatcher(taskList);
console.log(dispatch({ action: "complete", id: "t1" }));
```

两种入口收到同一份请求，约定的结果也相同。区别在于寻找功能的位置：分支版本在 `dispatch` 里比较名称；表版本在 `dispatch` 里取得一个函数，再执行这个函数。要知道 `"complete"` 最后做什么，还需要找到登记位置和处理函数的定义。

这就是开头所说的间接调用：先根据名称找到函数，再调用找到的函数。`handler(request)` 执行哪一个函数，要看前一行从表中取到了什么。读代码时增加了一次查找，程序组织也增加了一个需要维护的对应关系。

这层查找的收益是，`dispatch` 可以使用同一段查找代码处理已登记的操作。每一项操作各自怎样执行，写在对应处理器中。操作名称和对应函数集中列出时，维护者也有一个地方检查入口究竟提供了哪些功能。

## 为什么表里还需要两个处理函数

表里有 `handleList` 和 `handleComplete`，而任务对象已经有 `listTasks` 和 `completeTask`。是否可以直接把后两个函数存进去？

先看当前入口约定：查到的处理器统一收到整份 `request`。但完成任务函数需要的是编号字符串，而不是整份请求对象。

```js
function handleComplete(request) {
  return taskList.completeTask(request.id);
}
```

这几行取出 `id`，再按任务函数原来的方式调用。负责在两种使用方式之间转换的代码，经常叫**适配代码**。这里适配的就是“收到请求对象”和“需要任务编号”之间的差别。

如果直接登记 `taskList.completeTask`，入口后面仍执行 `handler(request)`，完成任务函数就会收到对象。按照上一篇的约定，它会把对象判为非法编号，返回 `invalid-id`。请求里面即使有正确的 `id`，也没有自动被取出来。

列出任务的差别在结果上。`listTasks` 返回任务数组，入口约定返回带 `ok` 和 `tasks` 的对象。`handleList` 完成这个转换。它没有声明参数，是因为它不需要读取请求里的任何信息；入口传入的请求在这里被忽略。

因此，需要分别判断表和处理函数的用途。表集中保存操作名称与功能的对应关系，两个处理函数转换参数或结果。这些是当前代码里能够指明的工作。如果两个接口本来完全相同，转调函数也没有增加任何规则，就需要重新判断它是否值得单独存在。

本例也没有要求任务函数读取操作名称。`completeTask` 仍然可以被其他代码直接调用；它只负责按编号完成任务。

## 沿着一次请求，找到真正修改数据的位置

现在追踪这份请求：

```js
{ action: "complete", id: "t1" }
```

使用表版本时，执行过程是：

1. 使用入口的代码调用 `dispatch`，交出整份请求。
2. `dispatch` 检查请求对象和操作名称。
3. `handlers.get("complete")` 找到 `handleComplete`。
4. `handler(request)` 执行这个处理函数，交出整份请求。
5. `handleComplete` 取出 `request.id`，调用 `taskList.completeTask("t1")`。
6. 完成任务函数找到 `t1`，把它的 `completed` 改为 `true`，交回结果。
7. 结果经过两个 `return` 回到最初使用入口的代码。

`return` 表示结束当前函数执行，并把指定的值交给调用者。这几个 `return` 没有重复完成任务，也没有自动复制结果；它们把任务函数已经产生的结果继续交回。结果中的任务副本仍由原来的任务函数创建。

在这条路径上，真正修改任务数据的地方仍是 `completeTask`。查表没有移动这项责任。它改变了如何到达这段代码，以及调用者需要提供什么信息。

分支版本的路径稍短：`dispatch` 看到 `"complete"` 后，直接取出编号并调用任务函数。直接调用版本更短，调用者直接把编号交给任务函数。理解三种安排时，可以沿着同一份输入比较这些步骤，不必先给某一种贴上“高级”的标签。

## 登记函数时加上括号，会发生什么

下面是故意写错的片段，完整演示在 `pitfalls.mjs` 中：

```js
const taskList = createTaskList();
const wrongHandlers = new Map();
wrongHandlers.set("complete", taskList.completeTask("t1"));
```

JavaScript 需要先计算传给 `set` 的值。由于右边有 `("t1")`，完成任务函数立即执行，`t1` 已经被标为完成。表里保存的是这次执行产生的结果对象。

这会带来两处可观察的问题：创建入口的阶段就修改了任务；以后按名称取出的值又无法当作函数调用。

示例输出是：

```text
错误登记后 t1 已完成： true
表里保存的类型： object
尝试调用保存的结果： TypeError
```

`TypeError` 是 JavaScript 用来表示某类操作与值的能力不匹配的错误。在这里，代码想调用一个普通结果对象，而这个对象不是函数。

正确登记的是函数本身：

```js
handlers.set("complete", handleComplete);
```

参数要等真正收到请求时再取得。如果创建入口时还没有请求，却已经写出 `completeTask("t1")`，就应当检查自己是否提前做了原本要以后才做的事。本文的行为检查还会专门确认：创建两种入口时，任务操作的执行次数都为零。

## 同一份请求，可能在哪一层被拒绝

入口有了请求检查，任务函数原来的检查还要不要保留？在本例中，两层承担的条件不同。

`dispatch` 知道当前入口接收什么形状的请求、允许哪些操作名。`completeTask` 知道合法任务编号是什么、任务是否存在、完成时应当改变什么。这部分与待办任务本身有关的代码，也常叫**业务代码**；这里“业务”就是任务操作的具体规则。

请求 `{ action: "complete" }` 有合法操作名，所以能够找到处理器。处理器把缺失的 `id` 交给任务函数，后者返回 `invalid-id`。请求 `{ action: "complete", id: "t9" }` 的编号格式合法，但任务不存在，因此返回 `not-found`。

把这些情况全部改成入口的 `unknown-action` 会丢掉信息。页面原本能区分“操作名称写错”和“任务不存在”，修改后就难以给出准确提示。统一入口应当保留哪些失败，也需要像成功结果一样明确。

入口也没有把一切错误转成结果对象。如果任务函数由于程序错误意外抛出异常，当前两个入口都让异常继续交给它们的调用者。**异常**是让正常执行中断并交出错误的机制，与正常返回 `{ ok: false }` 不同。示例用故意抛错的替代函数检查了这一点，没有把异常改写为成功或未知操作。

如果以后加入文件保存、需要等待的操作，错误怎样处理还会出现新的选择。这里先保留本地函数当前的行为，不把尚未实现的处理写成保证。

## 这次改写怎样改变了代码之间的依赖

前面把依赖解释为一段代码正常工作时所依靠的功能、数据或约定。现在可以用两个实际调用，观察它们依靠的内容发生变化时，哪些代码可能需要修改。

直接调用 `taskList.completeTask("t1")` 的代码，要知道任务对象有 `completeTask`，它接收编号，以及返回值怎样判断成功。这就是它对任务接口的依赖。

改成 `dispatch({ action: "complete", id: "t1" })` 后，使用入口的代码要知道 `dispatch`、操作名称 `"complete"`、编号字段 `id` 和结果约定。它可以不知道处理函数具体叫什么，但仍然依靠这几项规则。

同一个功能改成间接调用后，需要逐处看依赖移到了哪里：

| 代码所在位置 | 当前必须知道的内容 |
| --- | --- |
| 使用分发入口的代码 | 入口函数、操作名称、请求字段、结果约定 |
| 表版本的 `dispatch` | 请求检查、按名称查表、没有对应项时拒绝、把请求交给处理器 |
| 表中的登记代码 | 哪个公开操作名对应哪个处理函数 |
| `handleComplete` | 请求里哪里放编号，以及完成任务函数怎样使用 |
| `completeTask` | 编号和任务数据的规则，不需要知道 `action` 或处理器表 |

这种安排可以让两类名称分开变化。假如内部函数从 `completeTask` 改名为 `markTaskDone`，但请求仍叫 `"complete"`，使用请求入口的代码可以继续发送原来的名称。负责调用内部函数的适配代码需要修改，登记关系和任务实现也要保持正确。

反过来，如果公开操作名从 `"complete"` 改为 `"finish"`，只改内部函数名并没有用。表里的名称和所有发送请求的代码需要配合修改，或者入口暂时同时接受两个名称。怎样过渡属于接口兼容性的选择：已有使用者能否继续按原来的方式完成工作。

这解释了为什么“换成处理器表就没有依赖了”不能作为判断。当前调用者依靠的规则可以逐项写出来；减少了哪些必须知道的内部细节，也应当逐项说明。

## 新增统计功能，究竟要改哪里

假设程序需要显示还有多少任务没完成，新增操作名叫 `"count-open"`。先写负责统计的函数；下面片段位于创建入口的函数内部，使用同一份 `taskList`：

```js
function countOpenTasks() {
  let count = 0;
  for (const task of taskList.listTasks()) {
    if (task.completed === false) {
      count += 1;
    }
  }
  return { ok: true, count };
}
```

`for ... of` 逐项读取任务，看到尚未完成的任务就把计数加一。统计通过已有的 `listTasks` 取得数据，当前不需要给任务对象增加新接口。它会读取一份任务列表副本；是否值得为很大的列表增加单独的统计接口，需要按实际数据与需求重新判断，本文没有测量性能。

分支版本在返回 `unknown-action` 之前，增加这段选择：

```js
if (request.action === "count-open") {
  return countOpenTasks();
}
```

表版本增加一项登记：

```js
handlers.set("count-open", countOpenTasks);
```

两种方案都要写统计函数，都要规定操作名称和结果。发送统计请求的代码、界面显示和行为检查，也都需要增加对应内容。表版本在这个变化中的具体收益是：通用的 `dispatch` 查找代码不用增加第三个分支；新操作通过表项接入。

“没有修改 `dispatch` 的函数体”和“新增功能不用修改旧代码”是不同范围的说法。本例的表仍然写在同一个创建函数里，新增操作要修改这份文件。换一种文件组织能进一步改变修改位置，但还需要比较它的维护成本，下一篇会继续讨论。

完整的两种扩展方案位于 `extended.mjs`，与基础方案分开保存，便于对照。可以在示例目录运行：

```sh
node --input-type=module -e '
import { createTaskList } from "./tasks.mjs";
import { createExtendedTableDispatcher } from "./extended.mjs";
const dispatch = createExtendedTableDispatcher(createTaskList());
console.log(dispatch({ action: "count-open" }));
dispatch({ action: "complete", id: "t1" });
console.log(dispatch({ action: "count-open" }));
'
```

先得到 `{ ok: true, count: 2 }`，完成 `t1` 后得到 `{ ok: true, count: 1 }`。分支扩展方案也得到相同结果。这里新增的是一种读取任务的方式，完成任务原来的结果与失败处理继续保留。

## 把共同工作放在入口，什么时候有帮助

假设之后需要记录每次操作的名称和执行结果，方便查看发生过什么。这样的记录通常叫**日志**。这一项是假设的新需求，当前示例没有实现日志保存。

如果许多操作都经过 `dispatch`，可以考虑在这里记录：入口已经有请求，执行处理器后又能取得结果。这样有机会集中处理相同工作，而不必让每个任务函数分别读取操作名称。

不过，共同入口也要选对范围。例如，产品要求记录“用户从这个请求入口发起的操作”，在 `dispatch` 记录就符合范围。产品要求记录“所有任务完成操作”，而其他代码还在直接调用 `completeTask`，只改分发入口就会漏掉那些直接调用。

分支版本同样可以集中做这件事，只需让各分支的执行结果回到共同的记录位置。共同入口的收益并不是处理器表独有的；表版本让“找到处理器并执行”的代码比较统一，可能更容易把共同的前后处理放在附近。

也要检查各项操作是否真的具有相同规则。列出任务和完成任务使用的输入不同，未来允许执行它们的条件也可能不同。共同检查可以放在入口，各操作独有的条件仍需要有明确位置。只为了让入口看起来整齐，把不同规则压成一个含义模糊的判断，会增加使用者猜测结果的工作。

## 使用普通对象作表，为什么要检查名称是否确实登记

JavaScript 普通对象也可以保存名称和函数。例如：

```js
const objectHandlers = {
  list: function handleList() { return "任务列表"; },
};
console.log(typeof objectHandlers["toString"]);
```

这里用的是局部语法演示，`handleList` 只返回一段文字。`objectHandlers["toString"]` 表示按字符串读取对象属性，打印出的类型却是 `function`。我们明明只写了 `list`，为什么还能读到 `toString`？

普通对象可以沿着一条关联关系取得其他对象提供的属性，这条关系称为**原型链**。本例读到的是通过原型链得到的 `toString` 函数。对象上提供的函数，也常叫**方法**。只判断“取到的值是不是函数”，并不足以确认它是我们明确提供的操作。

对象自己直接拥有的属性，叫**自有属性**。`Object.hasOwn(objectHandlers, "toString")` 可以检查这个名称是否属于当前对象自身；在本例中结果是 `false`。语言规范的 [Object.hasOwn](https://tc39.es/ecma262/multipage/fundamental-objects.html#sec-object.hasown) 条目说明了这个检查。

如果用普通对象实现处理器表，就应当先确认名称是自有属性，再取得并调用对应函数。本文选择 `Map`，它的 `get` 读取的是明确保存的键值关系。没有登记 `"toString"`，`handlers.get("toString")` 就是 `undefined`，按未知操作拒绝。

这里仍要分清 `handlers.get("toString")` 和 `handlers["toString"]`：前者查 Map 保存的表项，后者读 Map 对象本身的属性。Map 对象也有自己的方法，选择这种表示方式以后，查表仍要使用它提供的 `get`。

这个选择只解决操作名称查找的这一处歧义。示例的处理函数由文章中的代码固定提供，请求也限于前面说明的普通数据。它没有实现用户身份、操作权限或任意外部代码的隔离；仅靠“名称在表里”无法回答某位使用者是否被允许完成某条任务。

## 同名登记会覆盖，表不会替你发现拼写错误

`Map` 允许对同一个键再次执行 `set`。第二次保存的值会替换第一次的值，可以运行下面这个独立例子：

```js
const handlers = new Map();
function first() { return "第一次登记"; }
function second() { return "第二次登记"; }
handlers.set("list", first);
handlers.set("list", second);
console.log(handlers.get("list")());
```

输出为 `第二次登记`。这符合 [Map 保存规则](https://tc39.es/ecma262/multipage/keyed-collections.html#sec-map.prototype.set)，但不一定符合应用希望的规则。如果许多位置都能登记处理器，同名操作应当覆盖、拒绝还是合并，需要由应用规定。

当前示例的表只在一个创建函数内固定登记两项，没有向外提供修改表的方法。维护者能够直接检查这些名称。假设以后真的增加由其他代码文件登记操作的能力，就还需要处理重复名称、登记顺序和替换时机，不能把这些尚未解决的问题算作当前表的收益。

名称拼写也一样。把 `"complete"` 错写成 `"compelete"`，Map 会如实保存这个新名称；它不知道哪个英文才符合我们的约定。界面继续发送 `"complete"` 时，就会得到 `unknown-action`。本文使用 JavaScript，运行时请求检查和行为测试提供了一部分检查；表本身不自动证明所有使用者与登记代码保持一致。

## 定位一个失败，需要多找哪些位置

假设用户点了完成按钮，页面收到 `unknown-action`。直接去看 `completeTask` 的数据修改过程，可能还找不到原因，因为请求没有执行到那里。

可以按当前实现的实际步骤检查：页面发出的 `action` 是什么，入口是否原样读到了这个字段，表里是否登记相同名称，对应值是不是预期处理函数。只要查表失败，后面的任务编号和任务查找还没有执行。

如果结果是 `invalid-id`，说明本例已经选择了完成操作。此时应继续看页面是否提供 `id`，处理器是否正确取出它，以及传给任务函数的值是否符合编号约定。

如果结果显示成功，但界面仍显示未完成，就还要检查界面是否重新读取任务、是否使用结果里的任务副本。这些属于后续使用结果的代码；改变查表写法不会自动修复它们。

直接调用时，名称转换和处理器这一层不存在。分支版本把名称与实际调用写在一起。表版本把名称关系和执行过程分开，定位问题时往往需要跨过登记位置。把登记集中放好、给处理器起清楚的名字、保留可以区分的失败结果，能帮助维护者沿路径查找；它们并不会让路径消失。

这里讨论的阅读成本，是为了理解一次操作需要查看哪些代码。没有为三种写法测量运行时间，也没有从代码行数推出哪一种“复杂度更低”。判断需要回到实际维护任务。

## 三种安排放在同一组条件下比较

直接调用和按名称分发服务的需求不同。前者适合调用者已经知道要使用哪项功能；后两者满足“收到操作名称后再选择功能”的需求。比较时应当先确认这项需求是否存在。

| 比较的问题 | 直接调用 | 条件分支入口 | 处理器表入口 |
| --- | --- | --- | --- |
| 调用者提供什么 | 任务函数需要的参数 | 带操作名的请求 | 带操作名的请求 |
| 操作名称在哪里解释 | 没有这一步 | 每个分支条件里 | 名称与函数的登记表里 |
| 参数或结果在哪里转换 | 调用者直接按任务接口使用 | 对应分支里 | 对应处理器里 |
| 新增一种按名称选择的操作 | 需要另建选择过程 | 增加分支及功能实现 | 增加表项及功能实现 |
| 读一次完成任务需要看哪里 | 调用位置、任务函数 | 请求、对应分支、任务函数 | 请求、查找、登记、处理器、任务函数 |
| 能否集中处理入口的共同规则 | 需另外安排共同位置 | 可以 | 可以 |

对当前只有列出和完成两项操作的示例，如果需求已经确定要使用请求对象，我会先选条件分支：选择关系很短，参数转换就在分支里。等操作增加、处理方式比较一致，集中查看名称关系比逐个读分支更有帮助时，再考虑表。

这不是按某个操作数量自动换方案。五项很短的操作可能仍然容易阅读，两项接收方式完全不同的操作也可能不适合硬凑成同一种处理器。具体要看新增功能改了什么、共同规则是否已经重复，以及维护者能否顺利找到执行代码。

同一个程序也可以同时保留直接调用与请求入口。演示脚本按名称发送请求，内部已知用途的代码直接使用任务接口。这样做时，需要决定哪些规则属于任务本身，确保它们在直接调用时仍然成立；哪些规则只属于请求入口，允许只对这类请求生效。

## 运行示例，检查行为是否保持一致

[下载完整示例包](software-design-03-examples.zip)。解压后进入 `software-design-03-examples` 目录。

本次在 macOS arm64、Node.js **25.9.0** 下运行示例。Node.js 是在浏览器外执行 JavaScript 的运行环境。示例只使用它提供的功能，没有第三方依赖，无需安装依赖包；运行以下命令即可：

```sh
node function-value.mjs
node demo.mjs
node pitfalls.mjs
node --test dispatch.test.mjs
```

`function-value.mjs` 演示保存函数与立即调用的区别。`pitfalls.mjs` 演示提前执行、普通对象属性查找和同名覆盖。两处故意写错的行为都与正式分发入口分开，便于观察原因。

`demo.mjs` 分别创建两份独立任务，交给条件分支和处理器表处理。两组输出中，相同请求的结果一致。下面列出每组对应的结果，省略左侧重复打印的请求：

```text
{"ok":true,"tasks":[{"id":"t1","title":"写周报","completed":false},{"id":"t2","title":"整理笔记","completed":false}]}
{"ok":true,"changed":true,"task":{"id":"t1","title":"写周报","completed":true}}
{"ok":true,"changed":false,"task":{"id":"t1","title":"写周报","completed":true}}
{"ok":false,"reason":"not-found"}
{"ok":false,"reason":"invalid-id"}
{"ok":false,"reason":"unknown-action"}
```

这六项依次对应列出任务、首次完成 `t1`、重复完成 `t1`、完成不存在的 `t9`、缺少任务编号，以及请求 `"toString"`。

最后一个命令运行 **22 项测试**，本次全部通过。测试是把输入、执行过程和预期结果写成可重复运行的检查。这里重点检查：创建入口不执行任务；请求只执行选中的功能；非法请求和未知名称不会改动任务；参数按约定传入；完成任务的结果、副本和失败处理继续成立；两种方案处理相同请求后，结果与最终数据一致。

扩展方案还检查了统计值从二变为一，以及新增操作后原来的列出、完成和失败结果仍然成立。故意抛错的任务函数用于观察异常是否原样继续传出。测试结果支持的是这些输入与当前实现下的行为，没有检查界面、文件保存或网络通信。

示例中的 `tasks.mjs` 与上一篇保持相同，便于把注意力集中在新增的选择过程。`by-branch.mjs` 与 `by-table.mjs` 是两个独立比较方案；`extended.mjs` 保留新增统计功能后的完整版本。这样可以直接对照修改位置，而不必猜测文章片段应当插到哪里。

## 再做一次会影响选择的变化

可以继续增加“只列出尚未完成任务”的操作，名称自己选定，先写清输入和成功结果，然后分别加入分支版与表版。

记录实际需要修改的地方：发送请求的代码、名称选择的位置、过滤任务的函数，以及行为检查。完成后，找一个同学或隔几天后的自己，从请求出发寻找实际读取数据的代码，看看是否容易找到。

还可以做一个不同性质的变化：只把内部完成任务函数改名，保留公开操作名不变。比较直接使用任务接口的代码和使用请求入口的代码，哪些位置需要跟着修改。这个练习能检查你是否分清了函数名与操作名，以及登记关系究竟替谁隐藏了哪些细节。

最后为自己的版本写几句话：是否需要按名称选择功能，当前选择关系放在哪里更容易理解，新增一项功能需要改什么，以及哪一种后续需求会让你重新考虑。选择说明能够对应实际代码，比单独写“表更灵活”更有帮助。

当处理器、登记关系和任务函数开始分到不同文件里，还会遇到下一组问题：哪些代码应该放在一起，哪个文件应该知道哪些细节，怎样让内部表示变化少影响其他代码。[下一篇：模块边界与信息隐藏](/articles/software-design-04-module-boundaries/)会沿用这个程序，比较按操作拆文件与集中维护任务表示的收益和代价。

## 资料与复现范围

语言行为核对到 **2026 年 10 月 14 日**，来源是 TC39 维护的 ECMAScript 在线规范，具体条目已在对应段落给出。核对时页面标为 ECMAScript 2027 工作稿；这是在线工作稿的标识，不表示 2027 年正式标准已经发布。读本文无需通读规范，可以先运行示例，再按需要核对函数调用、Map 和自有属性的语义。

三种方案的适用条件、任务案例与取舍比较，是本文依据这些语义和运行结果作出的分析。规范说明代码怎样执行，示例检查约定是否保持；是否值得增加一次查找，还要由实际需求和维护过程判断。
