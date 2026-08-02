# Add New Word Screenshot Attachment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user paste a screenshot directly into the "Add New Word" modal so a word and its image are captured in one pass.

**Architecture:** The pasted image is held in browser memory as a `Blob`. On submit, `POST /api/words` runs exactly as it does today; the `word_id` it returns is then used to `POST /api/words/<word_id>/image` — an endpoint that already exists and already performs the required compression. No backend file is touched and there is no database migration.

**Tech Stack:** Flask (Jinja templates), vanilla JavaScript (no framework, no build step, no JS test runner), plain CSS with custom properties, pytest.

**Spec:** `docs/superpowers/specs/2026-08-01-add-word-screenshot-design.md`

## Global Constraints

- **Do not modify `app.py`.** No endpoint is added, changed, or removed.
- **Do not modify the existing `pasteImageModal` flow** (`app.js` ~594-748) or its `currentPastedFile` variable. The new flow uses its own separate state.
- All work happens on branch `feature/add-word-screenshot`.
- All commands run inside the `bkdict` conda environment. The dev server is `http://localhost:5001`.
- Accepted clipboard image types, exactly: `image/png`, `image/jpeg`, `image/gif`, `image/webp`, `image/bmp`. SVG is deliberately excluded.
- Paste is bound to `#newWordPasteZone` only — never to `document` and never to the modal.
- New buttons carry `type="button"`.
- Match surrounding code style: 4-space indent in JS and CSS, emoji-prefixed status strings, JSDoc block comments on functions.
- **Every task must leave the app loadable with no console errors.** Do not commit an intermediate state where a listener references an undefined handler.

## File Structure

| File | Responsibility | Change |
| --- | --- | --- |
| `templates/index.html` | Markup for the screenshot control inside `#addWordModal` | Modify (insert one `.form-group`) |
| `static/css/style.css` | Visual styling for the thumbnail zone and its armed state | Modify (append one block) |
| `static/js/app.js` | Element refs, listeners, paste validation, submit integration | Modify (6 sites) |
| `test/test_basic.py` | Structural assertions that the markup exists | Modify (add 2 tests) |
| `app.py` | — | **Not modified** |

### Testing reality

`test/test_basic.py` is a database-free structural suite. There is no JS test runner in this project (no `package.json`, no jest), so the paste handler cannot be unit tested. The automated tests in this plan therefore guard only that the markup exists; the behaviour is verified by the scripted manual pass that closes each task, which is mandatory per the project's `GEMINI.md` validation rule.

Do not add a JS test framework. That is out of scope.

### Task ordering rationale

Task 2 defines functions that nothing calls yet — harmless, the app still runs. Task 3 wires them up in one shot (element refs, listeners, and the modal reset together), which is the first point the feature becomes live and testable. Splitting the wiring from the handlers would leave a commit where `addEventListener` references an undefined name and the page dies on load.

---

### Task 1: Static screenshot control (markup + styles)

Produces the control, rendered and styled but inert. Nothing responds to clicks yet.

**Files:**
- Modify: `templates/index.html` (inside `#addWordModal`, after the Example Sentences `.form-group`, immediately before `<div id="addWordStatus" class="form-status"></div>`)
- Modify: `static/css/style.css` (append at end of file)
- Test: `test/test_basic.py` (add to the existing `TestTemplates` class)

**Interfaces:**
- Consumes: nothing.
- Produces: DOM element IDs used by Task 3 — `newWordPasteZone`, `newWordPastePlaceholder`, `newWordThumb`, `attachScreenshotBtn`, `removeScreenshotBtn`, `newWordPasteHint`. CSS class `armed` on `#newWordPasteZone`.

- [ ] **Step 1: Write the failing tests**

Add these two methods to the **existing** `TestTemplates` class in `test/test_basic.py`:

