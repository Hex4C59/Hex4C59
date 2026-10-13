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

  document.querySelectorAll('[data-series-sidebar]').forEach((sidebar) => {
    const menu = sidebar.querySelector('.series-sidebar-menu');
    const nav = sidebar.querySelector('.series-sidebar-nav');
    const desktop = window.matchMedia('(min-width: 720px)');
    const storageKey = `series-nav:${sidebar.dataset.seriesSidebar}`;
    const revealCurrent = () => {
      if (!menu.open) return;
      const current = nav.querySelector('[aria-current="page"]');
      if (!current) return;
      const bounds = nav.getBoundingClientRect();
      const active = current.getBoundingClientRect();
      if (active.top < bounds.top || active.bottom > bounds.bottom) {
        nav.scrollTop += active.top - bounds.top - nav.clientHeight / 2 + active.height / 2;
      }
    };
    const syncMenu = () => {
      menu.open = desktop.matches;
      requestAnimationFrame(revealCurrent);
    };
    syncMenu();
    try { nav.scrollTop = Number(sessionStorage.getItem(storageKey)) || 0; } catch (_) {}
    menu.addEventListener('toggle', revealCurrent);
    desktop.addEventListener('change', syncMenu);
    nav.addEventListener('scroll', () => {
      try { sessionStorage.setItem(storageKey, String(nav.scrollTop)); } catch (_) {}
    }, { passive: true });
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
    const expand = collection.querySelector('[data-expand-series]');
    const rank = { beginner: 1, easy: 1, intermediate: 2, medium: 2, advanced: 3, hard: 3, unknown: 99 };
    const apply = () => {
      const query = search.value.trim().toLocaleLowerCase();
      const sorted = [...entries].sort((a, b) => {
        const left = a.node.dataset;
        const right = b.node.dataset;
        switch (sorter.value) {
          case 'title': return left.title.localeCompare(right.title, 'zh-CN');
          case 'difficulty': return (rank[left.difficulty] || 99) - (rank[right.difficulty] || 99) || Number(right.lastmod) - Number(left.lastmod);
          case 'newest': return Number(right.date) - Number(left.date);
          default: return Number(right.lastmod) - Number(left.lastmod) || Number(right.date) - Number(left.date);
        }
      });
      let count = 0;
      const fragment = document.createDocumentFragment();
      sorted.forEach(({ node, filters: values }) => {
        const matchesMode = node.dataset.mode === 'standalone' || node.dataset.mode === (expand?.checked ? 'member' : 'hub');
        const matches = filters.every((filter) => !filter.value || (values[filter.dataset.filter] || []).includes(filter.value));
        const matchesTitle = !query || node.dataset.title.includes(query);
        node.hidden = !(matchesMode && matches && matchesTitle);
        if (!node.hidden) count++;
        fragment.appendChild(node);
      });
      list.appendChild(fragment);
      const total = entries.filter(({ node }) => node.dataset.mode === 'standalone' || node.dataset.mode === (expand?.checked ? 'member' : 'hub')).length;
      collection.querySelector('[data-count]').textContent = count === total ? `共 ${count} 个阅读入口` : `显示 ${count} / ${total} 个阅读入口`;
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
    expand?.addEventListener('change', apply);
    search.addEventListener('input', apply);
    collection.querySelector('[data-reset]').addEventListener('click', () => {
      filters.forEach((filter) => { filter.value = ''; });
      search.value = '';
      sorter.value = 'recent';
      apply();
    });
    const params = new URLSearchParams(window.location.search);
    filters.forEach((filter) => { const value = params.get(filter.dataset.filter); if (value && Array.from(filter.options).some((option) => option.value === value)) filter.value = value; });
    if (params.has('q')) search.value = params.get('q');
    if (expand && params.get('expanded') === '1') expand.checked = true;
    apply();
  });

  const termSearch = document.querySelector('[data-term-search]');
  if (termSearch) {
    const terms = Array.from(document.querySelectorAll('[data-term]'));
    termSearch.addEventListener('input', () => {
      const query = termSearch.value.trim().toLocaleLowerCase();
      terms.forEach((term) => { term.hidden = !term.dataset.term.includes(query); });
      document.querySelector('[data-term-empty]').hidden = terms.some((term) => !term.hidden);
    });
  }
})();
