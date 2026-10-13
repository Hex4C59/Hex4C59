(() => {
  'use strict';

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