```python
    def test_index_has_screenshot_paste_zone(self):
        """Add New Word modal should contain the screenshot paste zone"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates', 'index.html')
        with open(template_path, encoding='utf-8') as f:
            markup = f.read()
        assert 'newWordPasteZone' in markup

    def test_index_has_attach_screenshot_button(self):
        """Add New Word modal should contain the attach screenshot button"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates', 'index.html')
        with open(template_path, encoding='utf-8') as f:
            markup = f.read()
        assert 'attachScreenshotBtn' in markup
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate bkdict
pytest test/test_basic.py -v -k screenshot
```

Expected: 2 FAILED, both `AssertionError`.

- [ ] **Step 3: Add the markup**

In `templates/index.html`, find this line inside `#addWordModal`:

```html
                    <div id="addWordStatus" class="form-status"></div>
```

Insert this block **immediately before** it:

```html
                    <div class="form-group">
                        <label>Screenshot (optional)</label>
                        <div class="screenshot-row">
                            <div id="newWordPasteZone" class="screenshot-zone" tabindex="0">
                                <span id="newWordPastePlaceholder" class="screenshot-placeholder">No image</span>
                                <img id="newWordThumb" class="screenshot-thumb" style="display: none;"
                                    alt="Screenshot preview">
                            </div>
                            <div class="screenshot-actions">
                                <button id="attachScreenshotBtn" class="btn btn-sm btn-secondary" type="button">📷
                                    Attach Screenshot</button>
                                <button id="removeScreenshotBtn" class="btn btn-sm btn-cancel" type="button"
                                    style="display: none;">✕ Remove</button>
                                <small id="newWordPasteHint" class="form-hint"></small>
                            </div>
                        </div>
                    </div>
```

The zone is a plain `div` — not an `input` and not `contenteditable`. That is deliberate: pasted text has nowhere to render even if the handler's `preventDefault()` were ever removed. `tabindex="0"` is present only because an element must be focusable to receive paste events.

- [ ] **Step 4: Add the styles**

Append to the end of `static/css/style.css`:

```css
/* ============================================
   Add New Word - Screenshot Attachment
   ============================================ */

.screenshot-row {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-xs);
}

.screenshot-zone {
    flex: 0 0 auto;
    width: 96px;
    height: 64px;
    border: 2px dashed var(--border-color);
    border-radius: var(--radius-md);
    background: var(--bg-main);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    outline: none;
    transition: all 0.2s ease;
}

.screenshot-zone.armed,
.screenshot-zone:focus {
    border-color: var(--primary-blue);
    background: rgba(135, 206, 235, 0.1);
}

.screenshot-placeholder {
    color: var(--text-secondary);
    font-size: 0.75rem;
    pointer-events: none;
}

.screenshot-thumb {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.screenshot-actions {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-xs);
}

.screenshot-actions .form-hint {
    margin-top: 0;
}
```

These custom properties are already defined in this file and are used by `.paste-area` at line ~2286: `--spacing-sm`, `--spacing-xs`, `--border-color`, `--radius-md`, `--bg-main`, `--primary-blue`, `--text-secondary`.

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest test/test_basic.py -v
```

Expected: all PASS, including the 2 new tests. The whole file must pass, not just the new ones.

- [ ] **Step 6: Verify it renders**

```bash
python app.py
```

Open `http://localhost:5001`, click **✨ Add New Word**. Confirm: a "Screenshot (optional)" row appears below Example Sentences, showing a 96×64 dashed box reading "No image", a `📷 Attach Screenshot` button beside it, and no Remove button. Nothing happens when the button is clicked — that is expected at this stage. Check the console (F12) is clean. Stop the server with Ctrl+C.

- [ ] **Step 7: Commit**

```bash
git add templates/index.html static/css/style.css test/test_basic.py
git commit -m "Add screenshot attachment control to Add New Word modal"
```

---

### Task 2: Paste handling functions

Defines the logic. Nothing calls these yet, so the app behaves exactly as before — this task is safe in isolation and is where the image-only validation lives.

