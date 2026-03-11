# Hex4C59 Blog

这是我的个人博客仓库，使用 [Hugo](https://gohugo.io/) 构建，主题为 [PaperMod](https://github.com/adityatelange/hugo-PaperMod)。

线上地址：[https://www.hex4c59.fun/](https://www.hex4c59.fun/)

## 项目简介

本项目是一个静态博客站点，主要用于：

- 编写和发布博客文章
- 本地预览页面效果
- 通过 GitHub Actions 自动部署到 GitHub Pages

项目特点：

- 静态站点生成器：Hugo
- 主题：PaperMod
- 支持搜索页
- 支持归档页
- 支持标签页
- 支持 KaTeX 数学公式渲染
- 支持 RSS 输出

## 目录结构

```text
.
├── archetypes/         # Hugo 文章模板
├── content/            # 博客内容
│   ├── posts/          # 博文
│   ├── archives.md     # 归档页
│   └── search.md       # 搜索页
├── layouts/            # 自定义模板覆盖
├── static/             # 静态资源
├── themes/             # Hugo 主题
│   └── PaperMod/
├── .github/workflows/  # GitHub Actions 部署配置
└── hugo.toml           # 站点配置
```

## 环境要求

本地开发只需要安装 Hugo extended 版本。

推荐版本：

- Hugo Extended >= 0.150.0

我当前本地验证通过的版本：

- Hugo Extended 0.157.0

注意：

- 普通浏览和线上访问不需要本地启动服务
- 只有在本地调试、预览内容、检查样式时，才需要运行 `hugo server`

## 本地启动说明

### 1. 安装 Hugo

如果你使用 macOS，并且装了 Homebrew：

```bash
brew install hugo
```

安装完成后可检查版本：

```bash
hugo version
```

如果输出中包含 `extended`，说明可正常用于本项目。

### 2. 克隆仓库

```bash
git clone <your-repo-url>
cd Hex4C59
```

### 3. 启动本地开发服务器

在项目根目录执行：

```bash
hugo server --bind 127.0.0.1 --port 1313
```

启动后在浏览器打开：

- [http://127.0.0.1:1313](http://127.0.0.1:1313)

Hugo 会监听内容和模板变更，保存后会自动刷新页面。

### 4. 仅做构建检查

如果你不需要本地预览，只想确认站点能否正常构建：

```bash
hugo
```

构建成功后会生成：

- `public/`：静态站点输出目录

## 常用开发命令

### 本地预览

```bash
hugo server
```

### 指定端口启动

```bash
hugo server --bind 127.0.0.1 --port 1313
```

### 构建生产版本

```bash
hugo --gc --minify
```

### 创建新文章

```bash
hugo new posts/my-new-post/index.md
```

创建后到对应文件中编写内容即可。

## 写作说明

博客文章主要位于：

- `content/posts/`

常见页面包括：

- `content/archives.md`：归档页
- `content/search.md`：搜索页

新增文章建议使用如下结构：

```text
content/posts/my-post/index.md
```

这样便于后续为文章添加配图或其他资源。

## 文章管理：增删改查

本项目中的已发布文章，本质上就是 `content/posts/` 目录下的 Markdown 文件。
因此，对文章的增删改查，主要就是对文章文件及其 front matter 进行管理。

### 查：查看和定位文章

所有文章主要位于：

- `content/posts/`

推荐的文章结构：

```text
content/posts/my-post/index.md
```

可以通过以下方式查看文章：

- 直接在 `content/posts/` 下定位文章目录
- 打开对应的 `index.md` 查看正文和 front matter
- 启动本地服务后在浏览器中检查文章页、归档页、搜索页、标签页

文章头部通常会包含类似下面的 front matter：

```yaml
---
title: "文章标题"
date: 2026-03-11T10:00:00+08:00
draft: false
tags: ["Hugo", "Blog"]
---
```

常用字段说明：

- `title`：文章标题
- `date`：发布时间
- `draft`：是否为草稿
- `tags`：文章标签
- `summary` 或 `description`：摘要

本地查看文章效果时，可运行：

```bash
hugo server
```

然后访问：

- <http://127.0.0.1:1313>

### 增：新增文章

推荐使用 Hugo 命令创建新文章：

```bash
hugo new posts/my-new-post/index.md
```

创建完成后，编辑生成的 `index.md` 即可。

如果希望文章正式发布，需要确认 front matter 中：

```yaml
draft: false
```

如果文章还是草稿状态，可在本地使用下面命令预览：

```bash
hugo server -D
```

其中 `-D` 表示在本地同时显示草稿文章。

### 改：修改已发布文章

已发布文章的修改主要分为两类：

#### 1. 修改正文内容

直接编辑对应文章文件，例如：

```text
content/posts/my-post/index.md
```

保存后，运行中的 `hugo server` 会自动刷新页面。

#### 2. 修改文章元信息

也就是修改 front matter，例如：

- 标题
- 发布时间
- 标签
- 摘要
- 草稿状态
- 封面图等参数

示例：

```yaml
---
title: "新的标题"
date: 2026-03-11T10:00:00+08:00
draft: false
tags: ["AI", "Hugo"]
---
```

修改完成后，建议执行一次构建检查：

```bash
hugo
```

然后再提交并推送到远程仓库：

```bash
git add .
git commit -m "update post"
git push origin source
```

### 删：删除或下线文章

#### 1. 彻底删除文章

直接删除对应文章目录，例如：

```text
content/posts/my-old-post/
```

删除后建议本地预览并执行构建检查，确认首页、归档页、搜索页中都不再出现该文章。

#### 2. 临时下线文章

如果不想真正删除文件，可以把文章改为草稿：

```yaml
draft: true
```

这样：

- 正式构建不会发布该文章
- 本地使用 `hugo server -D` 时仍可查看

### 常见管理场景

#### 1. 判断文章是否已发布

建议检查：

- 文件是否仍在 `content/posts/` 下
- front matter 中是否为 `draft: false`
- 本地执行 `hugo` 是否构建成功
- 本地页面中是否可以访问到该文章

#### 2. 文章为什么没有显示

优先检查：

- 文件路径是否正确
- front matter 格式是否写坏
- `draft` 是否为 `true`
- Markdown 文件结构是否规范
- 本地执行 `hugo` 是否报错

#### 3. 如何确认文章是否被搜索或归档收录

本地运行：

```bash
hugo server
```

然后查看：

- `/archives/`
- `/search/`
- `/tags/`

### 推荐的文章管理流程

#### 新增文章

```bash
hugo new posts/my-post/index.md
```

#### 修改文章

直接编辑：

```text
content/posts/my-post/index.md
```

#### 本地预览

```bash
hugo server
```

#### 构建检查

```bash
hugo
```

#### 发布变更

```bash
git add .
git commit -m "update post"
git push origin source
```

#### 删除文章

删除对应目录后，再提交并推送。

## 配置说明

站点主要配置文件为：

- `hugo.toml`

其中包含：

- 站点基础信息
- 菜单配置
- 主题参数
- 搜索配置
- KaTeX 配置
- RSS 输出配置相关参数

### 主题

当前主题为：

- `PaperMod`

配置项示例：

- 首页信息
- 社交链接
- 阅读时长
- 字数统计
- 面包屑导航
- 文章目录

### 数学公式

当前项目已集成 KaTeX，相关静态资源位于：

- `static/katex/`

额外头部注入位于：

- `layouts/partials/extend_head.html`

如果文章中需要公式，可直接在 Markdown 中使用常见数学公式语法。

## 部署说明

本项目不是依赖本地常驻服务上线，而是通过 GitHub Actions 自动部署。

当前部署方式：

- 推送到 `source` 分支
- 触发 `.github/workflows/deploy-hugo.yml`
- Actions 自动构建 Hugo 站点
- 构建产物部署到 GitHub Pages

也就是说：

- 本地只在开发调试时才需要执行 `hugo server`
- 正式上线依赖 GitHub Actions，不需要手动上传 `public/`

## 发布流程

推荐的日常发布流程如下：

### 1. 本地修改内容或样式

例如修改：

- `content/posts/...`
- `layouts/...`
- `hugo.toml`

### 2. 本地预览

```bash
hugo server
```

### 3. 本地构建检查

```bash
hugo
```

### 4. 提交并推送到远程仓库

```bash
git add .
git commit -m "update blog content"
git push origin source
```

### 5. 等待 GitHub Actions 自动部署完成

部署完成后即可在线上查看效果。

## 已知说明

- 本项目包含自定义 RSS 模板：`layouts/index.rss.xml`
- 为兼容当前 Hugo 版本，RSS 作者信息使用 `params.author` 与 `params.authorEmail`
- `public/`、`resources/`、`.hugo_build.lock` 已在 `.gitignore` 中忽略

## 故障排查

### 1. 运行 `hugo` 报错：找不到命令

说明本机尚未安装 Hugo，先执行：

```bash
brew install hugo
```

### 2. 运行 `hugo version` 后没有 `extended`

说明安装的不是扩展版 Hugo，可能会影响某些主题或资源处理能力。建议重新安装官方/包管理器提供的 extended 版本。

### 3. 本地能打开，线上没有更新

请检查：

- 是否推送到了 `source` 分支
- GitHub Actions 是否执行成功
- GitHub Pages 是否已正确关联该 workflow 的部署结果

### 4. 搜索页或归档页异常

请确认以下内容文件存在：

- `content/search.md`
- `content/archives.md`

并确认 `hugo.toml` 中输出配置未被误改。

## 维护建议

建议每次发布前至少执行一次：

```bash
hugo
```

这样可以在推送前尽早发现模板、配置或内容问题。

---

如果只是阅读线上博客，不需要在本地启动任何服务。
只有在本地写作、调试、预览时，才需要运行 `hugo server`。