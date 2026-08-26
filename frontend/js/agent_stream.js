/**
 * AegisPay-Controller: Live Agent Execution Stream
 * Shows real-time step-by-step reasoning during pipeline execution.
 */

const AgentStream = {
  container: null,
  panel: null,
  isVisible: true,
  startTime: 0,

  init() {
    this.container = document.getElementById('agentStreamLog');
    this.panel = document.getElementById('agentStreamPanel');
  },

  clear() {
    if (!this.container) this.init();
    if (this.container) this.container.innerHTML = '';
    this.startTime = performance.now();
  },

  toggle() {
    this.isVisible = !this.isVisible;
    if (this.panel) {
      this.panel.classList.toggle('collapsed', !this.isVisible);
    }
    const btn = document.getElementById('streamToggleBtn');
    if (btn) btn.textContent = this.isVisible ? 'Hide Stream' : 'Show Stream';
  },

  log(icon, message, type = 'info') {
    if (!this.container) this.init();
    if (!this.container) return;

    const elapsed = ((performance.now() - this.startTime) / 1000).toFixed(2);
    const entry = document.createElement('div');
    entry.className = `stream-entry stream-${type}`;
    entry.innerHTML = `
      <span class="stream-ts">[${elapsed}s]</span>
      <span class="stream-icon">${icon}</span>
      <span class="stream-msg">${message}</span>
    `;

    this.container.appendChild(entry);
    this.container.scrollTop = this.container.scrollHeight;

    entry.style.opacity = '0';
    entry.style.transform = 'translateY(4px)';
    requestAnimationFrame(() => {
      entry.style.transition = 'all 0.2s ease';
      entry.style.opacity = '1';
      entry.style.transform = 'translateY(0)';
    });
  },

  logStep(icon, message) { this.log(icon, message, 'step'); },
  logSuccess(icon, message) { this.log(icon, message, 'success'); },
  logWarning(icon, message) { this.log(icon, message, 'warning'); },
  logSeal(message) { this.log('🔒', message, 'seal'); }
};

window.AgentStream = AgentStream;
