/**
 * app.js -- Workspaces frontend
 * All data flows through the Flask API. No hardcoded mock data here.
 */

"use strict";

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  isDark:           false,
  scannedApps:      [],
  savedWorkspaces:  [],
  currentWS:        null,
  pendingManual:    [],   // items staged in the manual-add panel (new workspace flow)
  settings:         {
    auto_detect_browser_tabs: true,
    show_system_apps: true,
    auto_save_on_toggle: true,
    dark_mode: false,
  },
};

async function fetchSettings() {
  const res = await api("GET", "/api/settings");
  if (!res.ok || !res.data) return { ...state.settings };
  return {
    auto_detect_browser_tabs: res.data.auto_detect_browser_tabs !== false,
    show_system_apps: res.data.show_system_apps !== false,
    auto_save_on_toggle: res.data.auto_save_on_toggle !== false,
    dark_mode: res.data.dark_mode === true,
  };
}

async function persistSettings(partial = null) {
  if (partial && typeof partial === "object") {
    state.settings = { ...state.settings, ...partial };
  }
  const res = await api("POST", "/api/settings", { settings: state.settings });
  if (res.ok && res.data) {
    state.settings = {
      auto_detect_browser_tabs: res.data.auto_detect_browser_tabs !== false,
      show_system_apps: res.data.show_system_apps !== false,
      auto_save_on_toggle: res.data.auto_save_on_toggle !== false,
      dark_mode: res.data.dark_mode === true,
    };
  }
}

function setToggleState(el, isOn) {
  if (!el) return;
  el.classList.toggle("on", isOn);
  const knob = el.querySelector(".tgl-k");
  if (knob) knob.style.left = isOn ? "18px" : "2px";
}

async function handleSettingToggle(key, el) {
  if (!el || !(key in state.settings)) return;
  const next = !el.classList.contains("on");
  state.settings[key] = next;
  setToggleState(el, next);
  await persistSettings();

  // Apply settings immediately when the relevant screen is visible.
  if ((key === "show_system_apps" || key === "auto_detect_browser_tabs") && document.getElementById("s-new").classList.contains("active")) {
    renderScannedList();
  }
  if ((key === "show_system_apps" || key === "auto_detect_browser_tabs") && document.getElementById("s-edit").classList.contains("active") && state.currentWS) {
    openEdit(state.currentWS.name);
  }
}

async function initSettingsUI() {
  state.settings = await fetchSettings();
  setToggleState(document.getElementById("set-auto-tabs"), state.settings.auto_detect_browser_tabs);
  setToggleState(document.getElementById("set-show-system"), state.settings.show_system_apps);
  setToggleState(document.getElementById("set-auto-save"), state.settings.auto_save_on_toggle);
  applyThemeState(state.settings.dark_mode === true);
  fetchVersionInfo();
}

async function fetchVersionInfo() {
  const versionEl = document.getElementById("app-version-lbl");
  if (!versionEl) return;
  try {
    const res = await api("GET", "/api/version");
    if (res && res.ok) {
      versionEl.textContent = res.version || "1.0.0";
      window.__WORKSPACES_RELEASE_URL = res.release_url || "https://github.com/Nidhe-esh/Workspaces/releases/latest";
      return;
    }
  } catch {
    // fall back to the built-in version label
  }
  versionEl.textContent = "1.0.0";
  window.__WORKSPACES_RELEASE_URL = "https://github.com/Nidhe-esh/Workspaces/releases/latest";
}

function checkForUpdates() {
  const url = window.__WORKSPACES_RELEASE_URL || "https://github.com/Nidhe-esh/Workspaces/releases/latest";
  window.open(url, "_blank", "noopener,noreferrer");
}

// ── API helper ────────────────────────────────────────────────────────────────
async function api(method, path, body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== null) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  const text = await res.text();
  let payload = {};

  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { ok: false, error: text };
    }
  }

  if (!res.ok && payload.ok !== false) {
    payload = { ok: false, error: payload.error || `HTTP ${res.status}` };
  }

  return payload;
}

function slugify(str) {
  return str.trim().replace(/\s+/g, "_").replace(/[^\w\-]/g, "");
}

