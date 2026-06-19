/**
 * Theme toggle (dark/light)
 * - Reads prefers-color-scheme and localStorage
 * - Persists user override to localStorage
 * - Updates icon via appIcons.render()
 */
(function () {
  'use strict';

  const KEY = 'meetassistant-theme';

  function getIsDark() {
    const stored = localStorage.getItem(KEY);
    if (stored === 'dark') return true;
    if (stored === 'light') return false;
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function applyTheme(isDark) {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  }

  function renderIcon(btn, isDark) {
    btn.innerHTML = '<span data-lucide="' + (isDark ? 'sun' : 'moon') + '" data-size="18"></span>';
    if (window.appIcons) window.appIcons.render(btn);
  }

  function init() {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;

    // Apply stored/system theme on load
    const isDark = getIsDark();
    applyTheme(isDark);
    renderIcon(btn, isDark);

    btn.addEventListener('click', function () {
      const current = getIsDark();
      const next = !current;
      localStorage.setItem(KEY, next ? 'dark' : 'light');
      applyTheme(next);
      renderIcon(btn, next);
    });
  }

  // Run on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose for manual calls
  window.appTheme = { init: init, getIsDark: getIsDark };
})();
