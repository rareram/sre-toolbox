const DEFAULT_SETTINGS = {
  cache: true,
  serviceWorkers: true,
  cacheStorage: true,
  autoReload: true,
  showHUD: true,
  schedulerEnable: false,
  scheduleDomain: "",
  scheduleInterval: 10,
  scheduleNotify: true
};

async function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(DEFAULT_SETTINGS, (items) => {
      resolve(items);
    });
  });
}

// Visual Badge Feedback Helpers
async function showBadgeLoading(tabId) {
  try {
    await chrome.action.setBadgeBackgroundColor({ color: "#3b82f6", tabId });
    await chrome.action.setBadgeText({ text: "..", tabId });
  } catch (_) {}
}

async function showBadgeFeedback(tabId, text = "OK", color = "#16a34a", duration = 1500) {
  try {
    await chrome.action.setBadgeBackgroundColor({ color, tabId });
    await chrome.action.setBadgeText({ text, tabId });
    setTimeout(async () => {
      try {
        await chrome.action.setBadgeText({ text: "", tabId });
      } catch (_) {}
    }, duration);
  } catch (_) {}
}

// Injected into the target page DOM to render HUD
function renderHUDInPage(text, progress, isSuccess) {
  const HUD_ID = "keeplogin-hard-reload-hud";
  let hud = document.getElementById(HUD_ID);

  if (!hud) {
    hud = document.createElement("div");
    hud.id = HUD_ID;
    hud.style.cssText = [
      "position: fixed !important",
      "top: 24px !important",
      "left: 50% !important",
      "transform: translateX(-50%) !important",
      "z-index: 2147483647 !important",
      "pointer-events: none !important",
      "background: rgba(17, 24, 39, 0.94) !important",
      "color: #f9fafb !important",
      "backdrop-filter: blur(10px) !important",
      "-webkit-backdrop-filter: blur(10px) !important",
      "border: 1px solid rgba(255, 255, 255, 0.18) !important",
      "border-radius: 26px !important",
      "padding: 14px 26px !important",
      "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important",
      "font-size: 15px !important",
      "font-weight: 600 !important",
      "line-height: 1.3 !important",
      "box-shadow: 0 16px 40px rgba(0, 0, 0, 0.45) !important",
      "display: flex !important",
      "flex-direction: column !important",
      "align-items: center !important",
      "gap: 9px !important",
      "min-width: 280px !important",
      "box-sizing: border-box !important",
      "opacity: 1 !important"
    ].join("; ");

    const label = document.createElement("span");
    label.id = `${HUD_ID}-text`;
    label.style.cssText = "color: #f9fafb !important; font-size: 15px !important; font-weight: 600 !important; letter-spacing: -0.1px !important;";
    hud.appendChild(label);

    const track = document.createElement("div");
    track.style.cssText = [
      "width: 100% !important",
      "height: 4px !important",
      "background: rgba(255, 255, 255, 0.15) !important",
      "border-radius: 2px !important",
      "overflow: hidden !important"
    ].join("; ");

    const bar = document.createElement("div");
    bar.id = `${HUD_ID}-bar`;
    bar.style.cssText = [
      "height: 100% !important",
      "width: 0% !important",
      "background: #3b82f6 !important",
      "border-radius: 2px !important",
      "transition: width 0.15s ease-out, background-color 0.15s ease-out !important"
    ].join("; ");

    track.appendChild(bar);
    hud.appendChild(track);

    const root = document.body || document.documentElement;
    root.appendChild(hud);
  }

  const textEl = document.getElementById(`${HUD_ID}-text`);
  const barEl = document.getElementById(`${HUD_ID}-bar`);

  if (textEl) textEl.textContent = text;
  if (barEl) {
    barEl.style.width = `${progress}%`;
    if (isSuccess) {
      barEl.style.backgroundColor = "#10b981";
    }
  }
}