function relDate(iso) {
  if (!iso) return "";
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (diff < 60)    return "just now";
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function appEmoji(name, itemType) {
  if (itemType === "website") return "🔗";
  const map = {
    chrome: "🌐", firefox: "🦊", edge: "🌐", vs_code: "💙", code: "💙",
    notion: "📝", spotify: "🎵", slack: "💬", discord: "🎮",
    figma: "🎨", obsidian: "💜", teams: "💼", zoom: "📹",
    nvidia: "🟩", settings: "⚙️", explorer: "📁", linear: "📋",
  };
  for (const [k, v] of Object.entries(map)) {
    if (name.toLowerCase().includes(k)) return v;
  }
  return "📦";
}

// ── Screen navigation ─────────────────────────────────────────────────────────
function show(id) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  document.querySelectorAll(".settings-row").forEach(r => r.classList.remove("settings-active"));

  document.getElementById("s-" + id).classList.add("active");

  const navMap = { new: "nav-new", saved: "nav-saved", edit: "nav-saved", confirm: "nav-saved" };
  if (navMap[id]) document.getElementById(navMap[id]).classList.add("active");
  if (id === "settings") document.getElementById("nav-settings").classList.add("settings-active");

  if (id === "saved") loadSavedWorkspaces();
}

// ── Theme ─────────────────────────────────────────────────────────────────────
function applyThemeState(isDark) {
  state.isDark = !!isDark;
  document.getElementById("app").classList.toggle("dark", state.isDark);
  document.body.classList.toggle("dark", state.isDark);
  document.body.style.background = state.isDark ? "#1a1a1a" : "#e0ddc8";
  const btn  = document.getElementById("themeBtn");
  const knob = document.getElementById("themeKnob");
  btn.classList.toggle("lit", !state.isDark);
  knob.textContent = state.isDark ? "◑" : "☀";
}

async function toggleTheme() {
  const next = !state.isDark;
  applyThemeState(next);
  state.settings.dark_mode = next;
  await persistSettings();
}

// ── Toggle ────────────────────────────────────────────────────────────────────
function tgl(el) {
  const next = !el.classList.contains("on");
  setToggleState(el, next);
}

function renderScannedList() {
  const msg  = document.getElementById("scan-msg");
  const list = document.getElementById("app-list");
  const showSystem = state.settings.show_system_apps;

  list.innerHTML = "";

  const user = state.scannedApps.filter(a => !a.is_system);
  const sys = state.scannedApps.filter(a => a.is_system);

  if (showSystem) {
    msg.innerHTML = `<span style="color:var(--green)">✓ ${user.length} apps · ${sys.length} system excluded</span>`;
  } else {
    msg.innerHTML = `<span style="color:var(--green)">✓ ${user.length} apps scanned</span>`;
  }

  user.forEach((a, i) => list.appendChild(buildScanCard(a, i, false)));

  if (showSystem && sys.length) {
    const div = document.createElement("div");
    div.className = "sys-div";
    div.textContent = `// ${sys.length} system app${sys.length !== 1 ? "s" : ""} detected, excluded`;
    list.appendChild(div);
    sys.forEach((a, i) => list.appendChild(buildScanCard(a, user.length + i, true)));
  }

  // Keep manually-added items below scanned cards.
  renderPendingManual();
}

// ── SCAN ──────────────────────────────────────────────────────────────────────
async function doScan() {
  const msg      = document.getElementById("scan-msg");
  const list     = document.getElementById("app-list");
  const saveZone = document.getElementById("save-zone");

  msg.innerHTML = '<span style="color:var(--blue)">scanning…</span>';
  list.innerHTML = "";
  saveZone.style.display = "none";

  const res = await api("POST", "/api/scan");
  if (!res.ok) {
    msg.innerHTML = `<span style="color:var(--red)">✗ ${res.error}</span>`;
    return;
  }

  state.scannedApps = res.data.apps || [];
  renderScannedList();
  saveZone.style.display = "block";
}

