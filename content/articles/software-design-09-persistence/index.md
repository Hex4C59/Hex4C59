+++
title = "持久化与设计演化：任务保存后，怎样重新读回来"
date = 2026-10-15T00:00:00+08:00
lastmod = 2026-10-17
draft = false
author = "Hex4C59"
description = "把任务保存、退出与重新读取接起来，解释持久化、文件格式验证和版本迁移，处理缺失或损坏文件，并比较直接覆盖与先写临时文件再替换的范围。"
summary = "写出文件以后，还要决定下次启动相信哪些内容。沿用上一章任务所有者，新增文件读取、验证和启动组合，显式初始化新文件，兼容旧数组格式，并通过独立进程检查任务能否保留。"
tags = ["持久化", "JSON", "接口设计"]
categories = ["engineering"]
source_kind = "original"
article_type = "concept"
series = ["software-design"]
series_role = "chapter"
series_order = 9
series_number = 9
series_part = "保存、重读与应用边界"
difficulty = "beginner"
ShowToc = true
+++

待办事项程序完成一条任务，把新数据写进文件，然后退出。第二次启动时，如果仍然从代码中的两条默认任务开始，刚才的修改就没有回到程序里。

前几篇已经演示保存文件，但还没有完整安排重新打开文件的过程。这次需要回答：读到了什么才允许创建任务对象？文件不存在和文件损坏，能不能用同一个默认值处理？旧文件格式怎样继续使用？

本篇的选择是：**先读取并验证文件，成功后才创建任务对象；初始化由明确命令触发，读取失败不自动变成默认任务。** 新的文件写入带版本的格式，原来的数组文件仍能读取，在首次成功修改时升级。

**持久化**在这里指把任务保存在文件中，使程序正常退出、重新启动后，仍能取得此前保存的数据。它需要保存和重新读取共同配合。本章验证正常退出与重开，没有验证突然断电后仍能保留的更强条件。

**进程**是操作系统中一次正在运行的程序。连续执行三条 `node` 命令，会分别启动三个进程。我们会用前一个进程完成修改并退出、后一个进程重新读取，检查数据确实来自文件。[4]

本文面向能阅读简单 JavaScript 的读者，继续沿用待办事项程序。[第八篇](/articles/software-design-08-refactoring/)的任务所有者、完成计算和 Map 管理保持原样，新增文件格式、存储模块、启动函数及命令行入口。范围限定为普通本地文件，父目录已存在，同一时刻每个文件只有一个任务所有者。

## 1. “已经写文件”和“下次还能用”之间缺了什么

原来的保存函数接收任务数组，把它写成文本。调用者等待保存成功，任务模块再采用新数据。这解决了当前操作何时接受修改的问题。

重新启动以后，内存中的 Map、忙碌标记和对象都需要重新创建。程序必须先读文件，把文本还原为数据，再确认数据适合交给任务模块。

这里使用 **JSON（JavaScript Object Notation）**，一种用对象、数组、字符串、数字等表示数据的文本格式。`JSON.stringify` 把数据转成文本，`JSON.parse` 把文本解析成 JavaScript 值；格式不合法的文本会在解析时报告错误。[1]

解析成功只说明文本符合 JSON 语法。`{"completed":"false"}` 同样是合法 JSON，其中的 `"false"` 却是字符串，并不是任务需要的布尔值 `false`。

所以，新过程包含几项不同的工作：读到文本、解析文本、验证任务、创建任务对象。任何一步失败，都应当有明确结果，不能因为后面的代码需要数组，就随便提供一个数组继续运行。

## 2. 先决定启动失败时怎么办

本例对读取结果作出以下选择：

| 读取到的条件 | 启动结果 | 是否创建任务对象 |
| --- | --- | --- |
| 路径不存在 | `missing-file` | 否，提示需要明确初始化 |
| 其他文件读取失败 | `read-failed` | 否 |
| 文本不是合法 JSON | `invalid-json` | 否，保留原文件 |
| 数据字段不符合约定 | `invalid-data` | 否，保留原文件 |
| 文件声明了不支持的版本 | `unsupported-version` | 否，保留原文件 |
| 合法的旧任务数组 | 成功，标记 `legacy-array` | 是，读取本身不重写文件 |
| 合法的版本一文件 | 成功，标记 `v1` | 是 |

