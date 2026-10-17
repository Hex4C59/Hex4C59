+++
title = "从任务表到执行计划：数据库建模、SQL、事务与索引"
date = 2026-10-15T16:00:00+08:00
lastmod = 2026-10-17
draft = false
description = "用一个任务管理案例理解关系建模、SQL 查询、事务回滚和联合索引，并通过 SQLite 实验观察执行计划怎样变化。"
summary = "任务属于谁，完成状态与记录怎样一起保存，为什么查最新 20 条任务还要排序？从三个表出发，用可运行的 SQLite 示例串起建模、SQL、事务、索引与执行计划。"
ShowToc = true
author = "Hex4C59"
tags = ["SQL", "SQLite", "事务"]
categories = ["backend-data"]
source_kind = "original"
article_type = "tutorial"
+++

一个任务管理程序已经能把数据保存到文件。现在有了多个用户：任务必须归属于一个存在的用户；点击“完成”时，既要修改任务状态，也要留下完成记录；任务多起来后，页面还要快速取出某个用户最近创建的 20 条待办。

这些要求分别把我们带到数据库建模、SQL、事务和索引。建模决定什么数据可以存在，SQL 描述要读写哪些数据，事务决定哪些修改必须一起成功，索引提供额外的查找顺序。执行计划则让我们观察数据库怎样完成一条查询。

这篇面向写过简单程序、能读懂 Python 函数的读者，不要求先学过数据库。如果还不熟悉“保存”和“重新读回”的区别，可以先看[任务程序的文件持久化](/articles/software-design-09-persistence/)。这里继续沿用任务案例，所有用户和数据均为合成示例。

读完后，你应该能解释三个结果：为什么数据库拒绝一条错误任务，为什么第二次写入失败会让第一次修改撤销，以及为什么一个联合索引能同时参与筛选和排序。示例使用 SQLite，文中的锁行为、类型选项和计划输出都按 SQLite 说明；迁移到其他数据库时需要重新核对实现。

## 先运行，再看每一步为什么成立

完整实验只有两个文件：[run.py](examples/run.py) 和 [schema.sql](examples/schema.sql)。把它们放在同一目录，执行：

```sh
python3 -c 'import sqlite3, sys; print(sys.version); print(sqlite3.sqlite_version)'
python3 run.py
```

如果已经取得博客源码，也可以从仓库根目录执行：

```sh
python3 content/articles/database-modeling-sql-transactions-indexes/examples/run.py
```

脚本只使用 Python 标准库，要求 Python 3.9 或以上、其 `sqlite3` 模块连接的 SQLite 3.37 或以上。后一个版本要求来自本文使用的 `STRICT` 表选项。命令行工具 `sqlite3` 与 Python 模块可能连接不同版本的库，所以检查的是上面 Python 命令的输出。[^strict]

本次在 2026-10-15、Darwin arm64、Python 3.9.6 / SQLite 3.54.0 环境运行；另用 Python 3.14.4 / SQLite 3.53.4 复跑，检查也全部通过。以下摘录第一组环境的输出：

```text
constraints: 7/7 invalid writes rejected
queries: ordered ids=[2, 1]; LEFT JOIN counts=[2, 0, 0]
null and bound-parameter checks: passed
rollback: task 1=todo; completion events=0
commit and repeat: task 1=done; completion events=1
second writer: busy (timeout=0)
other connection reads: todo before commit; done after commit
```

后面还会打印索引前后的执行计划。脚本用断言检查数据和事务结果，最后应输出 `PASS; temporary databases removed`。请不要加 Python 的 `-O` 参数；脚本会拒绝关闭断言的运行方式。

每次运行都会建立独立的临时目录，分别创建业务实验库和查询计划实验库，退出时删除它们。脚本不需要已有数据库，不连接网络，也不安装依赖。下面的代码块用于解释其中的步骤；完整运行入口始终是 `run.py`。

## 建模：先写出允许存在的状态

把任务和用户名都放进一张表，起初很直观：

