(() => {
  'use strict';

  const toggle = document.getElementById('theme-toggle');
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  const updateTheme = (theme) => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    document.body.classList.toggle('dark', theme === 'dark');
    document.body.classList.toggle('light', theme === 'light');
    if (toggle) {
      toggle.textContent = theme === 'dark' ? '浅色' : '深色';
      toggle.setAttribute('aria-label', theme === 'dark' ? '切换到浅色主题' : '切换到深色主题');
    }
  };
  updateTheme(document.documentElement.dataset.theme);
  toggle?.addEventListener('click', () => {
    const theme = document.body.classList.contains('dark') ? 'light' : 'dark';
    try { localStorage.setItem('pref-theme', theme); } catch (_) {}
    updateTheme(theme);
  });
  media.addEventListener('change', (event) => {
    let preferred;
    try { preferred = localStorage.getItem('pref-theme'); } catch (_) {}
    if (!preferred || preferred === 'auto') updateTheme(event.matches ? 'dark' : 'light');
  });

  document.querySelectorAll('[data-collection]').forEach((collection) => {
    const list = collection.querySelector('[data-post-list]');
    const entries = Array.from(list.querySelectorAll('.collection-entry')).map((node) => ({
      node, filters: JSON.parse(node.dataset.filters),
    }));
    const filters = Array.from(collection.querySelectorAll('[data-filter]'));
    const sorter = collection.querySelector('[data-sort]');
    const search = collection.querySelector('[data-title-search]');
    const shortcuts = Array.from(collection.querySelectorAll('[data-filter-shortcut]'));
    const rank = { beginner: 1, easy: 1, intermediate: 2, medium: 2, advanced: 3, hard: 3, unknown: 99 };
    const apply = () => {
      const query = search.value.trim().toLocaleLowerCase();
      const sorted = [...entries].sort((a, b) => {
        const left = a.node.dataset;
        const right = b.node.dataset;
        switch (sorter.value) {
          case 'number': return Number(left.number) - Number(right.number);
          case 'title': return left.title.localeCompare(right.title, 'zh-CN');
          case 'difficulty': return (rank[left.difficulty] || 99) - (rank[right.difficulty] || 99) || Number(right.lastmod) - Number(left.lastmod);
          case 'newest': return Number(right.date) - Number(left.date);
          default: return Number(right.lastmod) - Number(left.lastmod) || Number(right.date) - Number(left.date);
        }
      });
      let count = 0;
      const fragment = document.createDocumentFragment();
      sorted.forEach(({ node, filters: values }) => {
        const matches = filters.every((filter) => !filter.value || (values[filter.dataset.filter] || []).includes(filter.value));
        const numericQuery = /^\d+$/.test(query) ? Number(query) : null;
        const matchesNumber = numericQuery !== null && Number(node.dataset.number) > 0 && Number(node.dataset.number) === numericQuery;
        const matchesTitle = !query || node.dataset.title.includes(query) || matchesNumber;
        node.hidden = !(matches && matchesTitle);
        if (!node.hidden) count++;
        fragment.appendChild(node);
      });
      list.appendChild(fragment);
      collection.querySelector('[data-count]').textContent = count === entries.length ? `共 ${count} 篇文章` : `显示 ${count} / ${entries.length} 篇`;
      shortcuts.forEach((button) => {
        const filter = filters.find((item) => item.dataset.filter === button.dataset.filterShortcut);
        const active = filter?.value === button.dataset.value;
        button.classList.toggle('is-active', active);
        button.setAttribute('aria-pressed', String(active));
      });
      collection.querySelector('[data-empty]').hidden = count > 0;
    };
    shortcuts.forEach((button) => button.addEventListener('click', () => {
      const filter = filters.find((item) => item.dataset.filter === button.dataset.filterShortcut);
      if (filter) { filter.value = button.dataset.value; apply(); }
    }));
    filters.forEach((filter) => filter.addEventListener('change', apply));
    sorter.addEventListener('change', apply);
    search.addEventListener('input', apply);
    collection.querySelector('[data-reset]').addEventListener('click', () => {
      filters.forEach((filter) => { filter.value = ''; });
      search.value = '';
      sorter.value = 'recent';
      apply();
    });
    apply();
  });

  const searchSection = document.getElementById('site-search');
  if (!searchSection) return;
  const input = document.getElementById('search-input');
  const status = document.getElementById('search-status');
  const results = document.getElementById('search-results');
  let enginePromise;
  let searchRevision = 0;
  const getEngine = () => {
    if (!enginePromise) {
      enginePromise = fetch(searchSection.dataset.index)
        .then((response) => {
          if (!response.ok) throw new Error('Search index request failed');
          return response.json();
        })
        .then((index) => new Fuse(index, JSON.parse(searchSection.dataset.options)))
        .catch((error) => { enginePromise = undefined; throw error; });
    }
    return enginePromise;
  };
  const search = async () => {
    const revision = ++searchRevision;
    const query = input.value.trim();
    results.replaceChildren();
    if (!query) {
      status.textContent = '输入关键词开始搜索。';
      return;
    }
    status.textContent = '正在搜索…';
    try {
      const engine = await getEngine();
      if (revision !== searchRevision) return;
      const hits = engine.search(query);
      status.textContent = hits.length ? `找到 ${hits.length} 篇相关文章。` : '没有找到相关文章，试试其他关键词。';
      const fragment = document.createDocumentFragment();
      hits.slice(0, 50).forEach(({ item }) => {
        const article = document.createElement('article');
        article.className = 'post-line';
        const date = document.createElement('time');
        date.className = 'line-date';
        date.dateTime = item.date;
        date.textContent = item.date;
        const body = document.createElement('div');
        body.className = 'line-body';
        const title = document.createElement('h2');
        title.className = 'line-title';
        const link = document.createElement('a');
        link.href = item.permalink;
        link.textContent = item.title;
        title.appendChild(link);
        const summary = document.createElement('p');
        summary.className = 'line-summary';
        summary.textContent = item.summary.length > 110 ? `${item.summary.slice(0, 110)}…` : item.summary;
        body.append(title, summary);
        article.append(date, body);
        fragment.appendChild(article);
      });
      results.replaceChildren(fragment);
      if (hits.length > 50) status.textContent += ' 当前显示前 50 篇，请增加关键词缩小范围。';
    } catch (_) {
      if (revision === searchRevision) status.textContent = '搜索暂时无法加载，请重试，或通过归档浏览文章。';
    }
  };
  let debounce;
  input.addEventListener('input', () => {
    ++searchRevision;
    clearTimeout(debounce);
    debounce = setTimeout(search, 150);
  });
})();