失败结果都有 `ok: false` 和表中的 `reason`。成功读取除了任务，还记录读到的格式，便于观察旧文件何时升级。

程序也可以选择第一次运行时自动创建新文件，但那需要明确区分“没有数据”和“已有数据暂时读不出来”。本例选择显式初始化，是为了让“建立一份新任务”成为清楚的操作。

对随时可以重新生成的缓存，丢弃旧文件的代价可能很低。这里保存的是希望继续保留的任务修改，因此遇到损坏时选择停止，让原文件留在现场。判断来自数据用途，并非所有程序都必须采取同样的策略。

## 3. 为什么“失败就用默认任务”会覆盖原内容

下载包保留一份故意错误的启动函数，完整代码如下：

```js
// 故意错误：把所有读取失败都替换成默认任务。
import { createAsyncTaskList } from "../task-list.mjs";
import { defaultTasks } from "../initial-tasks.mjs";

export async function openWithReset(store) {
  const loaded = await store.load();
  return {
    ok: true,
    format: loaded.ok ? loaded.format : "fallback",
    taskList: createAsyncTaskList(store.saveSnapshot, loaded.ok ? loaded.tasks : defaultTasks),
  };
}
```

它位于 `faults/reset-on-error.mjs`，路径按那个目录填写，不能当作正式实现使用。

假设文件保存过用户修改，但内容被截断，解析失败。这个函数仍然报告启动成功，并把写周报和整理笔记两条默认任务交给任务对象。用户接着完成一条任务，保存函数就用这份默认数据产生的新内容替换原文件。

读错文件时没有直接写盘，后续一次正常操作却完成了覆盖。因此，检查不应只问“读取函数有没有修改文件”，还要问“读取失败以后，程序是否已经拿一份替代数据继续运行”。

本章演示会在自己创建的临时目录里实际执行这个反例。正确启动器保留损坏内容，错误版本在后续保存后改变了它；这不是对读者已有文件的操作。

## 4. 文件格式与程序版本是两回事

前几篇写出的文件，最外层直接是一份任务数组：

```json
[
  { "id": "t1", "title": "写周报", "completed": false },
  { "id": "t2", "title": "整理笔记", "completed": false }
]
```

现在写出的格式增加一层对象：

```json
{
  "version": 1,
  "tasks": [
    { "id": "t1", "title": "写周报", "completed": false },
    { "id": "t2", "title": "整理笔记", "completed": false }
  ]
}
```

`version` 是文件格式版本，用来识别这份数据按什么约定组织。它不是应用发布版本号；程序修改了按钮颜色，并不需要因此更改数据格式版本。

这次选择保留两种读取方式：外层是数组，按旧格式验证；外层是对象，检查版本及任务字段。所有新保存都写版本一。

这已经是一次明确的文件行为变化。第八篇要求外部文件格式不变，本篇新增读取与格式演化需求，重新确定了边界，不能把它笼统称为一次完全不改变行为的重构。

## 5. 读取边界要补上过去的输入前提

任务所有者要求初始数据合法、编号唯一。过去由演示代码直接构造任务，调用者负责满足这些前提；现在文件可能缺字段、改过类型，或者包含重复编号。

因此，创建 Map 以前要验证这些条件。否则两个相同编号进入 Map 后，不能继续按同一个键分别保留两条记录。

`validate-tasks.mjs` 的完整代码是：

```js
export function isValidTasks(tasks) {
  if (!Array.isArray(tasks)) return false;
  const ids = new Set();
  for (const task of tasks) {
    if (task === null || typeof task !== "object" || Array.isArray(task)) return false;
    const keys = Object.keys(task);
    if (keys.length !== 3 || !keys.every(key => ["id", "title", "completed"].includes(key))) {
      return false;
    }
    if (typeof task.id !== "string" || task.id.trim() === "" || ids.has(task.id)) return false;
    if (typeof task.title !== "string" || typeof task.completed !== "boolean") return false;
    ids.add(task.id);
  }
  return true;
}
```

