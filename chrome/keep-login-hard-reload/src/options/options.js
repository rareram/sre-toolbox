const DEFAULT_SETTINGS = {
  cache: true,
  serviceWorkers: true,
  cacheStorage: true,
  autoReload: true,
  showHUD: true,
  theme: "system",
  customDomains: [],
  schedulerEnable: false,
  scheduleDomain: "",
  scheduleInterval: 10,
  scheduleNotify: true
};

// 1. i18n Internationalization
function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    const msg = chrome.i18n.getMessage(key);
    if (msg) {
      if (el.tagName === "INPUT" && el.type === "button") {
        el.value = msg;
      } else {
        el.textContent = msg;
      }
    }
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    const msg = chrome.i18n.getMessage(key);
    if (msg) {
      el.placeholder = msg;
    }
  });
}

// 2. Theme Management
function applyTheme(theme) {
  document.body.classList.remove("theme-dark", "theme-light");
  if (theme === "dark") {
    document.body.classList.add("theme-dark");
  } else if (theme === "light") {
    document.body.classList.add("theme-light");
  }

  document.querySelectorAll(".theme-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.theme === theme);
  });
}

function initTheme() {
  chrome.storage.sync.get({ theme: "system" }, (items) => {
    applyTheme(items.theme);
  });

  document.querySelectorAll(".theme-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const selected = btn.dataset.theme;
      applyTheme(selected);
      chrome.storage.sync.set({ theme: selected });
    });
  });
}

// 3. Tab Navigation
function initTabs() {
  const tabs = document.querySelectorAll(".nav-tab");
  const panes = document.querySelectorAll(".tab-pane");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      panes.forEach((p) => p.classList.remove("active"));

      tab.classList.add("active");
      const targetPane = document.getElementById(`tab-${tab.dataset.tab}`);
      if (targetPane) {
        targetPane.classList.add("active");
      }

      if (tab.dataset.tab === "domains") {
        loadOpenTabs();
        loadCustomDomains();
      } else if (tab.dataset.tab === "automation") {
        populateSchedulerDomainOptions();
      }
    });
  });
}

// 4. Tab 1: Current Active Tab Settings
function loadCurrentSettings() {
  chrome.storage.sync.get(DEFAULT_SETTINGS, (items) => {
    document.getElementById("opt-cache").checked = items.cache;
    document.getElementById("opt-serviceworkers").checked = items.serviceWorkers;
    document.getElementById("opt-cachestorage").checked = items.cacheStorage;
    document.getElementById("opt-autoreload").checked = items.autoReload;
    document.getElementById("opt-showhud").checked = items.showHUD;
  });
}

function saveCurrentSettings(e) {
  e.preventDefault();
  const settings = {
    cache: document.getElementById("opt-cache").checked,
    serviceWorkers: document.getElementById("opt-serviceworkers").checked,
    cacheStorage: document.getElementById("opt-cachestorage").checked,
    autoReload: document.getElementById("opt-autoreload").checked,
    showHUD: document.getElementById("opt-showhud").checked
  };

  chrome.storage.sync.set(settings, () => {
    showStatus("status-current", chrome.i18n.getMessage("saveSuccess") || "Saved.");
  });
}

// 5. Tab 2: Live Open Tabs Parsing & Custom Domains
async function loadOpenTabs() {
  const container = document.getElementById("open-tabs-container");
  container.innerHTML = "<div class='empty-list-notice'>Loading tabs...</div>";

  try {
    const tabs = await chrome.tabs.query({});
    const originCounts = {};

    tabs.forEach((t) => {
      if (t.url && t.url.startsWith("http")) {
        try {
          const origin = new URL(t.url).origin;
          originCounts[origin] = (originCounts[origin] || 0) + 1;
        } catch (_) {}
      }
    });

    const origins = Object.keys(originCounts).sort();
    if (origins.length === 0) {
      container.innerHTML = `<div class='empty-list-notice'>${chrome.i18n.getMessage("noOpenTabs") || "No open web tabs."}</div>`;
      return;
    }

    container.innerHTML = "";
    origins.forEach((origin) => {
      const item = document.createElement("div");
      item.className = "domain-item";
      item.innerHTML = `
        <label class="domain-info">
          <input type="checkbox" class="domain-checkbox open-tab-chk" value="${origin}" checked>
          <span class="domain-text">${origin}</span>
        </label>
        <span class="domain-badge">${originCounts[origin]} tab(s)</span>
      `;
      container.appendChild(item);
    });
  } catch (err) {
    container.innerHTML = `<div class='empty-list-notice'>Error reading tabs: ${err.message}</div>`;
  }
}

