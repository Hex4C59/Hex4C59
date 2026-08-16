# AGENTS.md

本仓库是基于 Hugo 和 PaperMod 的中文技术博客。DeepSeek Harness 项目的介绍文章属于 `Agent` 专栏，写作时既要遵循本文件，也要复用 [Agent 文章模板](archetypes/agent.md) 与现有文章的 front matter 约定。

## Conventions

### Commit messages

本仓库采用 Conventional Commits 的简化形式，提交主题使用下面的结构：

```text
<type>(<scope>): <description>
```

- `type` 必填，使用英文小写。允许使用 `feat`（新增能力或内容）、`fix`（修复错误）、`docs`（文章或文档）、`style`（不改变语义的格式或样式）、`refactor`（不改变行为的结构调整）、`perf`（性能）、`test`（测试）、`build`（构建或依赖）、`ci`（CI 配置）、`chore`（其他维护）和 `revert`（回退提交）。
- `scope` 可选，使用受影响的栏目或系统边界，例如 `agent`、`leetcode`、`translations`、`nav`、`hugo`、`theme` 和 `ci`。跨多个边界且没有一个主要归属时可以省略。
- `description` 使用简洁、具体、可行动的描述。中文内容默认使用中文描述，技术名词、命令和产品名保留官方写法；英文描述使用祈使式或现在时。描述首字不要无理由大写，末尾不要加句号。
- 主题行尽量控制在 72 个字符以内；简单变更优先压缩到 50 个字符左右。不要使用 `update`、`fix stuff`、`修改一下` 等无法说明结果的描述。
- 一个提交只表达一个可以独立理解的逻辑变更。不要把文章正文、导航配置、主题样式和无关格式化放进同一个提交；小型拼写或样式修复应在提交前合并成清晰的单一变更。
- 非平凡变更在主题行后空一行，用正文说明动机、影响范围、关键取舍和验证方式。正文不要逐行复述 diff；它要回答“为什么改”和“如何确认改对了”。纯粹的小型 `docs` 或 `style` 变更可以省略正文。
- 需要标记不兼容变化时，在类型或作用域后加 `!`，并在正文或 footer 中写明 `BREAKING CHANGE: ...` 以及迁移方式。Issue 或 PR 的关联信息使用 footer 或平台的 PR 描述，不要为了自动关闭问题而在没有约定的情况下滥用 `fixes` 或 `closes`。

推荐示例：

```text
docs(agent): 新增 DeepSeek Harness 工程分析文章
fix(nav): 统一顶部导航栏目名称
docs(translations): 发布 Agent Skills 译文
fix(leetcode): 修正滑动窗口题解的复杂度说明
chore(hugo): 更新站点构建配置
ci: 调整 Hugo Pages 部署参数
```

提交前检查暂存区而不是只看工作区：确认 `git diff --cached` 只包含本次逻辑变更，并根据变更运行相关的 Hugo 构建、测试或 `git diff --check`。已有历史提交不要求为了迁就本约定而重写；新提交遵循本节规则即可。