function buildScanCard(app, idx, isSystem) {
  const card = document.createElement("div");
  card.className = "app-card" + (isSystem ? " sys" : "");

  const isBrowser = ["chrome", "chromium", "firefox", "edge", "brave", "opera", "vivaldi", "thorium", "waterfox", "librewolf", "arc", "zen"].some(b => app.app_name.includes(b));
  const tabsSource = state.settings.auto_detect_browser_tabs ? (app.tabs || []) : [];
  const tabs = tabsSource.slice(0, 5);
  const more = tabsSource.length - 5;

  const tabsHTML = tabs.length
    ? `<div class="tab-row">
        ${tabs.map(t => `<div class="tab-i${isBrowser ? " bt" : ""}">${t}</div>`).join("")}
        ${more > 0 ? `<button class="more-link">+ ${more} more tabs →</button>` : ""}
       </div>`
    : "";

  const iconStyle = isSystem ? 'style="background:#ccc;border-color:#aaa"' : "";
  const tglLock   = isSystem ? 'style="cursor:not-allowed;opacity:.25"' : "";
  const isOn      = app.keep && !isSystem;

  const tglHTML = `
    <div class="tgl${isOn ? " on" : ""}" ${tglLock}
         onclick="state.scannedApps[${idx}].keep=!state.scannedApps[${idx}].keep;
                  this.classList.toggle('on');
                  this.querySelector('.tgl-k').style.left=this.classList.contains('on')?'18px':'2px'">
      <div class="tgl-k" style="left:${isOn ? "18" : "2"}px"></div>
    </div>`;

  card.innerHTML = `
    <div class="app-header">
      <div class="app-icon" ${iconStyle}>${appEmoji(app.app_name, app.item_type)}</div>
      <div class="app-meta">
        <div class="app-name">${app.app_name}</div>
        <div class="app-path">${app.exe_path}</div>
      </div>
      ${tglHTML}
    </div>
    ${tabsHTML}`;

  return card;
}

// ── MANUAL ADD PANEL (New Workspace) ─────────────────────────────────────────
function toggleAddPanel(ctx) {
  const panel = document.getElementById(`add-panel-${ctx}`);
  const btn   = document.getElementById(`btn-add-${ctx}`);
  const open  = panel.style.display === "none" || panel.style.display === "";
  panel.style.display = open ? "block" : "none";
  if (ctx === "new") {
    btn.textContent = open ? "[ + ADD MANUALLY ▲ ]" : "[ + ADD MANUALLY ]";
  } else {
    btn.textContent = open ? "[ + ADD MORE ▲ ]" : "[ + ADD MORE ]";
  }
}

function switchTab(ctx, tab) {
  ["app", "site"].forEach(t => {
    document.getElementById(`${ctx[0]}tab-${t}`).classList.toggle("on", t === tab);
    document.getElementById(`${ctx[0]}panel-${t}`).style.display = t === tab ? "block" : "none";
  });
}

// Stage a manual item in the New Workspace flow (not saved to disk yet)
function addManualNew() {
  const isApp   = document.getElementById("ntab-app").classList.contains("on");
  const nameEl  = document.getElementById("n-app-name");
  const pathEl  = document.getElementById("n-app-path");
  const urlEl   = document.getElementById("n-site-url");
  const labelEl = document.getElementById("n-site-label");

  let item;
  if (isApp) {
    const name = (nameEl.value || "").trim().replace(/\s+/g, "_").toLowerCase();
    if (!name) { nameEl.focus(); return; }
    item = {
      app_name: name, exe_path: (pathEl.value || "").trim(),
      is_system: false, keep: true, tabs: [], item_type: "app",
    };
    nameEl.value = pathEl.value = "";
  } else {
    const url   = (urlEl.value   || "").trim();
    const label = (labelEl.value || "").trim() || url;
    if (!url) { urlEl.focus(); return; }
    item = {
      app_name: label, exe_path: url, url,
      is_system: false, keep: true, tabs: [], item_type: "website",
    };
    urlEl.value = labelEl.value = "";
  }

  state.pendingManual.push(item);
  renderPendingManual();
}

function renderPendingManual() {
  const pillBox = document.getElementById("n-added-pills");
  pillBox.innerHTML = state.pendingManual.map((item, i) => `
    <div class="added-pill">
      ${item.item_type === "website" ? "🔗" : "📦"} ${item.app_name}
      <button onclick="state.pendingManual.splice(${i},1);renderPendingManual()">✕</button>
    </div>`).join("");

  // Also render them as cards in the app-list below scanned apps
  const existing = document.querySelectorAll("#app-list .manual-card");
  existing.forEach(c => c.remove());
  const list = document.getElementById("app-list");
  state.pendingManual.forEach(item => {
    const card = buildManualDisplayCard(item);
    list.appendChild(card);
  });
  
  // Show save button if items were added manually
  if (state.pendingManual.length > 0) {
    const saveZone = document.getElementById("save-zone");
    if (saveZone) saveZone.style.display = "block";
  }
}