async function updateHUD(tabId, text, progress, isSuccess = false) {
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      func: renderHUDInPage,
      args: [text, progress, isSuccess]
    });
  } catch (err) {
    console.warn("[KeepLogin Hard Reload] HUD injection skipped or failed:", err);
  }
}

// Execute Hard Reload on Active Tab
async function executeHardReload(tab) {
  if (!tab || !tab.url) {
    const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
    tab = activeTab;
  }

  if (!tab || !tab.url || !tab.url.startsWith("http")) {
    console.warn("KeepLogin Hard Reload: Only http/https pages are supported.");
    return;
  }

  const settings = await getSettings();

  // Step 1: Immediate HUD and badge reaction
  showBadgeLoading(tab.id);
  if (settings.showHUD) {
    const clearingMsg = chrome.i18n.getMessage("hudClearing") || "Clearing site cache & workers...";
    await updateHUD(tab.id, clearingMsg, 45, false);
  }

  try {
    const origin = new URL(tab.url).origin;
    const dataToRemove = {};
    if (settings.cache) dataToRemove.cache = true;
    if (settings.serviceWorkers) dataToRemove.serviceWorkers = true;
    if (settings.cacheStorage) dataToRemove.cacheStorage = true;

    // Remove targets for this specific origin only (Keep Cookies & LocalStorage)
    await chrome.browsingData.remove({ origins: [origin] }, dataToRemove);

    // Step 2: Complete clearance, switch HUD to reloading state
    if (settings.showHUD) {
      const reloadingMsg = chrome.i18n.getMessage("hudReloading") || "Hard reloading...";
      await updateHUD(tab.id, reloadingMsg, 100, true);
      await new Promise((resolve) => setTimeout(resolve, 150));
    }

    // Bypass browser cache on reload if enabled
    if (settings.autoReload) {
      await chrome.tabs.reload(tab.id, { bypassCache: true });
    }

    await showBadgeFeedback(tab.id, "OK", "#16a34a");
  } catch (error) {
    console.error("KeepLogin Hard Reload error:", error);
    try {
      await chrome.action.setBadgeText({ text: "", tabId: tab.id });
    } catch (_) {}
  }
}

// Emergency Global Sandbox Clean (Purge All Browser Cache, Keep Login)
async function purgeAllBrowserCache() {
  try {
    await chrome.action.setBadgeBackgroundColor({ color: "#ea580c" });
    await chrome.action.setBadgeText({ text: "ALL" });

    // Target entire browser cache, but exclude cookies, localStorage, and indexedDB
    await chrome.browsingData.remove({}, {
      cache: true,
      cacheStorage: true,
      serviceWorkers: true
    });

    await chrome.action.setBadgeBackgroundColor({ color: "#16a34a" });
    await chrome.action.setBadgeText({ text: "OK" });
    setTimeout(async () => {
      try {
        await chrome.action.setBadgeText({ text: "" });
      } catch (_) {}
    }, 2000);

    return { success: true };
  } catch (error) {
    console.error("Global purge error:", error);
    try {
      await chrome.action.setBadgeText({ text: "" });
    } catch (_) {}
    throw error;
  }
}

// Scheduler Setup
async function setupScheduler() {
  try {
    await chrome.alarms.clear("keep_login_scheduler");
    const settings = await getSettings();

    if (settings.schedulerEnable && settings.scheduleDomain) {
      const interval = Math.max(1, parseInt(settings.scheduleInterval, 10) || 10);
      chrome.alarms.create("keep_login_scheduler", { periodInMinutes: interval });
      console.log(`[KeepLogin Hard Reload] Scheduler active for ${settings.scheduleDomain} every ${interval} min`);
    }
  } catch (err) {
    console.error("Scheduler setup failed:", err);
  }
}

