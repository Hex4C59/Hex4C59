# 博客维护

这个仓库使用 Hugo 和 Typo。正文、布局和站点资源各有固定入口；日常写作通常只需要改文章目录，公共显示和发布规则集中维护。

## 目录用途

| 目录或文件 | 用途 |
| --- | --- |
| `content/agent/` | 原创 Agent 专题文章 |
| `content/tutorials/` | 编程、工具和原理教程，以及配套练习、参考资料 |
| `content/posts/` | 经验、比较、选型、观点和生活随笔 |
| `content/translations/` | 以外文原作为主体的翻译与译述 |
| `content/series/` | 系列专题页；正文仍放在自己的主栏目 |
| `archetypes/` | 新文章模板 |
| `data/sections.toml` | 栏目顺序、名称、导航地址、文章收录、评论和筛选配置 |
| `data/article_types.toml` | Agent 文章类型的字段值、显示标签和排序 |
| `data/collection_labels.toml` | 难度、主题及其他筛选值的中文标签 |
| `layouts/` | 本站布局覆盖；`partials/site/` 读取公共配置，`partials/series/` 处理系列阅读 |
| `assets/css/`、`assets/js/` | 通过 Hugo 合并、压缩并加内容指纹的样式和脚本 |
| `static/` | 字体、KaTeX 等保持固定地址的资源；`static/CNAME` 是域名文件的唯一来源 |
| `themes/typo/` | 当前使用的主题；本站改动优先放在 `layouts/` 和 `assets/` 中 |
| `scripts/` | 构建、链接检查、课程打包和验证工具 |
| `.agents/` | Agent 工作规则与写作计划，不参与站点发布 |
| `public/`、`resources/`、`.hugo_build.lock` | 本地生成物，不提交 |

## 新建文章

先按[栏目归类规则](../.agents/content/section-routing.md)选择目录。文章来源优先于主题：翻译放“译文”；原创 Agent 内容放“Agent”；其他教学内容放“教程”；经历与判断放“随笔”。系列组织阅读顺序，栏目说明文章的主要用途。

```sh
hugo new content --kind tutorials tutorials/my-first-topic/index.md
hugo new content --kind agent agent/my-agent-topic/index.md
hugo new content --kind translations translations/my-translation/index.md
hugo new content posts/my-observation/index.md
```

文章采用叶子页面包：正文是 `index.md`，图片、图表和下载文件放在旁边，用相对路径引用。发布前填写标题、日期、作者和 `description`，确认 `tags`、`categories` 为数组，再将 `draft` 改为 `false`。模板还提供 `summary`；未填写时 Hugo 会生成摘要。

Agent 文章需要 `difficulty` 和 `article_type`；五种类型的可用值见 `data/article_types.toml`。译文需要原文标题、URL、作者和站点名。草稿可以保留待填字段，发布构建只检查已发布文章。

文章目录决定栏目。Rust 教程虽存放在 `content/tutorials/`，仍通过 front matter 的 `url` 保留原来的 `/posts/rust-…/` 地址。这些地址同时用于外部链接和评论定位，迁移时不要删除。

## 连续课程与系列

章节填写 `series = ["系列键"]` 和非负整数 `series_order`。同一个系列内的章节排序不能重复。需要显示章号时使用正整数 `series_number`，章号也不能重复；序言可以不填章号。

专题说明放在 `content/series/<key>/_index.md`。其中的 `series_start` 使用正文的源路径，例如 `/tutorials/rust-00-learning-guide/`，供 Hugo 的 `site.GetPage` 查找。正文里的阅读链接使用公开地址，例如 `/posts/rust-00-learning-guide/`。两者在迁移过的文章上可能不同。

需要连续阅读布局时，创建一个带 `series_index = true`、`layout = "series"` 的目录文章，并且只加入一个系列。目录文章不参与章节序号去重，每个系列最多有一个目录文章；章节与目录文章放在同一主栏目。配套附录可以留在同一栏目，不加入正式章节序列。

目录文章可用 `series_notes_label` 自定义折叠说明的标题。教程默认显示“目录与配套资料”，译文默认显示“原指南目录与译文说明”。

## 样式与脚本

`layouts/partials/head/css.html` 是唯一的公共 CSS 入口。它依次合并主题基础样式、字体、代码高亮、配色和本站样式，生成一个带指纹的 CSS 文件。修改本站样式放在 `assets/css/site.css`，代码配色放在 `assets/css/syntax-highlighting.css`。

公共交互由 `assets/js/site.js` 负责。Fuse 和 `assets/js/search.js` 仅在搜索页加载；搜索索引仍在读者输入关键词后请求。存在代码块时加载复制按钮脚本；Mermaid 的加载继续由代码块渲染钩子决定。

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
