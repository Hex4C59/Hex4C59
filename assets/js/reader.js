(() => {
  'use strict';

  const content = document.querySelector('[data-reader-content]');
  const outline = document.querySelector('[data-reader-outline]');
  const progress = document.querySelector('[data-reading-progress]');
  const tools = document.querySelector('[data-reader-tools]');
  if (!content) return;
  const desktop = window.matchMedia('(min-width: 720px)');
  const preferenceKey = `reader-outline:${location.pathname}`;
  let preferences = {};
  try { preferences = JSON.parse(sessionStorage.getItem(preferenceKey)) || {}; } catch (_) {}

  const groups = [];
  outline?.querySelectorAll('nav li').forEach((item) => {
    const link = Array.from(item.children).find((child) => child.matches('a'));
    const children = Array.from(item.children).find((child) => child.matches('ul'));
    if (!link || !children) return;
    const key = decodeURIComponent(link.hash.slice(1));
    const row = document.createElement('div');
    row.className = 'reader-outline-row';
    link.replaceWith(row);
    row.append(link);
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'reader-outline-toggle';
    const panel = document.createElement('div');
    panel.className = 'reader-outline-children';
    panel.id = `reader-outline-group-${groups.length}`;
    const clip = document.createElement('div');
    clip.className = 'reader-outline-clip';
    children.replaceWith(panel);
    panel.append(clip);
    clip.append(children);
    button.setAttribute('aria-controls', panel.id);
    row.append(button);
    item.dataset.outlineGroup = key;
    const group = { item, link, panel, button, key, manual: preferences[key] };
    groups.push(group);
    button.addEventListener('click', () => {
      group.manual = button.getAttribute('aria-expanded') !== 'true';
      preferences[key] = group.manual;
      try { sessionStorage.setItem(preferenceKey, JSON.stringify(preferences)); } catch (_) {}
      renderGroups();
    });
  });

  let activeGroup;
  const renderGroups = () => {
    groups.forEach((group) => {
      const expanded = group.manual === true || (group.manual !== false && group === activeGroup);
      if (!expanded && group.panel.contains(document.activeElement)) group.button.focus({ preventScroll: true });
      group.panel.dataset.expanded = String(expanded);
      group.panel.inert = !expanded;
      group.panel.setAttribute('aria-hidden', String(!expanded));
      group.button.textContent = expanded ? '−' : '+';
      group.button.setAttribute('aria-expanded', String(expanded));
      group.button.setAttribute('aria-label', `${expanded ? '收起' : '展开'}“${group.link.textContent.trim()}”的小节`);
      group.item.dataset.currentGroup = String(group === activeGroup);
    });
  };
  renderGroups();

  const toolOrigin = tools ? document.createComment('reader tools') : null;
  if (tools) tools.before(toolOrigin);
  const syncLayout = () => {
    if (outline) outline.open = desktop.matches;
    if (tools) {
      if (desktop.matches) toolOrigin.after(tools);
      else document.querySelector('.single-intro-container')?.append(tools);
    }
  };
  syncLayout();
  desktop.addEventListener('change', syncLayout);

  outline?.addEventListener('click', (event) => {
    const link = event.target.closest('nav a');
    if (!link || desktop.matches || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const heading = document.getElementById(decodeURIComponent(link.hash.slice(1)));
    outline.open = false;
    requestAnimationFrame(() => {
      if (!heading) return;
      heading.tabIndex = -1;
      heading.focus({ preventScroll: true });
    });
  });

  const sections = Array.from(outline?.querySelectorAll('nav a') || []).map((link) => ({
    link, heading: document.getElementById(decodeURIComponent(link.hash.slice(1))),
  })).filter(({ heading }) => heading && content.contains(heading));
  const meter = progress?.querySelector('[role="progressbar"]');
  const glyphs = progress?.querySelector('[data-progress-glyphs]');
  const percentage = progress?.querySelector('[data-progress-percent]');
  let frame;
  let lastPercent = -1;
  let currentLink;
  const revealCurrentOutline = () => {
    if (!currentLink || !desktop.matches || !outline.open || currentLink.closest('[inert]')) return;
    const tree = outline.getBoundingClientRect();
    const item = currentLink.getBoundingClientRect();
    const top = tree.top + outline.querySelector('summary').offsetHeight;
    if (item.top < top) outline.scrollTop += item.top - top;
    else if (item.bottom > tree.bottom) outline.scrollTop += item.bottom - tree.bottom;
  };
  outline?.addEventListener('transitionend', (event) => {
    if (event.propertyName === 'grid-template-rows') revealCurrentOutline();
  });
  const updateReader = () => {
    frame = undefined;
    const bounds = content.getBoundingClientRect();
    const start = bounds.top + window.scrollY - 72;
    const end = bounds.bottom + window.scrollY - innerHeight;
    const ratio = end > start ? (window.scrollY - start) / (end - start) : bounds.bottom <= innerHeight ? 1 : 0;
    const percent = Math.round(Math.max(0, Math.min(1, ratio)) * 100);
    if (progress && percent !== lastPercent) {
      const filled = Math.round(percent / 100 * 18);
      glyphs.textContent = '▓'.repeat(filled) + '░'.repeat(18 - filled);
      percentage.textContent = `${percent}%`;
      meter.setAttribute('aria-valuenow', String(percent));
      lastPercent = percent;
    }
    let active;
    sections.forEach(({ link, heading }) => {
      if (heading.getBoundingClientRect().top <= 96) active = link;
    });
    if (percent === 100 && sections.length) active = sections[sections.length - 1].link;
    if (active !== currentLink) {
      currentLink?.removeAttribute('aria-current');
      active?.setAttribute('aria-current', 'location');
      currentLink = active;
      activeGroup = groups.find((group) => group.item.contains(active));
      renderGroups();
      revealCurrentOutline();
    }
  };
  const scheduleReader = () => { if (frame === undefined) frame = requestAnimationFrame(updateReader); };
  if (progress) progress.hidden = false;
  document.addEventListener('scroll', scheduleReader, { passive: true });
  window.addEventListener('resize', scheduleReader);
  if ('ResizeObserver' in window) new ResizeObserver(scheduleReader).observe(content);
  document.fonts?.ready.then(scheduleReader);
  scheduleReader();

  if (!tools) return;
  const buttons = Array.from(tools.querySelectorAll('[data-reader-copy]'));
  const status = tools.querySelector('[data-copy-status]');
  const fallback = tools.querySelector('[data-copy-fallback]');
  const textarea = tools.querySelector('[data-copy-text]');
  let markdown;
  let resetTimer;
  const loadMarkdown = () => {
    if (!markdown) {
      markdown = fetch(tools.dataset.markdownUrl).then((response) => {
        if (!response.ok) throw new Error('Markdown unavailable');
        return response.text();
      }).catch((error) => { markdown = undefined; throw error; });
    }
    return markdown;
  };
  buttons.forEach((button) => {
    button.hidden = false;
    button.addEventListener('click', async () => {
      clearTimeout(resetTimer);
      fallback.hidden = true;
      buttons.forEach((item) => { item.disabled = true; });
      const isMarkdown = button.dataset.readerCopy === 'markdown';
      const text = isMarkdown ? loadMarkdown() : Promise.resolve(tools.dataset.copyUrl);
      status.textContent = isMarkdown ? '正在准备 Markdown…' : '';
      try {
        // Promise-backed ClipboardItem keeps Safari's user activation during fetch.
        if (window.ClipboardItem && navigator.clipboard?.write) {
          await navigator.clipboard.write([new ClipboardItem({
            'text/plain': text.then((value) => new Blob([value], { type: 'text/plain' })),
          })]);
        } else {
          const value = await text;
          if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
          await navigator.clipboard.writeText(value);
        }
        status.textContent = isMarkdown ? 'Markdown 已复制' : '链接已复制';
        resetTimer = setTimeout(() => { status.textContent = ''; scheduleReader(); }, 2600);
      } catch (_) {
        try {
          textarea.value = await text;
          fallback.hidden = false;
          status.textContent = '请手动复制下方内容';
          textarea.focus();
          textarea.select();
        } catch (_) {
          status.textContent = '暂时无法读取，请重试或下载 Markdown';
        }
      } finally {
        buttons.forEach((item) => { item.disabled = false; });
        scheduleReader();
      }
    });
  });
  tools.querySelector('[data-copy-close]').addEventListener('click', () => {
    fallback.hidden = true;
    textarea.value = '';
    status.textContent = '';
    buttons[0].focus();
    scheduleReader();
  });
})();