`Set` 是保存不重复元素的集合。这里用它记录已经出现的编号，`has` 判断某个编号是否见过，`add` 记录新的编号。

验证要求每条任务包含且只包含 `id`、`title`、`completed`，编号是非空白字符串，标题是字符串，完成标记是布尔值，编号不能重复。

这里没有把编号前后的空格自动删掉，也没有把字符串 `"false"` 猜成布尔值。自动修改输入会引入另一套规则，应当在确实需要时另行约定。

## 6. 为什么拒绝未知字段，空数组却应该接受

旧的复制函数只保留三个任务字段。假如读取一条带 `note` 的任务后，忽略 `note` 并允许保存，下一次写出时，这个字段就会消失。

本例选择拒绝未知字段，提醒调用者当前程序还不理解这份数据。以后增加字段时，需要明确更新格式和处理规则，而不是靠忽略字段来假装兼容。

这也有代价：手工加一个备注字段，当前程序就会拒绝读取。选择严格规则，是因为本例优先避免读入后再悄悄丢失未知内容；如果应用需要保留扩展字段，就应当让读取、内部表示和保存一起支持它。

空任务数组则完全合法。`[]` 表示没有任务，与文件不存在、解析失败都不同。文件模块已经支持初始化空数组，启动后也应当保持为空。

本章命令行的 `init` 固定创建两条合成任务，便于继续使用 `t1`、`t2`；这不是把空数组当作失败的理由。完整检查专门验证了读回空数组时，不会重新出现默认任务。

## 7. 把文本转换集中在一个模块里

**编码**在本文中指把任务数据转换成文件文本；**解码**指把文本转换回经过验证的任务。`task-file-codec.mjs` 负责这两项工作，不读写文件。

完整代码如下：

```js
import { copyTasks } from "./copy-tasks.mjs";
import { isValidTasks } from "./validate-tasks.mjs";

export function decodeTaskFile(text) {
  let value;
  try {
    value = JSON.parse(text);
  } catch {
    return { ok: false, reason: "invalid-json" };
  }
  if (Array.isArray(value)) {
    if (!isValidTasks(value)) return { ok: false, reason: "invalid-data" };
    return { ok: true, format: "legacy-array", tasks: copyTasks(value) };
  }
  if (value === null || typeof value !== "object" || !Number.isInteger(value.version)) {
    return { ok: false, reason: "invalid-data" };
  }
  if (value.version !== 1) return { ok: false, reason: "unsupported-version" };
  const keys = Object.keys(value);
  if (keys.length !== 2 || !keys.every(key => ["version", "tasks"].includes(key))) {
    return { ok: false, reason: "invalid-data" };
  }
  if (!isValidTasks(value.tasks)) return { ok: false, reason: "invalid-data" };
  return { ok: true, format: "v1", tasks: copyTasks(value.tasks) };
}

export function encodeTaskFile(tasks) {
  if (!isValidTasks(tasks)) throw new TypeError("任务数据不符合文件格式");
  return JSON.stringify({ version: 1, tasks: copyTasks(tasks) }, null, 2) + "\n";
}
```

解析与验证分开报告原因。一个声明版本二的对象会先得到 `unsupported-version`，程序不会继续用版本一的字段要求解释它。

写出时也验证一次，防止文件模块直接收到非法任务时仍产生正式文件。任务所有者传来的数据应当已经合法，但文件模块也可以被其他代码调用，因此它自己的输入约定仍需要落实。

`JSON.stringify` 后面的 `null, 2` 让文件按两格缩进排版，末尾再加换行。排版方便阅读，不承担任务规则的含义；读取不要求字段按某个文本缩进出现。

## 8. 先把读取成功，再创建任务对象

`open-task-app.mjs` 负责先读文件，再用读到的任务创建对象，把这两步接成启动过程。完整代码如下：

