---
name: write-agent-blog
description: >-
  Write blog posts for the Hugo + PaperMod Agent series. Use when the user asks
  to create, draft, or write a new Agent blog post, or when they want to add
  content to the Agent section of the blog.
---

# Write Agent Blog Post

This skill helps write blog posts for the Agent series on a Hugo + PaperMod blog at `/Users/hex4c59/Code/personal/Hex4C59`.

## Project Structure

- Content dir: `content/agent/<slug>/index.md`
- Archetype template: `archetypes/agent.md`
- Custom CSS: `assets/css/extended/agent.css`
- Section layout: `layouts/agent/list.html`
- Config: `hugo.toml`

## Front Matter Template

Every Agent post uses TOML front matter (`+++`):

```toml
+++
title = "标题：用副标题补充说明核心问题"
date = <ISO 8601, +08:00 timezone>
draft = false
author = "Hex4C59"
description = "一句话概括文章核心内容与价值"
summary = "用于列表页展示的精炼摘要"
tags = ["Agent", "<topic-specific tags>"]
categories = ["Agent"]
series = ["agent-engineering"]
series_order = <next integer after existing max>
difficulty = "beginner|intermediate|advanced"
article_type = "concept|tutorial|practice|review|eval"
topics = ["agent", "<1-3 more specific topics>"]
frameworks = ["<if applicable>"]
ShowToc = true
+++
```

### Key Rules

1. `series` is always `["agent-engineering"]`
2. `series_order` must be the next number (check existing articles with `grep series_order content/agent/*/index.md`)
3. `date` uses Beijing timezone `+08:00`
4. `categories` is always `["Agent"]`
5. First tag is always `"Agent"`

## Writing Style & Structure

Follow the established voice: direct, opinionated, first-person, with clear judgment calls upfront.

### Mandatory Sections (in order)

1. **Opening paragraph** — Set up the problem in 2-3 paragraphs. Reference previous articles in the series where relevant using relative links like `[文章标题](/agent/slug/)`.
2. **先给结论** — Numbered list of 3-5 core judgments. Be opinionated. Start with the most important insight.
3. **Problem/motivation section** — Why this matters. Use concrete scenarios, not abstract descriptions.
4. **Core concepts / architecture** — Define key terms, show structure. Use diagrams (SVG) and code blocks.
5. **Implementation / design** — Show real code (Python, using `openai` SDK style). Include type hints, async patterns, and practical examples.
6. **Failure modes / common problems** — At least 2-3 real failure scenarios. This section is critical.
7. **Trade-offs / when to use** — Be explicit about when NOT to use this approach.
8. **总结** — Recap in 3-5 concise points. Tie back to the series.
9. **Navigation link** — End with `*上一篇：[title](/agent/slug/)*`

### Code Style

- Use Python with `openai` SDK, `async/await`, type hints
- Include docstrings in Chinese
- Keep examples minimal but complete
- Use `gpt-4o` as default model in examples

### Diagram Convention

- Use SVG files in the same directory as `index.md`
- Reference as `![描述](filename.svg)`
- Add italic caption below: `*图 N：说明*`
- SVG 内的文字除专有名词（如 LLM、Agent、MCP、ReAct 等）外，一律使用中文

### Cross-references

Link to other articles in the series using relative paths:

```markdown
在 [Tool Use](/agent/tool-use-core-of-agent/) 那篇里...
```

## Creating a New Post

1. Create directory: `content/agent/<slug>/`
2. Create `index.md` with TOML front matter
3. Write content following the structure above
4. Create SVG diagrams if needed
5. Verify with `hugo server -D` locally

## Language

All content is written in **Simplified Chinese** (`zh-cn`). Code comments are also in Chinese.
