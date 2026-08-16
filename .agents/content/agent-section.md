# Agent section guide

本文件适用于 `content/agent/` 下的文章。它负责 Agent 专栏共有的目录、模板和站点约定；具体文章类型的写作要求见 [technical-writing.md](technical-writing.md)，DeepSeek Harness 系列另见 [deepseek-harness.md](deepseek-harness.md)。

## Files and front matter

- 文章放在 `content/agent/<slug>/index.md`，图片和流程图放在同一文章目录，并使用相对路径。
- 新建文章使用 [archetypes/agent.md](../../archetypes/agent.md)。模板是 front matter 字段和文章骨架的唯一来源，不要在本文件或文章中复制一份长期维护的字段清单。
- 只有文章属于某个系列时才填写 `series` 和 `series_order`；系列顺序必须唯一且能反映实际阅读顺序。
- `article_type`、`difficulty` 和其他字段使用模板中声明的值。不要为了满足字段数量填写与文章内容无关的标签或框架。

## Site integration

- 保持 Agent section 的布局、列表页、RSS 和站点路径与现有实现一致。
- 修改 front matter、布局或系列顺序后，检查文章列表、上一篇/下一篇链接、目录和 RSS 是否仍然正确。
- SVG 图表遵循 [.agents/visuals/svg-style-guide.md](../visuals/svg-style-guide.md)；图表必须有可读的 alt 文本或正文说明。