```js
import { createAsyncTaskList } from "./task-list.mjs";

export async function openTaskApp(store) {
  const loaded = await store.load();
  if (loaded.ok === false) return loaded;
  return {
    ok: true,
    format: loaded.format,
    taskList: createAsyncTaskList(store.saveSnapshot, loaded.tasks),
  };
}
```

`store` 是文件存储模块提供的对象，包含读取和保存函数。启动器先等待读取结果；失败时返回原因，成功时才创建任务对象。

这就把“尚未取得可信初始任务”与“可以完成任务”分开了。失败结果里没有可以继续修改的 `taskList`，调用者需要先处理启动问题。

同时，不必把旧的 `createAsyncTaskList` 改成异步函数。它仍同步接收合法任务并创建对象；新增的 `openTaskApp` 负责等待外部文件，明确返回 Promise。调用者能从两个入口的职责看出谁需要等待。

`format` 记录这次读取到的文件格式，不是实时监控字段。保存后想确认磁盘当前格式，应当重新读取，不能假定原来的 `opened.format` 自动更新。

## 9. 初始化要表达“只创建，不覆盖”

文件不存在时，用户明确执行 `init`。初始化接收演示任务，编码后写成新文件；如果路径已经存在，就返回 `already-exists`。

关键调用是：

```js
// initialize 方法中的局部片段。
await writeFile(file, text, { encoding: "utf8", flag: "wx" });
```

Node.js 的 `wx` 标志表示独占创建：路径已存在时失败，避免用这次初始化覆盖已有文件。[2]

不要先判断路径是否存在，再用普通写入创建。那两次动作之间，文件情况可能已经变化。这里直接要求创建操作本身拒绝已有路径，规则更清楚。

初始化也不会帮忙建立缺失的父目录。路径选择和目录准备由调用者负责，示例演示与测试都先创建自己的临时目录。

`wx` 解决的是已有路径不能被覆盖，不表示创建过程中任何错误都不会留下新文件。如果新文件创建后只写入一部分就失败，下一次仍可能遇到损坏内容。本章没有模拟系统中途故障，也没有自动删掉这种现场重新初始化。

## 10. 先跑通一次完整的保存与重读

在下载包的示例目录执行：

```sh
node restart-demo.mjs
```

演示自己创建临时目录，依次启动三个进程，并在每个进程退出后才启动下一个。输出为：

```text
创建文件：{"ok":true,"created":true}
完成并退出：{"ok":true,"changed":true,"task":{"id":"t1","title":"写周报","completed":true}}
新进程读回：{"ok":true,"format":"v1","tasks":[{"id":"t1","title":"写周报","completed":true},{"id":"t2","title":"整理笔记","completed":false}]}
```

第二个进程完成写周报并等待保存，随后退出。第三个进程没有前一个进程的任务对象，它读到的完成标记来自文件。

这比在同一进程里再次调用 `listTasks()` 多验证了一步：文件不但写出过，还能被新的程序运行读懂，并用于创建新的任务对象。

演示结束后会等待清理本次临时目录。它不使用固定睡眠猜测保存是否结束，也不读取用户已有的任务文件。

## 11. 想逐条操作，可以直接运行命令行入口

`app.mjs` 支持三个命令：

| 命令 | 作用 |
| --- | --- |
| `init 文件路径` | 明确创建两条演示任务，拒绝覆盖已有路径 |
| `list 文件路径` | 读取并验证文件，输出当前任务及读取格式 |
| `complete 文件路径 任务编号` | 先读取，再完成任务并等待保存 |

例如在解压目录中执行：

```sh
mkdir -p demo-data
node app.mjs init demo-data/tasks.json
node app.mjs complete demo-data/tasks.json t1
node app.mjs list demo-data/tasks.json
```

路径可以自选；再次执行 `init` 会得到 `already-exists`，已有内容保留。命令的正常结果输出为 JSON，`ok: false` 时退出码为 `1`，成功为 `0`。

