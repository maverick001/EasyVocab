# Attach a Screenshot When Adding a New Word

**Date:** 2026-08-01
**Branch:** `feature/add-word-screenshot`
**Status:** Approved, pending implementation

## Problem

The "Add New Word" modal captures word, translation, category, and example
sentences. It cannot capture an image.

An image can only be attached *after* a word exists, via the image button on the
word card, which opens the `pasteImageModal` and posts to
`POST /api/words/<word_id>/image`. Adding a word with a screenshot therefore
takes two separate passes through the UI.

This feature lets the user paste a screenshot directly into the Add New Word
modal, so word and image are captured in one pass.

## What Already Exists

The image infrastructure is complete and is reused unchanged:

| Piece | Location |
| --- | --- |
| `words.image_file` column (`VARCHAR(255)`, nullable) | `app.py:220` `ensure_image_file_column()` |
| Upload endpoint: accepts a file, compresses to JPEG under 500KB, saves to `static/images/word_images/`, updates the row | `app.py:2341` `upload_word_image()` |
| Clipboard paste + preview flow for existing words | `app.js:594-700` (`pasteImageModal`) |
| Word creation, returns `word_id` on success | `app.py:725` / `app.js:1737` |

`static/images/word_images` is gitignored, so uploaded files never enter the
repository.

## Scope

### In scope

- An "Attach Image" button inside the Add New Word modal.
- Clipboard paste (Ctrl+V) as the only input method.
- Strict image-only validation of pasted content, in both flows.
- A remove action, before the word is submitted.
- Uploading the pasted image immediately after the word is created.

### Out of scope

- File-picker / browse-for-file input.
- Drag and drop.
- Resizing or changing image dimensions. The existing compression behaviour
  (quality-reduce to under 500KB, original dimensions preserved) is kept as-is.
- Redesigning the popup itself. It is reused as-is, apart from the tightened
  clipboard filter and the mode-dependent confirm label.
- Any change to `app.py`.

## Decisions

These were settled during brainstorming and are fixed:

1. **Clipboard paste only.** Screenshots reach the clipboard directly via
   Win+Shift+S; requiring a saved file first would add a step.
2. ~~**Inline in the form**, not a stacked modal.~~ **Superseded 2026-08-02:**
   the attach button opens the same popup the word card's image button opens,
   so both ways of adding an image look and behave identically.
3. **Existing compression kept.** No resize, no new dimension cap.
4. **The attach button must be clicked before Ctrl+V works.** There is no
   document-level or modal-level paste handler; paste is only captured inside
   the popup's own paste area.
5. **The word is kept if the image upload fails**, with a visible warning.
6. **Only image data is ever accepted.** Pasting text must attach nothing and
   insert nothing. See "Rejecting non-image content".

## Approach

**Create the word first, then upload the image.**

The pasted image is held in browser memory as a `Blob`. On submit,
`POST /api/words` runs exactly as it does today; the `word_id` it returns is
then used to `POST /api/words/<word_id>/image` — the endpoint that already
exists and already performs the required compression.

This adds no server-side surface area. Two alternatives were rejected:

- **Extend `POST /api/words` to accept multipart.** Would save one round trip,
  but requires a heavily-used JSON endpoint to handle two body formats, risking
  regressions in every existing caller for no user-visible gain.
- **Stage the image to a temporary endpoint before creating the word.** Needs a
  new endpoint plus cleanup for images belonging to abandoned submissions.

The create-then-upload ordering is safe because a rejected duplicate returns 409
without creating a row, so a failed submission can never leave an orphaned image
attached to the wrong word.

## Design

### Files changed

| File | Change |
| --- | --- |
| `templates/index.html` | New form group in `#addWordModal` |
| `static/js/app.js` | Element refs, listeners, paste/clear handlers, submit hook |
| `static/css/style.css` | Button row layout |
| `test/test_basic.py` | Markup-presence assertions |

`app.py` is not modified.

### Markup

> **Revised 2026-08-02 (twice).** Originally specified as a labelled row with a
> 96×64 dashed preview box, an attach button and a hint line; reduced to a
> single self-describing button; then changed again so the button **opens the
> existing `pasteImageModal`** rather than capturing paste inline. The new word
> flow and the word card flow now share one popup. See "Shared paste modal".

A new `.form-group` is inserted in `#addWordModal`, after the Example Sentences
group and before `#addWordStatus`. It contains two buttons and nothing else —
no field label, no placeholder box, no hint line:

