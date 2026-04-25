const MEMORYOS_MIN_PAGE_SECONDS = 45;
const MEMORYOS_MAX_CHARS = 3000;
const MEMORYOS_MIN_CHARS = 180;

function visibleText() {
  return (document.body?.innerText || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MEMORYOS_MAX_CHARS);
}

function shouldSkip() {
  if (!document.body) return true;
  if (document.visibilityState !== "visible") return true;
  const url = new URL(window.location.href);
  const host = url.hostname.toLowerCase();
  return [
    "bank",
    "chase.com",
    "wellsfargo.com",
    "capitalone.com",
    "paypal.com",
    "venmo.com",
    "netflix.com",
    "spotify.com",
    "tiktok.com",
    "instagram.com"
  ].some((fragment) => host.includes(fragment));
}

setTimeout(() => {
  if (shouldSkip()) return;

  const content = visibleText();
  if (content.length < MEMORYOS_MIN_CHARS) return;

  chrome.runtime.sendMessage({
    type: "page_capture",
    url: window.location.href,
    title: document.title,
    content,
    timestamp: Date.now()
  });
}, MEMORYOS_MIN_PAGE_SECONDS * 1000);
