(() => {
  'use strict';

  const root = document.documentElement;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const toggle = document.getElementById('motion-toggle');
  const activeAnimations = new Map();
  let preference;
  try { preference = localStorage.getItem('pref-motion'); } catch (_) {}

  const motionAllowed = () => !reducedMotion.matches && preference !== 'off';
  const updateMotion = () => {
    const enabled = motionAllowed();
    root.dataset.motion = enabled ? 'on' : 'off';
    if (toggle) {
      toggle.hidden = false;
      toggle.textContent = enabled ? '动效：开' : '动效：关';
      toggle.setAttribute('aria-pressed', String(enabled));
      toggle.setAttribute('aria-label', reducedMotion.matches ? '动效：关，已跟随系统减少动态效果设置' : enabled ? '动效：开，点击关闭动态效果' : '动效：关，点击开启动态效果');
      toggle.disabled = reducedMotion.matches;
    }
    if (!enabled) {
      activeAnimations.forEach((animation) => animation.cancel());
      activeAnimations.clear();
    }
  };
  updateMotion();
  toggle?.addEventListener('click', () => {
    preference = motionAllowed() ? 'off' : 'on';
    try { localStorage.setItem('pref-motion', preference); } catch (_) {}
    updateMotion();
  });
  reducedMotion.addEventListener('change', updateMotion);

  // Animate visible content without hiding it in CSS or changing document flow.
  if (!('IntersectionObserver' in window) || !Element.prototype.animate) return;
  const reveal = (element, duration = 650, delay = 0, distance = 10) => {
    if (!motionAllowed()) return;
    const animation = element.animate([
      { opacity: 0, transform: `translateY(${distance}px)` },
      { opacity: 1, transform: 'translateY(0)' },
    ], { duration, delay, easing: 'cubic-bezier(.19, 1, .22, 1)', fill: 'backwards' });
    activeAnimations.set(element, animation);
    const finish = () => {
      if (activeAnimations.get(element) === animation) activeAnimations.delete(element);
    };
    animation.finished.then(finish, finish);
  };

  const homeObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      homeObserver.unobserve(entry.target);
      reveal(entry.target, 320, 0, 8);
    });
  }, { threshold: .08 });
  document.querySelectorAll('.home-recent .post-line, .home-reading-rail section').forEach((element) => {
    if (element.getBoundingClientRect().top >= window.innerHeight) homeObserver.observe(element);
  });

  const content = document.querySelector('[data-reader-content]');
  if (!content) return;
  const enteringFromTop = !location.hash && window.scrollY < 16;
  const intro = document.querySelector('.single-intro-container');
  if (enteringFromTop) {
    Array.from(intro?.children || []).filter((element) => !element.matches('[data-reader-tools]'))
      .forEach((element, index) => reveal(element, 600, Math.min(index * 45, 135)));
  }

  // A chapter enters as one group. Keep the existing markup, margins and anchors.
  const chapters = [];
  let chapter;
  Array.from(content.children).forEach((element) => {
    if (element.matches('script, style, link')) return;
    if (!chapter || element.matches('h2')) {
      chapter = { marker: element, elements: [], entered: false };
      chapters.push(chapter);
    }
    chapter.elements.push(element);
  });
  const enterChapter = (item, animate = true) => {
    if (item.entered) return;
    item.entered = true;
    chapterObserver.unobserve(item.marker);
    if (animate) item.elements.forEach((element) => reveal(element));
  };
  const chapterObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const item = chapters.find(({ marker }) => marker === entry.target);
      if (item) enterChapter(item);
    });
  }, { threshold: 0, rootMargin: '0px 0px -40px 0px' });
  chapters.forEach((item) => {
    const bounds = item.marker.getBoundingClientRect();
    if (bounds.top < innerHeight) enterChapter(item, enteringFromTop && bounds.bottom > 0);
    else chapterObserver.observe(item.marker);
  });

  // Anchor navigation should land on readable text, even during an entry animation.
  const showAnchor = (hash) => {
    let target;
    try { target = document.getElementById(decodeURIComponent(hash.slice(1))); } catch (_) { return; }
    if (!target || !content.contains(target)) return;
    const item = chapters.find(({ elements }) => elements.some((element) => element === target || element.contains(target)));
    if (!item) return;
    enterChapter(item, false);
    item.elements.forEach((element) => activeAnimations.get(element)?.cancel());
  };
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const url = new URL(link.href, location.href);
    if (url.origin === location.origin && url.pathname === location.pathname && url.search === location.search && url.hash) showAnchor(url.hash);
  });
  window.addEventListener('hashchange', () => showAnchor(location.hash));
  showAnchor(location.hash);
})();