- `#attachScreenshotBtn` — opens the shared paste popup. Its label reports
  state:

  | State | Label |
  | --- | --- |
  | Idle | `📷 Attach Image` |
  | Attached | `✅ Image Attached` |

- `#removeScreenshotBtn` — a compact `✕`, hidden until an image is attached.

Both carry `type="button"` to match the modal's existing buttons and avoid
implicit form submission.

Preview happens inside the popup, so the form itself shows no thumbnail.
Attaching the wrong image is corrected by clicking the button again and
pasting a replacement.

### Shared paste modal

`#attachScreenshotBtn` opens `#pasteImageModal` — the same popup the word
card's image button opens. One popup, one paste area, one preview, serving two
flows. The difference is what happens on confirm, which a module-level
`pasteModalMode` decides:

| Mode | Set by | On confirm |
| --- | --- | --- |
| `'existing'` | `openPasteModal()`, from the word card button | Uploads immediately to `/api/words/<id>/image`, as it always has |
| `'newWord'` | `openNewWordPasteModal()`, from the attach button | Stores the blob in `newWordImageFile` and closes; nothing is sent yet |

The confirm button's label follows the mode via `pasteConfirmLabel()` —
`Save Image` for an existing word, `Attach Image` for a new one — because in
new-word mode nothing is being saved to the server.

`uploadPastedImage()` returns early in `'newWord'` mode. That early return is
what keeps the new flow from calling an endpoint that needs a `word_id` the
word does not have yet.

### Interaction

1. Clicking `#attachScreenshotBtn` sets the mode to `'newWord'` and opens the
   popup, which focuses its paste area and resets its state.
2. Ctrl+V in the popup previews the image, exactly as the existing flow does.
3. Confirming stores the blob, closes the popup, sets the button label to
   `✅ Image Attached` and reveals `#removeScreenshotBtn`.
4. Cancelling the popup leaves any previously attached image untouched.
5. `#removeScreenshotBtn` discards the blob and returns the button to idle.

### Rejecting non-image content

Pasting text must attach nothing and insert nothing. Three independent guards
enforce this:

Because both flows now share `handlePasteEvent`, these guards protect the word
card flow too. That handler previously filtered with
`item.type.indexOf('image') === 0`, which accepted `image/svg+xml` and had no
`kind` check; it was tightened to the allowlist below as part of this change.
That also fixes a pre-existing bug where an SVG pasted onto an existing word
reached the server and returned a 500.

1. **`event.preventDefault()` runs first, unconditionally** — before any
   inspection of the clipboard, and regardless of whether the paste is later
   accepted. No default paste behaviour of any kind occurs.
2. **The paste target is `#pasteArea`, a `div` with `tabindex="0"`** — not an
   input and not a `contenteditable`. Text pasted onto it has nowhere to render
   even if a future edit dropped the `preventDefault()` call. Do not turn this
   element into an input or add `contenteditable` — that would silently remove
   this guard.
3. **An explicit allowlist decides what is accepted.** A clipboard item
   qualifies only when *both* hold:
   - `item.kind === 'file'`, and
   - `item.type` is one of `image/png`, `image/jpeg`, `image/gif`,
     `image/webp`, `image/bmp`.

   The blob is used only if `item.getAsFile()` also returns non-null.

Why each half of the allowlist matters:

- **`kind === 'file'`** rejects copied text. Text from an editor or browser
  arrives as `kind: 'string'` with type `text/plain`, and rich text adds a
  second `text/html` item. Neither is a file, so neither is considered.
- **The type allowlist** rejects non-image *files*. A file copied in Windows
  Explorer arrives as `kind: 'file'` carrying its own MIME type, so a copied
  `.pdf` or `.docx` would pass a `kind` check alone.

The allowlist is used in preference to a `type.startsWith('image/')` test
because `image/svg+xml` passes a prefix test but Pillow cannot open SVG. That
would produce a 500 `Image processing failed` from `app.py:2423` *after* the
word had already been created — precisely the failure this filtering exists to
prevent. Screenshots are always PNG (Win+Shift+S) or JPEG, so the allowlist
costs nothing in practice.

**Mixed clipboards prefer the image.** Copying an image from a web page
typically yields a `text/html` item alongside an `image/png` item. The scan
takes the first qualifying image and ignores every other item, so this case
attaches the image rather than falling through to the "no image" message.

Server-side rejection remains as a last line of defence — `Image.open()` raises
for anything it cannot decode — but it is never expected to fire, and the client
filtering exists so that it does not, since by then the word already exists.

### State

