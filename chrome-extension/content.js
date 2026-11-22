// Runs on the app's pages. If background.js left a word in storage and this is
// the vocab page, put it in the Search box and press Search.

(() => {
  // The background script may inject this file into a tab that already has it.
  if (window.__bkdictAddLoaded) return;
  window.__bkdictAddLoaded = true;

  const PENDING_KEY = 'pendingWord';
  const MAX_AGE_MS = 5 * 60 * 1000; // ignore a word left over from long ago
  let lastHandledTs = 0;

  async function consume() {
    const input = document.getElementById('searchInput');
    const button = document.getElementById('searchBtn');
    // Not the vocab page (e.g. the login page): leave the word for after login.
    if (!input || !button) return;

    const stored = await chrome.storage.local.get(PENDING_KEY);
    const pending = stored[PENDING_KEY];
    // No await between this check and setting lastHandledTs, so a second
    // overlapping call (load + storage change) cannot handle the same word twice.
    if (!pending || pending.ts === lastHandledTs) return;
    lastHandledTs = pending.ts;

    await chrome.storage.local.remove(PENDING_KEY);
    if (Date.now() - pending.ts > MAX_AGE_MS) return;

    input.value = pending.word;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    button.click();
  }

  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'local' && changes[PENDING_KEY] && changes[PENDING_KEY].newValue) {
      consume();
    }
  });

  consume();
})();