async function clearSelectedTabs() {
  const checkboxes = document.querySelectorAll(".open-tab-chk:checked");
  const origins = Array.from(checkboxes).map((c) => c.value);

  if (origins.length === 0) return;

  const res = await chrome.runtime.sendMessage({ action: "clear_origins", origins });
  if (res && res.success) {
    showStatus("status-tabs", `${origins.length} site(s) cache cleared.`);
  }
}

// Custom Managed Domains
function loadCustomDomains() {
  const container = document.getElementById("custom-domains-container");
  chrome.storage.sync.get({ customDomains: [] }, (items) => {
    const domains = items.customDomains || [];
    if (domains.length === 0) {
      container.innerHTML = `<div class='empty-list-notice'>${chrome.i18n.getMessage("noCustomDomains") || "No managed sites registered."}</div>`;
      return;
    }

    container.innerHTML = "";
    domains.forEach((dom, idx) => {
      const item = document.createElement("div");
      item.className = "domain-item";
      item.innerHTML = `
        <span class="domain-text">${dom}</span>
        <button type="button" class="btn-delete-domain" data-idx="${idx}">&times;</button>
      `;
      container.appendChild(item);
    });

    container.querySelectorAll(".btn-delete-domain").forEach((btn) => {
      btn.addEventListener("click", () => {
        deleteCustomDomain(parseInt(btn.dataset.idx, 10));
      });
    });
  });
}

function addCustomDomain(e) {
  e.preventDefault();
  const input = document.getElementById("input-domain");
  let val = input.value.trim();
  if (!val) return;

  if (!val.startsWith("http://") && !val.startsWith("https://")) {
    val = "https://" + val;
  }

  try {
    const origin = new URL(val).origin;
    chrome.storage.sync.get({ customDomains: [] }, (items) => {
      const list = items.customDomains || [];
      if (!list.includes(origin)) {
        list.push(origin);
        chrome.storage.sync.set({ customDomains: list }, () => {
          input.value = "";
          loadCustomDomains();
          populateSchedulerDomainOptions();
        });
      }
    });
  } catch (_) {
    alert("Please enter a valid URL or domain.");
  }
}

function deleteCustomDomain(index) {
  chrome.storage.sync.get({ customDomains: [] }, (items) => {
    const list = items.customDomains || [];
    list.splice(index, 1);
    chrome.storage.sync.set({ customDomains: list }, () => {
      loadCustomDomains();
      populateSchedulerDomainOptions();
    });
  });
}

async function clearAllCustomDomains() {
  chrome.storage.sync.get({ customDomains: [] }, async (items) => {
    const domains = items.customDomains || [];
    if (domains.length === 0) return;

    const res = await chrome.runtime.sendMessage({ action: "clear_origins", origins: domains });
    if (res && res.success) {
      showStatus("status-custom", `${domains.length} site(s) cache cleared.`);
    }
  });
}

// 6. Tab 3: Scheduler & Global Sandbox Clean
async function populateSchedulerDomainOptions() {
  const select = document.getElementById("select-schedule-domain");
  select.innerHTML = "";

  const stored = await new Promise((r) => chrome.storage.sync.get(DEFAULT_SETTINGS, r));
  const domainsSet = new Set(stored.customDomains || []);

  const tabs = await chrome.tabs.query({});
  tabs.forEach((t) => {
    if (t.url && t.url.startsWith("http")) {
      try {
        domainsSet.add(new URL(t.url).origin);
      } catch (_) {}
    }
  });

  if (domainsSet.size === 0) {
    select.innerHTML = "<option value=''>No domains available</option>";
    return;
  }

  domainsSet.forEach((d) => {
    const opt = document.createElement("option");
    opt.value = d;
    opt.textContent = d;
    if (d === stored.scheduleDomain) {
      opt.selected = true;
    }
    select.appendChild(opt);
  });
}

