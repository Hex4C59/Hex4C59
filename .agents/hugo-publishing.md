# Hugo publishing guide

本文件适用于 Hugo 配置、布局、主题样式、文章发布和部署流程的修改。

## Content and links

- 内部链接使用 Hugo 站点路径，例如 `/agent/tool-use-core-of-agent/`；文章图片放在同一文章目录并使用相对路径。
- 修改 front matter、文章链接、图片或布局后，检查生成页面、图片 alt 文本、代码示例和敏感信息。
- `.agents/` 是仓库内部 Agent 指令目录，不属于 `content/`，不应被 Hugo 当作文章发布。

## Series type label colors

修改系列类型标签、系列入口或主题配色时，执行本节规则。颜色按内容类型统一，沿用当前的纯文字标签样式。

| 内容类型 | `series_kind` | 浅色模式 | 样式变量 |
| --- | --- | --- | --- |
| 文章合集 | `collection` | 酒红色 `#A13C54` | `--accent` |
| 译文合集 | `translation` | 灰蓝色 `#405D91` | `--blue` |
| 课程 | `course` | 墨绿色 `#2F6D5B` | `--green` |

- 系列列表、首页最近更新与推荐入口、专题侧栏、文章列表、系列详情和课程目录中的类型标签共用 `layouts/partials/series/kind-label.html`。从系列数据传入 `KindKey`，由 `assets/css/chroma.css` 根据 `data-series-kind` 选择颜色。
- 同一类型在各处使用同一种颜色。系列名称、网址和文章所属主题不参与类型标签的配色；新增系列复用现有类型规则。
- 颜色只用于类型文字。篇数、状态和更新时间使用原有的辅助文字样式，标题、字号、间距和布局沿用页面样式。
- 深色模式使用这些变量已有的浅色版本，避免在标签上直接写固定颜色。保留类型文字，让读者同时通过文字和颜色识别类别。
- `ordered`（有序系列）保留辅助文字色。新增类型时，在 `data/series_kinds.toml` 中定义类型，明确配色后补充本表和共享样式。
- 验收时检查多个同类系列，并对照系列列表、首页和详情页的标签；同时检查手机宽度和深色模式。课程应包含 RTC、Rust 与软件设计，译文合集应包含 AI论文精选与智能体工程模式。

## Local and CI checks

- 本地预览使用 `hugo server -D`。
- 发布检查使用 `python3 scripts/build.py`，它运行 `hugo --gc --minify` 并检查生成链接和课程下载包。Hugo 版本由 [.hugo-version](../.hugo-version) 固定，完整构建参数以 [.github/workflows/deploy-hugo.yml](../.github/workflows/deploy-hugo.yml) 为准。
- 发布前运行统一构建检查、`python3 -m unittest discover -s scripts/tests -v` 与 `git diff --check`，并记录实际执行的命令。目录、模板和资源入口见[维护说明](../docs/development.md)。
- 修改项目行为、版本、接口或验证结果后，同时更新受影响的文章、`lastmod` 和相关延伸阅读，不要留下与当前代码不一致的旧示例。