function buildManualDisplayCard(item) {
  const card = document.createElement("div");
  card.className = "app-card manual-card" + (item.item_type === "website" ? " manual-website" : " manual-app");
  const tag = item.item_type === "website" ? "↑ manually added · website" : "↑ manually added · application";
  const nameClass = item.item_type === "website" ? ' class="app-name blue"' : ' class="app-name"';
  const iconClass = item.item_type === "website" ? ' class="app-icon blue-icon"' : ' class="app-icon"';
  card.innerHTML = `
    <div class="manual-tag">${tag}</div>
    <div class="app-header">
      <div${iconClass}>${appEmoji(item.app_name, item.item_type)}</div>
      <div class="app-meta">
        <div${nameClass}>${item.app_name}</div>
        <div class="app-path">${item.exe_path}</div>
      </div>
      <div class="tgl on"><div class="tgl-k" style="left:18px"></div></div>
    </div>`;
  return card;
}

// ── SAVE (New Workspace) ──────────────────────────────────────────────────────
async function saveWS() {
  const rawName = document.getElementById("ws-name-input").value.trim();
  const name    = slugify(rawName) || "untitled_workspace";
  const ok      = document.getElementById("save-ok");

  const apps = [
    ...state.scannedApps.filter(a => !a.is_system),
    ...state.pendingManual,
  ];

  const res = await api("POST", "/api/save", { name, apps });

  if (!res.ok) {
    ok.style.color = "var(--red)";
    ok.textContent = `✗ ${res.error}`;
  } else {
    const kept = apps.filter(a => a.keep).length;
    ok.style.color = "var(--green)";
    ok.textContent = `✓ "${name}" saved · ${kept} apps`;
    // Reset
    state.scannedApps   = [];
    state.pendingManual = [];
    document.getElementById("app-list").innerHTML    = "";
    document.getElementById("n-added-pills").innerHTML = "";
    document.getElementById("ws-name-input").value   = "";
    document.getElementById("save-zone").style.display = "none";
    document.getElementById("scan-msg").innerHTML    = "";
    // Close panel if open
    const panel = document.getElementById("add-panel-new");
    if (panel.style.display !== "none") toggleAddPanel("new");
  }

  ok.style.display = "block";
  setTimeout(() => (ok.style.display = "none"), 3500);
}

function buildDraftWorkspacePayload() {
  if (state.currentWS) {
    const name = document.getElementById("edit-ws-name").value.trim() || state.currentWS.name;
    return {
      name,
      apps: Array.isArray(state.currentWS.apps) ? state.currentWS.apps : [],
    };
  }

  const apps = [
    ...state.scannedApps.filter(a => !a.is_system),
    ...state.pendingManual,
  ];
  if (!apps.length) return null;

  const rawName = document.getElementById("ws-name-input").value.trim();
  const name = slugify(rawName) || "untitled_workspace";
  return { name, apps };
}