// Alarm Listener for Periodic Auto Purge
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "keep_login_scheduler") {
    const settings = await getSettings();
    if (!settings.schedulerEnable || !settings.scheduleDomain) return;

    try {
      // Silent purge without reload
      await chrome.browsingData.remove({ origins: [settings.scheduleDomain] }, {
        cache: true,
        cacheStorage: true,
        serviceWorkers: true
      });

      // Visual badge feedback visible from any tab
      await chrome.action.setBadgeBackgroundColor({ color: "#7c3aed" }); // Purple AUTO
      await chrome.action.setBadgeText({ text: "AUTO" });
      setTimeout(async () => {
        try {
          await chrome.action.setBadgeText({ text: "" });
        } catch (_) {}
      }, 2000);

      // Chrome notification if enabled
      if (settings.scheduleNotify) {
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icons/icon-48.png",
          title: chrome.i18n.getMessage("notifTitle") || "KeepLogin Hard Reload",
          message: `${settings.scheduleDomain}: ${chrome.i18n.getMessage("notifAutoPurge") || "Cache auto-purged."}`
        });
      }
    } catch (err) {
      console.error("Scheduled purge failed:", err);
    }
  }
});

// Runtime Message Listener (for options page communication)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "clear_origins") {
    const origins = message.origins || [];
    chrome.browsingData.remove({ origins }, {
      cache: true,
      cacheStorage: true,
      serviceWorkers: true
    }).then(() => {
      sendResponse({ success: true, count: origins.length });
    }).catch((err) => {
      sendResponse({ success: false, error: err.message });
    });
    return true; // Async response
  }

  if (message.action === "purge_all_cache") {
    purgeAllBrowserCache().then(() => {
      sendResponse({ success: true });
    }).catch((err) => {
      sendResponse({ success: false, error: err.message });
    });
    return true; // Async response
  }

  if (message.action === "update_scheduler") {
    setupScheduler().then(() => {
      sendResponse({ success: true });
    });
    return true; // Async response
  }
});

// Command Listener (for clear-all-cache-sandbox shortcut)
chrome.commands.onCommand.addListener(async (command) => {
  if (command === "clear-all-cache-sandbox") {
    await purgeAllBrowserCache();
  }
});

// Toolbar Icon Click & _execute_action Shortcut
chrome.action.onClicked.addListener((tab) => {
  executeHardReload(tab);
});

// Local Agent Bridge Polling (Cross-Platform HTTP Long-polling)
let isBridgePolling = false;

async function startBridgePolling() {
  if (isBridgePolling) return;
  isBridgePolling = true;

  while (isBridgePolling) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s abort

      const resp = await fetch("http://127.0.0.1:8765/events", {
        method: "GET",
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (resp.ok) {
        const data = await resp.json();
        if (data && data.command === "hard_reload") {
          console.log("[KeepLogin Hard Reload] Bridge trigger received:", data);

          if (data.target_origin) {
            const tabs = await chrome.tabs.query({});
            const targetTab = tabs.find((t) => t.url && t.url.startsWith(data.target_origin));
            if (targetTab) {
              await executeHardReload(targetTab);
            } else {
              // Clear cache for origin even if tab isn't focused
              await chrome.browsingData.remove({ origins: [data.target_origin] }, {
                cache: true,
                cacheStorage: true,
                serviceWorkers: true
              });
              await showBadgeFeedback(null, "OK", "#16a34a");
            }
          } else {
            const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
            if (activeTab) {
              await executeHardReload(activeTab);
            }
          }
        }
      } else {
        // Bridge server returned non-200, wait 5s
        await new Promise((r) => setTimeout(r, 5000));
      }
    } catch (_) {
      // Bridge server not running, wait 5s before retrying
      await new Promise((r) => setTimeout(r, 5000));
    }
  }
}

// Initialization on install/startup
chrome.runtime.onInstalled.addListener(() => {
  setupScheduler();
  startBridgePolling();
});

chrome.runtime.onStartup.addListener(() => {
  setupScheduler();
  startBridgePolling();
});

// Immediate start for current session
startBridgePolling();

