(() => {
  'use strict';

  const root = document.documentElement;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const toggle = document.getElementById('motion-toggle');
  const activeAnimations = new Set();
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

  // Content stays visible by default, including without JS or animation support.
  if (!('IntersectionObserver' in window) || !Element.prototype.animate) return;
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      revealObserver.unobserve(entry.target);
      if (!motionAllowed()) return;
      const animation = entry.target.animate([
        { opacity: 0, transform: 'translateY(8px)' },
        { opacity: 1, transform: 'translateY(0)' },
      ], { duration: 320, easing: 'cubic-bezier(.22, 1, .36, 1)' });
      activeAnimations.add(animation);
      animation.finished.then(() => activeAnimations.delete(animation), () => activeAnimations.delete(animation));
    });
  }, { threshold: .08 });
  document.querySelectorAll('.home-recent .post-line, .home-reading-rail section').forEach((element) => {
    if (element.getBoundingClientRect().top >= window.innerHeight) revealObserver.observe(element);
  });
})();