| task_id | title | owner_name | status |
| --- | --- | --- | --- |
| 1 | 整理需求 | 小林 | todo |
| 2 | 写 SQL 练习 | 小林 | todo |

但“小林”出现在多条任务里。用户改名时，程序必须找到所有副本；另一个用户也叫“小林”时，名字又不能区分两个人。

在这个案例里，用户有独立的身份，任务只引用这个身份。我们把用户资料放进 `users`，把任务放进 `tasks`，再用 `owner_id` 建立联系。这是关系建模中减少重复的一种做法：同一个事实尽量在一个地方维护。是否需要保留历史名称，则是另一条业务要求。例如账单上记录开单时的名称，可能就应该保存当时的副本。

本文把业务范围限定为：每个任务只有一个所有者，状态只能从 `todo` 变为 `done`，不提供重新打开功能；成功完成任务时追加一条完成记录；用户或任务被其他记录引用时，禁止直接删除。

三个表各自承担的事实如下：

| 表 | 一行表示什么 | 与其他表的关系 |
| --- | --- | --- |
| `users` | 一个用户的账号和显示名称 | 一个用户可以拥有多条任务 |
| `tasks` | 一条任务当前的标题、状态和时间 | `owner_id` 引用一个用户 |
| `task_events` | 一次任务完成记录 | `task_id` 引用一条任务 |

“主键”是用来唯一标识一行的列或列组合。这里每张表都用 `id` 作为主键。“外键”是对另一张表中某个键的引用，用来要求被引用的记录存在。[^foreign-keys]

### 把确定的规则写成约束

下面是实验使用的完整表结构。时间字段统一保存 Unix 时间戳，单位为秒；程序负责解释和显示时间。

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    handle TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL
) STRICT;

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'done')),
    created_at INTEGER NOT NULL,
    completed_at INTEGER,
    CHECK (
        (status = 'todo' AND completed_at IS NULL)
        OR (status = 'done' AND completed_at IS NOT NULL)
    )
) STRICT;

CREATE TABLE task_events (
    id INTEGER PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
    kind TEXT NOT NULL CHECK (kind = 'completed'),
    created_at INTEGER NOT NULL
) STRICT;
```

`NOT NULL` 要求有值，`UNIQUE` 禁止账号重复，`CHECK` 检查写入后的条件。这里既限制状态的取值，也限制状态和完成时间的组合：待办没有完成时间，已完成必须有完成时间。`ON DELETE RESTRICT` 表示被引用时拒绝删除。[^constraints][^foreign-keys]

`CHECK` 不能代替 `NOT NULL`。例如在 SQLite 中，`CHECK (status IN ('todo', 'done'))` 的计算结果如果是 `NULL`，并不会因此拒绝这一行；必填字段还要显式声明非空。[^constraints]

SQLite 的普通表允许较灵活的类型存储。本文加上 `STRICT`，让无法无损转换为声明类型的值被拒绝，例如把 `'yesterday'` 写入整数时间列。它仍允许一些可转换的值，并不等于逐个禁止字符串输入。[^strict]

还有一个容易漏掉的步骤：SQLite 外键检查按连接启用。每次取得连接，都在事务开始前设置 `PRAGMA foreign_keys = ON`，再查询该选项确认返回 `1`。只在建表连接上设置一次，不能保证以后的连接也启用了检查。[^foreign-keys]

实验实际尝试了七种错误写入：不存在的所有者、空所有者、只含空格的标题、非法状态、缺少完成时间、错误的时间类型，以及重复账号。它们全部被拒绝，原来的三条任务保持不变。

约束只承接已经写出来的规则。这份结构没有检查标题的产品长度上限，也没有禁止把已完成任务改回待办，更没有要求每条已完成任务恰好对应一条事件。后两项由下面的写入流程维护；如果将来增加批量导入或管理工具，也必须维护同样的规则。

## SQL：先确认结果，再考虑怎样查

SQL 是 Structured Query Language，通常译为结构化查询语言。以查询为例，我们描述需要哪些行、哪些列以及结果顺序，由数据库选择具体的访问方式。

页面要显示“某个用户最新创建的 20 条待办”，对应的查询是：

```sql
SELECT id, title, created_at
FROM tasks
WHERE owner_id = ? AND status = 'todo'
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

