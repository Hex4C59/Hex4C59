# 博客维护

这个仓库使用 Hugo 和 Typo。正文、布局和站点资源各有固定入口；日常写作通常只需要改文章目录，公共显示和发布规则集中维护。

## 目录用途

| 路径 | 用途 |
| --- | --- |
| `content/articles/` | 新文章的统一目录；首页与文章页也汇总旧目录中的文章 |
| `content/agent/`、`content/tutorials/`、`content/posts/`、`content/translations/` | 已发布正文与兼容入口，保留现有网址和资源 |
| `content/series/` | 系列说明与阅读入口，成员正文只存放一份 |
| `content/categories/`、`content/tags/` | 分类显示信息与历史名称的跳转 |
| `content/about.md` | 作者与博客介绍 |
| `data/navigation.toml` | 首页、文章、系列、关于等稳定导航 |
| `data/categories.toml` | 主题键、名称、说明和顺序 |
| `data/article_sources.toml`、`data/article_types.toml` | 来源与文章形式 |
| `data/series_kinds.toml`、`data/series_roles.toml` | 系列类型、成员角色与是否参与阅读顺序 |
| `data/collections.toml` | 统一文章列表的筛选项 |
| `data/sections.toml` | 正文目录登记、评论开关与旧入口的筛选配置 |
| `layouts/`、`assets/`、`static/` | 页面模板、构建资源与直接复制的静态文件 |
| `archetypes/` | 新文章的 front matter 模板 |
| `scripts/` | 构建、链接检查、课程打包与行为测试 |
| `.agents/` | 内部写作与操作规则，不发布为正文 |
| `themes/typo/` | 当前使用的上游主题；本站覆盖优先放在 `layouts/` 和 `assets/` |

## 站点外观与动效

本站的排版覆盖位于 `assets/css/site.css`，配色和交互样式集中在 `assets/css/chroma.css`，通过 `layouts/partials/head/css.html` 合并。亮色与暗色使用同一组语义变量。首页主栏展示最近文章，侧栏展示系列和主题；阅读插画复用个人主页的 Open Doodles 素材，来源见 `assets/profile/README.md`。

`assets/js/motion.js` 管理入场动效和页脚中的动效开关。首页首屏直接显示，其余列表使用 320 毫秒的短距离入场。文章首屏使用 600 毫秒的淡入上移，标题、摘要和元信息略微错开；正文按二级标题分组，以 650 毫秒触发一次入场，同组内容同步出现，不逐段重复播放。它不改写正文结构，也不在 CSS 中预先隐藏内容。锚点跳转、带片段地址进入和恢复阅读位置时，目标章节直接可读。动效偏好存储在本机 `localStorage`；关闭动效或系统启用“减少动态效果”时，取消正在播放的入场并移除过渡。无 JavaScript 时正文和完整目录仍可使用。

## 新建文章

先按[内容归类规则](../.agents/content/section-routing.md)选择主题、来源、形式和阅读关系。新文章统一放在 `articles`，内容可以是技术、阅读、旅行或日常观察。

```sh
hugo new content articles/my-article/index.md
hugo new content --kind translations articles/my-translation/index.md
hugo new content --kind agent articles/my-agent-article/index.md
```

正文使用叶子页面包：`index.md` 和图片、图表、下载文件放在同一目录。发布前填写标题、日期、作者、描述、主题与标签，确认译文的出处完整，再将 `draft` 改为 `false`。例如：

```toml
categories = ["programming"]
source_kind = "original"
article_type = "tutorial"
tags = ["Rust", "所有权", "借用"]
```

`categories` 使用数据文件中的稳定主题键；`article_type` 可选。技术文章按需设置学习难度、公式或示例，其他文章无需这些字段。

新增主题时只需在 `data/categories.toml` 增加名称、说明和顺序，然后把键填写到文章中。分类页、文章筛选和首页主题入口会自动出现。改名优先调整显示名称，保持主题键与网址稳定。没有文章的主题不显示在浏览入口。