`app.mjs` 完整代码在下载包。它只选择命令、建立存储模块、等待启动或操作结果，不自己解析任务字段，也不直接修改内部 Map。

本例每条命令完成后退出，没有常驻界面和后台保存。这样，下一条命令必然重新读取文件；如果以后增加长时间运行的窗口，还要重新考虑多个任务对象和外部修改怎样协调。

## 12. 直接覆盖文件有什么需要考虑的地方

前几篇的保存方式直接调用 `writeFile(file, text)`。这很短，但写入正式文件的过程可能已经改变原内容，不能把“最后报告失败”理解成“原文件必然完整保留”。[3]

这里把替换分成几步：在目标目录里创建本次临时文件，写完并关闭，再用它替换目标路径。准备临时内容时，正式文件还保持原来的内容。

采用这个安排，是为了减少准备新内容时直接改动正式文件的范围。它增加了临时路径、关闭和失败清理，代码也比单次写入长。若数据可以随时生成，这些成本是否值得，需要根据用途判断。

这种安排并没有自动补齐所有故障恢复。我们会分别检查替换前失败和替换已经生效后再报告错误，而不把它们统称为“保存失败后原文件不变”。

## 13. 先写临时文件，再替换目标

`replace-file.mjs` 的完整实现是：

```js
import { open, rename, rm } from "node:fs/promises";
import { dirname, basename, join } from "node:path";
import { randomUUID } from "node:crypto";

export async function replaceFile(file, text, renameFile = rename) {
  const temporary = join(dirname(file), "." + basename(file) + "." + randomUUID() + ".tmp");
  // open 成功后，才知道这个临时文件属于本次调用。
  const handle = await open(temporary, "wx");
  try {
    try {
      await handle.writeFile(text, "utf8");
    } finally {
      await handle.close();
    }
    await renameFile(temporary, file);
  } catch (error) {
    try {
      await rm(temporary, { force: true });
    } catch {
      // 保留原错误；未清理的临时文件不会作为正式数据读取。
    }
    throw error;
  }
}
```

`dirname` 取得目标的父目录，`basename` 取得文件名；新名字放在相同目录下，并用 `wx` 创建。`handle` 是打开文件后得到的操作对象，通常称为文件句柄，用它写入并在结束时关闭。

写入或关闭失败，就不继续替换；准备结束后调用 `rename`，在目标路径上替换文件。[3] 正常替换以后，临时名字已经移走，因此成功路径不需要再执行一次删除。

发生错误时，清理只针对本次已经成功创建的临时路径。若清理也失败，原错误继续报告，可能留下临时文件；启动读取只认明确的正式路径，不会随便挑一个临时文件当成最新数据。

第三个参数让检查可以替换最后一步，例如人为让替换之前失败。正式文件存储模块使用默认的真实 `rename`；下面的合成失败，不代表操作系统实际发生过相同故障。

## 14. 文件存储模块怎样连接这些部分

`file-store.mjs` 集中处理路径和文件操作，完整代码如下：

```js
import { readFile, writeFile } from "node:fs/promises";
import { decodeTaskFile, encodeTaskFile } from "./task-file-codec.mjs";
import { isValidTasks } from "./validate-tasks.mjs";
import { replaceFile } from "./replace-file.mjs";

export function createFileStore(file) {
  async function load() {
    let text;
    try {
      text = await readFile(file, "utf8");
    } catch (error) {
      return { ok: false, reason: error.code === "ENOENT" ? "missing-file" : "read-failed" };
    }
    return decodeTaskFile(text);
  }
  async function initialize(tasks) {
    if (!isValidTasks(tasks)) return { ok: false, reason: "invalid-data" };
    const text = encodeTaskFile(tasks);
    try {
      await writeFile(file, text, { encoding: "utf8", flag: "wx" });
      return { ok: true, created: true };
    } catch (error) {
      return { ok: false, reason: error.code === "EEXIST" ? "already-exists" : "create-failed" };
    }
  }
  function saveSnapshot(tasks) {
    return replaceFile(file, encodeTaskFile(tasks));
  }
  return { load, initialize, saveSnapshot };
}
```

