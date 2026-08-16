# Commit message guide

本文件只在创建、修改或审查 Git commit 时读取。根 `AGENTS.md` 保留强制性摘要，本文件记录完整约定和示例。

## Format

```text
<type>(<scope>): <description>
```

- `type` 必填，使用英文小写。允许使用 `feat`（新增能力或内容）、`fix`（修复错误）、`docs`（文章或文档）、`style`（不改变语义的格式或样式）、`refactor`（不改变行为的结构调整）、`perf`（性能）、`test`（测试）、`build`（构建或依赖）、`ci`（CI 配置）、`chore`（其他维护）和 `revert`（回退提交）。
- `scope` 可选，使用受影响的栏目或系统边界，例如 `agent`、`leetcode`、`translations`、`nav`、`hugo`、`theme` 和 `ci`。跨多个边界且没有一个主要归属时可以省略。
- `description` 必须使用简洁、具体、可行动的英文描述。使用祈使式或现在时；技术名词、命令和产品名保留官方写法。首字使用小写（专有名词除外），末尾不要加句号。
- 主题行不超过 72 个字符；简单变更优先压缩到 50 个字符左右。不要使用 `update`、`fix stuff` 或其他无法说明结果的描述。
- 一个提交只表达一个可以独立理解的逻辑变更。不要把文章正文、导航配置、主题样式和无关格式化放进同一个提交；小型拼写或样式修复应在提交前合并成清晰的单一变更。
- 非平凡变更在主题行后空一行，用正文说明动机、影响范围、关键取舍和验证方式。正文不要逐行复述 diff；它要回答“为什么改”和“如何确认改对了”。纯粹的小型 `docs` 或 `style` 变更可以省略正文。
- 需要标记不兼容变化时，在类型或作用域后加 `!`，并在正文或 footer 中写明 `BREAKING CHANGE: ...` 以及迁移方式。Issue 或 PR 的关联信息使用 footer 或平台的 PR 描述，不要在没有约定的情况下滥用 `fixes` 或 `closes`。

## Examples

```text
docs(agent): add DeepSeek Harness engineering article
fix(nav): unify top navigation labels
docs(translations): publish Agent Skills translation
fix(leetcode): correct sliding-window complexity explanation
chore(hugo): update site build configuration
ci: adjust Hugo Pages deployment parameters
```

提交前检查暂存区而不是只看工作区：确认 `git diff --cached` 只包含本次逻辑变更，并根据变更运行相关的 Hugo 构建、测试或 `git diff --check`。新提交的 `description` 必须使用英文。

## References

这套约定参考了以下公开规则：

- [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)：类型、作用域、正文、footer 和破坏性变更的结构。
- [Angular commit message guidelines](https://github.com/angular/angular/blob/main/contributing-docs/commit-message-guidelines.md)：祈使式摘要、无句号，以及类型和作用域对 changelog 的支持。
- [Git SubmittingPatches](https://github.com/git/git/blob/master/Documentation/SubmittingPatches)：短主题、`area: subject`、祈使式和在正文记录动机。
- [Kubernetes contributing guide](https://github.com/kubernetes/community/blob/master/contributors/guide/contributing.md)：清晰有意义的提交、单一逻辑变更和小变更合并提交。