可以先按语义理解它：从 `tasks` 取数据，筛选所有者和状态，返回指定列，按时间和编号倒序排列，最多取 20 条。这个解释顺序有助于确认结果，数据库实际怎样访问表，要到执行计划里观察。[^select]

为什么排序里还有 `id`？两个任务可能在同一秒创建。如果只按 `created_at` 排序，相同时间的任务之间没有指定顺序；再加唯一的 `id`，就给当前数据集合确定了完整的排序规则。实验特意让任务 1 和 2 使用相同时间，结果应为 `[2, 1]`。这不意味着多次请求之间数据不会变化，分页时仍要单独考虑新增与删除。[^select]

### 参数是值，不能拼成 SQL 语法

上面的 `?` 是值的占位符。在 Python 中，把参数单独传入：

```python
rows = conn.execute(
    """
    SELECT id, title, created_at
    FROM tasks
    WHERE owner_id = ? AND status = 'todo'
    ORDER BY created_at DESC, id DESC
    LIMIT 20
    """,
    (owner_id,),
).fetchall()
```

这样，输入内容按参数值处理。实验还把 `x' OR 1=1 --` 作为账号参数查询，结果为空；这串字符不会变成查询条件。Python 官方文档也明确建议用参数绑定，避免把输入拼入 SQL。[^python]

参数绑定适用于值。表名、列名以及 `ASC` / `DESC` 这样的语法选择，需要程序从允许的选项中选择，不能指望用一个 `?` 代替。

### `NULL` 和零条任务各有自己的含义

`completed_at` 为 `NULL`，表示没有完成时间。查找这些任务要用：

```sql
SELECT id FROM tasks WHERE completed_at IS NULL;
```

写成 `completed_at = NULL` 时，比较结果是未知，筛选条件不会保留这些行。实验在修改任务前检查两种写法：前者找到两条待办，后者一条也找不到。[^expressions]

再看一个更容易影响页面的查询：统计每个用户的待办数量，包含没有待办的用户。

```sql
SELECT u.id, u.display_name, count(t.id) AS todo_count
FROM users AS u
LEFT JOIN tasks AS t
    ON t.owner_id = u.id AND t.status = 'todo'
GROUP BY u.id, u.display_name
ORDER BY u.id;
```

`JOIN` 把两边符合条件的行组合起来。`LEFT JOIN` 还保留左边没有匹配项的用户，并把右边列填成 `NULL`。`count(t.id)` 只数非空任务编号，所以没有匹配任务的用户得到 `0`；如果改为 `count(*)`，保留下来的那一行也会计数。实验结果是小林 `2`、小周 `0`、小陈 `0`。[^select][^aggregates]

待办条件放在 `ON` 里，也是为了保留这些零。如果把 `t.status = 'todo'` 放到后面的 `WHERE`，补出的空行就会被过滤掉，没有待办的用户可能从结果里消失。讨论查询性能前，应先确认这些结果符合页面需要。

## 事务：让状态与完成记录一起改变

现在实现“完成任务”。程序要执行两个写操作：

1. 把任务从 `todo` 改为 `done`，写入完成时间。
2. 向 `task_events` 追加一条完成记录。

如果两次写入各自提交，第二次失败时就会留下“任务已经完成，但没有完成记录”的状态。事务给这组操作一个提交边界：两次都成功后提交；出错时撤销本组修改。

这里还需要处理重复点击。把状态条件直接写进更新语句：

```sql
UPDATE tasks
SET status = 'done', completed_at = ?
WHERE id = ? AND owner_id = ? AND status = 'todo';
```

接着检查受影响行数。只有实际改动了一条待办，才追加事件。这样第二次完成同一任务时，条件不再成立，也就不会再写一个完成事件。

