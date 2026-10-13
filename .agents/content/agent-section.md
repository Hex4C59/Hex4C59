# Agent section guide

本文件适用于讨论 Agent 机制与实践的原创文章，包括 `content/articles/` 下的新文章与 `content/agent/` 下的已发布文章。它负责 Agent 内容的模板和写作约定；具体文章类型的写作要求见 [technical-writing.md](technical-writing.md)，DeepSeek Harness 系列另见 [deepseek-harness.md](deepseek-harness.md)。

## Files and front matter

- 新文章放在 `content/articles/<slug>/index.md`，以 `categories` 表达主题；已发布文章保留原目录。图片和流程图放在同一文章目录，并使用相对路径。
- 新建文章使用 [archetypes/agent.md](../../archetypes/agent.md)。模板是 front matter 字段和文章骨架的唯一来源，不要在本文件或文章中复制一份长期维护的字段清单。
- 只有文章属于系列时才填写 `series`；是否需要 `series_order` 和角色字段按[内容归类规则](section-routing.md)确定。
- `article_type`、`difficulty` 和其他字段使用模板中声明的值。不要为了满足字段数量填写与文章内容无关的标签或框架。

## Site integration

- 保持 Agent section 的布局、列表页、RSS 和站点路径与现有实现一致。
- 修改 front matter、布局或系列顺序后，检查文章列表、上一篇/下一篇链接、目录和 RSS 是否仍然正确。
- SVG 图表遵循 [.agents/visuals/svg-style-guide.md](../visuals/svg-style-guide.md)；图表必须有可读的 alt 文本或正文说明。
