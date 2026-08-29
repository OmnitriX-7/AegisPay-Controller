/**
 * AegisPay-Controller: Universal In-App Notification & Dialog System
 * Replaces browser "localhost:8000 says" alert popups with native dark-mode modals & toasts.
 */

const AegisNotice = {
  alertCallback: null,

  toast(message, type = 'success', duration = 3500) {
    let toast = document.getElementById('aegispayToast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'aegispayToast';
      toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: #18181b;
        color: #fff;
        border: 1px solid rgba(16, 185, 129, 0.4);
        padding: 12px 18px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        z-index: 999999;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        display: flex;
        align-items: center;
        gap: 10px;
        transition: all 0.25s ease;
        opacity: 0;
        transform: translateY(10px);
        max-width: 420px;
        line-height: 1.4;
      `;
      document.body.appendChild(toast);
    }
    const icon = type === 'success' ? '✅' : (type === 'error' ? '⚠️' : (type === 'webhook' ? '⚡' : 'ℹ️'));
    const borderColor = type === 'error' ? 'rgba(239, 68, 68, 0.6)' : (type === 'webhook' ? 'rgba(59, 130, 246, 0.6)' : 'rgba(16, 185, 129, 0.6)');
    toast.innerHTML = `<span style="font-size:15px;">${icon}</span> <span>${message}</span>`;
    toast.style.borderColor = borderColor;
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';

    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
    }, duration);
  },

  alert(message, title = 'System Notification', icon = 'ℹ️', callback = null) {
    const modal = document.getElementById('customAlertModal');
    const titleEl = document.getElementById('customAlertTitle');
    const msgEl = document.getElementById('customAlertMessage');
    const iconEl = document.getElementById('customAlertIcon');

    if (!modal) {
      this.toast(message, 'info');
      if (typeof callback === 'function') callback();
      return;
    }

    if (titleEl) titleEl.innerText = title;
    if (msgEl) msgEl.innerText = String(message || '').replace(/\\n/g, '\n');
    if (iconEl) iconEl.innerText = icon;
    this.alertCallback = callback;

    modal.style.display = 'flex';
  },

  closeAlert() {
    const modal = document.getElementById('customAlertModal');
    if (modal) modal.style.display = 'none';
    if (typeof this.alertCallback === 'function') {
      const cb = this.alertCallback;
      this.alertCallback = null;
      cb();
    }
  }
};

// Globally intercept window.alert so no browser "localhost:8000 says" popup can ever appear!
window.alert = function(message) {
  let title = 'AegisPay System Notification';
  let icon = 'ℹ️';
  const str = String(message || '');
  if (str.includes('⚠️') || str.toLowerCase().includes('error') || str.toLowerCase().includes('already registered') || str.toLowerCase().includes('permission')) {
    title = 'Notice';
    icon = '⚠️';
  } else if (str.includes('🎉') || str.includes('✅') || str.toLowerCase().includes('success')) {
    title = 'Success';
    icon = '✅';
  } else if (str.includes('⚡') || str.toLowerCase().includes('webhook')) {
    title = 'Live Webhook Event';
    icon = '⚡';
  }
  AegisNotice.alert(str, title, icon);
};

window.AegisNotice = AegisNotice;
