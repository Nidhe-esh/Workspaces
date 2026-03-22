/**
 * app.js — Workspaces frontend logic
 * All data comes from the Flask API. No hardcoded mock data.
 */

"use strict";

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  isDark: false,
  scannedApps: [],       // raw scan result (user + system)
  currentWS: null,       // workspace open in edit mode
  savedWorkspaces: [],   // loaded from /api/workspaces
};

// ── Utility ───────────────────────────────────────────────────────────────────
async function api(method, path, body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body !== null) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  return res.json();
}

function slugify(str) {
  return str.trim().replace(/\s+/g, "_").replace(/[^\w\-]/g, "");
}

function relDate(iso) {
  if (!iso) return "";
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// ── Screen navigation ─────────────────────────────────────────────────────────
function show(id) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
  document.querySelectorAll(".settings-row").forEach((r) => r.classList.remove("settings-active"));

  document.getElementById("s-" + id).classList.add("active");

  const ni = document.getElementById("nav-" + id);
  if (ni) ni.classList.add("active");
  if (id === "settings") {
    document.getElementById("nav-settings").classList.add("settings-active");
  }

  // Load data when switching to saved screen
  if (id === "saved") loadSavedWorkspaces();
}

// ── Theme ─────────────────────────────────────────────────────────────────────
function toggleTheme() {
  state.isDark = !state.isDark;
  document.getElementById("app").classList.toggle("dark", state.isDark);
  const btn = document.getElementById("themeBtn");
  const knob = document.getElementById("themeKnob");
  btn.classList.toggle("lit", !state.isDark);
  knob.textContent = state.isDark ? "◑" : "☀";
}

// ── Toggle helper ─────────────────────────────────────────────────────────────
function tgl(el) {
  el.classList.toggle("on");
  el.querySelector(".tgl-k").style.left = el.classList.contains("on") ? "18px" : "2px";
}

// ── SCAN ──────────────────────────────────────────────────────────────────────
async function doScan() {
  const msg = document.getElementById("scan-msg");
  const list = document.getElementById("app-list");
  const saveZone = document.getElementById("save-zone");

  msg.innerHTML = '<span style="color:var(--blue)">scanning processes…</span>';
  list.innerHTML = "";
  saveZone.style.display = "none";

  const res = await api("POST", "/api/scan");

  if (!res.ok) {
    msg.innerHTML = `<span style="color:var(--red)">✗ ${res.error}</span>`;
    return;
  }

  const apps = res.data.apps || [];
  state.scannedApps = apps;

  const userApps = apps.filter((a) => !a.is_system);
  const sysApps = apps.filter((a) => a.is_system);

  msg.innerHTML = `<span style="color:var(--green)">✓ ${userApps.length} apps · ${sysApps.length} system excluded</span>`;

  userApps.forEach((a, i) => list.appendChild(buildAppCard(a, i, false)));

  const div = document.createElement("div");
  div.className = "sys-div";
  div.textContent = "// system apps — detected, excluded";
  list.appendChild(div);

  sysApps.forEach((a, i) => list.appendChild(buildAppCard(a, userApps.length + i, true)));

  saveZone.style.display = "block";
}

function buildAppCard(app, idx, isSystem) {
  const card = document.createElement("div");
  card.className = "app-card" + (isSystem ? " sys" : "");

  const isBrowser =
    app.app_name.includes("chrome") || app.app_name.includes("firefox");
  const tabs = (app.tabs || []).slice(0, 5);
  const moreCount = (app.tabs || []).length - 5;

  const tabsHTML = tabs.length
    ? `<div class="tab-row">
        ${tabs
          .map((t) => `<div class="tab-i${isBrowser ? " bt" : ""}">${t}</div>`)
          .join("")}
        ${moreCount > 0 ? `<button class="more-link">+ ${moreCount} more tabs →</button>` : ""}
      </div>`
    : "";

  const iconStyle = isSystem ? 'style="background:#ccc;border-color:#aaa"' : "";
  const tglLocked = isSystem ? 'style="cursor:not-allowed;opacity:.25"' : "";
  const isOn = app.keep && !isSystem;
  const tglHTML = `
    <div class="tgl${isOn ? " on" : ""}"
         ${tglLocked}
         onclick="state.scannedApps[${idx}].keep=!state.scannedApps[${idx}].keep;
                  this.classList.toggle('on');
                  this.querySelector('.tgl-k').style.left=this.classList.contains('on')?'18px':'2px'">
      <div class="tgl-k" style="left:${isOn ? "18" : "2"}px"></div>
    </div>`;

  card.innerHTML = `
    <div class="app-header">
      <div class="app-icon" ${iconStyle}>${appEmoji(app.app_name)}</div>
      <div class="app-meta">
        <div class="app-name">${app.app_name}</div>
        <div class="app-path">${app.exe_path}</div>
      </div>
      ${tglHTML}
    </div>
    ${tabsHTML}`;

  return card;
}

