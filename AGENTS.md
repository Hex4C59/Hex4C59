# AGENTS.md

本仓库是基于 Hugo 和 PaperMod 的中文技术博客。根文件只记录所有任务都适用的约束和任务路由；专项规则放在 `.agents/`，命中任务范围后再按需读取。

## Always apply

- 保留用户已有的未提交修改，不使用 `reset --hard`、`checkout` 或其他方式覆盖无关工作。
- 修改前先检查相关文件、现有实现和工作区状态；遵循仓库已有的 Hugo、PaperMod、Markdown 和 front matter 约定。
- 一个提交只表达一个可独立理解的逻辑变更；不要把无关内容、生成物、凭据、token、个人信息或私有路径加入仓库。
- Agent 操作规则放在 `.agents/`，不要把内部指令文档放进 `content/`；`content/` 是 Hugo 发布内容树。

## Conventions

本仓库采用简化的 Conventional Commits 格式：

```text
<type>(<scope>): <description>
```

- `type` 使用英文小写，例如 `feat`、`fix`、`docs`、`refactor`、`test`、`ci` 和 `chore`；`scope` 可选并表示受影响的边界。
- 冒号后的 `description` 必须是简洁、具体、可行动的英文，使用祈使式或现在时，首字使用小写（专有名词除外），末尾不加句号。
- 主题行不超过 72 个字符；非平凡变更在主题后空一行，用正文记录动机、影响、取舍和验证方式。
- 创建或修改提交时，先读取 [.agents/commit-messages.md](.agents/commit-messages.md)，并确认暂存区只包含本次逻辑变更。

## Task routing

只读取与当前任务匹配的专项文档：

- 创建或编辑任意技术文章：读取 [.agents/content/technical-writing.md](.agents/content/technical-writing.md)。
- 编辑 `content/agent/` 下的文章：再读取 [.agents/content/agent-section.md](.agents/content/agent-section.md)，并使用 [archetypes/agent.md](archetypes/agent.md) 作为 front matter 和文章骨架的来源。
- 编辑 `series = ["DeepSeek Harness"]` 的文章：再读取 [.agents/content/deepseek-harness.md](.agents/content/deepseek-harness.md)。
- 修改 Hugo 配置、布局、主题、构建或发布流程：读取 [.agents/hugo-publishing.md](.agents/hugo-publishing.md)。
- 创建或修改 SVG 图表：读取 [.agents/visuals/svg-style-guide.md](.agents/visuals/svg-style-guide.md)。
- 修改上述规则或其依据：需要追溯规范来源时读取 [.agents/references/writing-standards.md](.agents/references/writing-standards.md)。

## Validation

- 文章或站点变更按任务运行相关检查；发布前运行 `hugo --gc --minify` 和 `git diff --check`。
- 提交前记录实际执行的验证命令；不要把未验证的主分支行为、性能结果或模型能力写成稳定事实。