**Files:**
- Modify: `static/js/app.js` (insert a new function section after the existing `removeWordImage()` function, ~line 748, immediately before the `// API Functions` divider)

**Interfaces:**
- Consumes: `Elements.*` slots declared in Task 3. These functions only run after Task 3 wires them, so the forward reference is safe.
- Produces:
  - `NEW_WORD_IMAGE_TYPES` — `string[]` of accepted MIME types.
  - `NO_IMAGE_MESSAGE` — `string`, the rejection hint text.
  - `newWordImageFile` — module-level `Blob | null`, the pending screenshot.
  - `armScreenshotZone()` → `void`
  - `handleNewWordPaste(event: ClipboardEvent)` → `void`
  - `clearNewWordImage()` → `void`
  - `uploadNewWordImage(wordId: number)` → `Promise<boolean>` — `true` on success. Used by Task 4.

- [ ] **Step 1: Add the function section**

In `static/js/app.js`, find this divider (it follows `removeWordImage()`):

```javascript
// ============================================
// API Functions
// ============================================
```

Insert this **before** that divider:

```javascript
// ============================================
// Add Word Screenshot Functions
// ============================================

// Clipboard image types accepted for a new word's screenshot.
// SVG is deliberately excluded: it would pass an "image/" prefix test but
// Pillow cannot decode it, so it would fail server-side with a 500 only
// after the word had already been created.
const NEW_WORD_IMAGE_TYPES = [
    'image/png',
    'image/jpeg',
    'image/gif',
    'image/webp',
    'image/bmp'
];

const NO_IMAGE_MESSAGE = '❌ No image found in clipboard.';

// Pending screenshot for the Add New Word modal. Deliberately separate from
// currentPastedFile, which belongs to the existing pasteImageModal flow.
let newWordImageFile = null;

/**
 * Arm the paste zone so the next Ctrl+V is captured
 */
function armScreenshotZone() {
    Elements.newWordPasteZone.classList.add('armed');
    Elements.newWordPasteHint.textContent = 'Press Ctrl+V';
    Elements.newWordPasteZone.focus();
}

/**
 * Handle a paste into the new word screenshot zone
 *
 * Only image files are accepted. Text, rich text and non-image files are
 * discarded without being attached or inserted anywhere.
 */
function handleNewWordPaste(event) {
    // Runs first and unconditionally, so no default paste behaviour occurs
    // regardless of what the clipboard holds.
    event.preventDefault();

    const items = event.clipboardData ? event.clipboardData.items : [];

    for (const item of items) {
        // Copied text arrives as kind 'string' and is never a file.
        if (item.kind !== 'file') continue;

        // A file copied in Explorer is kind 'file' but carries its own MIME
        // type, so the allowlist is what rejects a .pdf or .docx.
        if (!NEW_WORD_IMAGE_TYPES.includes(item.type)) continue;

        const blob = item.getAsFile();
        if (!blob) continue;

        newWordImageFile = blob;

        const reader = new FileReader();
        reader.onload = function (e) {
            Elements.newWordThumb.src = e.target.result;
            Elements.newWordThumb.style.display = 'block';
            Elements.newWordPastePlaceholder.style.display = 'none';
            Elements.removeScreenshotBtn.style.display = 'inline-block';
            Elements.newWordPasteHint.textContent = '';
        };
        reader.readAsDataURL(blob);

        Elements.newWordPasteZone.classList.remove('armed');
        return;
    }

    // Nothing qualified. A mixed clipboard holding both an image and text
    // would have returned above, so reaching here means no usable image.
    Elements.newWordPasteHint.textContent = NO_IMAGE_MESSAGE;
    setTimeout(() => {
        if (Elements.newWordPasteHint.textContent === NO_IMAGE_MESSAGE) {
            Elements.newWordPasteHint.textContent = '';
        }
    }, 3000);
}

/**
 * Clear any pending screenshot and reset the control to its empty state
 */
function clearNewWordImage() {
    newWordImageFile = null;
    Elements.newWordThumb.src = '';
    Elements.newWordThumb.style.display = 'none';
    Elements.newWordPastePlaceholder.style.display = 'block';
    Elements.removeScreenshotBtn.style.display = 'none';
    Elements.newWordPasteHint.textContent = '';
    Elements.newWordPasteZone.classList.remove('armed');
}

/**
 * Upload the pending screenshot to a newly created word
 *
 * @param {number} wordId - ID returned by POST /api/words
 * @returns {Promise<boolean>} true if the image was stored
 */
async function uploadNewWordImage(wordId) {
    try {
        const formData = new FormData();
        formData.append('image', newWordImageFile);

        const response = await fetch(`/api/words/${wordId}/image`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        return data.success === true;
    } catch (error) {
        console.error('Error uploading new word screenshot:', error);
        return false;
    }
}
```