function loadSchedulerSettings() {
  chrome.storage.sync.get(DEFAULT_SETTINGS, (items) => {
    document.getElementById("opt-scheduler-enable").checked = items.schedulerEnable;
    document.getElementById("input-schedule-interval").value = items.scheduleInterval || 10;
    document.getElementById("opt-schedule-notify").checked = items.scheduleNotify;
  });
}

function saveSchedulerSettings(e) {
  e.preventDefault();
  const select = document.getElementById("select-schedule-domain");
  const targetDomain = select.value;
  const interval = parseInt(document.getElementById("input-schedule-interval").value, 10) || 10;
  const enable = document.getElementById("opt-scheduler-enable").checked;
  const notify = document.getElementById("opt-schedule-notify").checked;

  const payload = {
    schedulerEnable: enable,
    scheduleDomain: targetDomain,
    scheduleInterval: Math.max(1, interval),
    scheduleNotify: notify
  };

  chrome.storage.sync.set(payload, async () => {
    await chrome.runtime.sendMessage({ action: "update_scheduler" });
    showStatus("status-scheduler", chrome.i18n.getMessage("saveSuccess") || "Saved.");
  });
}

// Emergency Global Sandbox Clean
async function handlePurgeAllCache() {
  const confirmMsg = chrome.i18n.getMessage("confirmPurgeAll") || "Are you sure you want to purge ALL browser cache?";
  if (!confirm(confirmMsg)) {
    return;
  }

  const btn = document.getElementById("btn-purge-all-cache");
  btn.disabled = true;

  try {
    const res = await chrome.runtime.sendMessage({ action: "purge_all_cache" });
    if (res && res.success) {
      showStatus("status-all-cache", chrome.i18n.getMessage("purgeSuccess") || "Global cache purged successfully.");
    }
  } catch (err) {
    showStatus("status-all-cache", `Error: ${err.message}`);
  } finally {
    btn.disabled = false;
  }
}

// Helper: Feedback message
function showStatus(elementId, message) {
  const el = document.getElementById(elementId);
  if (el) {
    el.textContent = message;
    setTimeout(() => {
      el.textContent = "";
    }, 2500);
  }
}

// Initialize Everything
document.addEventListener("DOMContentLoaded", () => {
  applyI18n();
  initTheme();
  initTabs();

  // Tab 1
  loadCurrentSettings();
  document.getElementById("form-current-settings").addEventListener("submit", saveCurrentSettings);

  // Tab 2
  loadOpenTabs();
  loadCustomDomains();
  document.getElementById("btn-refresh-tabs").addEventListener("click", loadOpenTabs);
  document.getElementById("btn-select-all-tabs").addEventListener("click", () => {
    document.querySelectorAll(".open-tab-chk").forEach((c) => (c.checked = true));
  });
  document.getElementById("btn-deselect-all-tabs").addEventListener("click", () => {
    document.querySelectorAll(".open-tab-chk").forEach((c) => (c.checked = false));
  });
  document.getElementById("btn-clear-selected-tabs").addEventListener("click", clearSelectedTabs);
  document.getElementById("form-add-domain").addEventListener("submit", addCustomDomain);
  document.getElementById("btn-clear-custom-domains").addEventListener("click", clearAllCustomDomains);

  // Tab 3
  loadSchedulerSettings();
  populateSchedulerDomainOptions();
  document.getElementById("form-scheduler").addEventListener("submit", saveSchedulerSettings);
  document.getElementById("btn-purge-all-cache").addEventListener("click", handlePurgeAllCache);
});