读取失败在读取附近转换成启动能够理解的原因，解析失败和格式错误则由解码函数报告。`ENOENT` 对应路径不存在，其他读取错误不回退成新建状态。[3]

保存仍遵守原来的接口：接收任务数组，正常结束得到 `undefined`，失败抛错或拒绝。任务所有者继续等待它，并负责转换为 `save-failed`；文件模块不需要反过来修改任务的当前 Map。

路径由创建存储模块时提供，计算规则不需要知道文件名。以后调整文件组织或更换存储方式，可以在负责读写的模块中处理；但仍要把新实现与任务模块接起来检查，确认真实数据能正确保存并读回。

## 15. 旧文件什么时候升级

**格式迁移**在这里指把旧数组表示转换成带版本的表示。程序会读两种格式，但只写版本一，所以第一次成功保存实际修改时，会自然写成新格式。

读取本身不写回。重复完成一条已经完成的任务，也保持 `changed: false` 和不额外保存，因此不会为了升级而偷偷改变文件。

这是一项具体选择：迁移跟随一次实际保存。如果需要打开文件就立刻升级，或者提供专门的升级命令，应当另行规定失败和重试行为，不能假定当前已经实现。

运行 `node failure-demo.mjs`，可以看到旧文件部分的实际输出：

```text
旧格式读取： legacy-array
修改后格式： v1
重新读取标记： [true,false]
```

这里“修改后格式”来自重新打开文件，不是改写旧启动结果中的 `format`。检查还比较了整个任务数组，确认标题、另一条任务和顺序保留。

版本二的格式迁移没有实现。示例只支持旧数组与当前版本一，不需要先建立一套任意版本自动转换的框架。

## 16. 损坏文件的演示观察了什么

同一个失败演示还包含以下输出：

```text
损坏文件启动： {"ok":false,"reason":"invalid-json"}
再次初始化： {"ok":false,"reason":"already-exists"}
原内容保留： true
```

程序既没有创建一个可继续操作的任务对象，也没有允许 `init` 覆盖已经存在的损坏文件。

随后，演示对另一份自己创建的损坏文件运行错误默认值版本，完成任务以后输出：

```text
错误默认值版保留原内容： false
```

这份对照把风险落到一次具体动作上：读取失败被当成启动成功，默认任务继续参与保存，原内容被替换。

还可以运行 `node probe.mjs correct`，正常实现通过损坏启动约定；`node probe.mjs reset` 则预期失败并退出 `1`，提示“损坏文件应拒绝启动”。完整测试核对了这两个退出结果，没有为了让错误版本通过而放宽约定。

## 17. 替换前失败与替换后错误，不能混成一个保证

检查替换前失败时，我们让临时文件真实写入并关闭，在最后替换动作处人为抛错。观察到正式文件仍是原内容，本次临时文件也被清理。

另一个检查先真正完成 `rename`，随后人为抛出错误。任务所有者收到的是保存失败，因此保留旧内存；正式文件却已经包含新任务。

这个合成例子的结果是：

| 观察位置 | 完成标记 |
| --- | --- |
| 失败后当前任务对象 | `[false, false]` |
| 重新读取的正式文件 | `[true, false]` |

它与第五篇指出的限制一致：保存报错以前，文件替换可能已经完成。任务所有者收到错误后保留旧内存，并不能让文件也恢复原状。先写临时文件，可以避免在准备新内容时就直接改写正式文件，但没有实现任意失败下恢复旧内容的机制。

上述“替换后错误”由检查主动制造，不是一次真实系统中途故障测量。它用来说明当前接口能表达什么，不能把这一项通过写成已经验证断电或崩溃恢复。

本例命令遇到失败后退出，下一条命令会重新读取实际文件。若以后把同一个任务对象长期保留在窗口里，就需要明确保存结果不确定时是否停止修改、怎样重新读取，不能一直假定旧内存就是磁盘状态。

## 18. 报告原因以后，调用者应当怎样行动