function appEmoji(name) {
  const map = {
    chrome: "🌐", firefox: "🦊", vs_code: "💙", code: "💙",
    notion: "📝", spotify: "🎵", slack: "💬", discord: "🎮",
    figma: "🎨", obsidian: "💜", teams: "💼", zoom: "📹",
    nvidia: "🟩", settings: "⚙️", explorer: "📁",
  };
  for (const [k, v] of Object.entries(map)) {
    if (name.toLowerCase().includes(k)) return v;
  }
  return "📦";
}

// ── SAVE ──────────────────────────────────────────────────────────────────────
async function saveWS() {
  const rawName = document.getElementById("ws-name-input").value.trim();
  const name = slugify(rawName) || "untitled_workspace";
  const ok = document.getElementById("save-ok");

  const appsToSave = state.scannedApps.filter((a) => !a.is_system);

  const res = await api("POST", "/api/save", { name, apps: appsToSave });

  if (!res.ok) {
    ok.style.color = "var(--red)";
    ok.textContent = `✗ ${res.error}`;
  } else {
    const kept = appsToSave.filter((a) => a.keep).length;
    ok.style.color = "var(--green)";
    ok.textContent = `✓ "${name}" saved · ${kept} apps included`;
  }

  ok.style.display = "block";
  setTimeout(() => (ok.style.display = "none"), 3000);
}

// ── SAVED WORKSPACES ──────────────────────────────────────────────────────────
async function loadSavedWorkspaces() {
  const grid = document.getElementById("ws-grid");
  grid.innerHTML = '<div style="font-size:11px;opacity:.4;font-family:var(--font)">loading…</div>';

  const res = await api("GET", "/api/workspaces");

  if (!res.ok) {
    grid.innerHTML = `<div style="color:var(--red);font-size:11px">${res.error}</div>`;
    return;
  }

  state.savedWorkspaces = res.data || [];
  renderWorkspaceGrid(state.savedWorkspaces);
}

function renderWorkspaceGrid(list) {
  const grid = document.getElementById("ws-grid");

  if (!list.length) {
    grid.innerHTML =
      '<div style="font-size:11px;opacity:.4;font-family:var(--font);grid-column:1/-1">No saved workspaces yet. Scan &amp; save one first.</div>';
    return;
  }

  grid.innerHTML = list
    .map(
      (ws) => `
    <div class="ws-card" onclick="openEdit('${ws.name}')">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div class="ws-name">${ws.name}</div>
        <span class="tag">${ws.apps ? ws.apps.length : 0} apps</span>
      </div>
      <div class="ws-meta">${relDate(ws.saved_at)}</div>
      <div class="ws-pills">
        ${(ws.apps || [])
          .slice(0, 3)
          .map((a) => `<div class="pill">${a.app_name}</div>`)
          .join("")}
        ${(ws.apps || []).length > 3
          ? `<div class="pill">+${(ws.apps || []).length - 3}</div>`
          : ""}
      </div>
    </div>`
    )
    .join("");
}

function filterWS(q) {
  const filtered = state.savedWorkspaces.filter((ws) =>
    ws.name.toLowerCase().includes(q.toLowerCase())
  );
  renderWorkspaceGrid(filtered);
}

// ── EDIT MODE ─────────────────────────────────────────────────────────────────
function openEdit(name) {
  const ws = state.savedWorkspaces.find((w) => w.name === name);
  if (!ws) return;

  state.currentWS = ws;
  document.getElementById("edit-ws-name").value = ws.name;

  const container = document.getElementById("edit-app-list");
  container.innerHTML = "";
  (ws.apps || []).forEach((app, i) => {
    container.appendChild(buildEditCard(app, i));
  });

  show("edit");
  document.getElementById("nav-saved").classList.add("active");
}

