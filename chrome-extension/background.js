// Add to BKDict: right-click selected text -> search it in the local app.
//
// Hand-off: the word is saved to chrome.storage.local and content.js (which runs
// on the app's vocab page) picks it up, fills the Search box and presses Search.
// Going through storage means the same path works for a freshly opened tab, an
// already-open tab, and a tab that first has to go through the login page.

const APP_URL = 'http://127.0.0.1:5001/';
const APP_TAB_PATTERNS = ['http://127.0.0.1:5001/*', 'http://localhost:5001/*'];
// A static file: cheap, never behind the login guard, and (unlike /login) not rate limited.
const HEALTH_URL = APP_URL + 'static/css/style.css';
const MENU_ID = 'add-to-bkdict';
const PENDING_KEY = 'pendingWord';
const MAX_WORD_LENGTH = 200;

chrome.runtime.onInstalled.addListener(() => {
  // removeAll first: reloading the extension would otherwise hit "duplicate id".
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: MENU_ID,
      title: 'Add to BKDict',
      contexts: ['selection'],
    });
  });
});

chrome.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId !== MENU_ID) return;

  const word = (info.selectionText || '').trim().slice(0, MAX_WORD_LENGTH);
  if (!word) return;

  if (!(await isAppUp())) {
    notify('BKDict is not running', 'Start the local app (python app.py) and try again.');
    return;
  }

  await chrome.storage.local.set({ [PENDING_KEY]: { word, ts: Date.now() } });

  const tab = await findVocabTab();
  if (tab) {
    await chrome.tabs.update(tab.id, { active: true });
    await chrome.windows.update(tab.windowId, { focused: true });
    // A tab that was open before the extension was installed or reloaded has no
    // content script yet; injecting is harmless when one is there (it guards itself).
    try {
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] });
    } catch (err) {
      console.warn('Could not inject into the existing tab:', err);
    }
  } else {
    await chrome.tabs.create({ url: APP_URL });
  }
});

async function isAppUp() {
  try {
    // Any HTTP response (even an error status) means the server is listening.
    await fetch(HEALTH_URL, { cache: 'no-store', signal: AbortSignal.timeout(2000) });
    return true;
  } catch {
    return false;
  }
}

// An open tab on the vocab page ("/"), most recently used first. The quiz and
// login pages are skipped because they have no Search box.
async function findVocabTab() {
  const tabs = await chrome.tabs.query({ url: APP_TAB_PATTERNS });
  const vocabTabs = tabs.filter((t) => {
    try {
      return new URL(t.url).pathname === '/';
    } catch {
      return false;
    }
  });
  vocabTabs.sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0));
  return vocabTabs[0] || null;
}

function notify(title, message) {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icons/icon128.png',
    title,
    message,
  });
}