把错误分开，不只是为了给终端打印更多名字。不同原因对应不同的下一步，才能避免修错问题。

路径缺失时，先核对路径和父目录。如果确实要建立新任务，再明确初始化；若只是把路径拼错，自动创建可能使程序一直在另一份文件上工作。

读取失败时，应该检查当前路径和读取条件，而不是生成默认任务。格式损坏时，先保留原文件副本，再决定是否恢复已有备份或进行人工修复。本章没有实现自动备份和修复程序。

未知版本表示当前程序不知道怎样解释这份文件。应当使用理解该格式的程序或明确的迁移办法，不能只把版本号改成 1，就假定字段和含义都已经兼容。

保存失败以后也要区分当前内存与磁盘。命令行会退出，下一次操作重新读取；长时间运行的程序则需要明确怎样停止继续修改并重新确认数据。本章没有替窗口实现这一套交互。

当前入口只交回 JSON 原因和退出状态。以后增加界面，可以把它们变成可理解的提示，但提示应当对应真实支持的动作，而不是在没有恢复功能时显示“已经自动恢复”。

## 19. 新需求究竟影响了哪些模块

本篇与第八篇的关系可以按职责核对：

| 部分 | 本次变化 | 负责什么 |
| --- | --- | --- |
| 任务所有者 `task-list.mjs` | 内容不变，沿用最终 Map 版 | 当前任务、等待、失败结果与采用顺序 |
| 初始数据、复制、Map 构造、完成计算 | 内容不变 | 原来的三字段任务规则 |
| 数据验证与文件编解码 | 新增 | 判断外部数据是否符合任务及文件约定 |
| 文件存储与临时替换 | 新增 | 路径、读取、初始化与保存 |
| 启动函数 | 新增 | 读取成功以后才创建任务对象 |
| 命令行入口 | 新增 | 选择操作、等待结果、交回退出状态 |

任务所有者能沿用，是因为它原来就通过保存函数处理外部动作，并接收外部给定的初始任务。这些边界与当前新增需求能够配合。

但新需求的复杂度并没有消失。文件格式、未知版本、初始化和损坏处理，现在都需要有人负责，只是没有塞进“完成任务”的计算里。

以后若增加任务的新字段，复制与完成结果可能都要调整；若要求多个窗口同时修改，单个所有者的 `busy` 也不够。边界是否合适，需要沿具体变化重新检查，不能仅凭本次复用了几个文件就判定以后都不用改。

## 20. 怎样验证真的经历了退出与重新启动

只在同一个进程中创建第二个对象，可以检查重新构造，但不能据此报告已经验证独立进程启动。

本章的 `process.test.mjs` 使用子进程依次运行真实的 `app.mjs`。每次调用都等待上一个子进程退出，检查退出码和完整 JSON 结果，再发起下一次。

其中一项先初始化、完成 `t1`、重新读取，再用另一个进程完成 `t2`。最后两条任务都为完成，说明后一次修改确实从包含前一次修改的文件开始。

同组检查还覆盖损坏文件上的修改拒绝、重新初始化拒绝、旧格式读取与升级，以及缺失文件不自动创建。

这里检查的是顺序运行，没有两个进程同时写一个文件。进程数量多于一个，不等于已经验证并发；本例的每一次使用都遵守先退出再启动的条件。

## 21. 单个 `busy` 仍然不能协调多个使用者

`busy` 只属于一个任务对象。另一个对象可能已经读过相同旧文件，之后用自己的旧任务产生一份新保存，覆盖前一个对象的修改。

前面的临时文件替换并不比较“我读取以后，别人是否已经修改过”。它负责准备和替换内容，不负责决定哪一份修改应该优先。

因此，本章明确要求同一时刻每个文件只有一个任务所有者，也不承诺识别外部编辑。本次命令顺序运行、每次重新加载，与这个范围相符。

若实际应用需要多窗口或多人共享，就出现了新需求。需要明确冲突如何发现和解决，再选择相应存储与协调方式。不能在当前代码旁边加一句“已经持久化”，就把这些要求一并算成完成。