- [ ] **Step 2: Verify nothing broke**

```bash
conda activate bkdict
python app.py
```

Open `http://localhost:5001`. Confirm with F12 open: the page loads, the console is clean, and adding a word still works exactly as before. The screenshot control is still inert — nothing is wired yet. Stop the server.

- [ ] **Step 3: Commit**

```bash
git add static/js/app.js
git commit -m "Add image-only clipboard paste handlers for new word screenshots"
```

---

### Task 3: Wire the control up

Connects markup to handlers. This is the first point the feature is live.

**Files:**
- Modify: `static/js/app.js` (3 sites: the `Elements` object ~line 143, `initializeElements()` ~line 359, listener registration ~line 414)
- Modify: `static/js/app.js` — `openAddWordModal()` ~line 1442

**Interfaces:**
- Consumes: DOM IDs from Task 1; `armScreenshotZone`, `clearNewWordImage`, `handleNewWordPaste` from Task 2.
- Produces: `Elements.newWordPasteZone`, `Elements.newWordPastePlaceholder`, `Elements.newWordThumb`, `Elements.attachScreenshotBtn`, `Elements.removeScreenshotBtn`, `Elements.newWordPasteHint`.

- [ ] **Step 1: Declare the element slots**

Find the end of the `Elements` object:

```javascript
    removeImageBtn: null,
    imageDisplayTitle: null
};
```

Replace with:

```javascript
    removeImageBtn: null,
    imageDisplayTitle: null,

    // Add Word Screenshot
    newWordPasteZone: null,
    newWordPastePlaceholder: null,
    newWordThumb: null,
    attachScreenshotBtn: null,
    removeScreenshotBtn: null,
    newWordPasteHint: null
};
```

- [ ] **Step 2: Look the elements up**

Find the last lines of `initializeElements()`:

```javascript
    Elements.imageDisplayTitle = document.getElementById('imageDisplayTitle');
}
```

Replace with:

```javascript
    Elements.imageDisplayTitle = document.getElementById('imageDisplayTitle');

    // Add Word Screenshot
    Elements.newWordPasteZone = document.getElementById('newWordPasteZone');
    Elements.newWordPastePlaceholder = document.getElementById('newWordPastePlaceholder');
    Elements.newWordThumb = document.getElementById('newWordThumb');
    Elements.attachScreenshotBtn = document.getElementById('attachScreenshotBtn');
    Elements.removeScreenshotBtn = document.getElementById('removeScreenshotBtn');
    Elements.newWordPasteHint = document.getElementById('newWordPasteHint');
}
```

- [ ] **Step 3: Register the listeners**

Find this line in the "Add Word Modal" listener group:

```javascript
    Elements.toggleCategoryBtn.addEventListener('click', toggleNewCategoryInput);
```

Insert **after** it:

```javascript
    Elements.attachScreenshotBtn.addEventListener('click', armScreenshotZone);
    Elements.removeScreenshotBtn.addEventListener('click', clearNewWordImage);
    Elements.newWordPasteZone.addEventListener('paste', handleNewWordPaste);
```

