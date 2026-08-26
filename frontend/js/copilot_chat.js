/**
 * AegisPay-Controller: CFO Copilot & Settlement Q&A Chat Client
 * Swiss Modernist high-contrast layout, zero hallucination.
 */

const CopilotChat = {
  messagesContainer: null,
  chatInput: null,

  init(containerId = 'chatMessages', inputId = 'chatInput') {
    this.messagesContainer = document.getElementById(containerId || 'chatMessages');
    this.chatInput = document.getElementById(inputId || 'chatInput');

    if (this.chatInput) {
      this.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendQuery();
        }
      });
    }

    // Default Greeting Message
    if (this.messagesContainer && this.messagesContainer.children.length === 0) {
      this.addAiMessage(
        "👋 Hello! I am your **Autonomous Financial Controller Copilot**.\n\n" +
        "I have verified the active multi-source reconciliation batch and forward cash positions. " +
        "You can ask me to explain any fee variance, audit specific order invariants, or simulate liquidity scenarios."
      );
    }
  },

  sendQuery(presetText) {
    if (!this.messagesContainer) {
      this.init('chatMessages', 'chatInput');
    }
    const text = presetText || (this.chatInput ? this.chatInput.value.trim() : "");
    if (!text) return;

    if (this.chatInput) this.chatInput.value = "";

    // Add User Message to UI
    this.addUserMessage(text);

    // Show AI Thinking indicator
    const thinkingId = this.addThinkingIndicator();

    // Call API Endpoint
    fetch('/api/copilot/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: text })
    })
    .then(res => res.json())
    .then(data => {
      this.removeThinkingIndicator(thinkingId);
      this.addAiMessage(data.answer, data.suggested_followups);
    })
    .catch(err => {
      this.removeThinkingIndicator(thinkingId);
      this.addAiMessage(`❌ Error processing query: ${err.message}`);
    });
  },

  addUserMessage(text) {
    if (!this.messagesContainer) return;
    const msg = document.createElement('div');
    msg.className = 'chat-msg user';
    msg.innerHTML = `<div>${text}</div>`;
    this.messagesContainer.appendChild(msg);
    this.scrollToBottom();
  },

  addAiMessage(markdownText, followups = []) {
    if (!this.messagesContainer) return;
    const msg = document.createElement('div');
    msg.className = 'chat-msg ai';

    // Simple markdown renderer for bold, code, lists, and headers
    let html = (markdownText || '')
      .replace(/### (.*?)\n/g, '<h4 style="font-size:13px; font-weight:800; color:#fff; margin:4px 0 8px;">$1</h4>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code class="font-mono" style="background:rgba(255,255,255,0.08); padding:2px 5px; border-radius:4px; font-size:11px; color:var(--accent-emerald);">$1</code>')
      .replace(/• (.*?)\n/g, '<div style="margin-left:8px; margin-bottom:4px;">• $1</div>')
      .replace(/\n\n/g, '<div style="height:8px;"></div>');

    let followupsHtml = '';
    if (followups && followups.length > 0) {
      followupsHtml = `
        <div style="margin-top:12px; display:flex; flex-wrap:wrap; gap:6px;">
          ${followups.map(f => `
            <span class="prompt-btn" onclick="CopilotChat.sendQuery('${f.replace(/'/g, "\\'")}')">${f}</span>
          `).join('')}
        </div>
      `;
    }

    msg.innerHTML = `<div>${html}${followupsHtml}</div>`;
    this.messagesContainer.appendChild(msg);
    this.scrollToBottom();
  },

  addThinkingIndicator() {
    if (!this.messagesContainer) return null;
    const id = `thinking_${Date.now()}`;
    const msg = document.createElement('div');
    msg.id = id;
    msg.className = 'chat-msg ai';
    msg.innerHTML = `
      <div style="color:var(--text-muted); font-style:italic;">
        Auditing double-entry ledger invariants...
      </div>
    `;
    this.messagesContainer.appendChild(msg);
    this.scrollToBottom();
    return id;
  },

  removeThinkingIndicator(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (el) el.remove();
  },

  scrollToBottom() {
    if (this.messagesContainer) {
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
  }
};

window.CopilotChat = CopilotChat;
