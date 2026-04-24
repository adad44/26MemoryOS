const MEMORYOS_MIN_PAGE_SECONDS = 10;
const MEMORYOS_MAX_CHARS = 3000;

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
    "venmo.com"
  ].some((fragment) => host.includes(fragment));
}

setTimeout(() => {
  if (shouldSkip()) return;

  const content = visibleText();
  if (content.length < 100) return;

  chrome.runtime.sendMessage({
    type: "page_capture",
    url: window.location.href,
    title: document.title,
    content,
    timestamp: Date.now()
  });
}, MEMORYOS_MIN_PAGE_SECONDS * 1000);
