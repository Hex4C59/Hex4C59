document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.copy-code-button').forEach((button) => {
    button.textContent = '复制';
    button.setAttribute('aria-label', '复制代码');
    button.addEventListener('click', async () => {
      const code = button.previousElementSibling?.querySelector('code');
      if (!code) return;
      try {
        await navigator.clipboard.writeText(code.textContent);
        button.textContent = '已复制';
      } catch (_) {
        button.textContent = '请选中代码复制';
      }
      setTimeout(() => { button.textContent = '复制'; }, 1800);
    });
  });
});