The `paste` listener attaches to the zone element only. Do not attach it to `document`, `window`, or `#addWordModal` — that binding choice is the structural guarantee that Ctrl+V still pastes text normally into the Word, Translation, and Example Sentences fields.

- [ ] **Step 4: Reset the control when the modal opens**

In `openAddWordModal()`, find:

```javascript
    Elements.addWordStatus.textContent = '';
    Elements.addWordStatus.className = 'form-status';
```

Replace with:

```javascript
    Elements.addWordStatus.textContent = '';
    Elements.addWordStatus.className = 'form-status';
    clearNewWordImage();
```

This is what guarantees a cancelled or completed add never leaks its image into the next one.

- [ ] **Step 5: Verify paste behaviour in the browser**

```bash
conda activate bkdict
python app.py
```

At `http://localhost:5001`, open **✨ Add New Word** and confirm every row:

| Action | Expected |
| --- | --- |
| Snip a screenshot (Win+Shift+S), click `📷 Attach Screenshot` | Box highlights, hint reads "Press Ctrl+V" |
| Press Ctrl+V | Thumbnail appears, `✕ Remove` appears, hint clears |
| Click `✕ Remove` | Box returns to "No image", Remove hides |
| Copy plain text, click `📷 Attach Screenshot`, Ctrl+V | Hint reads "❌ No image found in clipboard.", **no text appears anywhere**, box stays empty; hint clears after ~3s |
| Copy text, click into **Translation**, Ctrl+V | Text pastes into the field normally, nothing attaches |
| Attach an image, press Cancel, reopen the modal | Control is empty |

Check the console for errors. Stop the server.

- [ ] **Step 6: Commit**

```bash
git add static/js/app.js
git commit -m "Wire up screenshot control refs, listeners and modal reset"
```

---

### Task 4: Upload on submit, with failure warning

Connects the pending blob to word creation.

**Files:**
- Modify: `static/js/app.js` — `submitNewWord()`, the `if (data.success) {` branch (~line 1791) and its close timer (~line 1811)

**Interfaces:**
- Consumes: `newWordImageFile` and `uploadNewWordImage(wordId)` from Task 2; `data.word_id` from the existing `POST /api/words` response.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Upload before reporting success**

In `submitNewWord()`, find:

```javascript
        if (data.success) {
            Elements.addWordStatus.textContent = `✅ ${data.message}`;
            Elements.addWordStatus.className = 'form-status success';
```

Replace with:

```javascript
        if (data.success) {
            let imageFailed = false;

            // Attach the pending screenshot to the word that was just created.
            // Awaited here so the outcome is known before the close timer starts.
            if (newWordImageFile && data.word_id) {
                Elements.addWordStatus.textContent = '⏳ Uploading screenshot...';
                Elements.addWordStatus.className = 'form-status';
                imageFailed = !(await uploadNewWordImage(data.word_id));
            }

            if (imageFailed) {
                Elements.addWordStatus.textContent = '⚠️ Word added, but screenshot failed to upload';
                Elements.addWordStatus.className = 'form-status error';
            } else {
                Elements.addWordStatus.textContent = `✅ ${data.message}`;
                Elements.addWordStatus.className = 'form-status success';
            }
```

- [ ] **Step 2: Extend the close delay when the upload failed**

Still inside the `if (data.success)` branch, find:

```javascript
            // Close modal after 1.5 seconds
            setTimeout(() => {
                closeAddWordModal();

                // If the word was added to current category, reload it
                if (AppState.currentCategory === category) {
                    loadWord(category, 0);  // Load first word (the newly added one if sorted by recent edits)
                }
            }, 1500);
```

Replace with:

