"""Floating chat assistant widget — SCRUM-41.

Injects a floating chat button + slide-in panel directly into the parent
Streamlit document via window.parent.document so that position:fixed works
correctly across the entire viewport.
"""

import streamlit as st
import streamlit.components.v1 as components


def render_floating_chat_widget(api_url: str) -> None:
    """Inject floating chat button + slide-in panel into the page."""
    html = _build_floating_chat_html(api_url)
    # height=0 makes the iframe invisible; all UI is injected into parent
    components.html(html, height=0, scrolling=False)


def _build_floating_chat_html(api_url: str) -> str:
    """Return JS that injects the chat widget into the parent Streamlit page."""
    return f"""
<script>
(function() {{
  // Prevent duplicate injection on Streamlit re-runs
  var parentDoc = window.parent.document;
  var existingBtn = parentDoc.getElementById('smartshop-chat-btn');
  var existingClose = parentDoc.getElementById('smartshop-chat-close');
  if (existingBtn && existingClose) return;
  // Remove stale elements from previous version
  if (existingBtn) existingBtn.remove();
  var existingPanel = parentDoc.getElementById('smartshop-chat-panel');
  if (existingPanel) existingPanel.remove();

  // ── Inject CSS into parent <head> ──────────────────────────────
  var style = parentDoc.createElement('style');
  style.textContent = `
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
      z-index: 99999;
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
      right: -420px;
      width: 400px;
      min-width: 280px;
      max-width: 80vw;
      height: 100vh;
      background: #fff;
      box-shadow: -4px 0 24px rgba(0,0,0,0.15);
      z-index: 99998;
      display: flex;
      flex-direction: column;
      transition: right 0.3s ease;
      border-left: 1px solid #e0e0e0;
    }}
    #smartshop-chat-panel.open {{ right: 0; transition: right 0.3s ease; }}
    #smartshop-chat-panel.resizing {{ transition: none; }}

    /* Resize Handle */
    #smartshop-chat-resize {{
      position: absolute;
      top: 0;
      left: -4px;
      width: 8px;
      height: 100%;
      cursor: col-resize;
      z-index: 99999;
    }}
    #smartshop-chat-resize:hover,
    #smartshop-chat-resize:active {{
      background: rgba(31,119,180,0.15);
    }}

    /* Panel Header */
    #smartshop-chat-header {{
      background: #1f77b4 !important;
      color: #fff !important;
      padding: 14px 16px !important;
      display: flex !important;
      align-items: center !important;
      justify-content: space-between !important;
      flex-shrink: 0 !important;
      user-select: none;
      min-height: 48px !important;
      box-sizing: border-box !important;
    }}
    #smartshop-chat-header .ss-chat-title {{
      margin: 0 !important;
      padding: 0 !important;
      font-size: 1rem !important;
      font-weight: bold !important;
      color: #fff !important;
      display: inline !important;
    }}
    .ss-chat-header-btns {{
      display: flex !important;
      gap: 8px !important;
      align-items: center !important;
      flex-shrink: 0 !important;
    }}
    .ss-chat-header-btns button {{
      background: rgba(255,255,255,0.2) !important;
      border: 1px solid rgba(255,255,255,0.4) !important;
      color: #fff !important;
      font-size: 0.85rem !important;
      font-weight: bold !important;
      cursor: pointer !important;
      line-height: 1 !important;
      padding: 4px 8px !important;
      border-radius: 4px !important;
      min-width: 28px !important;
      min-height: 28px !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      visibility: visible !important;
      opacity: 1 !important;
    }}
    .ss-chat-header-btns button:hover {{ background: rgba(255,255,255,0.35) !important; }}

    /* Messages */
    #smartshop-chat-messages {{
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .ss-chat-msg-user {{
      align-self: flex-end;
      background: #1f77b4;
      color: #fff;
      padding: 8px 12px;
      border-radius: 12px 12px 2px 12px;
      max-width: 80%;
      font-size: 0.9rem;
      word-wrap: break-word;
    }}
    .ss-chat-msg-bot {{
      align-self: flex-start;
      background: #f0f4f8;
      color: #333;
      padding: 8px 12px;
      border-radius: 12px 12px 12px 2px;
      max-width: 85%;
      font-size: 0.9rem;
      word-wrap: break-word;
      white-space: pre-wrap;
    }}
    .ss-chat-spinner {{ color: #999; font-style: italic; font-size: 0.85rem; }}

    /* Input Row */
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
      font-family: inherit;
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
    #smartshop-chat-send:hover {{ background: #1a6aa0; }}

    /* Mobile */
    @media (max-width: 600px) {{
      #smartshop-chat-panel {{ width: 100vw; right: -100vw; min-width: 100vw; }}
      #smartshop-chat-panel.open {{ right: 0; }}
      #smartshop-chat-resize {{ display: none; }}
    }}
  `;
  parentDoc.head.appendChild(style);

  // ── Inject Button into parent <body> ───────────────────────────
  var btn = parentDoc.createElement('button');
  btn.id = 'smartshop-chat-btn';
  btn.setAttribute('aria-label', 'Open AI chat assistant');
  btn.title = 'Chat with AI Assistant';
  btn.innerHTML = '&#x1F4AC;';  // 💬
  parentDoc.body.appendChild(btn);

  // ── Inject Chat Panel into parent <body> ───────────────────────
  var panel = parentDoc.createElement('div');
  panel.id = 'smartshop-chat-panel';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', 'AI Chat Assistant');

  // Build header via createElement to avoid Streamlit CSS interference
  var resizeDiv = parentDoc.createElement('div');
  resizeDiv.id = 'smartshop-chat-resize';
  resizeDiv.title = 'Drag to resize';
  panel.appendChild(resizeDiv);

  var header = parentDoc.createElement('div');
  header.id = 'smartshop-chat-header';
  header.style.cssText = 'background:#1f77b4;color:#fff;padding:10px 16px;flex-shrink:0;text-align:center;font-weight:bold;font-size:0.95rem;';
  header.textContent = 'SmartShop AI';
  panel.appendChild(header);

  var msgsDiv = parentDoc.createElement('div');
  msgsDiv.id = 'smartshop-chat-messages';
  msgsDiv.setAttribute('aria-live', 'polite');
  var welcomeMsg = parentDoc.createElement('div');
  welcomeMsg.className = 'ss-chat-msg-bot';
  welcomeMsg.textContent = 'Hi! Ask me about products, prices, or reviews!';
  msgsDiv.appendChild(welcomeMsg);
  panel.appendChild(msgsDiv);

  var inputRow = parentDoc.createElement('div');
  inputRow.id = 'smartshop-chat-input-row';
  var chatInputEl = parentDoc.createElement('input');
  chatInputEl.id = 'smartshop-chat-input';
  chatInputEl.type = 'text';
  chatInputEl.placeholder = 'Ask me anything...';
  chatInputEl.setAttribute('aria-label', 'Chat message input');
  inputRow.appendChild(chatInputEl);
  var sendBtnEl = parentDoc.createElement('button');
  sendBtnEl.id = 'smartshop-chat-send';
  sendBtnEl.setAttribute('aria-label', 'Send message');
  sendBtnEl.textContent = 'Send';
  inputRow.appendChild(sendBtnEl);
  panel.appendChild(inputRow);

  // Footer bar with Close button
  var footerBar = parentDoc.createElement('div');
  footerBar.id = 'smartshop-chat-footer';
  footerBar.style.cssText = 'display:flex;padding:8px 12px;border-top:1px solid #e0e0e0;flex-shrink:0;justify-content:flex-start;background:#f8f9fa;';

  var closeB = parentDoc.createElement('button');
  closeB.id = 'smartshop-chat-close';
  closeB.setAttribute('aria-label', 'Close chat');
  closeB.title = 'Close chat';
  closeB.textContent = '>>';
  closeB.style.cssText = 'background:none;border:none;color:#808495;font-size:1.3rem;cursor:pointer;padding:4px 8px;line-height:1;';

  footerBar.appendChild(closeB);
  panel.appendChild(footerBar);

  parentDoc.body.appendChild(panel);

  // ── Wire up event handlers ─────────────────────────────────────
  var msgs     = msgsDiv;
  var chatInput = chatInputEl;
  var sendBtn  = sendBtnEl;
  var API_URL  = '{api_url}';

  // Session ID (persisted in parent sessionStorage)
  var parentWin = window.parent;
  var sessionId = parentWin.sessionStorage.getItem('smartshop_session_id');
  if (!sessionId) {{
    sessionId = 'chat-' + Math.random().toString(36).substr(2, 9);
    parentWin.sessionStorage.setItem('smartshop_session_id', sessionId);
  }}

  // Open panel
  btn.addEventListener('click', function() {{
    panel.classList.add('open');
    btn.style.display = 'none';
    chatInput.focus();
  }});

  // Close panel
  closeB.addEventListener('click', function() {{
    panel.classList.remove('open');
    btn.style.display = 'flex';
  }});

  // Resize handle — drag to change panel width
  resizeDiv.addEventListener('mousedown', function(e) {{
    e.preventDefault();
    panel.classList.add('resizing');
    var startX = e.clientX;
    var startWidth = panel.offsetWidth;
    function onMouseMove(ev) {{
      var newWidth = startWidth - (ev.clientX - startX);
      if (newWidth < 280) newWidth = 280;
      if (newWidth > parentDoc.documentElement.clientWidth * 0.8) newWidth = parentDoc.documentElement.clientWidth * 0.8;
      panel.style.width = newWidth + 'px';
    }}
    function onMouseUp() {{
      panel.classList.remove('resizing');
      parentDoc.removeEventListener('mousemove', onMouseMove);
      parentDoc.removeEventListener('mouseup', onMouseUp);
    }}
    parentDoc.addEventListener('mousemove', onMouseMove);
    parentDoc.addEventListener('mouseup', onMouseUp);
  }});

  // Escape to close
  parentDoc.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape' && panel.classList.contains('open')) {{
      panel.classList.remove('open');
      btn.style.display = 'flex';
      btn.focus();
    }}
  }});

  // Send message
  function sendMessage() {{
    var text = chatInput.value.trim();
    if (!text) return;
    chatInput.value = '';

    // User bubble
    var userDiv = parentDoc.createElement('div');
    userDiv.className = 'ss-chat-msg-user';
    userDiv.textContent = text;
    msgs.appendChild(userDiv);

    // Spinner
    var spinner = parentDoc.createElement('div');
    spinner.className = 'ss-chat-msg-bot ss-chat-spinner';
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
      if (msgs.contains(spinner)) msgs.removeChild(spinner);
      var reply = '';
      if (data.success) {{
        // ChatResponse has intent and response at top level
        var intent = data.intent || 'general';
        var resp = data.response || {{}};
        // Update session ID from server
        if (data.session_id) {{
          sessionId = data.session_id;
          parentWin.sessionStorage.setItem('smartshop_session_id', sessionId);
        }}
        if (intent === 'general') {{
          reply = resp.answer || 'I am not sure how to help with that.';
        }} else if (intent === 'policy') {{
          reply = resp.answer || 'No policy information found.';
        }} else if (intent === 'price') {{
          reply = (resp.best_deal ? '\\uD83C\\uDFC6 Best Deal: ' + resp.best_deal + '\\n\\n' : '') +
                  (resp.recommendation || 'No comparison data.');
        }} else if (intent === 'recommendation' || intent === 'comparison') {{
          var recs = resp.recommendations || [];
          if (recs.length > 0) {{
            reply = (resp.reasoning_summary ? resp.reasoning_summary + '\\n\\n' : '');
            recs.forEach(function(r, i) {{
              reply += (i+1) + '. ' + (r.name || r.product_id || 'Product') +
                       (r.price ? ' - $' + r.price : '') +
                       (r.reason ? '\\n   ' + r.reason : '') + '\\n';
            }});
          }} else {{
            reply = resp.reasoning_summary || 'No recommendations found.';
          }}
        }} else if (intent === 'review') {{
          reply = resp.overall_summary || resp.summary || 'No review summary available.';
          if (resp.average_rating) {{
            reply = '\\u2B50 ' + resp.average_rating.toFixed(1) + '/5 (' + (resp.total_reviews || 0) + ' reviews)\\n\\n' + reply;
          }}
        }} else {{
          reply = resp.answer || resp.reasoning_summary || JSON.stringify(resp).substring(0, 300);
        }}
      }} else {{
        reply = '\\u26A0\\uFE0F ' + (data.error || data.detail || 'Something went wrong.');
      }}
      var botDiv = parentDoc.createElement('div');
      botDiv.className = 'ss-chat-msg-bot';
      botDiv.textContent = reply;
      msgs.appendChild(botDiv);
      msgs.scrollTop = msgs.scrollHeight;
    }})
    .catch(function(err) {{
      if (msgs.contains(spinner)) msgs.removeChild(spinner);
      var errDiv = parentDoc.createElement('div');
      errDiv.className = 'ss-chat-msg-bot';
      errDiv.textContent = '\\u26A0\\uFE0F Could not connect to assistant.';
      msgs.appendChild(errDiv);
      msgs.scrollTop = msgs.scrollHeight;
    }});
  }}

  sendBtn.addEventListener('click', sendMessage);
  chatInput.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') sendMessage();
  }});
}})();
</script>
"""
