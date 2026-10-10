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

## 访问统计

站点支持 Cloudflare Web Analytics，统计页面浏览量、访问来源和文章路径。统计脚本只在生产构建中加载；`hugo server` 不加载，本地预览不计入正式数据。它统计页面访问，不代表读者读完了文章。

首次启用：

1. 在 Cloudflare 后台进入 **Web Analytics**，添加 `hex4c59.cc`，使用手动安装脚本的方式。此方式无需更换 DNS 或迁移 GitHub Pages。
2. 从安装代码的 `data-cf-beacon` 中取得 `token` 值。它是 32 位十六进制的网站统计标识，区别于 Cloudflare API Token；这里不需要账户 API 凭据。
3. 在 GitHub 仓库 **Settings → Secrets and variables → Actions → Variables** 添加仓库变量 `CLOUDFLARE_WEB_ANALYTICS_TOKEN`，值为该网站统计标识。工作流会将它映射到 Hugo 允许读取的环境变量 `HUGO_CLOUDFLARE_WEB_ANALYTICS_TOKEN`。不要把实际标识写进仓库文件。
4. 重新运行 **Deploy Hugo Site to Pages** 工作流。部署后检查首页和文章页包含 `static.cloudflareinsights.com/beacon.min.js`，再到 Cloudflare Web Analytics 确认收到数据。

缺少该变量时不会输出统计脚本，不能视为统计已启用。错误格式会使生产构建失败，避免误用账户 API Token。可通过 `params.analytics.cloudflare.enabled = false` 停用统计。

后台按 **Path** 查看各篇文章的页面浏览量，按 **Referer** 查看访问来源。历史访问不会因接入而补录，屏蔽统计脚本的浏览器可能不会计入。

接入依据：Cloudflare 官方 [安装说明](https://developers.cloudflare.com/web-analytics/get-started/)与[数据维度](https://developers.cloudflare.com/web-analytics/data-metrics/dimensions/)。
