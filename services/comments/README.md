# 划线评论服务

这层 API 连接 Hugo 文章页和现有的 GitHub Discussions。评论和回复保留在 `Hex4C59/Hex4C59` 的 `Comments` 分类中；既有评论沿用 pathname 映射，不需要迁移。服务自身不保存评论正文，只在每篇文章的 Durable Object 中保存 Discussion ID 和编号，以串行处理首次建帖，避免多人同时评论时建立重复的文章讨论。匿名读取有 15 秒内存缓存，每位登录用户每分钟最多提交 10 次。

## 部署

需要可部署 Workers 和 SQLite Durable Objects 的 Cloudflare 账号。仓库包含部署配置，不包含账号凭据，也不会自动创建资源或发布博客。

在仓库根目录执行：

```sh
node --test services/comments/tests/*.test.mjs
npx --yes wrangler@4.151.0 deploy --dry-run --config services/comments/wrangler.toml
npx --yes wrangler@4.151.0 login
npx --yes wrangler@4.151.0 deploy --config services/comments/wrangler.toml
```

Wrangler 会提供 Worker 的 HTTPS 地址。把这个地址（例如 `https://your-worker.your-subdomain.workers.dev`）填进 GitHub 仓库 Actions 的变量 `COMMENTS_API_URL`，然后按站点原有流程发布。自定义域名或现有代理路由也可以使用，但 API URL 必须指向这份 Worker。

不需要把 GitHub token、Giscus 密钥或 Cloudflare 凭据写进 Hugo 配置。Worker 的 `SITE_URL` 限制浏览器来源，`REPO`、`REPO_ID`、`CATEGORY`、`CATEGORY_ID`、`OWNER` 必须与站点一致。换站点时先修改 `wrangler.toml` 中这些公开配置。`SITE_URL` 支持带站点前缀的部署地址。

当前博客的 Worker 地址为 `https://hex4c59-comments.ex4-59.workers.dev`，通过仓库变量 `COMMENTS_API_URL` 传入生产构建。2026-10-15 已完成实际部署，并检查匿名读取、跨域预检、非本站来源拒绝、未登录拒绝和无效路径拒绝。

## 本地预览

先使用 Wrangler 在本地启动 Worker，并覆盖允许的网站来源；临时配置和运行状态不纳入版本控制：

```sh
npx --yes wrangler@4.151.0 dev --config services/comments/wrangler.toml \
  --var SITE_URL:http://localhost:1313/
```

另一个终端执行：

```sh
HUGO_COMMENTS_API_URL=http://localhost:8787 hugo server -D
```

使用 `http://localhost:1313` 打开文章。来源主机名需要一致，不能把 `localhost` 与 `127.0.0.1` 混用。未登录的真实读取可以访问既有公开评论；发表和管理会写入真实 Discussions，验证时应使用单独的测试仓库。自动化测试替换了上游请求，不向公开仓库发送合成评论。

## 登录与数据

登录继续使用现有 Giscus 的 GitHub 授权。回调通过标签页中一次性的 nonce 核对，并在页面头部移除 URL 中的加密会话参数。浏览器沿用 Giscus 的 `giscus-session` 保存格式；它只把这个加密会话发送给评论 Worker。Worker 请求 Giscus 解密并核对当前 GitHub 用户，短暂使用获得的 token 调用 GitHub；不把 token 返回浏览器、写入持久存储或输出日志。跨站写入、无来源的写入、越过本仓库或本篇文章的回复都会被拒绝。

这份接入依赖 Giscus 当前服务端的 `/api/discussions` 和 `/api/oauth/token`，它们是现有服务实现，不是版本化的公共 SDK 契约。相关调用集中在 `worker.mjs`；上游变更时需要重新核验适配。匿名读取与登录使用现有 Giscus 服务的可用性和 GitHub API 配额。禁用 `annotations.enabled` 或清空 API 地址可恢复原来的 Giscus 嵌入。

每个划线话题是一条普通的 Discussion 顶层评论，包含引用、携带定位信息的“查看划线原文”链接和读者正文。定位保存原文、前后文与段落指纹；原文发生变化或匹配不唯一时保留评论，并提示引用无法定位，不会强行挂到其他句子。

文章更新后，旧引用仍留在 GitHub 评论中。作者精选以作者本人的管理回复记录，普通读者的同名标记不会被采信；折叠与恢复使用 GitHub 原生管理接口。文章所有者可以在侧栏管理，也可以继续到 GitHub 管理。

## 多人讨论与边界

- 首屏读取最近 50 个话题，再按游标加载更早的话题。段落标记只计算已加载的有效话题；有未加载页时带 `+`，页面会说明这个含义。
- 话题可以按精选优先或最新排列；具体话题内的回复按时间排列，分批展开。每 90 秒在面板可见时检查更新，点击更新提示后才合并数据。
- 现有 Giscus 匿名接口每个话题最多提供最近 100 条回复。超过这个范围会明确提供 GitHub 原讨论链接，避免把截取的数据当作完整历史；它不会伪造更早的回复或回复总数。
- 草稿保存在当前标签页的 sessionStorage；切换话题、登录跳转和网络失败时保留。退出登录会移除加密登录会话，草稿保留供读者继续编辑。浏览器完全禁止存储时，当前页面仍可以在内存中保留草稿，但登录跳转和刷新不能保证恢复。
- 自定义界面只渲染评论中允许的 Markdown HTML，移除脚本、表单、事件属性及不安全链接；图片只显示替代文本。没有第三方远程内容自动执行入口。

## 检查

```sh
node --check assets/js/annotations.mjs
node --check services/comments/worker.mjs
node --test services/comments/tests/*.test.mjs
python3 -m unittest discover -s scripts/tests -v
python3 scripts/build.py
```

可选的浏览器检查位于 `services/comments/tests/browser-check.mjs`，需要测试环境能够解析 Playwright，并有可用的 Chrome。在构建产物或 Hugo 预览中启用 API 地址 `http://127.0.0.1:8787`，设置 `BLOG_PREVIEW_URL` 指向本地站点后运行这个文件。检查会拦截全部评论 API 请求，以合成数据验证选区、草稿、错误重试、更新提示、分页、HTML 清理及桌面和手机布局；不会向真实仓库发表测试评论。`ANNOTATION_SCREENSHOTS` 可以指定站点外的截图目录。

本地检查使用替代上游请求和合成评论；线上 API 检查不代表真实访客 OAuth 或发表已经验证。访客登录和一条经授权的测试评论仍需在实际站点核验，不能用本地测试结果代替。
