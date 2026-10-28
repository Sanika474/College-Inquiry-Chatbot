/**
 * CampusIQ Interactive Chat Controller
 * Manages chat turn cycles, suggestion chips, conversation persistence, and markdown formatting.
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
    if (!historyList) return;

    const res = await window.api.get('/chat/conversations');
    if (res.success && Array.isArray(res.data) && res.data.length > 0) {
      historyList.innerHTML = '';
      res.data.forEach((conv) => {
        const item = document.createElement('div');
        item.className = 'chat-history-item';
        item.innerHTML = `
          <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 190px;">${this.escapeHtml(conv.title)}</span>
          <span style="font-size: 0.7rem; color: var(--text-muted);">${conv.message_count}</span>
        `;
        item.addEventListener('click', () => this.openConversation(conv.id));
        historyList.appendChild(item);
      });
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
    }
  }

  startNewConversation() {
    this.currentConversationId = null;
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
      'MCA Course Details',
      'MCA Fees (FRA Sanctioned)',
      'Prof. Rohan Kokate (HOD MCA)',
      'TBI Startup Incubation',
      'Placement Highlights & Recruiters',
    ]);
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

    if (meta && sender === 'bot') {
      const metaDiv = document.createElement('div');
      metaDiv.className = 'message-meta';

      let engineBadge = '';
      if (meta.engine === 'rule_based') {
        engineBadge = `<span style="color: #60a5fa;">● Verified Rule Engine</span>`;
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

    // Bold **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italic *text*
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Links [text](url)
    html = html.replace(/\[(.*?)\]\((https?:\/\/.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #60a5fa; text-decoration: underline;">$1</a>');

    // Bullet Lists
    const lines = html.split('\n');
    let inList = false;
    let result = [];

    lines.forEach((line) => {
      const trimmed = line.trim();
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        if (!inList) {
          result.push('<ul style="padding-left: 1.25rem; margin: 0.4rem 0;">');
          inList = true;
        }
        result.push(`<li>${trimmed.substring(2)}</li>`);
      } else {
        if (inList) {
          result.push('</ul>');
          inList = false;
        }
        if (trimmed) {
          result.push(`<p style="margin-bottom: 0.4rem;">${line}</p>`);
        }
      }
    });

    if (inList) {
      result.push('</ul>');
    }

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
document.addEventListener('DOMContentLoaded', () => {
  window.chatbot.init();
});