下面的函数来自实验脚本。它独自管理一个事务，要求传入的连接使用脚本中的连接设置，且调用前没有外层事务。`event_kind` 是演示失败用的参数，正常调用保持默认值。

```python
def complete_task(conn, task_id, owner_id, completed_at, *, event_kind="completed"):
    conn.execute("BEGIN IMMEDIATE")
    try:
        changed = conn.execute("""
            UPDATE tasks
            SET status = 'done', completed_at = ?
            WHERE id = ? AND owner_id = ? AND status = 'todo'
        """, (completed_at, task_id, owner_id)).rowcount
        if changed == 0:
            conn.execute("ROLLBACK")
            return False
        conn.execute(
            "INSERT INTO task_events (task_id, kind, created_at) VALUES (?, ?, ?)",
            (task_id, event_kind, completed_at),
        )
        conn.execute("COMMIT")
        return True
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
```

`BEGIN IMMEDIATE` 是 SQLite 的事务启动方式，会立即尝试取得写事务。`COMMIT` 提交，`ROLLBACK` 撤销；异常处理先撤销仍在进行的事务，再把异常交给调用者。SQLite 中有些错误只撤销当前语句，事务里之前成功的语句仍可能保留，因此这里显式处理回滚。[^transactions]

这里的驱动是 Python 中负责与 SQLite 通信的模块。脚本关闭了它自动开启事务的行为，改用 SQL 明确指定事务何时开始、提交或撤销。在 Python 3.12 及以上，这通过 `autocommit=True` 设置；较早版本使用 `isolation_level=None`。这些设置下的连接仍可以执行显式 `BEGIN` / `COMMIT` / `ROLLBACK`。复制代码到已有项目时，要先核对驱动或框架是否已经管理了事务，避免重复 `BEGIN`。[^python]

### 用一次失败检查整组修改

实验故意把 `event_kind` 传成 `invalid`，让第二次写入违反事件表的约束。捕获异常后，再查询任务与事件：

```text
rollback: task 1=todo; completion events=0
```

随后正常完成任务，再重复调用一次：

```text
commit and repeat: task 1=done; completion events=1
```

实验还检查完成时间没有被重复调用覆盖。这里的重复执行结果保持不变，通常称为幂等。它成立的前提是本文只有单向完成操作，并且所有完成写入都遵守这个事务流程。加入“重新打开任务”后，旧请求与新一轮完成就需要额外的版本或请求标识来区分。

返回 `False` 只说明没有改动符合条件的待办，可能是任务不存在、所有者不匹配，也可能是已经完成。真实接口怎样反馈这些情况，要结合权限和产品需求设计；这个函数不处理用户身份认证。

### 另一个连接在提交前看到什么

事务还涉及隔离：一个连接的修改，什么时候对另一个连接可见。实验使用 WAL（Write-Ahead Logging，预写日志）模式，以及没有共享缓存的两个独立连接。WAL 允许读操作与写操作并行，但同一个 SQLite 数据库同时仍只有一个写事务。[^isolation]

脚本按明确顺序执行，不依靠线程睡眠碰运气：连接 A 开始写事务，把任务 2 改为完成但先不提交；连接 B 查询它，仍读到 `todo`。B 再尝试 `BEGIN IMMEDIATE`，因为 A 仍占有写事务而返回忙错误；这里故意设置 `timeout=0`，让冲突立即暴露。A 提交后，B 的下一次查询读到 `done`。

B 在这段实验中没有持有显式的长读事务，每次查询都已读取完结果。在 WAL 模式下，如果 B 已经开启并持有一个读事务，它会继续看到原来的快照，需要结束该读事务后才能读取新状态。[^isolation]

这两个连接的实验检查了提交可见性和写事务冲突，没有测量服务吞吐量，也没有模拟断电恢复。真实程序应给锁等待设置期限，保持写事务短小；调用网络服务或等待用户输入，会把写事务占用时间拉长。数据库事务也不会撤销已经发出的邮件或远端请求。

## 索引：为这条查询准备另一种排列

先回到页面查询：

