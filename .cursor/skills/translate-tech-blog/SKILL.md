---
name: translate-tech-blog
description: >-
  Translates non-Chinese technical articles and blogs into Simplified Chinese and
  produces Hugo Markdown for the Hex4C59 translations section
  (https://www.hex4c59.fun/translations/). Aligns front matter with
  archetypes/translations.md and layouts/translations/list.html; keeps proper
  nouns in English, preserves original figures, and requires attribution
  (original URL, author, original publication date, translation date). Use when
  the user asks to translate an article or blog, add a translation to the
  translations section, localize English technical content for the site, or
  mentions 翻译、译文、转载、英文博客、translation、localization for this blog.
---

# 技术博客翻译（Hex4C59 / translations）

将外文技术文章译为简体中文，并写入本站 `translations` 栏目。项目路径：`/Users/hex4c59/Code/personal/Hex4C59`。

## Hugo 输出清单

- **目录**：`content/translations/<slug>/index.md`（Page Bundle；`<slug>` 用小写英文、连字符，与 URL 一致）。
- **同目录资源**：原文图表另存为 `png`/`svg` 等，与 `index.md` 并列；正文中用相对路径引用，例如 `![说明](diagram.svg)`。
- **线上 URL**：`https://www.hex4c59.fun/translations/<slug>/`
- **配置与模板**：[`hugo.toml`](hugo.toml) 已包含 `translations` section；列表逻辑见 [`layouts/translations/list.html`](layouts/translations/list.html)；脚手架见 [`archetypes/translations.md`](archetypes/translations.md)。

## Front matter 模板

使用 **TOML**（`+++` … `+++`），字段必须与列表页读取的参数一致。下列块可直接复制后填空（勿在 TOML 内写 `#` 注释，以免个别环境不兼容）。

```toml
+++
title = ""
date = 2025-03-25T12:00:00+08:00
lastmod = 2025-03-25T12:00:00+08:00
draft = true
author = "Hex4C59"
description = ""
summary = ""
tags = []
categories = ["Translations"]
topics = []
original_title = ""
original_url = ""
original_author = ""
original_date = ""
original_site = ""
ShowToc = true
+++
```

| 字段 | 含义 |
|------|------|
| `title` | 中文标题（列表主标题） |
| `date` | 翻译首次发布日；列表显示「翻译于 …」；建议 `+08:00` |
| `lastmod` | 译文修订日；与 `date` 不同时列表显示「更新于 …」 |
| `description` | 列表摘要，一至两句中文 |
| `topics` | 主题筛选标签，建议小写，如 `["llm", "rag"]` |
| `original_title` | 原文标题 |
| `original_url` | 原文 canonical URL |
| `original_author` | 原作者署名 |
| `original_date` | 原文首次发布日期（字符串，与「译文信息」块一致） |
| `original_site` | 来源站点短名（徽章与筛选），如 `OpenAI Blog` |

**必填**：`original_title`、`original_url`、`original_author`、`original_date`、`original_site`、`description`、`date`；`topics` 至少一项便于筛选。

**说明**：`original_date` 可能未在列表卡片展示，但必须写在 front matter；**正文开头「译文信息」块**向读者展示原文发布日与翻译日（见下节）。

## 正文开头的译文信息块

紧接 front matter 之后、正文第一段之前插入（链接用真实 `original_url`，列表与元数据保持一致）：

```markdown
> **译文信息**  
> - 原文：[在此填写与 `original_title` 或站点名一致的链接文字](https://example.com/original-post)  
> - 作者：与 `original_author` 一致  
> - 原文发布：与 `original_date` 一致  
> - 翻译发布：与 front matter `date` 一致（若后文修订可写：「最新修订见页面元数据中的更新日期。」）
```

若原文含 **License / 转载条款**，在译文信息块下方或文末增加 **「转载与版权」** 小节，逐条说明（默认策略见 [reference.md](reference.md)）。

## 翻译规则

1. **语言**：正文使用 **简体中文**；**专有名词**（产品、API、库名、论文名、公司名、标准名等）**保留英文**；必要时首次出现可用「中文（English）」，后文统一为一种形式。
2. **代码**：代码块内代码不翻译；不擅自改写标识符与命令；保留语言标签与缩进；仅当用户明确要求时才译代码注释。
3. **图表**：优先使用 **原作者图表**（下载放入同 bundle 或引用原图稳定 URL）；图下可用斜体说明，并标明引用自原文。
4. **链接**：外链 URL 保持可访问；锚文本可中文化；指向原文站内路径的链接保持原文 URL。
5. **结构**：标题层级与原文对应；列表、表格、引用块与原文信息等价。
6. **译注**：歧义、文化梗或技术背景用简短括号或脚注说明，避免长篇发挥。
7. **语气**：与原文正式程度大致相当；不擅自改变技术论断与数据。
8. **长文可选**：文末可加「术语对照」小节（见 [reference.md](reference.md)）。

## 发布前检查

- [ ] 路径为 `content/translations/<slug>/index.md`，资源在同目录。
- [ ] `draft`：校对完成前为 `true`，发布前改为 `false`。
- [ ] `original_url` 在浏览器中可打开；`original_author`、`original_title`、`original_date`、`original_site` 已核对。
- [ ] `date` / `lastmod` 与「译文信息」中的翻译/修订叙述一致。
- [ ] `description` 非空；`topics` 至少一项且拼写统一。
- [ ] 专有名词与代码块符合「翻译规则」。
- [ ] 本地执行 `hugo` 构建无报错，列表页 `/translations/` 卡片展示正常。

## 附加资源

- 专有名词示例、版权默认策略、主题命名习惯：[reference.md](reference.md)
