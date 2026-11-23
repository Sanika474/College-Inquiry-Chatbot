/**
 * CampusIQ Interactive Chat Controller
 * Manages chat turn cycles, suggestion chips, conversation persistence,
 * structured tables, document link action pills, and markdown formatting.
 */

class ChatController {
  constructor() {
    this.currentConversationId = null;
    this.speechEnabled = false;
    this.synth = window.speechSynthesis || null;

    // Audio SFX
    this.sendAudio = new Audio('sounds/click.wav');
    this.receiveAudio = new Audio('sounds/typing.wav');
    this.receiveAudio.volume = 0.5;
    this.sendAudio.volume = 0.4;
  }

  init() {
    this.chatMessagesContainer = document.getElementById('chat-messages');
    this.chatInput = document.getElementById('chat-input');
    this.sendButton = document.getElementById('btn-send-message');
    this.suggestionContainer = document.getElementById('suggestion-chips-container');
    this.newChatButton = document.getElementById('btn-new-chat');
    this.voiceToggle = document.getElementById('btn-voice-toggle');
    this.deleteChatButton = document.getElementById('btn-delete-chat');
    this.clearAllHistoryButton = document.getElementById('btn-clear-all-history');

    if (!this.chatMessagesContainer || !this.chatInput) return;

    // Attach event listeners
    this.sendButton.addEventListener('click', () => this.handleSendMessage());
    this.chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleSendMessage();
      }
    });

    if (this.newChatButton) {
      this.newChatButton.addEventListener('click', () => this.startNewConversation());
    }

    if (this.deleteChatButton) {
      this.deleteChatButton.addEventListener('click', () => this.deleteCurrentConversation());
    }

    if (this.clearAllHistoryButton) {
      this.clearAllHistoryButton.addEventListener('click', () => this.deleteAllConversations());
    }

    if (this.voiceToggle) {
      this.voiceToggle.addEventListener('click', () => {
        this.speechEnabled = !this.speechEnabled;
        this.voiceToggle.classList.toggle('active', this.speechEnabled);
        window.showToast(this.speechEnabled ? 'Voice output enabled' : 'Voice output disabled', 'info');
      });
    }

    // Bind initial suggestion chips present in the DOM
    if (this.suggestionContainer) {
      this.suggestionContainer.querySelectorAll('button.chip').forEach((chip) => {
        chip.addEventListener('click', () => this.handleSendMessage(chip.textContent.trim()));
      });
    }

    // Load initial conversation history if user is authenticated
    this.loadConversationHistory();
  }

  async loadConversationHistory() {
    const historyList = document.getElementById('conversation-history-list');
    const clearAllBtn = document.getElementById('btn-clear-all-history');
    if (!historyList) return;

    const res = await window.api.get('/chat/conversations');
    if (res.success && Array.isArray(res.data) && res.data.length > 0) {
      historyList.innerHTML = '';
      if (clearAllBtn) clearAllBtn.style.display = 'inline-flex';

      res.data.forEach((conv) => {
        const item = document.createElement('div');
        item.className = 'chat-history-item';
        if (conv.id === this.currentConversationId) {
          item.classList.add('active');
        }
        item.innerHTML = `
          <span class="chat-history-title" title="${this.escapeHtml(conv.title)}">${this.escapeHtml(conv.title)}</span>
          <div class="chat-history-actions">
            <span style="font-size: 0.7rem; color: var(--text-muted);">${conv.message_count}</span>
            <button type="button" class="btn-delete-conv" title="Delete conversation" data-id="${conv.id}">
              <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        `;

        item.addEventListener('click', (e) => {
          if (e.target.closest('.btn-delete-conv')) return;
          this.openConversation(conv.id);
        });

        const delBtn = item.querySelector('.btn-delete-conv');
        if (delBtn) {
          delBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.deleteConversation(conv.id);
          });
        }

        historyList.appendChild(item);
      });
    } else {
      if (clearAllBtn) clearAllBtn.style.display = 'none';
      historyList.innerHTML = `
        <div style="padding: 1.25rem 0.5rem; text-align: center; color: var(--text-muted); font-size: 0.8rem;">
          No past conversations found.
        </div>
      `;
    }
  }

  async openConversation(convId) {
    const res = await window.api.get(`/chat/conversations/${convId}`);
    if (res.success && res.data) {
      this.currentConversationId = convId;
      this.chatMessagesContainer.innerHTML = '';
      res.data.messages.forEach((msg) => {
        this.appendMessage(msg.content, msg.sender === 'user' ? 'user' : 'bot', {
          engine: msg.processing_engine,
          sources: msg.source_reference ? [msg.source_reference] : [],
        });
      });
      this.scrollToBottom();

      // Update active highlight in sidebar
      document.querySelectorAll('.chat-history-item').forEach((item) => {
        const btn = item.querySelector('.btn-delete-conv');
        if (btn && btn.getAttribute('data-id') == convId) {
          item.classList.add('active');
        } else {
          item.classList.remove('active');
        }
      });
    }
  }

  startNewConversation() {
    this.currentConversationId = null;
    document.querySelectorAll('.chat-history-item').forEach((item) => item.classList.remove('active'));
    this.chatMessagesContainer.innerHTML = `
      <div class="message-bubble message-bot">
        <div class="message-avatar">IQ</div>
        <div class="message-content">
          <p>Hello! 👋 Welcome to <strong>CampusIQ — Intelligent College Companion</strong> for <strong>JD College of Engineering & Management (JDCOEM), Nagpur</strong>.</p>
          <p style="margin-top: 0.5rem;">I am specialized in the <strong>Master of Computer Applications (MCA)</strong> department and campus admissions. How can I assist you today?</p>
        </div>
      </div>
    `;
    this.renderSuggestions([
      'MCA Sem 2 Syllabus',
      'What is the MCA fee?',
      'Which documents are required for admission?',
      'Show MCA timetable',
      'Prof. Rohan Kokate (HOD MCA)',
    ]);
  }

  async deleteConversation(convId) {
    if (!confirm('Are you sure you want to delete this conversation?')) return;

    const res = await window.api.delete(`/chat/conversations/${convId}`);
    if (res.success) {
      window.showToast('Conversation deleted', 'info');
      if (this.currentConversationId === convId) {
        this.startNewConversation();
      }
      this.loadConversationHistory();
    } else {
      window.showToast(res.error || 'Failed to delete conversation', 'error');
    }
  }

  async deleteAllConversations() {
    if (!confirm('Are you sure you want to delete all chat history? This cannot be undone.')) return;

    const res = await window.api.delete('/chat/conversations');
    if (res.success) {
      window.showToast('All chat history deleted', 'info');
      this.startNewConversation();
      this.loadConversationHistory();
    } else {
      window.showToast(res.error || 'Failed to delete history', 'error');
    }
  }

  async deleteCurrentConversation() {
    if (!this.currentConversationId) {
      this.startNewConversation();
      window.showToast('Chat history cleared', 'info');
      return;
    }
    await this.deleteConversation(this.currentConversationId);
  }

  async handleSendMessage(overrideText = null) {
    const text = (overrideText || this.chatInput.value).trim();
    if (!text) return;

    // Clear input
    if (!overrideText) {
      this.chatInput.value = '';
    }

    // Play send audio effect
    this.playAudio(this.sendAudio);

    // Append user message to UI
    this.appendMessage(text, 'user');
    this.scrollToBottom();

    // Show typing indicator
    const typingIndicator = this.showTypingIndicator();

    try {
      const res = await window.api.post('/chat', {
        message: text,
        conversation_id: this.currentConversationId,
      });

      typingIndicator.remove();

      if (res.success && res.data) {
        this.currentConversationId = res.data.conversation_id;
        this.playAudio(this.receiveAudio);

        this.appendMessage(res.data.message, 'bot', {
          engine: res.data.engine,
          confidence: res.data.confidence,
          sources: res.data.sources,
          links: res.data.links,
          format: res.data.format,
          items: res.data.items,
        });

        // Speak aloud if voice toggle enabled
        if (this.speechEnabled) {
          this.speak(res.data.message);
        }

        // Render suggestion chips
        if (res.data.suggestions && res.data.suggestions.length > 0) {
          this.renderSuggestions(res.data.suggestions);
        }

        // Refresh sidebar history if user is logged in
        if (window.auth && window.auth.isAuthenticated) {
          this.loadConversationHistory();
        }
      } else {
        this.appendMessage(
          res.error || 'I encountered an error connecting to CampusIQ backend. Please try again.',
          'bot'
        );
      }
    } catch (err) {
      typingIndicator.remove();
      this.appendMessage('Network error. Please verify the backend service is online.', 'bot');
    }

    this.scrollToBottom();
  }

  appendMessage(content, sender, meta = null) {
    const bubble = document.createElement('div');
    bubble.className = `message-bubble message-${sender}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = sender === 'user' ? 'YOU' : 'IQ';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = this.renderMarkdown(content);

    // Render interactive document link pills if returned by structured schema
    if (meta && sender === 'bot' && meta.links && Array.isArray(meta.links) && meta.links.length > 0) {
      const linksContainer = document.createElement('div');
      linksContainer.className = 'doc-action-container';
      meta.links.forEach((lnk) => {
        const linkBtn = document.createElement('a');
        linkBtn.href = lnk.url;
        linkBtn.target = '_blank';
        linkBtn.rel = 'noopener noreferrer';
        linkBtn.className = 'doc-link-btn';
        linkBtn.innerHTML = `📄 ${this.escapeHtml(lnk.label)} ↗`;
        linksContainer.appendChild(linkBtn);
      });
      contentDiv.appendChild(linksContainer);
    }

    if (meta && sender === 'bot') {
      const metaDiv = document.createElement('div');
      metaDiv.className = 'message-meta';

      let engineBadge = '';
      if (meta.engine === 'rule_based') {
        engineBadge = `<span style="color: #60a5fa;">● Verified Knowledge Graph</span>`;
      } else if (meta.engine === 'ai_fallback') {
        engineBadge = `<span style="color: #c084fc;">● Grounded AI Assistant</span>`;
      } else if (meta.engine === 'clarification') {
        engineBadge = `<span style="color: #fbbf24;">● Query Clarification</span>`;
      }

      const sourcesText = meta.sources && meta.sources.length > 0 
        ? ` | Source: ${this.escapeHtml(meta.sources.join(', '))}`
        : '';

      metaDiv.innerHTML = `${engineBadge}${sourcesText}`;
      contentDiv.appendChild(metaDiv);
    }

    bubble.appendChild(avatar);
    bubble.appendChild(contentDiv);
    this.chatMessagesContainer.appendChild(bubble);
  }

  showTypingIndicator() {
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble message-bot typing-indicator';
    bubble.innerHTML = `
      <div class="message-avatar">IQ</div>
      <div class="message-content" style="display: flex; gap: 4px; align-items: center; padding: 1rem 1.25rem;">
        <span style="width: 7px; height: 7px; border-radius: 50%; background: #60a5fa; animation: pulse 1s infinite alternate;"></span>
        <span style="width: 7px; height: 7px; border-radius: 50%; background: #818cf8; animation: pulse 1s infinite alternate; animation-delay: 200ms;"></span>
        <span style="width: 7px; height: 7px; border-radius: 50%; background: #c084fc; animation: pulse 1s infinite alternate; animation-delay: 400ms;"></span>
      </div>
    `;
    this.chatMessagesContainer.appendChild(bubble);
    this.scrollToBottom();
    return bubble;
  }

  renderSuggestions(suggestions) {
    if (!this.suggestionContainer) return;
    this.suggestionContainer.innerHTML = '';
    suggestions.forEach((chipText) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip';
      chip.textContent = chipText;
      chip.addEventListener('click', () => this.handleSendMessage(chipText));
      this.suggestionContainer.appendChild(chip);
    });
  }

  scrollToBottom() {
    this.chatMessagesContainer.scrollTop = this.chatMessagesContainer.scrollHeight;
  }

  playAudio(audio) {
    try {
      audio.currentTime = 0;
      audio.play().catch(() => {});
    } catch (e) {}
  }

  speak(text) {
    if (!this.synth || !this.speechEnabled) return;
    this.synth.cancel();
    // Strip markdown formatting characters for clean speech synthesis
    const cleanText = text.replace(/[*_#`\[\]]/g, '').replace(/https?:\/\/\S+/g, '');
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    this.synth.speak(utterance);
  }

  renderMarkdown(text) {
    if (!text) return '';
    let html = this.escapeHtml(text);

    // Inline Code `code`
    html = html.replace(/`([^`]+)`/g, '<code style="background: rgba(15, 23, 42, 0.7); padding: 0.15rem 0.35rem; border-radius: 4px; font-size: 0.8rem; color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.2);">$1</code>');

    // Bold **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italic *text*
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Links [text](url) — supports absolute http/https and relative /api/v1 endpoints
    html = html.replace(/\[(.*?)\]\(((?:https?:\/\/|\/)[^\s\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="doc-link-btn">$1 ↗</a>');

    // Blockquotes > text
    html = html.replace(/^&gt;\s*(.*)$/gm, '<blockquote style="border-left: 3px solid #38bdf8; padding-left: 0.75rem; margin: 0.5rem 0; color: var(--text-secondary); background: rgba(56, 189, 248, 0.05); padding-top: 0.25rem; padding-bottom: 0.25rem; border-radius: 0 4px 4px 0;">$1</blockquote>');

    // Headings
    html = html.replace(/^###\s*(.*)$/gm, '<h4 style="font-size: 0.95rem; font-weight: 700; color: #38bdf8; margin: 0.6rem 0 0.25rem;">$1</h4>');
    html = html.replace(/^##\s*(.*)$/gm, '<h3 style="font-size: 1.15rem; font-weight: 800; color: #fff; margin: 0.75rem 0 0.4rem; letter-spacing: -0.01em;">$1</h3>');

    // Horizontal Rule
    html = html.replace(/^---$/gm, '<hr style="border: none; border-top: 1px solid var(--border-subtle); margin: 0.75rem 0;">');

    // Parse Markdown Tables
    const lines = html.split('\n');
    let inTable = false;
    let tableHeaderDone = false;
    let inBulletList = false;
    let inOrderedList = false;
    let result = [];

    lines.forEach((line) => {
      const trimmed = line.trim();

      // Table line detection: starts and ends with |
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        // Close lists if open
        if (inBulletList) { result.push('</ul>'); inBulletList = false; }
        if (inOrderedList) { result.push('</ol>'); inOrderedList = false; }

        // Separator line e.g. | :--- | :--- |
        if (/^\|(\s*[:\-]+\s*\|)+$/.test(trimmed)) {
          tableHeaderDone = true;
          return;
        }

        const cells = trimmed.split('|').slice(1, -1).map(c => c.trim());

        if (!inTable) {
          result.push('<table>');
          result.push('<thead><tr>' + cells.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>');
          inTable = true;
          tableHeaderDone = false;
        } else {
          result.push('<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>');
        }
        return;
      } else {
        if (inTable) {
          result.push('</tbody></table>');
          inTable = false;
          tableHeaderDone = false;
        }
      }

      // Ordered List detection: 1. , 2. 
      const olMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
      if (olMatch) {
        if (inBulletList) { result.push('</ul>'); inBulletList = false; }
        if (!inOrderedList) {
          result.push('<ol>');
          inOrderedList = true;
        }
        result.push(`<li>${olMatch[2]}</li>`);
        return;
      } else {
        if (inOrderedList) {
          result.push('</ol>');
          inOrderedList = false;
        }
      }

      // Bullet List detection: - , • , * 
      if (trimmed.startsWith('- ') || trimmed.startsWith('• ') || trimmed.startsWith('* ')) {
        if (inOrderedList) { result.push('</ol>'); inOrderedList = false; }
        if (!inBulletList) {
          result.push('<ul style="padding-left: 1.25rem; margin: 0.4rem 0;">');
          inBulletList = true;
        }
        result.push(`<li>${trimmed.substring(2)}</li>`);
        return;
      } else {
        if (inBulletList) {
          result.push('</ul>');
          inBulletList = false;
        }
      }

      // Regular paragraph
      if (trimmed) {
        result.push(`<p style="margin-bottom: 0.4rem;">${line}</p>`);
      }
    });

    if (inTable) { result.push('</tbody></table>'); }
    if (inBulletList) { result.push('</ul>'); }
    if (inOrderedList) { result.push('</ol>'); }

    return result.join('');
  }

  escapeHtml(unsafe) {
    return unsafe
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

window.chatbot = new ChatController();
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.chatbot.init();
  });
} else {
  window.chatbot.init();
}