```sql
SELECT id, title, created_at
FROM tasks
WHERE owner_id = ? AND status = 'todo'
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

任务表有主键，并不意味着按所有者找待办、再按创建时间排序已经有了合适的访问路径。主键表达身份；这个查询需要的是另一种数据排列。

SQLite 索引使用 B-tree 组织有序键。这里先按查询怎么用它来理解：数据库另外维护一份有序的查找结构。查询选用它时，可以先按键缩小范围，再找需要的记录。联合索引包含多个字段，先比较第一个字段，相同再比较第二个，继续比较后面的字段。查询能够利用这种顺序缩小查找范围，有时也能直接取得需要的结果顺序。[^planner]

我们分两步建立索引，观察两种收益的区别。

### 先帮助筛选

```sql
CREATE INDEX idx_tasks_owner_status
ON tasks(owner_id, status);
```

这个索引按所有者和状态组织数据，能帮助定位“用户 7 的待办”这一部分。但这一部分内部仍没有按 `created_at DESC, id DESC` 排好，需要另外满足排序要求。

### 再把结果顺序放进去

第二个实验阶段删除上面的索引，再创建：

```sql
CREATE INDEX idx_tasks_owner_status_created
ON tasks(owner_id, status, created_at DESC, id DESC);
```

对本文的查询，前两列都是等值条件。固定所有者和状态后，对应索引范围里的记录就按后两列倒序排列，符合 `ORDER BY`。数据库可以沿着这个顺序取得前 20 条。[^planner]

这个推导有明确条件：查询固定了前两列，而且后续排序与索引顺序相符。若改成“所有用户的待办，按时间统一排序”，同一索引最前面的 `owner_id` 就会影响顺序，不能直接照搬结论。范围条件、不同排序方向和多种查询组合，都要重新看计划。

索引也有写入与存储代价。修改被索引的字段时，数据库需要维护对应索引记录；索引越多，写入路径上需要维护的结构越多。因此先列出实际查询，再为查询选择索引，比见到字段就建立索引更有依据。

## 执行计划：把“用到了什么”读出来

实验给查询计划准备了单独的数据集：100 个用户、20,000 条任务，每个用户 200 条任务，其中 50 条待办。查询用户 7 的最新 20 条待办，并故意让部分任务拥有相同创建时间。

每个索引阶段都执行 `ANALYZE`，收集供规划器使用的数据统计，再输出 `EXPLAIN QUERY PLAN`。这里的 `ANALYZE` 更新统计信息；`EXPLAIN QUERY PLAN` 描述计划，不提供一次真实执行的耗时或实际访问行数。[^planner][^eqp]

把参数绑定为 `7` 后，本次运行输出的计划详情如下。

没有为这条查询建立额外索引时：

```text
SCAN tasks
USE TEMP B-TREE FOR ORDER BY
```

加入 `(owner_id, status)` 索引后：

```text
SEARCH tasks USING INDEX idx_tasks_owner_status (owner_id=? AND status=?)
USE TEMP B-TREE FOR ORDER BY
```

换成包含排序字段的联合索引后：

```text
SEARCH tasks USING INDEX idx_tasks_owner_status_created (owner_id=? AND status=?)
```

读这几行时，先看两件事：怎样找到候选行，以及怎样取得结果顺序。

| 计划信息 | 在本次实验中表示什么 |
| --- | --- |
| `SCAN tasks` | 从任务表扫描数据来筛选 |
| `SEARCH ... (owner_id=? AND status=?)` | 根据索引中的条件定位候选范围 |
| `USE TEMP B-TREE FOR ORDER BY` | 需要额外的临时结构满足排序 |
| 第三个计划没有临时排序行 | 这条查询可以使用索引顺序满足排序 |

SQLite 官方说明中，`SCAN` 也可能表示按索引顺序遍历，并不能一看到它就判定查询有问题；这里要结合完整计划和查询目的判断。计划文本还可能随版本变化，脚本打印它供人观察，不把字符串格式当成接口断言。[^eqp]

三种索引配置都执行了真实查询。脚本把结果与 Python 中独立筛选、排序得到的参考结果比较，确认返回的 20 条任务及顺序完全相同。改变访问路径时，先保持查询语义，再观察数据库少做了什么。

### 覆盖索引还取决于返回哪些列

查询仍然要返回 `title`，它不在联合索引中，因此数据库还要取得表中的标题值。若改为只返回 `id` 和 `created_at`，本次计划变成：

```text
SEARCH tasks USING COVERING INDEX idx_tasks_owner_status_created (owner_id=? AND status=?)
```

“覆盖索引”表示这条查询需要的信息都可以从索引取得。它是索引与具体查询之间的关系：同一个索引，改变返回列后，覆盖情况也会改变。[^planner][^eqp]

本文没有为了覆盖查询把标题也塞进索引。标题越长，索引额外保存的信息就越多，是否值得要结合读写负载评估。这里把根据索引再到表中取得标题等数据的动作称为“回表”。计划中减少了回表或排序步骤，也不能直接换算为“快了多少倍”；那需要固定环境和输入，单独测量延迟、访问量与写入成本。

## 接着练习什么

先改动一个条件，再观察结果和计划，比同时加很多功能更容易解释变化：

- 把零待办统计中的 `count(t.id)` 改成 `count(*)`，解释多出来的计数来自哪一行。
- 在两个连接实验中，让 B 用显式 `BEGIN` 保持读事务，比较 A 提交前后 B 的查询结果，再结束 B 的事务重读。
- 去掉待办列表中的所有者条件，观察原来的联合索引还能否同时满足筛选与全局时间排序。

这些练习会继续引出外连接语义、读事务快照和索引列顺序。更完整的数据库路线还需要专门讨论多对多关系、连接与子查询、隔离级别、锁冲突处理、范围查询和分页，以及迁移与备份。

对这个任务程序，下一步可以把“完成任务”的数据库函数接到服务接口上，再明确身份从哪里来、重复请求怎样反馈，以及锁等待超时怎样返回给调用者。数据库实验提供了可检查的存储行为，接口层还需要把这些行为转成用户能理解的结果。

## 参考资料

以下均为 SQLite 或 Python 官方资料，核对日期为 2026-10-15。文中的数字、错误写入结果和计划输出来自随文脚本；机制解释参考这些文档。

[^constraints]: SQLite，[CREATE TABLE](https://www.sqlite.org/lang_createtable.html)，约束、空值和表定义。
[^strict]: SQLite，[STRICT Tables](https://www.sqlite.org/stricttables.html)，严格类型表及 3.37.0 版本要求。
[^foreign-keys]: SQLite，[Foreign Key Support](https://www.sqlite.org/foreignkeys.html)，外键关系、删除动作和按连接启用检查。
[^select]: SQLite，[SELECT](https://www.sqlite.org/lang_select.html)，连接、筛选、排序与结果数量。
[^expressions]: SQLite，[SQL Language Expressions](https://www.sqlite.org/lang_expr.html)，空值比较和表达式规则。
[^aggregates]: SQLite，[Built-in Aggregate Functions](https://www.sqlite.org/lang_aggfunc.html)，`count(X)` 与 `count(*)` 的区别。
[^python]: Python，[sqlite3](https://docs.python.org/3.14/library/sqlite3.html)，参数绑定及事务控制；脚本兼容较早 Python 的连接设置。
[^transactions]: SQLite，[Transaction](https://www.sqlite.org/lang_transaction.html)，显式事务、`BEGIN IMMEDIATE` 和错误后的事务状态。
[^isolation]: SQLite，[Isolation In SQLite](https://www.sqlite.org/isolation.html)，连接间可见性、WAL 快照与单写事务。
[^planner]: SQLite，[Query Planning](https://www.sqlite.org/queryplanner.html)，联合索引、排序、覆盖索引与统计信息。
[^eqp]: SQLite，[EXPLAIN QUERY PLAN](https://www.sqlite.org/eqp.html)，计划详情、临时排序结构及输出兼容性。