```javascript
            // Close modal after a short delay, held longer when the screenshot
            // warning needs to stay readable
            setTimeout(() => {
                closeAddWordModal();

                // If the word was added to current category, reload it
                if (AppState.currentCategory === category) {
                    loadWord(category, 0);  // Load first word (the newly added one if sorted by recent edits)
                }
            }, imageFailed ? 4000 : 1500);
```

Do not change the `else` branch that handles duplicates and errors. A 409 duplicate must keep leaving the thumbnail attached so the user can change category and resubmit.

- [ ] **Step 3: Verify the happy path**

```bash
conda activate bkdict
python app.py
```

At `http://localhost:5001`: snip a screenshot, open **✨ Add New Word**, attach it, fill in word, translation and category, click **Add Word**. Expected: brief "Uploading screenshot...", then the success message, then the modal closes and the word card shows the image.

Confirm a new `.jpg` landed in the image folder:

```bash
ls -lt static/images/word_images | head -3
```

- [ ] **Step 4: Verify a word with no screenshot still works**

Add another word without attaching anything. Expected: behaves exactly as before, no upload request in the Network tab, modal closes after ~1.5s.

- [ ] **Step 5: Verify the duplicate case**

Attach a screenshot, then submit a word/category pair that already exists. Expected: the duplicate warning with its "Go to Word" button appears, the modal stays open, and the thumbnail is **still attached**. Change the category and resubmit — it saves with the image.

- [ ] **Step 6: Commit**

```bash
git add static/js/app.js
git commit -m "Upload pending screenshot after new word is created"
```

---

### Task 5: Full spec verification pass

Runs the complete manual checklist from the spec. Nothing ships until this passes.

**Files:** none modified unless a defect is found.

**Interfaces:**
- Consumes: the finished feature.
- Produces: a verified branch ready for review.

- [ ] **Step 1: Run the automated suite**

```bash
conda activate bkdict
pytest test/test_basic.py -v
```

Expected: all PASS, including the 2 tests added in Task 1. Record the actual pass count.

- [ ] **Step 2: Run the spec's manual checklist**

Start the server, then walk all 9 steps from the "Manual" section of `docs/superpowers/specs/2026-08-01-add-word-screenshot-design.md`. The rejection cases are the point of this pass — do not skip them:

1. Snip, click Attach, Ctrl+V → thumbnail appears.
2. Click Remove → clears.
3. Re-attach, fill form, submit → word saves, image shows on card.
4. Copy text, click into Translation, Ctrl+V → text pastes normally.
5. Copy text, click Attach, Ctrl+V → "no image" hint, no text inserted.
6. Repeat 5 with rich text copied from a web page, and again with a `.pdf` copied in Explorer → both rejected identically.
7. Copy an image from a web page (puts HTML **and** image on the clipboard), attach → image is used, no text leaks in.
8. Attach, Cancel, reopen → control empty.
9. Submit a duplicate word → error shown, thumbnail still attached.

- [ ] **Step 3: Check the console**

With F12 open, repeat steps 1, 5 and 7. Expected: no uncaught errors. The `console.error` in `uploadNewWordImage` should not fire during normal use.

- [ ] **Step 4: Confirm nothing else regressed**

Open an existing word that already has an image and click its image button. Expected: the original `pasteImageModal` flow still works unchanged — this confirms the new code did not disturb `currentPastedFile`.

- [ ] **Step 5: Report results**

Report the pytest output and the outcome of each manual step. If any step failed, fix it and re-run this whole task — do not report completion with a failing step.

- [ ] **Step 6: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "Fix issues found during screenshot feature verification"
```

If no fixes were needed, skip this step — do not create an empty commit.

---

## Rollback

Per the spec, the whole feature reverts cleanly:

```bash
git checkout development
git branch -D feature/add-word-screenshot
```

There is no migration to unwind and `app.py` is untouched. Screenshots already uploaded through the feature stay in `static/images/word_images/` and their words keep their `image_file` value; those words then behave exactly like words whose images were attached through the existing card button.
