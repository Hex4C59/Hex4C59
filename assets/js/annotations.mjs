import { ANCHOR_PREFIX, MAX_QUOTE, makeAnchor, resolveAnchor, decodeAnchor, validAnchor, textKey } from './annotations-model.mjs';

const root = document.querySelector('[data-annotations]');
if (root) initialize(root);

function initialize(root) {
  const content = document.querySelector('[data-reader-content]');
  if (!content) return;
  const pageURL = new URL(root.dataset.pageUrl);
  const siteURL = new URL(root.dataset.siteUrl || pageURL.origin);
  const owner = root.dataset.owner.toLowerCase();
  let api;
  try {
    api = new URL(root.dataset.api.replace(/\/$/, '') + '/', location.href);
    if (api.protocol !== 'https:' && !['localhost', '127.0.0.1'].includes(api.hostname)) throw Error();
  } catch { root.querySelector('[data-status]').textContent = '划线讨论暂时不可用，请前往 GitHub 参与讨论。'; return; }
  const panel = root.querySelector('[data-panel]');
  const panelBody = root.querySelector('[data-panel-body]');
  const panelScroll = root.querySelector('[data-panel-scroll]');
  const panelTitle = root.querySelector('#annotation-panel-title');
  const status = root.querySelector('[data-status]');
  const toolbar = root.querySelector('[data-selection-toolbar]');
  const mobile = matchMedia('(max-width: 1059px)');
  let tabStore, userStore;
  try { tabStore = window.sessionStorage; userStore = window.localStorage; } catch {}
  const draftKey = 'annotation-drafts:' + root.dataset.path;
  const uiKey = 'annotation-ui:' + root.dataset.path;
  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const store = (kind, key, value) => { try { kind.setItem(key, JSON.stringify(value)); } catch {} };
  const restore = (kind, key, fallback) => { try { return JSON.parse(kind.getItem(key)) ?? fallback; } catch { return fallback; } };
  const state = {
    threads: [], discussion: null, cursor: '', more: false, total: 0, loading: false, writing: false,
    view: 'list', block: null, threadId: null, anchor: null, sort: 'featured', limit: 5, replyLimit: 8,
    viewer: null, pending: null, error: '', detached: false, open: false, modal: false, opener: null,
    drafts: restore(tabStore, draftKey, {}), session: '', markers: restore(userStore, 'annotation-markers', true),
  };
  if (!state.drafts || typeof state.drafts !== 'object' || Array.isArray(state.drafts)) state.drafts = {};
  const blocks = Array.from(content.querySelectorAll('p, pre, ul, ol, table')).filter(el =>
    !el.parentElement.closest('p, pre, ul, ol, table') && !el.closest('figure, .katex, .interactive-diagram, [data-no-annotation]') && el.textContent.trim()
  ).map(el => ({ el, text: el.textContent }));
  const markerLayer = document.createElement('div');
  markerLayer.className = 'annotation-markers'; markerLayer.setAttribute('aria-label', '段落讨论');
  const highlightLayer = document.createElement('div'); highlightLayer.className = 'annotation-highlight-layer'; highlightLayer.setAttribute('aria-hidden', 'true');
  content.classList.add('annotation-content');
  content.append(markerLayer, highlightLayer);
  let layoutFrame, activeRange, selectionAnchor, returnPosition, switchingMode = false;
  const thread = () => state.threads.find(item => item.id === state.threadId);
  const announce = text => { status.textContent = text; };
  const isOwner = () => state.viewer?.login?.toLowerCase() === owner;
  const draftId = () => state.view === 'thread' ? 'reply:' + state.threadId : state.anchor ? 'new:' + textKey(JSON.stringify([state.anchor.quote, state.anchor.prefix, state.anchor.suffix, state.anchor.blockKey])) : 'general';
  const saveDraft = text => {
    if (text) state.drafts[draftId()] = text; else delete state.drafts[draftId()];
    // A bounded per-tab cache preserves text through login and topic switching.
    const keys = Object.keys(state.drafts);
    keys.slice(0, Math.max(0, keys.length - 30)).forEach(key => delete state.drafts[key]);
    store(tabStore, draftKey, state.drafts);
  };
  const saveUI = () => store(tabStore, uiKey, { view: state.view, block: state.block, threadId: state.threadId, anchor: state.anchor, scrollY: window.scrollY });

  async function request(route, { body, auth = false, query = {} } = {}) {
    const url = new URL(route, api);
    Object.entries(query).forEach(([key, value]) => { if (value !== '' && value != null) url.searchParams.set(key, value); });
    const headers = { Accept: 'application/json' };
    if (auth) {
      if (!state.session) throw Error('请先使用 GitHub 登录');
      headers.Authorization = 'Giscus ' + state.session;
    }
    if (body) headers['Content-Type'] = 'application/json';
    let response;
    try { response = await fetch(url, { method: body ? 'POST' : 'GET', headers, body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(20000), credentials: 'omit', referrerPolicy: 'no-referrer' }); }
    catch { throw Error('评论服务连接失败。你的草稿已保留，可以稍后重试。'); }
    let result;
    try { result = await response.json(); } catch { throw Error('评论服务暂时不可用，请稍后重试。'); }
    if (!response.ok) {
      if (response.status === 401) { state.session = ''; state.viewer = null; try { userStore?.removeItem('giscus-session'); } catch {} renderAccount(); }
      throw Error(result.error || '操作未完成，请稍后重试。');
    }
    return result;
  }

  function safeURL(value) {
    try { const url = new URL(value, pageURL); return ['https:', 'http:'].includes(url.protocol) ? url : null; } catch { return null; }
  }
  function parseHTML(html) { const template = document.createElement('template'); template.innerHTML = typeof html === 'string' ? html : ''; return template.content; }
  function annotationFrom(fragment) {
    const link = Array.from(fragment.querySelectorAll('a[href]')).find(a => {
      const url = safeURL(a.getAttribute('href'));
      const paragraph = a.closest('p');
      const quote = paragraph?.previousElementSibling;
      return a.textContent.trim() === '查看划线原文' && quote?.tagName === 'BLOCKQUOTE' && quote === fragment.firstElementChild && url?.origin === pageURL.origin && url.pathname === pageURL.pathname && url.hash.startsWith(ANCHOR_PREFIX);
    });
    if (!link) return null;
    const url = safeURL(link.getAttribute('href'));
    const anchor = decodeAnchor(url.hash.slice(ANCHOR_PREFIX.length));
    if (!anchor) return null;
    const paragraph = link.closest('p');
    const quote = paragraph?.previousElementSibling;
    if (quote?.tagName === 'BLOCKQUOTE') quote.remove();
    if (paragraph?.textContent.trim() === '查看划线原文') paragraph.remove(); else link.remove();
    return anchor;
  }
  function sanitized(fragment) {
    const allowed = new Set(['P', 'BR', 'STRONG', 'EM', 'B', 'I', 'DEL', 'S', 'CODE', 'PRE', 'BLOCKQUOTE', 'UL', 'OL', 'LI', 'A', 'HR']);
    const clean = document.createDocumentFragment();
    function append(node, parent) {
      if (node.nodeType === Node.TEXT_NODE) { parent.append(document.createTextNode(node.textContent)); return; }
      if (node.nodeType !== Node.ELEMENT_NODE) return;
      if (['SCRIPT', 'STYLE', 'IFRAME', 'OBJECT', 'FORM', 'INPUT', 'TEXTAREA', 'BUTTON', 'SVG', 'MATH'].includes(node.tagName)) return;
      if (node.tagName === 'IMG') { parent.append(document.createTextNode(node.getAttribute('alt') || '')); return; }
      if (!allowed.has(node.tagName)) { node.childNodes.forEach(child => append(child, parent)); return; }
      const el = document.createElement(node.tagName.toLowerCase());
      if (node.tagName === 'A') {
        const url = safeURL(node.getAttribute('href'));
        if (url) { el.href = url.href; el.rel = 'noopener noreferrer nofollow'; el.target = '_blank'; }
      }
      node.childNodes.forEach(child => append(child, el)); parent.append(el);
    }
    fragment.childNodes.forEach(node => append(node, clean));
    const container = document.createElement('div'); container.append(clean); return container.innerHTML;
  }
  function managementAction(comment) {
    if (comment.author?.login?.toLowerCase() !== owner) return '';
    const fragment = parseHTML(comment.bodyHTML);
    for (const link of fragment.querySelectorAll('a[href]')) {
      const url = safeURL(link.getAttribute('href'));
      if (url?.origin === pageURL.origin && url.pathname === siteURL.pathname && ['#annotation-feature', '#annotation-unfeature'].includes(url.hash)) return url.hash.slice('#annotation-'.length);
    }
    return '';
  }
  function adapt(comment) {
    const fragment = parseHTML(comment.bodyHTML);
    const anchor = annotationFrom(fragment);
    const replies = (comment.replies || []).filter(reply => !reply.deletedAt);
    let featured = false;
    replies.forEach(reply => { const action = managementAction(reply); if (action) featured = action === 'feature'; });
    const visibleReplies = replies.filter(reply => !managementAction(reply));
    return { ...comment, sourceReplyCount: comment.replyCount || 0, html: sanitized(fragment), summary: fragment.textContent.trim().replace(/\s+/g, ' ').slice(0, 150), anchor, featured,
      replies: visibleReplies, replyCount: Math.max(visibleReplies.length, (comment.replyCount || 0) - (replies.length - visibleReplies.length)),
      location: anchor ? resolveAnchor(anchor, blocks) : null };
  }
  function merge(comments, replace = false) {
    const byId = new Map((replace ? [] : state.threads).map(item => [item.id, item]));
    comments.forEach(comment => byId.set(comment.id, adapt(comment)));
    state.threads = Array.from(byId.values());
  }
  function applyPage(discussion, older = false) {
    state.discussion = discussion;
    state.total = discussion?.totalCommentCount || 0;
    if (!discussion) { state.threads = []; state.cursor = ''; state.more = false; }
    if (discussion) {
      const incoming = discussion.comments || [];
      if (!older && !discussion.pageInfo?.hasPreviousPage) merge(incoming, true);
      else {
        if (!older && incoming.length) {
          const first = Math.min(...incoming.map(item => new Date(item.createdAt).getTime()));
          const ids = new Set(incoming.map(item => item.id));
          state.threads = state.threads.filter(item => new Date(item.createdAt).getTime() < first || ids.has(item.id));
        }
        merge(incoming);
      }
      if (!older || discussion.pageInfo?.startCursor) {
        state.cursor = discussion.pageInfo?.startCursor || '';
        state.more = !!discussion.pageInfo?.hasPreviousPage;
      }
    }
    state.error = '';
    root.querySelector('[data-total]').textContent = state.total ? `（${state.total}）` : '';
    scheduleLayout();
  }
  async function load({ older = false } = {}) {
    if (state.loading) return;
    state.loading = true;
    const button = panelBody.querySelector('[data-load-older]'); if (button) button.disabled = true;
    try {
      const { discussion } = await request('discussion', { query: { path: root.dataset.path, before: older ? state.cursor : '' } });
      applyPage(discussion, older);
      announce(state.more ? `已加载最近 ${state.threads.length} 条讨论，可以继续查看更早的话题。` : state.total ? '讨论已就绪。' : '还没有讨论，选中一段文字就可以开始。');
    } catch (error) { state.error = error.message; announce(error.message); }
    finally { state.loading = false; if (state.open) render(); }
  }
  function identity(comment) {
    const login = comment.author?.login || '已注销用户';
    const ownerBadge = login.toLowerCase() === owner ? '<span class="annotation-owner">作者</span>' : '';
    const date = new Date(comment.createdAt);
    const time = Number.isNaN(date.valueOf()) ? '' : date.toLocaleDateString('zh-CN');
    return `<div class="annotation-identity"><span>${escape(login)}</span>${ownerBadge}<time datetime="${escape(comment.createdAt)}">${escape(time)}</time></div>`;
  }
  function quote(anchor) { return anchor ? `<blockquote class="annotation-quote">${escape(anchor.quote)}</blockquote>` : ''; }
  function authorTools(item) {
    if (!isOwner()) return '';
    return `<div class="annotation-admin"><button type="button" data-moderate="${item.featured ? 'unfeature' : 'feature'}" data-id="${escape(item.id)}">${item.featured ? '取消精选' : '标为精选'}</button><button type="button" data-moderate="${item.isMinimized ? 'restore' : 'minimize'}" data-id="${escape(item.id)}">${item.isMinimized ? '恢复讨论' : '折叠讨论'}</button></div>`;
  }
  function topicCard(item) {
    const collapsed = item.isMinimized;
    return `<li class="annotation-topic"><button type="button" data-open-thread="${escape(item.id)}">${item.anchor ? `<span class="annotation-topic-quote">“${escape(item.anchor.quote.slice(0, 90))}${item.anchor.quote.length > 90 ? '…' : ''}”</span>` : '<span class="annotation-topic-quote">文章讨论</span>'}<span class="annotation-topic-summary">${collapsed ? '这条讨论已折叠' : escape(item.summary || '查看这条讨论')}</span><span class="annotation-topic-meta">${escape(item.author?.login || '已注销用户')} · ${item.replyCount} 条回复${item.featured ? '<span class="annotation-owner">精选</span>' : ''}</span></button></li>`;
  }
  function composer() {
    if (state.discussion?.locked || (state.view === 'thread' && thread()?.isMinimized)) return '<p class="annotation-notice">这条讨论暂不接受新回复。</p>';
    const value = state.drafts[draftId()] || '';
    return `<form class="annotation-composer" data-compose><label for="annotation-message">${state.view === 'thread' ? '继续这条讨论' : '写下你的想法'}</label><textarea id="annotation-message" name="message" rows="4" maxlength="4000" required ${state.writing ? 'disabled' : ''} placeholder="支持 Markdown；回复某人时可以使用 @用户名">${escape(value)}</textarea><div class="annotation-composer-actions"><span class="annotation-draft-note">草稿保留在当前标签页</span><button type="submit" class="annotation-primary" ${state.writing || !state.viewer ? 'disabled' : ''}>${state.writing ? '发送中…' : state.view === 'thread' ? '发送回复' : '发布讨论'}</button></div>${state.viewer ? '' : '<button class="annotation-login" type="button" data-login>使用 GitHub 登录后发表</button>'}</form>`;
  }
  function visibleThreads() {
    let items = state.threads.filter(item => state.block === null || item.location?.index === state.block);
    if (state.sort === 'featured') items.sort((a, b) => Number(b.featured) - Number(a.featured) || Number(a.isMinimized) - Number(b.isMinimized) || (b.upvoteCount || 0) - (a.upvoteCount || 0) || new Date(b.createdAt) - new Date(a.createdAt));
    else items.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    return items;
  }
  function renderAccount() {
    const account = root.querySelector('[data-account]');
    account.innerHTML = state.viewer ? `<span>${escape(state.viewer.login)}</span><button type="button" data-logout>退出登录</button>` : '<button type="button" data-login>使用 GitHub 登录</button>';
  }
  function renderPending() {
    const target = root.querySelector('[data-pending]');
    target.innerHTML = state.pending ? '<button type="button" class="annotation-new" data-apply-pending>讨论有更新，点击查看</button>' : '';
  }
  function render() {
    renderAccount(); renderPending();
    root.querySelector('[data-back]').hidden = state.view === 'list';
    root.querySelector('[data-toggle-markers]').textContent = state.markers ? '隐藏段落标记' : '显示段落标记';
    root.querySelector('[data-toggle-markers]').setAttribute('aria-pressed', String(state.markers));
    let html = '';
    if (state.error) html += `<p class="annotation-error" role="alert">${escape(state.error)}</p><button type="button" data-retry>重试读取讨论</button>`;
    if (state.view === 'list') {
      panelTitle.textContent = state.block === null ? '文章讨论' : '本段讨论';
      const items = visibleThreads();
      html += `<div class="annotation-sort" role="group" aria-label="话题排序"><button type="button" data-sort="featured" aria-pressed="${state.sort === 'featured'}">精选优先</button><button type="button" data-sort="latest" aria-pressed="${state.sort === 'latest'}">最新</button></div>`;
      html += items.length ? `<ul class="annotation-topics">${items.slice(0, state.limit).map(topicCard).join('')}</ul>` : `<p class="annotation-notice">${state.loading ? '正在读取讨论…' : '这里还没有已加载的讨论。'}</p>`;
      if (items.length > state.limit) html += `<button type="button" data-more-topics>再看 ${Math.min(5, items.length - state.limit)} 条讨论</button>`;
      if (state.more) html += `<button type="button" data-load-older ${state.loading ? 'disabled' : ''}>${state.loading ? '正在加载…' : '加载更早的讨论'}</button><p class="annotation-pagination-note">段落数字为已加载的话题数，带 + 表示还有未加载的讨论。</p>`;
      html += `<button type="button" class="annotation-new-topic" data-new-topic>${state.block === null ? '评论这篇文章' : '针对本段发起新讨论'}</button>`;
    } else if (state.view === 'suggest') {
      panelTitle.textContent = '针对这段文字讨论';
      const related = state.threads.filter(item => item.location?.index === state.block && !item.isMinimized);
      html += quote(state.anchor);
      if (related.length) html += '<p class="annotation-notice">附近已有这些话题，可以加入，也可以提出新问题。</p><ul class="annotation-topics">' + related.slice(0, 3).map(topicCard).join('') + '</ul>';
      html += `<button type="button" class="annotation-primary" data-start-compose>${related.length ? '我的问题不同，另开讨论' : '发起讨论'}</button>`;
    } else if (state.view === 'compose') {
      panelTitle.textContent = state.anchor ? '发起划线讨论' : '评论这篇文章';
      html += quote(state.anchor) + composer();
    } else {
      const item = thread();
      if (!item) { panelTitle.textContent = '讨论暂未加载'; html += '<p class="annotation-notice">可以返回列表加载更早的讨论。</p>'; }
      else {
        panelTitle.textContent = '讨论详情';
        html += quote(item.anchor);
        if (item.anchor && !item.location) html += '<p class="annotation-notice">原文已有更新，这段引用暂时无法定位。</p>';
        html += `<article class="annotation-comment">${identity(item)}<div class="annotation-comment-body">${item.isMinimized ? '<p>这条讨论已由作者折叠。</p>' : item.html}</div>${authorTools(item)}</article>`;
        const replies = item.replies.filter(reply => !reply.isMinimized);
        const omitted = item.replyCount > item.replies.length;
        if (omitted) html += `<p class="annotation-notice">更早的回复可以<a href="${escape(item.url)}" target="_blank" rel="noopener noreferrer">在 GitHub 查看</a>，这里显示最近加载的回复。</p>`;
        if (!item.isMinimized) {
          html += replies.slice(0, state.replyLimit).map(reply => `<article class="annotation-comment annotation-reply">${identity(reply)}<div class="annotation-comment-body">${sanitized(parseHTML(reply.bodyHTML))}</div><button type="button" class="annotation-reply-to" data-reply-to="${escape(reply.author?.login || '')}">回复 ${escape(reply.author?.login || '')}</button></article>`).join('');
          if (replies.length > state.replyLimit) html += `<button type="button" data-more-replies>继续查看回复（还有 ${replies.length - state.replyLimit} 条）</button>`;
        }
        html += composer();
      }
    }
    panelBody.innerHTML = html;
    highlight(); scheduleLayout();
  }

  function nodeRange(block, start, end) {
    const walker = document.createTreeWalker(block.el, NodeFilter.SHOW_TEXT);
    let node, offset = 0, startNode, endNode, startOffset, endOffset;
    while ((node = walker.nextNode())) {
      const next = offset + node.length;
      if (!startNode && start >= offset && start < next) { startNode = node; startOffset = start - offset; }
      if (end > offset && end <= next) { endNode = node; endOffset = end - offset; break; }
      offset = next;
    }
    if (!startNode || !endNode) return null;
    const range = document.createRange(); range.setStart(startNode, startOffset); range.setEnd(endNode, endOffset); return range;
  }
  function highlight() {
    CSS.highlights?.delete('annotation-active'); highlightLayer.replaceChildren(); activeRange = null;
    if (!state.open || state.view === 'list') return;
    const anchor = state.view === 'thread' ? thread()?.anchor : state.anchor;
    const resolved = anchor && resolveAnchor(anchor, blocks);
    if (!resolved) return;
    activeRange = nodeRange(blocks[resolved.index], resolved.start, resolved.end);
    if (activeRange && CSS.highlights && typeof Highlight !== 'undefined') CSS.highlights.set('annotation-active', new Highlight(activeRange));
    else drawFallbackHighlight();
  }
  function drawFallbackHighlight() {
    if (!activeRange || CSS.highlights) return;
    highlightLayer.replaceChildren(); const origin = content.getBoundingClientRect();
    for (const rect of activeRange.getClientRects()) {
      const mark = document.createElement('span');
      Object.assign(mark.style, { left: `${rect.left - origin.left}px`, top: `${rect.top - origin.top}px`, width: `${rect.width}px`, height: `${rect.height}px` }); highlightLayer.append(mark);
    }
  }
  function layout() {
    layoutFrame = null;
    let changed = false;
    for (const block of blocks) { const text = block.el.textContent; if (text !== block.text) { block.text = text; changed = true; } }
    if (changed) { state.threads.forEach(item => { item.location = item.anchor ? resolveAnchor(item.anchor, blocks) : null; }); highlight(); }
    markerLayer.hidden = !state.markers;
    const groups = new Map();
    state.threads.filter(item => !item.isMinimized && item.location).forEach(item => {
      const index = item.location.index; groups.set(index, (groups.get(index) || 0) + 1);
    });
    const existing = new Map(Array.from(markerLayer.children).map(button => [Number(button.dataset.block), button]));
    const origin = content.getBoundingClientRect();
    groups.forEach((count, index) => {
      let button = existing.get(index);
      if (!button) { button = document.createElement('button'); button.type = 'button'; button.className = 'annotation-marker'; button.dataset.block = index; markerLayer.append(button); }
      button.textContent = count + (state.more ? '+' : '');
      button.setAttribute('aria-label', `本段${state.more ? '至少' : '有'} ${count} 条讨论，点击查看`);
      button.setAttribute('aria-expanded', String(state.open && state.block === index));
      button.classList.toggle('is-selecting', !toolbar.hidden && selectionAnchor?.block === index);
      button.style.top = `${blocks[index].el.getBoundingClientRect().top - origin.top}px`;
      existing.delete(index);
    });
    existing.forEach(button => button.remove()); drawFallbackHighlight();
  }
  function scheduleLayout() { if (!layoutFrame) layoutFrame = requestAnimationFrame(layout); }
  function focusTitle() { panelTitle.focus({ preventScroll: true }); }
  function applyMode() {
    const shouldModal = mobile.matches;
    if (panel.open && state.modal === shouldModal) return;
    switchingMode = true;
    if (panel.open) panel.close();
    state.modal = shouldModal;
    panel.setAttribute('aria-modal', String(shouldModal));
    if (shouldModal) panel.showModal(); else panel.show();
    document.body.classList.toggle('annotations-modal', shouldModal);
    switchingMode = false;
  }
  function open({ view = 'list', block = null, anchor = null, id = null, opener = document.activeElement } = {}) {
    hideSelection();
    state.opener = opener; returnPosition = { y: window.scrollY, block, top: block === null ? null : blocks[block]?.el.getBoundingClientRect().top };
    state.open = true; state.view = view; state.block = block; state.anchor = anchor; state.threadId = id;
    state.limit = 5; state.replyLimit = 8; state.error = '';
    document.body.classList.add('annotations-open'); applyMode(); render(); focusTitle(); saveUI();
    if (returnPosition?.block != null && !mobile.matches) {
      requestAnimationFrame(() => { const top = blocks[returnPosition.block]?.el.getBoundingClientRect().top; if (top != null) window.scrollBy({ top: top - returnPosition.top, behavior: 'instant' }); });
    }
  }
  function close() {
    if (!state.open || switchingMode) return;
    state.open = false; hideSelection();
    document.body.classList.remove('annotations-open', 'annotations-modal');
    if (panel.open) panel.close();
    CSS.highlights?.delete('annotation-active'); activeRange = null; highlightLayer.replaceChildren();
    requestAnimationFrame(() => {
      if (returnPosition) window.scrollTo({ top: returnPosition.y, behavior: 'instant' });
      if (state.opener?.isConnected && state.opener.getClientRects().length) state.opener.focus({ preventScroll: true });
      else if (returnPosition?.block != null) { const el = blocks[returnPosition.block]?.el; if (el) { el.tabIndex = -1; el.focus({ preventScroll: true }); } }
      scheduleLayout();
    });
    try { tabStore?.removeItem(uiKey); } catch {}
  }
  function chooseThread(id) {
    const item = state.threads.find(item => item.id === id); if (!item) return;
    state.threadId = id; state.anchor = item.anchor; state.block = item.location?.index ?? null; state.view = 'thread'; state.replyLimit = 8;
    render(); panelScroll.scrollTop = 0; focusTitle(); saveUI();
    if (item.location && !mobile.matches) blocks[item.location.index].el.scrollIntoView({ block: 'center', behavior: 'instant' });
  }
  function hideSelection() {
    toolbar.hidden = true;
    markerLayer.querySelectorAll('.is-selecting').forEach(marker => marker.classList.remove('is-selecting'));
  }
  function showSelection() {
    if (state.open && mobile.matches) return;
    blocks.forEach(block => { block.text = block.el.textContent; });
    const selection = window.getSelection();
    if (!selection?.rangeCount || selection.isCollapsed) { hideSelection(); return; }
    const range = selection.getRangeAt(0);
    const index = blocks.findIndex(block => block.el.contains(range.startContainer) && block.el.contains(range.endContainer));
    if (index < 0 || selection.toString().trim().length < 2) { hideSelection(); return; }
    const prefix = range.cloneRange(); prefix.selectNodeContents(blocks[index].el); prefix.setEnd(range.startContainer, range.startOffset);
    const start = prefix.toString().length;
    const text = selection.toString();
    if (text.length > MAX_QUOTE) { hideSelection(); announce(`一次可以引用最多 ${MAX_QUOTE} 字，请缩小选区。`); return; }
    selectionAnchor = makeAnchor(blocks[index].text, index, start, start + text.length);
    if (selectionAnchor.quote !== text) { hideSelection(); return; }
    const rect = Array.from(range.getClientRects()).find(rect => rect.width && rect.height) || range.getBoundingClientRect();
    const bounds = content.getBoundingClientRect();
    toolbar.hidden = false;
    // The reading column reserves a right gutter, so the action never covers text.
    toolbar.style.left = `${Math.max(8, Math.min(innerWidth - toolbar.offsetWidth - 8, bounds.right - toolbar.offsetWidth))}px`;
    toolbar.style.top = `${Math.max(8, Math.min(innerHeight - toolbar.offsetHeight - 8, rect.top + (rect.height - toolbar.offsetHeight) / 2))}px`;
    markerLayer.querySelectorAll('button').forEach(marker => marker.classList.toggle('is-selecting', Number(marker.dataset.block) === index));
  }

  async function login() {
    if (!tabStore || !userStore) { announce('浏览器未允许保存登录状态，请开启本站存储后重试。'); return; }
    saveUI();
    const url = new URL('https://giscus.app/api/oauth/authorize');
    const redirect = new URL(location.href);
    const nonce = crypto.randomUUID();
    store(tabStore, 'annotation-login-pending', { nonce, expires: Date.now() + 600000 });
    redirect.searchParams.set('annotation_login', nonce);
    url.searchParams.set('redirect_uri', redirect.href);
    location.assign(url);
  }
  async function loadViewer() {
    if (!state.session) return;
    try { const result = await request('viewer', { auth: true }); state.viewer = result.viewer; }
    catch (error) { announce(error.message); }
    renderAccount(); if (state.open) render();
  }
  async function submit(form) {
    if (state.writing || !state.viewer || !form.reportValidity()) return;
    const message = form.elements.message.value.trim(); if (!message) return;
    saveDraft(message); state.writing = true; state.error = '';
    form.elements.message.disabled = true;
    const submitButton = form.querySelector('[type="submit"]'); submitButton.disabled = true; submitButton.textContent = '发送中…';
    try {
      const { comment, discussion } = await request('comment', { auth: true, body: { path: root.dataset.path, message,
        replyToId: state.view === 'thread' ? state.threadId : undefined, anchor: state.view === 'thread' ? undefined : state.anchor } });
      saveDraft(''); state.pending = null;
      if (state.view === 'thread') {
        const item = thread(); item.replies.push(comment); item.replyCount++; item.sourceReplyCount++; state.replyLimit = item.replies.length;
      } else {
        merge([{ ...comment, replies: [], replyCount: 0 }]); state.total++;
        state.threadId = comment.id; state.view = 'thread';
        if (discussion && !state.discussion) state.discussion = { ...discussion, locked: false };
      }
      state.error = ''; root.querySelector('[data-total]').textContent = `（${state.total}）`; announce('已发表，评论保存在 GitHub Discussions。'); if (state.open) saveUI();
    } catch (error) { state.error = error.message; announce(error.message); }
    finally { state.writing = false; render(); }
  }
  async function moderate(button) {
    if (state.writing) return;
    state.writing = true; button.disabled = true;
    try {
      const result = await request('moderate', { auth: true, body: { path: root.dataset.path, commentId: button.dataset.id, action: button.dataset.moderate } });
      const item = state.threads.find(item => item.id === button.dataset.id);
      if (button.dataset.moderate === 'feature' || button.dataset.moderate === 'unfeature') { item.featured = button.dataset.moderate === 'feature'; if (result.comment) item.sourceReplyCount++; }
      else item.isMinimized = button.dataset.moderate === 'minimize';
      announce('讨论状态已更新。');
    } catch (error) { state.error = error.message; announce(error.message); }
    finally { state.writing = false; render(); }
  }
  function handleClick(event) {
    const button = event.target.closest('button'); if (!button) return;
    if (state.writing && !button.hasAttribute('data-close')) return;
    if (button.closest('.annotation-markers')) { open({ block: Number(button.dataset.block), opener: button }); return; }
    if (!root.contains(button)) return;
    if (button.hasAttribute('data-open-all')) return open({ opener: button });
    if (button.hasAttribute('data-write-general')) return open({ view: 'compose', opener: button });
    if (button.hasAttribute('data-close')) return close();
    if (button.hasAttribute('data-login')) return login();
    if (button.hasAttribute('data-logout')) { state.session = ''; state.viewer = null; try { userStore?.removeItem('giscus-session'); } catch {} render(); return; }
    if (button.hasAttribute('data-toggle-markers')) { state.markers = !state.markers; store(userStore, 'annotation-markers', state.markers); render(); return; }
    if (button.hasAttribute('data-comment-selection')) { if (selectionAnchor) { const anchor = selectionAnchor; window.getSelection()?.removeAllRanges(); return open({ view: 'suggest', block: anchor.block, anchor, opener: button }); } }
    if (button.hasAttribute('data-back')) { state.view = 'list'; render(); panelScroll.scrollTop = 0; saveUI(); return; }
    if (button.hasAttribute('data-open-thread')) return chooseThread(button.dataset.openThread);
    if (button.hasAttribute('data-start-compose')) { state.view = 'compose'; render(); panelBody.querySelector('textarea')?.focus({ preventScroll: true }); saveUI(); return; }
    if (button.hasAttribute('data-new-topic')) {
      if (state.block !== null) {
        const block = blocks[state.block];
        if (block.text.length > MAX_QUOTE) { announce('这段内容较长，请在正文中选中要讨论的部分。'); return; }
        state.anchor = makeAnchor(block.text, state.block, 0, block.text.length); state.view = 'suggest';
      } else { state.anchor = null; state.view = 'compose'; }
      render(); saveUI(); return;
    }
    if (button.hasAttribute('data-sort')) { state.sort = button.dataset.sort; state.limit = 5; render(); return; }
    if (button.hasAttribute('data-more-topics')) { state.limit += 5; render(); return; }
    if (button.hasAttribute('data-more-replies')) { state.replyLimit += 10; render(); return; }
    if (button.hasAttribute('data-load-older')) return load({ older: true });
    if (button.hasAttribute('data-retry')) return load();
    if (button.hasAttribute('data-reply-to')) { const textarea = panelBody.querySelector('textarea'); if (textarea) { textarea.value = `@${button.dataset.replyTo} ` + textarea.value; saveDraft(textarea.value); textarea.focus({ preventScroll: true }); } return; }
    if (button.hasAttribute('data-apply-pending')) {
      const pending = state.pending; state.pending = null;
      const cursor = state.cursor, more = state.more;
      applyPage(pending); state.cursor = cursor; state.more = more;
      render(); announce('已显示新到的讨论与回复。'); return;
    }
    if (button.hasAttribute('data-moderate')) return moderate(button);
  }
  document.addEventListener('click', handleClick);
  root.addEventListener('input', event => { if (event.target.matches('#annotation-message')) saveDraft(event.target.value); });
  root.addEventListener('submit', event => { if (event.target.matches('[data-compose]')) { event.preventDefault(); submit(event.target); } });
  toolbar.addEventListener('pointerdown', event => event.preventDefault());
  content.addEventListener('pointerup', () => setTimeout(showSelection, 0));
  document.addEventListener('selectionchange', () => { if (document.activeElement?.closest('.annotation-panel')) return; showSelection(); });
  document.addEventListener('scroll', () => { hideSelection(); }, { passive: true });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && state.open && !state.modal) { event.preventDefault(); close(); } else if (event.key === 'Escape') hideSelection(); });
  panel.addEventListener('cancel', event => { event.preventDefault(); close(); });
  panel.addEventListener('close', () => { if (!switchingMode && !panel.open) close(); });
  panel.addEventListener('click', event => { if (state.modal && event.target === panel) { const bounds = panel.getBoundingClientRect(); if (event.clientY < bounds.top || event.clientX < bounds.left || event.clientX > bounds.right) close(); } });
  mobile.addEventListener('change', () => { if (state.open) { applyMode(); focusTitle(); scheduleLayout(); } });
  window.addEventListener('resize', () => { hideSelection(); scheduleLayout(); });
  if ('ResizeObserver' in window) new ResizeObserver(scheduleLayout).observe(content);
  document.fonts?.ready.then(scheduleLayout);
  setInterval(async () => {
    if (!state.open || state.loading || state.writing || document.visibilityState !== 'visible') return;
    try {
      const { discussion } = await request('discussion', { query: { path: root.dataset.path } });
      if (!discussion || state.writing || !state.open) return;
      const changed = discussion.totalCommentCount !== state.total || (discussion.comments || []).some(item => {
        const current = state.threads.find(old => old.id === item.id);
        return !current || current.sourceReplyCount !== item.replyCount || current.bodyHTML !== item.bodyHTML || current.isMinimized !== item.isMinimized;
      });
      if (changed) { state.pending = discussion; renderPending(); }
    } catch { /* Background errors leave the current discussion and draft intact. */ }
  }, 90000);

  // Capture the login callback before analytics or another navigation can reuse it.
  try {
    const url = new URL(location.href);
    const callback = url.searchParams.get('giscus');
    if (callback) { const pending = restore(tabStore, 'annotation-login-pending', null); if (pending?.nonce === url.searchParams.get('annotation_login') && pending.expires > Date.now()) { state.session = callback; store(userStore, 'giscus-session', callback); } url.searchParams.delete('giscus'); url.searchParams.delete('annotation_login'); tabStore?.removeItem('annotation-login-pending'); history.replaceState(history.state, '', url); }
    else state.session = restore(userStore, 'giscus-session', '');
    if (typeof state.session !== 'string') state.session = '';
  } catch {}
  render();
  Promise.all([load(), loadViewer()]).then(async () => {
    const anchor = location.hash.startsWith(ANCHOR_PREFIX) ? decodeAnchor(location.hash.slice(ANCHOR_PREFIX.length)) : null;
    const saved = restore(tabStore, uiKey, null);
    if (anchor) {
      const found = state.threads.find(item => item.anchor?.id === anchor.id);
      if (found) { open({ block: found.location?.index ?? null }); chooseThread(found.id); }
      else { const resolved = resolveAnchor(anchor, blocks); open({ view: 'suggest', anchor, block: resolved?.index ?? null }); if (state.more) announce('这条引用的讨论可能在更早的话题中，可以继续加载。'); }
    } else if (saved && ['list', 'thread', 'suggest', 'compose'].includes(saved.view)) {
      if (Number.isFinite(saved.scrollY)) window.scrollTo({ top: saved.scrollY, behavior: 'instant' });
      const safeAnchor = saved.anchor && decodeAnchorFromSaved(saved.anchor);
      open({ view: saved.view, block: Number.isInteger(saved.block) && blocks[saved.block] ? saved.block : null, anchor: safeAnchor, id: saved.threadId });
    }
  });
  function decodeAnchorFromSaved(anchor) { return validAnchor(anchor) ? anchor : null; }
}