function buildEditCard(app, idx) {
  const card = document.createElement("div");
  card.className = "app-card" + (app.is_system ? " sys" : "");

  const isBrowser =
    app.app_name.includes("chrome") || app.app_name.includes("firefox");
  const tabs = (app.tabs || []).slice(0, 5);
  const moreCount = (app.tabs || []).length - 5;

  const tabsHTML = tabs.length
    ? `<div class="tab-row">
        ${tabs
          .map((t) => `<div class="tab-i${isBrowser ? " bt" : ""}">${t}</div>`)
          .join("")}
        ${moreCount > 0 ? `<button class="more-link">+ ${moreCount} more tabs →</button>` : ""}
      </div>`
    : "";

  const isSystem = app.is_system;
  const tglLocked = isSystem ? 'style="cursor:not-allowed;opacity:.25"' : "";
  const isOn = app.keep !== false && !isSystem;

  const tglHTML = `
    <div class="tgl${isOn ? " on" : ""}"
         ${tglLocked}
         onclick="state.currentWS.apps[${idx}].keep=!state.currentWS.apps[${idx}].keep;
                  this.classList.toggle('on');
                  this.querySelector('.tgl-k').style.left=this.classList.contains('on')?'18px':'2px';
                  autoSaveEdit()">
      <div class="tgl-k" style="left:${isOn ? "18" : "2"}px"></div>
    </div>`;

  card.innerHTML = `
    <div class="app-header">
      <div class="app-icon">${appEmoji(app.app_name)}</div>
      <div class="app-meta">
        <div class="app-name">${app.app_name}</div>
        <div class="app-path">${app.exe_path || ""}</div>
      </div>
      ${tglHTML}
    </div>
    ${tabsHTML}`;

  return card;
}

async function autoSaveEdit() {
  if (!state.currentWS) return;
  const name = document.getElementById("edit-ws-name").value.trim() || state.currentWS.name;
  await api("POST", "/api/save", {
    name,
    apps: state.currentWS.apps,
  });
  // badge flashes
  const badge = document.getElementById("autosave-badge");
  badge.style.opacity = "1";
  setTimeout(() => (badge.style.opacity = ".6"), 800);
}

async function deleteWS() {
  if (!state.currentWS) return;
  if (!confirm(`Delete "${state.currentWS.name}"? This cannot be undone.`)) return;

  const res = await api("DELETE", `/api/workspace/${encodeURIComponent(state.currentWS.name)}`);

  if (res.ok) {
    state.currentWS = null;
    show("saved");
  } else {
    alert(`Delete failed: ${res.error}`);
  }
}

// ── RESTORE CONFIRM ───────────────────────────────────────────────────────────
function showConfirm() {
  if (!state.currentWS) return;

  const apps = (state.currentWS.apps || []).filter((a) => !a.is_system);
  const kept = apps.filter((a) => a.keep !== false);
  const skipped = apps.filter((a) => a.keep === false);

  const list = document.getElementById("restore-list");
  list.innerHTML =
    kept
      .map(
        (a) => `
      <div class="restore-item">
        <div class="r-icon">${appEmoji(a.app_name)}</div>
        <div>
          <div style="font-weight:700;font-size:12px">${a.app_name}</div>
          <div style="font-size:9.5px;opacity:.4;margin-top:1px">
            ${a.tabs && a.tabs.length ? `${a.tabs.length} tabs` : "launches app"}
          </div>
        </div>
      </div>`
      )
      .join("") +
    skipped
      .map(
        (a) => `
      <div class="restore-item" style="opacity:.28">
        <div class="r-icon">${appEmoji(a.app_name)}</div>
        <div style="font-size:11.5px">${a.app_name} — skipped (toggled off)</div>
      </div>`
      )
      .join("");

  document.getElementById("restore-prog").style.display = "none";
  document.getElementById("restore-btns").style.display = "flex";
  document.getElementById("restore-done").style.display = "none";
  document.getElementById("prog-bar").style.width = "0";

  show("confirm");
  document.getElementById("nav-saved").classList.add("active");
}

async function runRestore() {
  if (!state.currentWS) return;

  document.getElementById("restore-btns").style.display = "none";
  document.getElementById("restore-prog").style.display = "block";

  const wsName = state.currentWS.name;
  const apps = (state.currentWS.apps || []).filter(
    (a) => !a.is_system && a.keep !== false
  );

  // Animate progress while waiting for API
  let pct = 0;
  const bar = document.getElementById("prog-bar");
  const lbl = document.getElementById("prog-lbl");
  const tick = setInterval(() => {
    pct = Math.min(pct + 8, 88);
    bar.style.width = pct + "%";
    if (pct < 30) lbl.textContent = `launching ${apps[0]?.app_name || "apps"}…`;
    else if (pct < 60) lbl.textContent = "restoring windows…";
    else lbl.textContent = "finalizing…";
  }, 250);

  const res = await api("POST", `/api/restore/${encodeURIComponent(wsName)}`);

  clearInterval(tick);
  bar.style.width = "100%";
  lbl.textContent = "done!";

  setTimeout(() => {
    document.getElementById("restore-prog").style.display = "none";
    if (res.ok) {
      document.getElementById("restore-done").style.display = "block";
    } else {
      document.getElementById("restore-done").style.display = "block";
      document.getElementById("restore-done").textContent =
        `✗ Restore error: ${res.error}`;
      document.getElementById("restore-done").style.color = "var(--red)";
    }
  }, 400);
}
