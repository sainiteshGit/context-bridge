/**
 * Context Bridge — ChatGPT Content Script
 *
 * Injected into chatgpt.com / chat.openai.com.
 * Uses Shadow DOM so ChatGPT's React cannot remove our elements.
 * Adds a floating button + panel to inject personal context into chat.
 */

(() => {
  "use strict";

  // ─── Shadow DOM Host (React-proof) ──────────────────────

  function ensureHost() {
    let host = document.getElementById("cb-shadow-host");
    if (host) return host;

    host = document.createElement("div");
    host.id = "cb-shadow-host";
    // Make host invisible to React — place outside main content
    host.style.cssText =
      "position:fixed;top:0;left:0;width:0;height:0;overflow:visible;z-index:2147483647;pointer-events:none;";
    document.documentElement.appendChild(host);
    return host;
  }

  const host = ensureHost();

  // Prevent double init
  if (host.shadowRoot) return;

  const shadow = host.attachShadow({ mode: "open" });

  // ─── Inject styles into shadow DOM ───────────────────────

  const style = document.createElement("style");
  style.textContent = `
    * { box-sizing: border-box; margin: 0; padding: 0; }

    #cb-floating-btn {
      position: fixed;
      bottom: 90px;
      right: 24px;
      width: 48px;
      height: 48px;
      border-radius: 50%;
      border: 2px solid #e94560;
      background: #1a1a2e;
      color: white;
      font-size: 22px;
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(233,69,96,0.35);
      transition: transform 0.2s, box-shadow 0.2s;
      display: flex;
      align-items: center;
      justify-content: center;
      pointer-events: auto;
      z-index: 2147483647;
    }
    #cb-floating-btn:hover {
      transform: scale(1.1);
      box-shadow: 0 6px 24px rgba(233,69,96,0.5);
    }

    #cb-panel {
      position: fixed;
      bottom: 150px;
      right: 24px;
      width: 360px;
      max-height: 480px;
      background: #1a1a2e;
      border: 1px solid #2a2a4a;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: #eee;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      pointer-events: auto;
      z-index: 2147483647;
    }
    #cb-panel.cb-hidden { display: none !important; }

    .cb-panel-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 12px 16px; border-bottom: 1px solid #2a2a4a; background: #16213e;
    }
    .cb-panel-title { font-size: 14px; font-weight: 700; }
    .cb-close-btn {
      background: none; border: none; color: #999; font-size: 20px;
      cursor: pointer; padding: 0 4px; line-height: 1;
    }
    .cb-close-btn:hover { color: #e94560; }

    .cb-panel-body { padding: 12px 16px; overflow-y: auto; flex: 1; }
    .cb-status { font-size: 12px; color: #999; margin-bottom: 10px; }

    .cb-categories { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
    .cb-badge {
      background: #0f3460; color: #eee; font-size: 11px;
      padding: 3px 8px; border-radius: 12px; white-space: nowrap;
    }
    .cb-badge small { color: #e94560; font-weight: 700; }

    .cb-preview { margin-top: 8px; }
    .cb-label {
      display: block; font-size: 10px; text-transform: uppercase;
      color: #999; letter-spacing: 0.5px; margin-bottom: 4px;
    }
    #cb-context-text {
      width: 100%; min-height: 100px; padding: 8px 10px;
      border: 1px solid #2a2a4a; border-radius: 8px;
      background: #16213e; color: #eee; font-size: 12px;
      font-family: inherit; resize: vertical; outline: none; line-height: 1.5;
    }
    #cb-context-text:focus { border-color: #e94560; }

    .cb-panel-footer {
      display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid #2a2a4a;
    }
    .cb-btn {
      flex: 1; padding: 8px 12px; border-radius: 8px; font-size: 12px;
      font-weight: 600; cursor: pointer; border: none; transition: opacity 0.2s;
    }
    .cb-btn:hover { opacity: 0.9; }
    .cb-btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .cb-btn-load { background: #0f3460; color: white; }
    .cb-btn-inject { background: #e94560; color: white; }
    .cb-btn-sync { background: #533483; color: white; }

    .cb-sync-status {
      font-size: 11px; color: #999; padding: 4px 16px 0;
      text-align: center; min-height: 0;
      transition: all 0.2s;
    }
    .cb-sync-status.cb-success { color: #4ecca3; }
    .cb-sync-status.cb-error { color: #e94560; }

    .cb-hidden { display: none !important; }
  `;
  shadow.appendChild(style);

  // ─── State ───────────────────────────────────────────────

  let contextText = "";
  let isLoading = false;

  // ─── Create Floating Button ──────────────────────────────

  const btn = document.createElement("button");
  btn.id = "cb-floating-btn";
  btn.title = "Inject your Context Bridge preferences";
  btn.innerHTML = "🌉";
  shadow.appendChild(btn);

  // ─── Create Context Panel ────────────────────────────────

  const panel = document.createElement("div");
  panel.id = "cb-panel";
  panel.classList.add("cb-hidden");
  panel.innerHTML = `
    <div class="cb-panel-header">
      <span class="cb-panel-title">🌉 Context Bridge</span>
      <button class="cb-close-btn">&times;</button>
    </div>
    <div class="cb-panel-body">
      <p class="cb-status" id="cb-status">Click "Load Context" to fetch your preferences.</p>
      <div class="cb-categories" id="cb-categories"></div>
      <div class="cb-preview cb-hidden" id="cb-preview">
        <label class="cb-label">Preview (editable)</label>
        <textarea id="cb-context-text" rows="6"></textarea>
      </div>
    </div>
    <div class="cb-sync-status cb-hidden" id="cb-sync-status"></div>
    <div class="cb-panel-footer">
      <button class="cb-btn cb-btn-load" id="cb-load-btn">Load Context</button>
      <button class="cb-btn cb-btn-inject cb-hidden" id="cb-inject-btn">Inject into Chat</button>
      <button class="cb-btn cb-btn-sync" id="cb-sync-btn">Sync Chat</button>
    </div>
  `;
  shadow.appendChild(panel);

  // ─── Event Handlers ──────────────────────────────────────

  btn.addEventListener("click", () => {
    panel.classList.toggle("cb-hidden");
  });

  panel.querySelector(".cb-close-btn").addEventListener("click", () => {
    panel.classList.add("cb-hidden");
  });

  const loadBtn = shadow.querySelector("#cb-load-btn");
  const injectBtn = shadow.querySelector("#cb-inject-btn");
  const syncBtn = shadow.querySelector("#cb-sync-btn");
  const statusEl = shadow.querySelector("#cb-status");
  const categoriesEl = shadow.querySelector("#cb-categories");
  const previewEl = shadow.querySelector("#cb-preview");
  const textArea = shadow.querySelector("#cb-context-text");
  const syncStatusEl = shadow.querySelector("#cb-sync-status");

  loadBtn.addEventListener("click", loadContext);
  injectBtn.addEventListener("click", injectContext);
  syncBtn.addEventListener("click", syncChat);

  // ─── Load Context from API via Background ────────────────

  async function loadContext() {
    if (isLoading) return;
    isLoading = true;
    loadBtn.textContent = "Loading…";
    loadBtn.disabled = true;
    statusEl.textContent = "Fetching your context…";

    try {
      const response = await chrome.runtime.sendMessage({
        type: "FETCH_CONTEXT",
      });

      if (response.error) {
        statusEl.textContent = "Error: " + response.error;
        return;
      }

      const { snapshots, user } = response;

      if (!snapshots || snapshots.length === 0) {
        statusEl.textContent = "No context found. Add facts via the popup first.";
        return;
      }

      // Render category badges
      const activeCats = snapshots.filter((s) => s.fact_count > 0);
      categoriesEl.innerHTML = activeCats
        .map(
          (s) =>
            `<span class="cb-badge">${esc(s.category)} <small>(${s.fact_count})</small></span>`
        )
        .join("");

      // Build context text
      contextText = buildContextPrompt(snapshots, user);
      textArea.value = contextText;

      statusEl.textContent = `Loaded ${activeCats.length} categories with context.`;
      previewEl.classList.remove("cb-hidden");
      injectBtn.classList.remove("cb-hidden");
      loadBtn.textContent = "Reload";
    } catch (err) {
      statusEl.textContent = "Failed to load: " + err.message;
    } finally {
      isLoading = false;
      loadBtn.disabled = false;
    }
  }

  // ─── Build the context prompt ────────────────────────────

  function buildContextPrompt(snapshots, user) {
    let parts = [];

    parts.push(
      "Here is some personal context about me. Use it to personalize your responses:\n"
    );

    if (user && user.display_name) {
      parts.push(`My name: ${user.display_name}`);
    }

    for (const snap of snapshots) {
      if (!snap.facts || snap.facts.length === 0) continue;

      const catName = snap.category.replace(/_/g, " ");
      parts.push(`\n## ${catName.charAt(0).toUpperCase() + catName.slice(1)}`);

      for (const fact of snap.facts) {
        parts.push(`- ${fact.key}: ${fact.value}`);
      }
    }

    return parts.join("\n");
  }

  // ─── Inject into ChatGPT Input ───────────────────────────

  function injectContext() {
    const finalText = textArea.value.trim();
    if (!finalText) {
      statusEl.textContent = "Nothing to inject — load context first.";
      return;
    }

    // ChatGPT input is in the main document, not our shadow DOM
    const inputEl = findChatInput();

    if (!inputEl) {
      statusEl.textContent =
        "Could not find the ChatGPT input box. Try clicking on it first.";
      return;
    }

    // Insert text
    if (inputEl.tagName === "TEXTAREA") {
      const nativeSet = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        "value"
      ).set;
      nativeSet.call(inputEl, finalText + "\n\n");
      inputEl.dispatchEvent(new Event("input", { bubbles: true }));
    } else {
      // ProseMirror / contenteditable
      inputEl.focus();
      document.execCommand("selectAll", false, null);
      document.execCommand("insertText", false, finalText + "\n\n");
    }

    statusEl.textContent = "✅ Context injected! Type your question after it.";
    panel.classList.add("cb-hidden");
    inputEl.focus();

    // Place cursor at end
    const range = document.createRange();
    const sel = window.getSelection();
    if (inputEl.lastChild) {
      range.setStartAfter(inputEl.lastChild);
      range.collapse(true);
      sel.removeAllRanges();
      sel.addRange(range);
    }
  }

  // ─── Helpers ─────────────────────────────────────────────

  /**
   * Detect which site we are on.
   */
  function detectSource() {
    const host = window.location.hostname;
    if (host.includes("chatgpt") || host.includes("openai")) return "chatgpt";
    if (host.includes("perplexity")) return "perplexity";
    return "unknown";
  }

  /**
   * Extract chat messages from the current page DOM.
   * Returns array of { role: "user"|"assistant", text: string }.
   * Uses multiple selector strategies to handle DOM changes.
   */
  function extractChatMessages() {
    const source = detectSource();
    const messages = [];

    if (source === "chatgpt") {
      // Strategy 1: data-message-author-role (classic)
      let msgEls = document.querySelectorAll("[data-message-author-role]");
      if (msgEls.length > 0) {
        msgEls.forEach((el) => {
          const role = el.getAttribute("data-message-author-role");
          const text = el.innerText.trim();
          if (text) {
            messages.push({ role: role === "user" ? "user" : "assistant", text });
          }
        });
        return messages;
      }

      // Strategy 2: conversation turns with data-testid
      const turns = document.querySelectorAll("[data-testid^='conversation-turn-']");
      if (turns.length > 0) {
        turns.forEach((el) => {
          const text = el.innerText.trim();
          if (text) {
            // Extract turn number from data-testid to determine role
            const testId = el.getAttribute("data-testid") || "";
            const turnNum = parseInt(testId.replace("conversation-turn-", ""), 10);
            messages.push({ role: turnNum % 2 === 0 ? "user" : "assistant", text });
          }
        });
        return messages;
      }

      // Strategy 3: article elements inside main
      const articles = document.querySelectorAll("main article");
      if (articles.length > 0) {
        articles.forEach((el) => {
          const text = el.innerText.trim();
          if (text) {
            messages.push({ role: messages.length % 2 === 0 ? "user" : "assistant", text });
          }
        });
        return messages;
      }

      // Strategy 4: grouped message containers (recent ChatGPT layouts)
      const groups = document.querySelectorAll(
        "main .group\\/conversation-turn, main [class*='ConversationItem'], main [class*='message']"
      );
      if (groups.length > 0) {
        groups.forEach((el) => {
          const text = el.innerText.trim();
          if (text) {
            messages.push({ role: messages.length % 2 === 0 ? "user" : "assistant", text });
          }
        });
        return messages;
      }

      // Strategy 5: brute force — grab all direct children of the chat thread
      const threadContainer = document.querySelector(
        "main .flex.flex-col, main [class*='thread'], main [role='presentation']"
      );
      if (threadContainer) {
        const children = threadContainer.children;
        for (let i = 0; i < children.length; i++) {
          const text = children[i].innerText.trim();
          if (text && text.length > 5) {
            messages.push({ role: i % 2 === 0 ? "user" : "assistant", text });
          }
        }
      }

    } else if (source === "perplexity") {
      // Perplexity: each answer thread is a block
      // Strategy 1: question headings + answer prose
      const threadBlocks = document.querySelectorAll(
        "[class*='ThreadMessage'], [class*='AnswerBlock'], [class*='ConversationPair']"
      );
      if (threadBlocks.length > 0) {
        threadBlocks.forEach((el) => {
          const text = el.innerText.trim();
          if (text) {
            messages.push({ role: messages.length % 2 === 0 ? "user" : "assistant", text });
          }
        });
        return messages;
      }

      // Strategy 2: query elements + answer elements
      const allBlocks = document.querySelectorAll(
        "main [class*='query'], main [class*='Query'], main h1, " +
        "main [class*='answer'], main [class*='Answer'], main [class*='prose']"
      );
      allBlocks.forEach((el) => {
        const text = el.innerText.trim();
        const cls = (el.className || "").toLowerCase();
        if (text) {
          const isQuery = cls.includes("query") || el.tagName === "H1";
          messages.push({ role: isQuery ? "user" : "assistant", text });
        }
      });
    }

    return messages;
  }

  /**
   * Convert extracted messages into fact payloads for the API.
   * Only user messages are synced — they represent the user's actual context.
   */
  function messagesToFacts(messages, source) {
    const now = new Date().toISOString().slice(0, 19).replace("T", " ");
    const userMessages = messages.filter((m) => m.role === "user");

    return userMessages.map((msg, i) => ({
      category: "profile",
      key: `chat-${source}-${now}-${i + 1}`,
      value: msg.text.slice(0, 2000), // cap at 2000 chars per fact
      sensitivity: "low",
    }));
  }

  // ─── Sync Chat Messages to API ───────────────────────────

  async function syncChat() {
    const source = detectSource();
    console.log("[Context Bridge] Sync started, source:", source);

    syncStatusEl.textContent = "Extracting messages…";
    syncStatusEl.className = "cb-sync-status";
    syncStatusEl.classList.remove("cb-hidden");
    syncBtn.disabled = true;
    syncBtn.textContent = "Syncing…";

    try {
      const messages = extractChatMessages();
      console.log("[Context Bridge] Extracted messages:", messages.length, messages);

      if (messages.length === 0) {
        syncStatusEl.textContent = "No chat messages found on this page.";
        syncStatusEl.classList.add("cb-error");
        return;
      }

      const facts = messagesToFacts(messages, source);

      syncStatusEl.textContent = `Found ${messages.length} messages, syncing ${facts.length} user facts…`;

      const response = await chrome.runtime.sendMessage({
        type: "SYNC_CHAT",
        payload: { messages: facts, source },
      });

      if (response.error) {
        syncStatusEl.textContent = "Error: " + response.error;
        syncStatusEl.classList.add("cb-error");
        return;
      }

      syncStatusEl.textContent =
        `✅ Synced ${response.synced}/${response.total} facts from ${source}.` +
        (response.errors.length > 0
          ? ` (${response.errors.length} failed)`
          : "");
      syncStatusEl.classList.add("cb-success");
    } catch (err) {
      syncStatusEl.textContent = "Sync failed: " + err.message;
      syncStatusEl.classList.add("cb-error");
    } finally {
      syncBtn.disabled = false;
      syncBtn.textContent = "Sync Chat";
    }
  }

  function findChatInput() {
    // ChatGPT: ProseMirror editor
    const proseMirror = document.querySelector(
      "#prompt-textarea, div[contenteditable='true'].ProseMirror"
    );
    if (proseMirror) return proseMirror;

    // Perplexity: textarea in the search/ask area
    const perplexityTA = document.querySelector(
      "textarea[placeholder*='Ask'], textarea[placeholder*='ask'], textarea[placeholder*='Search'], textarea[placeholder*='search']"
    );
    if (perplexityTA) return perplexityTA;

    // Generic: any contenteditable in main area
    const editable = document.querySelector(
      "main div[contenteditable='true']"
    );
    if (editable) return editable;

    // Fallback: any textarea in main
    const textarea = document.querySelector("main textarea");
    if (textarea) return textarea;

    // Last resort: any visible textarea on page
    const anyTA = document.querySelector("textarea");
    if (anyTA) return anyTA;

    return null;
  }

  function esc(str) {
    const div = document.createElement("span");
    div.textContent = str;
    return div.innerHTML;
  }
})();