A module-level `newWordImageFile` holds the pending blob. It is deliberately
separate from the existing `currentPastedFile` used by `pasteImageModal`, so the
two flows cannot interfere with each other.

`openAddWordModal()` clears it. A cancelled or completed add therefore never
leaks an image into the next one.

### Submit flow

`submitNewWord()` is unchanged up to the point where `data.success` is true.
Then, if `newWordImageFile` is set:

1. Status shows an uploading message.
2. `POST /api/words/<data.word_id>/image` with the blob as `FormData` field
   `image` — the same field name the existing flow uses.
3. On success, the normal success message and the existing 1.5s close timer
   proceed as today.
4. On failure, the status reads `⚠️ Word added, but screenshot failed to upload`
   and the close delay is extended to 4 seconds so the warning is readable. The
   word remains saved and the image can be attached later through the existing
   image button on the word card.

The upload is awaited **before** the close timer starts. Otherwise the modal
could close before the outcome is known.

### Error and edge cases

| Case | Behaviour |
| --- | --- |
| Clipboard holds plain text | Nothing attached, nothing inserted; `❌ No image found in clipboard.` |
| Clipboard holds rich text (`text/html`) | Nothing attached, nothing inserted; `❌ No image found in clipboard.` |
| Clipboard holds a non-image file (`.pdf`, `.docx`) | Rejected by the type allowlist; `❌ No image found in clipboard.` |
| Clipboard holds an image *and* text | Image attached, text ignored |
| Clipboard holds an SVG (`image/svg+xml`) | Rejected client-side, before any word is created |
| Clipboard is empty | Nothing attached; `❌ No image found in clipboard.` |
| Rejected while an image is already attached | Popup shows the error; cancelling keeps the existing image |
| Duplicate word (409) | No word created, existing error shown, pending image stays attached so the user can change category and resubmit |
| Validation fails (missing word/translation/category) | Existing early return; image stays attached |
| Modal cancelled, then reopened | Image cleared |
| Image upload fails after word created | Word kept, warning shown (see above) |
| Word added with no screenshot | Identical to today's behaviour |

## Testing

### Automated

`test/test_basic.py` runs without a database and covers structure, not
behaviour. Two assertions are added in that existing style, verifying
`templates/index.html` contains `attachScreenshotBtn` and
`removeScreenshotBtn`.

These guard against the markup being removed. They do not test the paste flow;
clipboard interaction is not reachable from this suite.

### Manual

Run in the `bkdict` conda environment on `http://localhost:5001`:

1. Snip a screenshot (Win+Shift+S). Open Add New Word. Click
   `📷 Attach Image`, press Ctrl+V — label becomes `✅ Image Attached`.
2. Click `✕` — label returns to `📷 Attach Image`, the `✕` hides.
3. Re-attach, fill in word/translation/category, submit — word saves and the
   image shows on the word card.
4. Copy some text. Click into Translation, press Ctrl+V — text pastes normally,
   no screenshot is attached.
5. Copy some text. Click `📷 Attach Image`, press Ctrl+V in the popup — it
   shows "No image found in clipboard.", no text appears anywhere, and the
   confirm button stays disabled.
6. Repeat step 5 with rich text copied from a web page, and again with a
   non-image file copied in Explorer (e.g. a `.pdf`). Both must be rejected the
   same way.
7. Copy an image from a web page, which puts both HTML and an image on the
   clipboard. Attach it — the image is used, no text leaks in.
8. Attach an image, then Cancel. Reopen the modal — the control is empty.
9. Submit a word that already exists in the chosen category — duplicate error
   shows and the button still reads `✅ Image Attached`.

## Reversibility

The change is designed to be undone cleanly:

- **All work is on `feature/add-word-screenshot`.** Deleting the branch, or
  `git revert`-ing the implementation commit on `development`, removes the
  feature entirely.
- **No database migration.** The `image_file` column already exists and is
  already written to by the current image feature. Nothing is added, altered, or
  backfilled, so there is no schema state to roll back.
- **No `app.py` change.** No endpoint is added, modified, or removed, so
  reverting cannot break any other caller.
- **Existing flows are untouched.** `pasteImageModal` and its
  `currentPastedFile` state are not modified, so a revert restores prior
  behaviour exactly.

One residue survives a revert: JPEGs already uploaded through this feature
remain in `static/images/word_images/`, and the words pointing at them keep
their `image_file` value. This is harmless — those words display and behave
exactly like words whose images were attached through the existing card button,
and the files are gitignored so they never entered the repository. If a full
purge is wanted, the images must be removed through the existing UI before
reverting.
