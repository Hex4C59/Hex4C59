# Hugo publishing guide

本文件适用于 Hugo 配置、布局、主题样式、文章发布和部署流程的修改。

## Content and links

- 内部链接使用 Hugo 站点路径，例如 `/agent/tool-use-core-of-agent/`；文章图片放在同一文章目录并使用相对路径。
- 修改 front matter、文章链接、图片或布局后，检查生成页面、图片 alt 文本、代码示例和敏感信息。
- `.agents/` 是仓库内部 Agent 指令目录，不属于 `content/`，不应被 Hugo 当作文章发布。

## Local and CI checks

- 本地预览使用 `hugo server -D`。
- 发布检查使用 `python3 scripts/build.py`，它运行 `hugo --gc --minify` 并检查生成链接和课程下载包。Hugo 版本由 [.hugo-version](../.hugo-version) 固定，完整构建参数以 [.github/workflows/deploy-hugo.yml](../.github/workflows/deploy-hugo.yml) 为准。
- 发布前运行统一构建检查、`python3 -m unittest discover -s scripts/tests -v` 与 `git diff --check`，并记录实际执行的命令。目录、模板和资源入口见[维护说明](../docs/development.md)。
- 修改项目行为、版本、接口或验证结果后，同时更新受影响的文章、`lastmod` 和相关延伸阅读，不要留下与当前代码不一致的旧示例。
