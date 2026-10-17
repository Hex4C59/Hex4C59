---
name: write-blog
description: >-
  Write a small Chinese teaching draft from the supplied notes. Use when the task
  explicitly requests a blog draft. These are this tutorial's sample rules.
triggers:
  - 写博客
  - 写一篇
  - blog draft
references:
  - references/structure.md
---

# 写作示例规则

为会写简单 Python 的读者解释任务指定的主题。先读取工作区里的
`inputs/source-notes.md`，区分资料给出的事实与为了演示而设置的条件。

1. 按 references/structure.md 组织草稿；写清对象、动作及至少一种失效条件。
2. 把文章写到本次任务指定的 `drafts/` Markdown 路径。现有文件须由外部授权覆盖。
3. 写入后说明文件路径。程序还会重新读回文件检查结构；保存说明不能代替文章。

这些规则只用于本教程的合成草稿，不是任何现有博客的发布规范。
