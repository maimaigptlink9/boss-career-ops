const BRIDGE_URL = "ws://127.0.0.1:18765/ws";
const RECONNECT_ALARM = "bco-reconnect";
const RECONNECT_DELAY_MINUTES = 0.08;
let ws = null;

function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }
  ws = new WebSocket(BRIDGE_URL);
  ws.onopen = () => {
    console.log("[Boss-Career-Ops] Bridge connected");
    chrome.alarms.clear(RECONNECT_ALARM);
  };
  ws.onmessage = async (event) => {
    const data = JSON.parse(event.data);
    const result = await handleCommand(data);
    ws.send(JSON.stringify(result));
  };
  ws.onclose = () => {
    console.log("[Boss-Career-Ops] Bridge disconnected, scheduling reconnect...");
    scheduleReconnect();
  };
  ws.onerror = (err) => {
    console.error("[Boss-Career-Ops] Bridge error:", err);
  };
}

function scheduleReconnect() {
  chrome.alarms.create(RECONNECT_ALARM, { delayInMinutes: RECONNECT_DELAY_MINUTES });
}

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === RECONNECT_ALARM) {
    connect();
  }
});

async function handleCommand(data) {
  const { type, params, id } = data;
  try {
    switch (type) {
      case "ping":
        return { ok: true, data: "pong", id };

      case "get_cookies":
        const cookies = await chrome.cookies.getAll({ url: "https://www.zhipin.com/" });
        return { ok: true, data: cookies, id };

      case "navigate":
        const [navTab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (navTab) {
          await chrome.tabs.update(navTab.id, { url: params.url });
        }
        return { ok: true, data: "navigated", id };

      case "click":
        const [clickTab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (clickTab) {
          await chrome.scripting.executeScript({
            target: { tabId: clickTab.id },
            func: (sel) => {
              const el = document.querySelector(sel);
              if (el) { el.click(); return true; }
              return false;
            },
            args: [params.selector],
          });
        }
        return { ok: true, data: "clicked", id };

      case "type_text":
        const [typeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (typeTab) {
          await chrome.scripting.executeScript({
            target: { tabId: typeTab.id },
            func: (sel, text) => {
              const el = document.querySelector(sel);
              if (el) {
                el.focus();
                el.value = text;
                el.dispatchEvent(new Event("input", { bubbles: true }));
                el.dispatchEvent(new Event("change", { bubbles: true }));
                return true;
              }
              return false;
            },
            args: [params.selector, params.text],
          });
        }
        return { ok: true, data: "typed", id };

      case "screenshot":
        const screenshotDataUrl = await chrome.tabs.captureVisibleTab(null, { format: "png" });
        return { ok: true, data: screenshotDataUrl, id };

      case "execute_js":
        const [jsTab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (jsTab) {
          const results = await chrome.scripting.executeScript({
            target: { tabId: jsTab.id },
            func: new Function(params.script),
          });
          const jsResult = results && results[0] ? results[0].result : null;
          return { ok: true, data: jsResult, id };
        }
        return { ok: false, error: "No active tab", id };

      default:
        return { ok: false, error: `Unknown command: ${type}`, id };
    }
  } catch (err) {
    return { ok: false, error: err.message, id };
  }
}

chrome.webNavigation.onCompleted.addListener((details) => {
  if (details.url && details.url.includes("zhipin.com")) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: "page_loaded",
        params: { url: details.url },
      }));
    }
  }
});

chrome.runtime.onInstalled.addListener(() => {
  connect();
});

connect();
