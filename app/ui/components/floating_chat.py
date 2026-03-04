"""Floating chat assistant widget — SCRUM-41."""

import streamlit as st


def render_floating_chat_widget(api_url: str) -> None:
    """Inject floating chat button + slide-in panel into the page."""
    html = _build_floating_chat_html(api_url)
    st.markdown(html, unsafe_allow_html=True)


def _build_floating_chat_html(api_url: str) -> str:
    """Return self-contained HTML/CSS/JS for the floating chat widget."""
    return f"""
<style>
/* Floating Chat Button */
#smartshop-chat-btn {{
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: #1f77b4;
    color: #fff;
    border: none;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(31,119,180,0.4);
    font-size: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    animation: chatPulse 2s ease-in-out 3;
    transition: transform 0.15s ease;
}}
#smartshop-chat-btn:hover {{ transform: scale(1.1); }}
@keyframes chatPulse {{
    0%, 100% {{ box-shadow: 0 4px 16px rgba(31,119,180,0.4); }}
    50% {{ box-shadow: 0 4px 28px rgba(31,119,180,0.8); }}
}}

/* Chat Panel */
#smartshop-chat-panel {{
    position: fixed;
    top: 0;
    right: -400px;
    width: 380px;
    height: 100vh;
    background: #fff;
    box-shadow: -4px 0 24px rgba(0,0,0,0.15);
    z-index: 9998;
    display: flex;
    flex-direction: column;
    transition: right 0.3s ease;
    border-left: 1px solid #e0e0e0;
}}
#smartshop-chat-panel.open {{ right: 0; }}

/* Panel Header */
#smartshop-chat-header {{
    background: #1f77b4;
    color: #fff;
    padding: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
}}
#smartshop-chat-header h3 {{ margin: 0; font-size: 1rem; }}
#smartshop-chat-close {{
    background: none;
    border: none;
    color: #fff;
    font-size: 1.4rem;
    cursor: pointer;
    line-height: 1;
    padding: 0 4px;
}}

/* Messages */
#smartshop-chat-messages {{
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}}
.chat-msg-user {{
    align-self: flex-end;
    background: #1f77b4;
    color: #fff;
    padding: 8px 12px;
    border-radius: 12px 12px 2px 12px;
    max-width: 80%;
    font-size: 0.9rem;
}}
.chat-msg-bot {{
    align-self: flex-start;
    background: #f0f4f8;
    color: #333;
    padding: 8px 12px;
    border-radius: 12px 12px 12px 2px;
    max-width: 85%;
    font-size: 0.9rem;
}}
.chat-spinner {{ color: #999; font-style: italic; font-size: 0.85rem; }}

/* Input */
#smartshop-chat-input-row {{
    display: flex;
    padding: 12px;
    border-top: 1px solid #e0e0e0;
    gap: 8px;
    flex-shrink: 0;
}}
#smartshop-chat-input {{
    flex: 1;
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.9rem;
    outline: none;
}}
#smartshop-chat-input:focus {{ border-color: #1f77b4; }}
#smartshop-chat-send {{
    background: #1f77b4;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    cursor: pointer;
    font-size: 0.9rem;
}}

/* Mobile */
@media (max-width: 600px) {{
    #smartshop-chat-panel {{ width: 100%; right: -100%; }}
}}
</style>

<!-- Floating Button -->
<button id="smartshop-chat-btn" aria-label="Open AI chat assistant" title="Chat with AI Assistant">
  💬
</button>

<!-- Chat Panel -->
<div id="smartshop-chat-panel" role="dialog" aria-label="AI Chat Assistant" aria-modal="true">
  <div id="smartshop-chat-header">
    <h3>🛒 SmartShop AI</h3>
    <button id="smartshop-chat-close" aria-label="Close chat">✕</button>
  </div>
  <div id="smartshop-chat-messages" aria-live="polite" aria-label="Chat messages">
    <div class="chat-msg-bot">
      👋 Hi! Ask me about products, prices, or reviews!
    </div>
  </div>
  <div id="smartshop-chat-input-row">
    <input id="smartshop-chat-input" type="text"
           placeholder="Ask me anything..." aria-label="Chat message input" />
    <button id="smartshop-chat-send" aria-label="Send message">Send</button>
  </div>
</div>

<script>
(function() {{
  var btn   = document.getElementById('smartshop-chat-btn');
  var panel = document.getElementById('smartshop-chat-panel');
  var close = document.getElementById('smartshop-chat-close');
  var msgs  = document.getElementById('smartshop-chat-messages');
  var input = document.getElementById('smartshop-chat-input');
  var send  = document.getElementById('smartshop-chat-send');
  var API_URL = '{api_url}';

  // Session ID
  var sessionId = sessionStorage.getItem('smartshop_session_id');
  if (!sessionId) {{
    sessionId = 'chat-' + Math.random().toString(36).substr(2, 9);
    sessionStorage.setItem('smartshop_session_id', sessionId);
  }}

  // Open/close
  btn.addEventListener('click', function() {{
    panel.classList.add('open');
    btn.style.display = 'none';
    input.focus();
  }});
  close.addEventListener('click', function() {{
    panel.classList.remove('open');
    btn.style.display = 'flex';
  }});

  // Keyboard: Escape to close
  document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape' && panel.classList.contains('open')) {{
      panel.classList.remove('open');
      btn.style.display = 'flex';
      btn.focus();
    }}
  }});

  // Send message
  function sendMessage() {{
    var text = input.value.trim();
    if (!text) return;
    input.value = '';

    // User bubble
    var userDiv = document.createElement('div');
    userDiv.className = 'chat-msg-user';
    userDiv.textContent = text;
    msgs.appendChild(userDiv);

    // Spinner
    var spinner = document.createElement('div');
    spinner.className = 'chat-msg-bot chat-spinner';
    spinner.textContent = 'Thinking...';
    msgs.appendChild(spinner);
    msgs.scrollTop = msgs.scrollHeight;

    fetch(API_URL + '/api/v1/chat', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        message: text,
        session_id: sessionId,
        max_results: 5
      }})
    }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      msgs.removeChild(spinner);
      var reply = '';
      if (data.success) {{
        var d = data.data || {{}};
        var intent = d.intent || 'general';
        var resp = d.response || {{}};
        if (intent === 'general') {{
          reply = resp.answer || 'I am not sure how to help with that.';
        }} else if (intent === 'policy') {{
          reply = resp.answer || 'No policy information found.';
        }} else if (intent === 'price') {{
          reply = (resp.best_deal ? '🏆 Best Deal: ' + resp.best_deal + '\\n\\n' : '') +
                  (resp.recommendation || 'No comparison data.');
        }} else {{
          reply = resp.summary || resp.reasoning_summary || JSON.stringify(resp).substring(0, 200);
        }}
      }} else {{
        reply = '⚠️ ' + (data.error || 'Something went wrong.');
      }}
      var botDiv = document.createElement('div');
      botDiv.className = 'chat-msg-bot';
      botDiv.textContent = reply;
      msgs.appendChild(botDiv);
      msgs.scrollTop = msgs.scrollHeight;
    }})
    .catch(function(err) {{
      msgs.removeChild(spinner);
      var errDiv = document.createElement('div');
      errDiv.className = 'chat-msg-bot';
      errDiv.textContent = '⚠️ Could not connect to assistant.';
      msgs.appendChild(errDiv);
      msgs.scrollTop = msgs.scrollHeight;
    }});
  }}

  send.addEventListener('click', sendMessage);
  input.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') sendMessage();
  }});
}})();
</script>
"""
