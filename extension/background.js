/**
 * Context Bridge — Background Service Worker
 *
 * Handles extension lifecycle events.
 * Keeps connection config in chrome.storage.local.
 * Proxies API requests from content scripts (which can't call localhost directly).
 */

chrome.runtime.onInstalled.addListener(() => {
  console.log("Context Bridge extension installed");
});

// Listen for messages from popup or content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_CONFIG") {
    chrome.storage.local.get(["apiUrl", "userId"], (config) => {
      sendResponse(config);
    });
    return true; // keep channel open for async response
  }

  if (message.type === "FETCH_CONTEXT") {
    handleFetchContext().then(sendResponse).catch((err) => {
      sendResponse({ error: err.message });
    });
    return true; // async
  }

  if (message.type === "SYNC_CHAT") {
    handleSyncChat(message.payload)
      .then(sendResponse)
      .catch((err) => {
        sendResponse({ error: err.message });
      });
    return true; // async
  }
});

/**
 * Fetch the user's full context (all snapshots) from the API.
 * Called by the content script on chatgpt.com.
 */
async function handleFetchContext() {
  const config = await chrome.storage.local.get(["apiUrl", "userId"]);

  if (!config.apiUrl || !config.userId) {
    return {
      error:
        "Not configured. Open the Context Bridge popup and connect first.",
    };
  }

  const { apiUrl, userId } = config;

  // Check API is reachable
  const healthRes = await fetch(`${apiUrl}/health`);
  if (!healthRes.ok) {
    return { error: "API unreachable at " + apiUrl };
  }

  // Fetch all snapshots
  const snapRes = await fetch(
    `${apiUrl}/api/v1/users/${userId}/facts/snapshots`,
    { headers: { "Content-Type": "application/json" } }
  );

  if (!snapRes.ok) {
    const body = await snapRes.json().catch(() => ({}));
    return { error: body.detail || `HTTP ${snapRes.status}` };
  }

  const snapshots = await snapRes.json();

  // Optionally fetch user profile
  let user = null;
  try {
    const userRes = await fetch(`${apiUrl}/api/v1/users/${userId}`, {
      headers: { "Content-Type": "application/json" },
    });
    if (userRes.ok) {
      user = await userRes.json();
    }
  } catch (_) {
    // user profile is optional
  }

  return { snapshots, user };
}

/**
 * Sync chat messages back to the Context Bridge API as context facts.
 * Each message becomes a fact under the PROFILE category with source tracking.
 */
async function handleSyncChat(payload) {
  const config = await chrome.storage.local.get(["apiUrl", "userId"]);

  if (!config.apiUrl || !config.userId) {
    return { error: "Not configured. Open the Context Bridge popup and connect first." };
  }

  const { apiUrl, userId } = config;
  const { messages, source } = payload;

  if (!messages || messages.length === 0) {
    return { error: "No messages found to sync." };
  }

  let synced = 0;
  const errors = [];

  for (const msg of messages) {
    try {
      const res = await fetch(`${apiUrl}/api/v1/users/${userId}/facts/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category: msg.category || "profile",
          key: msg.key,
          value: msg.value,
          sensitivity: msg.sensitivity || "low",
          source: source || "chat",
          confidence: 0.7,
          tags: ["synced-from-chat", source || "chat"],
        }),
      });

      if (res.ok) {
        synced++;
      } else {
        const body = await res.json().catch(() => ({}));
        errors.push(body.detail || `HTTP ${res.status}`);
      }
    } catch (err) {
      errors.push(err.message);
    }
  }

  return { synced, total: messages.length, errors };
}
