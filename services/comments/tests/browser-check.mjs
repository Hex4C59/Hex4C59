// Optional integration check: run against a local build with annotations enabled.
// All comment API calls are fulfilled locally; no synthetic posts reach GitHub.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { makeAnchor, encodeAnchor } from '../../../assets/js/annotations-model.mjs';
const { chromium } = createRequire(import.meta.url)('playwright');
const base = process.env.BLOG_PREVIEW_URL;
if (!base) throw Error('Set BLOG_PREVIEW_URL to a local Hugo preview with HUGO_COMMENTS_API_URL=http://127.0.0.1:8787');
const artifacts = process.env.ANNOTATION_SCREENSHOTS;
if (artifacts) await mkdir(artifacts, { recursive: true });
const target = new URL('/articles/software-design-02-contracts/', base).href;
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const escape = text => text.replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
let checks = 0;
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  await context.addInitScript(() => localStorage.setItem('giscus-session', JSON.stringify('test-session-for-browser-only')));
  const page = await context.newPage();
  await page.clock.install();
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  let roots = [], posts = 0, failNextPost = false, seed = false;
  const author = { login: 'Reader', url: 'https://github.com/Reader' };
  const comment = (id, message, replies = []) => ({ id, bodyHTML: `<p>${escape(message)}</p>`, createdAt: '2026-10-15T01:00:00Z', author, replies, replyCount: replies.length,
    url: 'https://github.com/Hex4C59/Hex4C59/discussions/1#discussioncomment-' + id, isMinimized: false, upvoteCount: 0 });
  async function anchored(id, index, start, end, message) {
    const blocks = await page.locator('[data-reader-content]').evaluate(content => Array.from(content.querySelectorAll('p, pre, ul, ol, table')).filter(el => !el.parentElement.closest('p, pre, ul, ol, table') && !el.closest('figure, .katex, .interactive-diagram, [data-no-annotation]') && el.textContent.trim()).map(el => el.textContent));
    const anchor = makeAnchor(blocks[index], index, start, Math.min(end, blocks[index].length), 'fixture-anchor-' + id);
    const item = comment(id, message);
    item.bodyHTML = `<blockquote><p>${escape(anchor.quote)}</p></blockquote><p><a href="${target}#annotation=${encodeAnchor(anchor)}">查看划线原文</a></p><p>${escape(message)}</p>`;
    return item;
  }
  await page.route('http://127.0.0.1:8787/**', async route => {
    const request = route.request(), url = new URL(request.url());
    const headers = { 'Access-Control-Allow-Origin': new URL(base).origin, 'Access-Control-Allow-Headers': 'Content-Type, Authorization', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS' };
    const fulfill = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', headers, body: JSON.stringify(body) });
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    if (url.pathname.endsWith('/viewer')) return fulfill({ viewer: { login: 'Hex4C59' } });
    if (url.pathname.endsWith('/discussion')) {
      if (!seed) {
        seed = true;
        roots = await Promise.all([
          anchored('one', 0, 0, 22, '同一句话可以分别讨论几个问题吗？'),
          anchored('two', 0, 8, 30, '引用重叠时也保留不同话题'),
          anchored('three', 0, 0, 22, '一次实践补充'),
          anchored('four', 1, 0, 18, '下一段的讨论'),
        ]);
        roots[0].replies = Array.from({ length: 12 }, (_, i) => comment('reply-' + i, '第 ' + (i + 1) + ' 条回复')); roots[0].replyCount = 12;
        roots.push(comment('general', '已有文章级评论也能继续查看'));
        const unsafe = comment('unsafe', 'unsafe'); unsafe.bodyHTML = '<p>安全显示评论</p><img src=x onerror="window.annotationXSS=true"><script>window.annotationXSS=true</script><a href="javascript:alert(1)" onclick="window.annotationXSS=true">危险链接</a>'; roots.push(unsafe);
      }
      return fulfill({ discussion: { id: 'discussion', totalCommentCount: roots.length, locked: false, comments: roots, pageInfo: { hasPreviousPage: false, startCursor: 'cursor' } } });
    }
    if (url.pathname.endsWith('/comment')) {
      posts++;
      if (failNextPost) { failNextPost = false; return fulfill({ error: '合成网络错误' }, 503); }
      const body = request.postDataJSON();
      const item = comment('created-' + posts, body.message);
      if (body.replyToId) { const root = roots.find(item => item.id === body.replyToId); root.replies.push(item); root.replyCount++; }
      else {
        item.bodyHTML = body.anchor ? `<blockquote><p>${escape(body.anchor.quote)}</p></blockquote><p><a href="${target}#annotation=${encodeAnchor(body.anchor)}">查看划线原文</a></p><p>${escape(body.message)}</p>` : item.bodyHTML;
        roots.push(item);
      }
      return fulfill({ comment: item, discussion: { id: 'discussion', number: 1 } }, 201);
    }
    if (url.pathname.endsWith('/moderate')) return fulfill({ ok: true });
    throw Error('Unexpected test API request: ' + url.pathname);
  });
  await page.goto(target); await page.locator('.annotation-marker').first().waitFor();
  await page.evaluate(() => document.fonts.ready);
  const marker = page.locator('.annotation-marker').first();
  assert.equal(await marker.textContent(), '3'); checks++;
  await marker.click(); await page.locator('[data-open-thread="one"]').waitFor();
  assert.equal(await page.locator('.annotation-topic').count(), 3); checks++;
  await page.locator('[data-open-thread="one"]').click();
  assert.equal(await page.evaluate(() => CSS.highlights.get('annotation-active').size), 1); checks++;
  assert.equal(await page.locator('.annotation-reply').count(), 8);
  await page.locator('[data-more-replies]').click(); assert.equal(await page.locator('.annotation-reply').count(), 12); checks++;
  await page.locator('textarea#annotation-message').fill('保留这个回复草稿');
  await page.locator('[data-back]').click(); await page.locator('[data-open-thread="two"]').click();
  await page.locator('textarea#annotation-message').fill('另一个话题的草稿');
  await page.locator('[data-back]').click(); await page.locator('[data-open-thread="one"]').click();
  assert.equal(await page.locator('textarea#annotation-message').inputValue(), '保留这个回复草稿'); checks++;
  failNextPost = true;
  await page.locator('.annotation-composer [type="submit"]').click(); await page.locator('.annotation-error').waitFor();
  assert.equal(await page.locator('textarea#annotation-message').inputValue(), '保留这个回复草稿'); checks++;
  await page.locator('.annotation-composer [type="submit"]').click();
  await page.locator('.annotation-comment-body').filter({ hasText: '保留这个回复草稿' }).waitFor(); checks++;
  await page.keyboard.press('Escape'); await page.locator('[data-panel]').waitFor({ state: 'hidden' }); checks++;

  async function selectFirst() {
    await page.locator('[data-reader-content] > p').first().scrollIntoViewIfNeeded();
    await page.locator('[data-reader-content] > p').first().evaluate(el => {
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); const text = walker.nextNode();
      const range = document.createRange(); range.setStart(text, 0); range.setEnd(text, Math.min(18, text.length));
      const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range); el.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }));
    });
    await page.locator('[data-comment-selection]').click(); await page.locator('[data-start-compose]').click();
  }
  await selectFirst();
  await page.locator('textarea#annotation-message').fill('划线草稿在重新选择后保留'); await page.locator('[data-close]').click();
  await selectFirst(); assert.equal(await page.locator('textarea#annotation-message').inputValue(), '划线草稿在重新选择后保留'); checks++;
  await page.locator('.annotation-composer [type="submit"]').click();
  await page.locator('.annotation-comment-body').filter({ hasText: '划线草稿在重新选择后保留' }).waitFor(); checks++;
  await page.locator('[data-close]').click();
  await page.locator('[data-open-all]').click(); if (!await page.locator('[data-open-thread="unsafe"]').count()) await page.locator('[data-more-topics]').click(); await page.locator('[data-open-thread="unsafe"]').click();
  assert.equal(await page.locator('.annotation-comment-body script, .annotation-comment-body img, .annotation-comment-body [onclick], .annotation-comment-body a[href^="javascript:"]').count(), 0);
  assert.equal(await page.evaluate(() => window.annotationXSS), undefined); checks++;

  await page.locator('[data-close]').click(); await page.locator('[data-open-all]').click();
  await page.locator('[data-open-thread="one"]').click(); await page.locator('textarea#annotation-message').fill('更新到来时继续编辑');
  roots.push(comment('remote-new', '新到的话题'));
  await page.clock.fastForward(91000);
  await page.locator('[data-apply-pending]').waitFor();
  assert.equal(await page.locator('textarea#annotation-message').inputValue(), '更新到来时继续编辑'); checks++;
  await page.locator('[data-apply-pending]').click(); assert.equal(await page.locator('textarea#annotation-message').inputValue(), '更新到来时继续编辑'); checks++;
  await page.clock.resume();
  await page.locator('[data-back]').click();
  if (artifacts) await page.screenshot({ path: artifacts + '/blog-annotations-desktop.png' });
  for (const width of [1280, 1060, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    const size = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
    assert.ok(size.scroll <= size.width + 1, `Horizontal overflow at ${width}: ${JSON.stringify(size)}`); checks++;
    const dialogBox = await page.locator('[data-panel]').boundingBox();
    assert.ok(dialogBox.x >= -1 && dialogBox.x + dialogBox.width <= width + 1); checks++;
    if (width === 390 && artifacts) await page.screenshot({ path: artifacts + '/blog-annotations-mobile.png' });
  }
  await page.keyboard.press('Escape'); await page.locator('[data-panel]').waitFor({ state: 'hidden' }); checks++;
  assert.deepEqual(errors, []); checks++;
  await context.close();
  for (const trusted of [true, false]) {
    const authContext = await browser.newContext();
    await authContext.addInitScript(({ trusted }) => {
      sessionStorage.setItem('annotation-login-pending', JSON.stringify({ nonce: trusted ? 'expected-nonce' : 'different-nonce', expires: Date.now() + 600000 }));
    }, { trusted });
    await authContext.route('http://127.0.0.1:8787/**', route => route.fulfill({
      status: route.request().method() === 'OPTIONS' ? 204 : 200,
      headers: { 'Access-Control-Allow-Origin': new URL(base).origin, 'Access-Control-Allow-Headers': 'Content-Type, Authorization', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS' },
      contentType: 'application/json',
      body: route.request().method() === 'OPTIONS' ? '' : JSON.stringify(route.request().url().endsWith('/viewer') ? { viewer: { login: 'Reader' } } : { discussion: null }),
    }));
    const authPage = await authContext.newPage();
    authPage.on('pageerror', error => errors.push(error.message));
    await authPage.goto(target + '?giscus=callback-session-sample&annotation_login=expected-nonce');
    const callback = await authPage.evaluate(() => ({ search: location.search, session: JSON.parse(localStorage.getItem('giscus-session') || 'null'), pending: sessionStorage.getItem('annotation-login-pending') }));
    assert.equal(callback.search, ''); checks++;
    assert.equal(callback.session, trusted ? 'callback-session-sample' : null); checks++;
    assert.equal(callback.pending, null); checks++;
    await authContext.close();
  }
  assert.deepEqual(errors, []);
  console.log(`Browser checks passed: ${checks}; all writes mocked; desktop/mobile selection, drafts, failed sends, new replies, reply pagination and HTML sanitization verified.`);
} finally { await browser.close(); }