这套约定参考了截至 2026-08-16 调研到的公开项目规则：[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) 规定了类型、可选作用域、正文、footer 和破坏性变更的结构；[Angular 的提交消息指南](https://github.com/angular/angular/blob/main/contributing-docs/commit-message-guidelines.md)要求祈使式摘要、无句号并用类型和作用域支持 changelog；[Git 的 SubmittingPatches](https://github.com/git/git/blob/master/Documentation/SubmittingPatches)强调短主题、`area: subject`、祈使式和在正文记录动机；[Kubernetes 贡献指南](https://github.com/kubernetes/community/blob/master/contributors/guide/contributing.md)强调清晰有意义的提交、单一逻辑变更和小变更合并提交。本仓库近期历史已经使用 `feat`、`fix` 和 `chore`，但作用域、语言和主题长度不完全一致；本节用于统一后续提交，不追溯修改已有历史。

## DeepSeek Harness 专栏

专栏用于解释 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 的架构、运行机制、扩展方式和工程取舍。文章应帮助读者形成可验证的理解，而不是把项目 README 改写成宣传文案。

- 文章放在 `content/agent/<slug>/index.md`，使用 `series = ["DeepSeek Harness"]` 归入专栏，并用唯一的 `series_order` 表示阅读顺序。
- 文章至少填写 `title`、`date`、`draft`、`description`、`summary`、`tags`、`categories`、`series`、`difficulty`、`article_type`、`topics`、`frameworks` 和 `ShowToc`。字段含义和可选值以 [archetypes/agent.md](archetypes/agent.md) 为准。
- `article_type` 只能从 `concept`、`tutorial`、`practice`、`review`、`eval` 中选择；概念解释、操作教程、工程实战、复盘和评测不要混成一种文章。
- 介绍项目当前行为时记录被测试的仓库版本或 commit、操作系统、运行时、依赖、模型和关键配置。不要把未经验证的主分支行为写成稳定事实。
- 引用源码、架构和配置时链接到 DeepSeek Harness 的原始仓库、具体文档或代码位置；不要复制一份会快速过期的包清单或 API 清单。

## 技术文章规范

### 读者和范围

文章开头要明确目标读者、前置知识、要解决的问题、文章范围和可观察结果。标题应直接说明主题或问题，避免只有“深入理解”“全面解析”一类无法判断内容的标题。

### 结构和论证

先给结论，再说明问题、背景、关键概念、系统结构、实现过程、验证证据、限制和延伸阅读。每个段落只承载一个主要观点，每个标题只服务于一个明确目的。教程按前置条件和操作顺序组织；解释性文章按概念依赖和证据组织；参考性内容不要伪装成故事。

### 事实、证据和观点

明确区分四类内容：仓库中可以直接观察到的事实、实验或 benchmark 的测量结果、设计理由，以及作者的判断。涉及性能、成本、延迟、准确率或模型能力的结论必须说明版本、环境、输入、方法、样本或数据集和结果；不能用“明显更好”“效果很好”替代证据。外部资料优先引用一手来源，并在快速变化的资料旁标注发布日期或访问日期。

### 代码和复现

代码示例必须服务于文章论点，并尽量通过真实项目入口验证。说明 Node.js、Python、Hugo、模型和依赖版本，给出安装步骤、工作目录、完整命令、相关文件路径、必要 import、预期输出和已知失败条件。伪代码、删节代码和不可直接运行的片段必须显式标注；示例不能包含 API key、token、个人信息、私有路径或不安全的默认配置。

### 语言和可读性

使用具体主语、主动语态、短句和稳定术语；第一次出现的缩写要给出全称。避免空泛的营销词、夸张承诺、隐喻、口语化歧义和没有定义的专业术语。标题层级与正文结构一致，不用加粗或大段感叹来制造重点。

### 图表、引用和可访问性

图片和流程图必须有能传达信息的 alt 文本；图示不能只依赖颜色区分状态，并在正文或图注中说明读者应观察的结论。链接文字要描述目标，不使用孤立的“点击这里”。截图、日志和配置先脱敏，再发布；引用的图表、代码和文字要符合原始资料的许可证要求。

### 安全和边界

文章必须主动说明权限、文件系统、网络、沙箱、成本、延迟、兼容性和失败恢复等重要限制。不要公开真实凭据、用户数据、内部 URL、机器目录或未经授权的日志。涉及安全机制时说明威胁模型、保护范围和未覆盖的情况，避免把“默认配置”写成安全保证。

## 发布和维护

- 内部链接使用 Hugo 站点路径，例如 `/agent/tool-use-core-of-agent/`；文章图片放在同一文章目录并使用相对路径。
- 本地预览使用 `hugo server -D`；发布构建使用 `hugo --gc --minify`。CI 的 Hugo 版本和完整构建参数以 [.github/workflows/deploy-hugo.yml](.github/workflows/deploy-hugo.yml) 为准。
- 发布前检查 front matter、文章链接、图片 alt 文本、代码示例和敏感信息，运行 `hugo --gc --minify` 与 `git diff --check`，并记录实际执行的命令。
- 修改项目行为、版本、接口或验证结果后，同时更新受影响的专栏文章、`lastmod` 和相关延伸阅读。不要留下与当前代码不一致的旧示例。

## 规范来源

本文件的技术写作要求综合了以下公开规范：

- [Google Technical Writing One](https://developers.google.com/tech-writing/one)：受众、范围、段落主题、术语一致、清晰和简洁。
- [Google active voice guidance](https://developers.google.com/tech-writing/one/active-voice) 与 [clear sentences guidance](https://developers.google.com/tech-writing/one/clear-sentences)：主动语态、明确主语和可读句子。
- [Microsoft Writing Style Guide](https://learn.microsoft.com/en-us/style-guide/welcome/)：清晰、简洁、友好和无偏见的表达。
- [Microsoft accessible content guidance](https://learn.microsoft.com/en-us/style-guide/accessible-content/)：替代文本、结构化内容和可访问性。
- [Write the Docs software documentation guide](https://www.writethedocs.org/guide/writing/beginners-guide-to-docs/)：说明项目解决的问题、安装和使用路径，避免用不断膨胀的 FAQ 代替正式内容。
- [Diataxis documentation framework](https://diataxis.fr/)：区分教程、操作指南、解释和参考，选择内容类型后再安排文章结构。
