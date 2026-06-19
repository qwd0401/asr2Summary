/**
 * Toast notifications
 * - Stacked, top-right, auto-dismiss 4s
 * - aria-live polite for screen readers
 */
(function () {
  'use strict';

  function ensureContainer() {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      container.setAttribute('role', 'region');
      container.setAttribute('aria-label', '通知');
      container.setAttribute('aria-live', 'polite');
      document.body.appendChild(container);
    }
    return container;
  }

  function show(message, type = 'info', duration = 4000) {
    const container = ensureContainer();
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');

    const iconWrap = document.createElement('span');
    iconWrap.setAttribute(
      'data-lucide',
      type === 'success' ? 'check-circle' : type === 'error' ? 'alert-circle' : 'info'
    );
    iconWrap.setAttribute('data-size', '20');
    iconWrap.style.flexShrink = '0';
    iconWrap.style.color = `var(--color-${type === 'error' ? 'destructive' : type === 'success' ? 'success' : 'info'})`;
    toast.appendChild(iconWrap);

    const msg = document.createElement('span');
    msg.style.flex = '1';
    msg.textContent = message;
    toast.appendChild(msg);

    container.appendChild(toast);
    if (window.appIcons) window.appIcons.render(toast);

    setTimeout(() => {
      toast.style.transition = 'opacity 200ms';
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 220);
    }, duration);
  }

  window.toast = {
    success: (msg, dur) => show(msg, 'success', dur),
    error: (msg, dur) => show(msg, 'error', dur),
    info: (msg, dur) => show(msg, 'info', dur),
  };
})();