## 22. 这一次多出的结构是否值得

如果需求只是一次性打印任务，新增的编码、启动和文件模块确实没有必要。这里明确要求退出后继续使用任务，读取和错误策略就成为程序必须承担的工作。

我们把它们分开，是为了让每部分的判断更具体：任务是否合法，可以不碰磁盘检查；真实路径和替换，可以用临时文件检查；启动是否在失败后停止，可以通过组合观察。

分开也增加了文件和调用关系。读者需要从命令入口追到启动、存储，再进入任务对象。是否继续拆出更细的组件，要看它是否承担实际区别，而不是把每一行都变成一个可替换接口。

当前只保留两种文件格式、一种正式存储实现和三条命令，没有通用迁移注册表，也没有提前加入数据库。后续需求如果确实使这些选择失效，再用新增条件重新比较。

## 23. 下载、命令与实际检查结果

下载[第九篇完整示例](software-design-09-examples.zip)，解压后进入 `software-design-09-examples`。仅使用 Node.js 自带模块，无需安装依赖：

```sh
node --version
node --test owner.test.mjs codec.test.mjs store.test.mjs replace.test.mjs process.test.mjs
node restart-demo.mjs
node failure-demo.mjs
```

本次在 macOS arm64、Node.js **25.9.0** 上运行，完整测试为 **40 项通过**，无跳过或取消。组成如下：

| 检查组 | 数量 | 实际范围 |
| --- | --- | --- |
| 原任务约定 | 4 | 等待、拒绝、第二次修改与同步创建 |
| 文件编码和验证 | 12 | 新旧格式、空数组、类型、重复编号、未知字段与版本 |
| 文件存储及启动 | 12 | 初始化、缺失、损坏、拒绝覆盖、读取与升级 |
| 临时文件替换 | 5 | 真实成功、合成失败、清理与替换后错误范围 |
| 独立进程 | 7 | 真实命令重开、失败退出、格式升级与启动反例 |

源目录和解压包都实际运行上述测试和演示。任务所有者及六个公共文件与第八篇逐字节相同，正文完整模块对应源码；错误默认值版只用于对照。

检查没有测量性能，没有验证不同操作系统、网络文件系统、磁盘满、突然断电或崩溃恢复。替换使用新文件，没有实现保留旧文件权限等额外属性的逻辑；测试只操作本次创建的普通临时文件。留下的临时文件不自动恢复，也不按名字猜哪份最新。

可以继续做两个练习。第一，为命令行增加明确的空任务初始化选项，保留已有路径不能覆盖的约定。第二，增加单独的旧格式升级命令，先写清重复执行、没有实际任务修改以及升级失败分别怎样报告。这些是练习，当前命令行没有实现它们。

下一篇将把任务功能接到界面请求：按钮怎样发起操作，输入在哪里检查，哪些外部能力可以交给页面使用。返回[系列目录](/articles/software-design/)，可以查看前后各篇。

## 参考资料

资料访问于 2026-10-15。文件格式、初始化及迁移策略是本篇的设计选择；接口规则与实际运行证据分别核对。

1. [TC39：JSON 对象、parse 与 stringify](https://tc39.es/ecma262/multipage/structured-data.html#sec-json-object)。用于核对文本与 JavaScript 值之间的转换；合法 JSON 不替代任务字段验证。
2. [Node.js 25.9.0：文件系统标志](https://nodejs.org/download/release/v25.9.0/docs/api/fs.html#file-system-flags)。用于核对 `wx` 对已有路径的拒绝，不把它扩大为完整初始化恢复机制。
3. [Node.js 25.9.0：Promise 文件接口](https://nodejs.org/download/release/v25.9.0/docs/api/fs.html#promises-api)。用于读取、写入、打开关闭、重命名及删除；临时替换不能单凭接口调用证明更强故障条件。
4. [Node.js 25.9.0：同步子进程](https://nodejs.org/download/release/v25.9.0/docs/api/child_process.html#child_processspawnsynccommand-args-options)。用于按顺序运行独立命令进程并取得退出结果。