每篇文章最多填写 3 个标签，使用具体、统一且贴合正文主题的名称。构建时会检查标签数量。归并旧标签时，在新标签的 `content/tags/<slug>/_index.md` 中设置旧地址的 `aliases`。普通标签无需建立单独的内容文件。

已发布文章保留原目录及 `url`。例如 Rust 正文仍在 `content/tutorials/`，公开地址仍为 `/posts/rust-…/`；旧 Agent 和译文入口也继续可访问。

## 连续课程与系列

系列说明放在 `content/series/<key>/_index.md`，成员使用相同的 `series` 键。普通合集可以不填排序，按最近更新展示；需要固定顺序时为所有正文填写唯一的 `series_order`。

连续阅读系列增加一个 `series_index = true`、`layout = "series"` 的目录文章。目录可以选择 `series_kind = "course"`、`"translation"` 或 `"ordered"`。成员可以来自不同源目录；文章最多加入一个连续阅读系列，还可以加入多个开放合集。

```toml
# 正式章节
series = ["rust-from-zero"]
series_role = "chapter"
series_order = 4
series_number = 4
```

```toml
# 配套附录：属于同一课程，不参与章节顺序
series = ["rust-from-zero"]
series_role = "appendix"
```

导读使用 `guide`，练习使用 `exercise`。只有参与阅读顺序的成员填写非负整数 `series_order`；章号为唯一的正整数。配套资料不填这两个字段。角色与显示名称在 `data/series_roles.toml` 中维护，是否参与顺序由 `in_sequence` 决定。

系列起点 `series_start` 使用源路径，例如 `/tutorials/rust-00-learning-guide/`；正文链接使用公开网址。首页和文章页把连续系列合并到目录入口，更新日期包含附录。文章列表可展开成员，标签页默认展开；搜索和归档保留全部内容页。

首页的推荐起点由 `hugo.toml` 中的 `startSeries` 选择，精选系列由 `featuredSeries` 选择。内容主题变化时调整这些选择，不修改首页模板。

## 样式与脚本

`layouts/partials/head/css.html` 是唯一的公共 CSS 入口。它依次合并主题基础样式、字体、代码高亮、配色和本站样式，生成一个带指纹的 CSS 文件。修改本站样式放在 `assets/css/site.css`，代码配色放在 `assets/css/syntax-highlighting.css`。

文章页与连续阅读系列共用 `layouts/partials/reader/outline.html`。桌面目录按章节展开，子目录使用 300 毫秒的网格高度过渡；折叠内容退出键盘和辅助技术访问，关闭动效时即时切换。当前章节自动显示下级小节；读者手动展开或收起的状态在当前浏览会话中按文章保存。系列目录单独折叠，手机端点击本文目录完成定位后收起并把焦点交给对应标题。关闭 JavaScript 时仍可展开完整目录并使用锚点。

文章阅读交互放在 `assets/js/reader.js`，仅在文章页加载。它按正文更新字符进度，并提供复制链接、复制 Markdown 和下载 Markdown。手机端把保存工具移到文章头部，进度保留在底部。复制受限时显示可选中的文本；Markdown 读取失败时保留重试和下载入口。

`layouts/partials/reader/markdown.html` 在构建时生成带内容摘要文件名的 Markdown，并在 HTML 中提供 `text/markdown` alternate 链接。导出包含标题、作者、日期和原文地址，展开 Hugo shortcode，保留围栏代码及公式；常规图片、附件、站内链接和 HTML 图片地址转为绝对地址，展示用脚本与样式不进入正文。草稿只会在显式包含草稿的预览中生成，生产构建不发布草稿导出。

普通文章末尾通过 `reader/related-data.html` 选择最多三条继续阅读入口，按同系列、同话题、同主题排序，并展示对应关系。连续课程合并到目录入口，系列文章保留章节顺序导航。可以在文章 front matter 中优先指定入口及理由；`ref` 使用源内容路径，目标必须是另一篇已发布页面：

