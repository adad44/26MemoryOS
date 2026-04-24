chrome.runtime.onMessage.addListener((message, sender) => {
  if (message?.type !== "page_capture") return;
  if (sender.tab?.incognito) return;

  fetch("http://127.0.0.1:8765/capture/browser", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      url: message.url,
      title: message.title,
      content: message.content,
      timestamp: message.timestamp
    })
  }).catch(() => {
    // The local ingest server is optional during Phase 1.
  });
});
