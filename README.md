# Hex4C59's Blog

中文技术博客，使用 Hugo 和 Typo，内容包括技术文章、AI Agent、LeetCode 题解和译文。

## 本地预览

```sh
hugo server --bind 127.0.0.1 --port 1313 --disableFastRender
```

浏览器打开 `http://127.0.0.1:1313/`。生成生产页面：

```sh
hugo --gc --minify
```

`public/` 是生成目录，不提交。GitHub Actions 在 `source` 分支推送后构建并部署到 GitHub Pages；仅修改本地文件不会发布网站。构建使用的 Hugo 版本见 `.github/workflows/deploy-hugo.yml`。

## 内容与主题

- `content/`：Markdown 文章及文章内图片，现有文章路径保持不变。
- `themes/typo/`：固定版本的上游主题、字体和许可证，来源与提交见 `themes/typo/UPSTREAM.md`。
- `layouts/`：站点模板覆盖，包含内容栏目与浏览工具两层导航、首页栏目导览、文章列表、专题筛选、搜索、归档、RSS 和评论。
- `assets/css/site.css`：Typo 的中文排版与站点扩展样式。
- `assets/js/site.js`：主题切换、专题筛选和搜索交互；Agent 的阅读类型入口与详细筛选同步。
- `assets/js/vendor/fuse.basic.min.js`：从原主题沿用的 Fuse.js 7.0.0，许可证保留在文件头。
- `static/katex/`：本地数学公式渲染资源。

更新 Typo 时保留站点覆盖文件，并检查首页、文章页、专题筛选、搜索、分页、RSS、代码复制及手机窄屏显示。评论继续使用原 Giscus 仓库和 `pathname` 映射；本地页面可以检查加载和主题同步，但评论登录与提交应在正式域名上确认。
