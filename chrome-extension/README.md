# Add to BKDict (Chrome extension)

Highlight a word on any web page, right-click, choose **Add to BKDict**. The word
goes into the Search box of your local EasyVocab app and the search runs.

Windows 11 + Chrome only; it talks to `http://127.0.0.1:5001` (or `localhost:5001`).

## Install

1. Open `chrome://extensions` and turn on **Developer mode**.
2. Click **Load unpacked** and pick this `chrome-extension` folder.
3. Start the app (`python app.py`), highlight a word somewhere, right-click it.

After editing the extension's files, click the reload icon on its card in
`chrome://extensions`. A tab that was open before a reload gets the new content
script the next time you use the menu item.

## Behaviour

- App not running: a Windows notification says so and nothing opens.
- A vocab-page tab (`/`) is already open: Chrome switches to it and fills the box.
  Otherwise a new tab opens.
- Not logged in: the new tab lands on the login page; once you log in, the word is
  filled in and searched (it is kept for 5 minutes).
- Quiz tabs are never reused, since they have no Search box.

## How it works

`background.js` owns the context menu, checks the server is up (a request for
`/static/css/style.css`, since `/login` is rate limited), saves the word in
`chrome.storage.local`, then focuses or opens the tab. `content.js` runs on the
app's pages; on the vocab page it takes the saved word, fills `#searchInput` and
clicks `#searchBtn`. If you change those element ids in `templates/index.html`,
update `content.js`.

To use another port, change the port in `manifest.json` (`host_permissions` and
`content_scripts.matches`) and in the constants at the top of `background.js`.