```toml
related_reading = [
  { ref = "/articles/example/", reason = "补充前置知识" },
]
```

正文和全站主标题、文章列表标题使用 Source Sans 3 与思源黑体；文章内的小节标题、元信息、目录和代码使用 Anthrosevka Mono 的本地网页子集 Hex Mono，中文回退到思源黑体。站点品牌标题保留原有衬线字体，页脚复用首页的阅读者插画并生成独立的深浅色资源。字体在 `static/fonts/editorial/` 与 `static/fonts/anthrosevka/` 自托管，来源、许可与摘要随文件记录。代码块由 `layouts/_default/_markup/render-codeblock.html` 统一提供语言栏和复制按钮。

链接颜色和按钮背景使用 160–180 毫秒的短过渡，导航下划线与少量箭头使用 200–220 毫秒的位移过渡，同样遵循动效偏好。公共交互由 `assets/js/site.js` 负责。Fuse 和 `assets/js/search.js` 仅在搜索页加载；搜索索引仍在读者输入关键词后请求。存在代码块时加载复制按钮脚本；Mermaid 的加载继续由代码块渲染钩子决定。

需要数学公式的文章在 front matter 中填写 `math = true`，支持 `$…$` 和 `$$…$$`。未开启的页面不加载 KaTeX。连续阅读布局同时考虑当前展示章节与目录文章的设置。

## 预览与发布检查

Hugo 固定为 `.hugo-version` 中的版本。本地和 CI 读取同一个版本文件；升级时一起运行以下检查，不单独修改工作流中的版本号。验证工具只使用 Python 3.9 及以上的标准库，无需安装 npm、Go 或 Dart Sass 工具链。

```sh
hugo version
hugo server -D
```

发布检查使用统一入口：

```sh
python3 -m unittest discover -s scripts/tests -v
python3 scripts/build.py
git diff --check
```

`build.py` 检查 Hugo 版本和课程 ZIP，运行 `hugo --gc --minify --cleanDestinationDir`，再检查生成 HTML 与 CSS 中的站内链接、资源地址、页面锚点及搜索索引。Hugo 模板在构建时检查栏目、文章元数据、系列排序和入口。任何检查失败都会以非零状态退出，CI 会在上传 Pages 产物之前停止。

统一构建入口会清理输出目录中的旧生成文件，`--destination` 应指向专门存放构建产物的目录。仅检查已有构建或使用临时输出目录时：

```sh
python3 scripts/check_site.py public
python3 scripts/build.py --destination /tmp/blog-preview
```

发布到带路径前缀的地址时，可以传入 `--base-url https://example.org/blog/`；CI 使用 GitHub Pages 给出的地址。检查范围是本站构建产物，不请求外部网站，也不代替文章归类判断或代码示例的运行验证。

## Rust 配套源码

课程源码位于 `content/tutorials/rust-from-zero/course/`，下载包位于旁边的 `course.zip`，公开地址为 `/posts/rust-from-zero/course.zip`。

改完源码后重新打包并检查：

```sh
python3 scripts/package_course.py --write
python3 scripts/package_course.py --check
```

打包工具固定文件顺序、ZIP 时间戳和权限，保留 `rust-course/` 顶层目录，排除编译产物与课程运行数据。同一环境中，源码不变时再次打包会得到相同字节。检查模式逐文件比较下载包与源码，能发现遗漏、额外文件和内容不一致。提交课程变动时一起提交源码和 ZIP。

## 部署

推送 `source` 分支会触发 `.github/workflows/deploy-hugo.yml`。工作流从 `.hugo-version` 安装 Hugo，校验官方压缩包摘要，然后运行工具测试、站点构建和发布检查，通过后部署到 GitHub Pages。

README 继续用作 GitHub 个人主页；维护说明放在本文件。站点凭据通过 GitHub 的环境变量或本机环境提供，不写入正文、配置或构建日志。
