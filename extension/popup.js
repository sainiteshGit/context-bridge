/**
 * Context Bridge — Browser Extension Popup
 *
 * Thin UI layer that talks to the Python API.
 * No business logic here — just fetch calls and DOM updates.
 */

const $ = (sel) => document.querySelector(sel);

// ─── State ───────────────────────────────────────────────────

let config = { apiUrl: "", userId: "" };

// ─── Init ────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  const stored = await chrome.storage.local.get(["apiUrl", "userId"]);
  if (stored.apiUrl && stored.userId) {
    config.apiUrl = stored.apiUrl;
    config.userId = stored.userId;
    await connect();
  }

  $("#connect-btn").addEventListener("click", onConnect);
  $("#disconnect-btn").addEventListener("click", onDisconnect);
  $("#add-fact-btn").addEventListener("click", onAddFact);
});

// ─── Connection ──────────────────────────────────────────────

async function onConnect() {
  const apiUrl = $("#api-url").value.replace(/\/+$/, "");
  const userId = $("#user-id").value.trim();

  if (!apiUrl || !userId) {
    showToast("Please fill in both fields");
    return;
  }

  config = { apiUrl, userId };
  await chrome.storage.local.set(config);
  await connect();
}

async function connect() {
  try {
    const res = await fetch(`${config.apiUrl}/health`);
    if (!res.ok) throw new Error("API unreachable");

    setConnected(true);
    await refreshDashboard();
  } catch (err) {
    setConnected(false);
    showToast("Cannot reach API: " + err.message);
  }
}

function onDisconnect() {
  chrome.storage.local.remove(["apiUrl", "userId"]);
  config = { apiUrl: "", userId: "" };
  setConnected(false);
}

function setConnected(connected) {
  const bar = $("#status-bar");
  const text = $("#status-text");

  if (connected) {
    bar.className = "status connected";
    text.textContent = "Connected";
    $("#setup-section").classList.add("hidden");
    $("#dashboard-section").classList.remove("hidden");
  } else {
    bar.className = "status disconnected";
    text.textContent = "Disconnected";
    $("#setup-section").classList.remove("hidden");
    $("#dashboard-section").classList.add("hidden");
  }
}

// ─── Dashboard ───────────────────────────────────────────────

async function refreshDashboard() {
  try {
    // Fetch counts
    const countRes = await api(`/api/v1/users/${config.userId}/facts/count`);
    $("#fact-count").textContent = countRes.count || 0;

    // Fetch snapshots for category count
    const snapshots = await api(`/api/v1/users/${config.userId}/facts/snapshots`);
    const activeCats = snapshots.filter((s) => s.fact_count > 0).length;
    $("#category-count").textContent = activeCats;

    // Fetch apps
    const apps = await api("/api/v1/apps");
    $("#app-count").textContent = apps.length || 0;

    // Fetch recent facts
    const facts = await api(`/api/v1/users/${config.userId}/facts?limit=10`);
    renderFacts(facts);
  } catch (err) {
    showToast("Error loading data");
  }
}

function renderFacts(facts) {
  const list = $("#facts-list");
  list.innerHTML = "";

  if (!facts.length) {
    list.innerHTML = '<li style="color:var(--text-muted)">No facts yet — add one above!</li>';
    return;
  }

  for (const fact of facts) {
    const li = document.createElement("li");
    li.innerHTML = `
      <span>
        <span class="fact-key">${esc(fact.key)}</span>
        <span class="fact-category">${esc(fact.category)}</span>
      </span>
      <span class="fact-value">${esc(truncate(fact.value, 30))}</span>
    `;
    list.appendChild(li);
  }
}

// ─── Add Fact ────────────────────────────────────────────────

async function onAddFact() {
  const category = $("#fact-category").value;
  const key = $("#fact-key").value.trim();
  const value = $("#fact-value").value.trim();

  if (!key || !value) {
    showToast("Key and value are required");
    return;
  }

  try {
    await api(`/api/v1/users/${config.userId}/facts`, {
      method: "POST",
      body: JSON.stringify({ category, key, value }),
    });

    $("#fact-key").value = "";
    $("#fact-value").value = "";
    showToast("Fact added!");
    await refreshDashboard();
  } catch (err) {
    showToast("Error: " + err.message);
  }
}

// ─── Helpers ─────────────────────────────────────────────────

async function api(path, options = {}) {
  const res = await fetch(`${config.apiUrl}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }

  if (res.status === 204) return null;
  return res.json();
}

function showToast(msg) {
  const toast = $("#toast");
  toast.textContent = msg;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 2500);
}

function esc(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function truncate(str, len) {
  return str.length > len ? str.slice(0, len) + "…" : str;
}