function persistDraftWorkspaceOnExit() {
  const payload = buildDraftWorkspacePayload();
  if (!payload) return;

  try {
    if (navigator.sendBeacon) {
      const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
      navigator.sendBeacon("/api/save", blob);
      return;
    }
  } catch {
    // Fall through to the fetch keepalive path below.
  }

  fetch("/api/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => {});
}

// ── SAVED WORKSPACES ──────────────────────────────────────────────────────────
async function loadSavedWorkspaces() {
  const grid = document.getElementById("ws-grid");
  grid.innerHTML = `<div style="font-size:11px;opacity:.4;font-family:var(--font)">loading…</div>`;

  const res = await api("GET", "/api/workspaces");
  if (!res.ok) {
    grid.innerHTML = `<div style="color:var(--red);font-size:11px">${res.error}</div>`;
    return;
  }

  state.savedWorkspaces = res.data || [];
  renderWSGrid(state.savedWorkspaces);
}

function renderWSGrid(list) {
  const grid = document.getElementById("ws-grid");
  if (!list.length) {
    grid.innerHTML = `<div style="font-size:11px;opacity:.4;grid-column:1/-1;font-family:var(--font)">
      No saved workspaces yet. Scan &amp; save one first.</div>`;
    return;
  }
  grid.innerHTML = list.map(ws => `
    <div class="ws-card" onclick="openEdit('${ws.name}')">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div class="ws-name">${ws.name}</div>
        <span class="tag">${(ws.apps || []).length} apps</span>
      </div>
      <div class="ws-meta">${relDate(ws.saved_at)}</div>
      <div class="ws-pills">
        ${(ws.apps || []).slice(0, 3).map(a => `<div class="pill">${a.app_name}</div>`).join("")}
        ${(ws.apps || []).length > 3 ? `<div class="pill">+${(ws.apps || []).length - 3}</div>` : ""}
      </div>
    </div>`).join("");
}

function filterWS(q) {
  renderWSGrid(state.savedWorkspaces.filter(ws =>
    ws.name.toLowerCase().includes(q.toLowerCase())
  ));
}

// ── EDIT MODE ─────────────────────────────────────────────────────────────────
function openEdit(name) {
  const ws = state.savedWorkspaces.find(w => w.name === name);
  if (!ws) return;
  state.currentWS = JSON.parse(JSON.stringify(ws)); // deep copy

  document.getElementById("edit-ws-name").value = ws.name;

  const container = document.getElementById("edit-app-list");
  container.innerHTML = "";

  const userApps = (ws.apps || []).filter(a => !a.is_system);
  const sysApps  = (ws.apps || []).filter(a =>  a.is_system);

  userApps.forEach((app, i) => container.appendChild(buildEditCard(app, i)));

  if (state.settings.show_system_apps && sysApps.length) {
    const div = document.createElement("div");
    div.className = "sys-div";
    div.textContent = "// system apps — detected, excluded";
    container.appendChild(div);
    sysApps.forEach(app => {
      const card = buildEditCard(app, -1);
      card.classList.add("sys");
      container.appendChild(card);
    });
  }

  // Reset add panel
  const addPanel = document.getElementById("add-panel-edit");
  if (addPanel.style.display !== "none") toggleAddPanel("edit");

  show("edit");
  document.getElementById("nav-saved").classList.add("active");
}

function buildEditCard(app, idx) {
  const card = document.createElement("div");
  const isManual = app.item_type === "app" || app.item_type === "website";
  card.className = "app-card" + (isManual ? (app.item_type === "website" ? " manual-website" : " manual-app") : "");

  const isBrowser = ["chrome", "firefox", "edge"].some(b => app.app_name.includes(b));
  const tabsSource = state.settings.auto_detect_browser_tabs ? (app.tabs || []) : [];
  const tabs = tabsSource.slice(0, 5);
  const more = tabsSource.length - 5;

  const tabsHTML = tabs.length
    ? `<div class="tab-row">
        ${tabs.map(t => `<div class="tab-i${isBrowser ? " bt" : ""}">${t}</div>`).join("")}
        ${more > 0 ? `<button class="more-link">+ ${more} more tabs →</button>` : ""}
       </div>`
    : "";

  const manualTag = app.item_type
    ? `<div class="manual-tag">↑ manually added · ${app.item_type}</div>`
    : "";
  const isSystem = app.is_system;
  const tglLock  = isSystem ? 'style="cursor:not-allowed;opacity:.25"' : "";
  const isOn     = app.keep !== false && !isSystem;
  const nameClass = app.item_type === "website" ? ' class="app-name blue"' : ' class="app-name"';
  const iconClass = app.item_type === "website" ? ' class="app-icon blue-icon"' : ' class="app-icon"';

  const tglHTML = `
    <div class="tgl${isOn ? " on" : ""}" ${tglLock}
         onclick="${idx >= 0 ? `toggleEditKeep(${idx}, this)` : ""}">
      <div class="tgl-k" style="left:${isOn ? "18" : "2"}px"></div>
    </div>`;

  card.innerHTML = `
    ${manualTag}
    <div class="app-header">
      <div${iconClass}>${appEmoji(app.app_name, app.item_type)}</div>
      <div class="app-meta">
        <div${nameClass}>${app.app_name}</div>
        <div class="app-path">${app.exe_path || app.url || ""}</div>
      </div>
      ${tglHTML}
    </div>
    ${tabsHTML}`;

  return card;
}

function toggleEditKeep(idx, el) {
  if (!state.currentWS || !state.currentWS.apps || !state.currentWS.apps[idx]) return;
  state.currentWS.apps[idx].keep = !state.currentWS.apps[idx].keep;
  setToggleState(el, !!state.currentWS.apps[idx].keep);
  if (state.settings.auto_save_on_toggle) autoSaveEdit();
}

// Manual add inside Edit mode -- calls API immediately
async function addManualEdit() {
  if (!state.currentWS) return;

  const isApp   = document.getElementById("etab-app").classList.contains("on");
  const nameEl  = document.getElementById("e-app-name");
  const pathEl  = document.getElementById("e-app-path");
  const urlEl   = document.getElementById("e-site-url");
  const labelEl = document.getElementById("e-site-label");

  let body;
  if (isApp) {
    const name = (nameEl.value || "").trim();
    if (!name) { nameEl.focus(); return; }
    body = { type: "app", app_name: name, exe_path: (pathEl.value || "").trim() };
    nameEl.value = pathEl.value = "";
  } else {
    const url   = (urlEl.value   || "").trim();
    const label = (labelEl.value || "").trim();
    if (!url) { urlEl.focus(); return; }
    body = { type: "website", url, label };
    urlEl.value = labelEl.value = "";
  }

  const res = await api("POST", `/api/workspace/${encodeURIComponent(state.currentWS.name)}/add-item`, body);
  if (!res.ok) { alert(`Add failed: ${res.error}`); return; }

  // Append new card to edit list
  const item = res.item;
  state.currentWS.apps.push(item);
  const container  = document.getElementById("edit-app-list");
  const sysDiv     = container.querySelector(".sys-div");
  const card       = buildEditCard(item, state.currentWS.apps.length - 1);
  container.insertBefore(card, sysDiv || null);

  // Close the panel
  toggleAddPanel("edit");

  // Flash autosave badge
  const badge = document.getElementById("autosave-badge");
  badge.style.opacity = "1";
  setTimeout(() => (badge.style.opacity = ".6"), 900);
}

async function autoSaveEdit() {
  if (!state.currentWS) return;
  const name = document.getElementById("edit-ws-name").value.trim() || state.currentWS.name;
  await api("POST", "/api/save", { name, apps: state.currentWS.apps });
  const badge = document.getElementById("autosave-badge");
  badge.style.opacity = "1";
  setTimeout(() => (badge.style.opacity = ".6"), 900);
}

async function deleteWS() {
  if (!state.currentWS) return;
  const ok = await showAppConfirm({
    title: "DELETE_WORKSPACE",
    message: `Delete "${state.currentWS.name}"? This cannot be undone.`,
    okLabel: "[ DELETE ]",
  });
  if (!ok) return;
  const res = await api("DELETE", `/api/workspace/${encodeURIComponent(state.currentWS.name)}`);
  if (res.ok) { state.currentWS = null; show("saved"); }
  else alert(`Delete failed: ${res.error}`);
}

// ── RESTORE ───────────────────────────────────────────────────────────────────
function showConfirm() {
  if (!state.currentWS) return;

  const apps    = (state.currentWS.apps || []).filter(a => !a.is_system);
  const kept    = apps.filter(a => a.keep !== false);
  const skipped = apps.filter(a => a.keep === false);

  document.getElementById("restore-ws-title").textContent =
    `RESTORE: "${state.currentWS.name}"?`;

  document.getElementById("restore-list").innerHTML =
    kept.map(a => `
      <div class="restore-item">
        <div class="r-icon">${appEmoji(a.app_name, a.item_type)}</div>
        <div>
          <div style="font-weight:700;font-size:12px">${a.app_name}</div>
          <div style="font-size:9.5px;opacity:.4;margin-top:1px">
            ${a.tabs && a.tabs.length ? `${a.tabs.length} tabs` : a.item_type === "website" ? "open in browser" : "launches app"}
          </div>
        </div>
      </div>`).join("") +
    skipped.map(a => `
      <div class="restore-item" style="opacity:.28">
        <div class="r-icon">${appEmoji(a.app_name, a.item_type)}</div>
        <div style="font-size:11.5px">${a.app_name} — skipped (toggled off)</div>
      </div>`).join("");

  document.getElementById("restore-prog").style.display  = "none";
  document.getElementById("restore-btns").style.display  = "flex";
  document.getElementById("restore-done").style.display  = "none";
  document.getElementById("prog-bar").style.width        = "0";
  document.getElementById("restore-done").style.color    = "var(--green)";
  document.getElementById("restore-done").textContent    = "✓ ALL APPS LAUNCHED SUCCESSFULLY";

  show("confirm");
  document.getElementById("nav-saved").classList.add("active");
}

async function runRestore() {
  if (!state.currentWS) return;

  const apps = (state.currentWS.apps || []).filter(a => !a.is_system && a.keep !== false);
  if (!apps.length) {
    const done = document.getElementById("restore-done");
    document.getElementById("restore-btns").style.display = "none";
    document.getElementById("restore-prog").style.display = "none";
    done.style.display = "block";
    done.style.color = "var(--red)";
    done.textContent = "✗ no enabled apps to restore";
    return;
  }

  document.getElementById("restore-btns").style.display = "none";
  document.getElementById("restore-prog").style.display = "block";

  const bar  = document.getElementById("prog-bar");
  const lbl  = document.getElementById("prog-lbl");

  let pct = 0;
  const tick = setInterval(() => {
    pct = Math.min(pct + 7, 88);
    bar.style.width = pct + "%";
    if      (pct < 30) lbl.textContent = `launching ${apps[0]?.app_name || "apps"}…`;
    else if (pct < 60) lbl.textContent = "restoring windows…";
    else               lbl.textContent = "finalizing…";
  }, 220);

  let res;
  try {
    res = await api("POST", `/api/restore/${encodeURIComponent(state.currentWS.name)}`);
  } catch (err) {
    clearInterval(tick);
    bar.style.width = "100%";
    lbl.textContent = "failed";
    const done = document.getElementById("restore-done");
    done.style.display = "block";
    done.style.color = "var(--red)";
    done.textContent = `✗ ${err?.message || err}`;
    return;
  }

  clearInterval(tick);
  bar.style.width = "100%";
  lbl.textContent = res.ok ? "done!" : "failed";

  setTimeout(() => {
    document.getElementById("restore-prog").style.display = "none";
    const done = document.getElementById("restore-done");
    done.style.display = "block";
    if (!res.ok) {
      done.style.color   = "var(--red)";
      done.textContent   = `✗ ${res.error}`;
    } else {
      done.style.color   = "var(--green)";
      done.textContent   = `✓ workspace restored!`;
    }
  }, 350);
}

// ── Settings clear-all ────────────────────────────────────────────────────────
async function clearAll() {
  const res = await api("DELETE", "/api/workspaces");
  if (!res.ok) {
    alert(`Clear failed: ${res.error || "unknown error"}`);
    return;
  }
  state.savedWorkspaces = [];
  show("saved");
}

async function clearAllConfirm() {
  const ok = await showAppConfirm({
    title: "CLEAR_ALL_WORKSPACES",
    message: "Delete ALL workspaces? This cannot be undone.",
    okLabel: "[ CLEAR ALL ]",
  });
  if (!ok) return;
  await clearAll();
}

async function openStorageLocation() {
  const res = await api("POST", "/api/storage-location/open");
  if (!res.ok) {
    alert(`Open folder failed: ${res.error || "unknown error"}`);
  }
}

initSettingsUI();
window.addEventListener("beforeunload", persistDraftWorkspaceOnExit);

function showAppConfirm({ title = "CONFIRM", message = "Are you sure?", okLabel = "[ OK ]" } = {}) {
  const modal = document.getElementById("confirm-modal");
  const titleEl = document.getElementById("confirm-title");
  const textEl = document.getElementById("confirm-text");
  const okBtn = document.getElementById("confirm-ok");
  const cancelBtn = document.getElementById("confirm-cancel");

  // Fallback for missing modal markup.
  if (!modal || !titleEl || !textEl || !okBtn || !cancelBtn) {
    return Promise.resolve(confirm(message));
  }

  titleEl.textContent = title;
  textEl.textContent = message;
  okBtn.textContent = okLabel;

  return new Promise(resolve => {
    const close = val => {
      modal.style.display = "none";
      okBtn.removeEventListener("click", onOk);
      cancelBtn.removeEventListener("click", onCancel);
      modal.removeEventListener("click", onBackdrop);
      document.removeEventListener("keydown", onEsc);
      resolve(val);
    };

    const onOk = () => close(true);
    const onCancel = () => close(false);
    const onBackdrop = e => {
      if (e.target === modal) close(false);
    };
    const onEsc = e => {
      if (e.key === "Escape") close(false);
    };

    modal.style.display = "flex";
    okBtn.addEventListener("click", onOk);
    cancelBtn.addEventListener("click", onCancel);
    modal.addEventListener("click", onBackdrop);
    document.addEventListener("keydown", onEsc);
  });
}