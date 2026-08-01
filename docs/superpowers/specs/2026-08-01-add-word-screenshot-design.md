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

- A "Screenshot (optional)" control inside the Add New Word modal.
- Clipboard paste (Ctrl+V) as the only input method.
- Thumbnail preview and a remove action, before the word is submitted.
- Uploading the pasted image immediately after the word is created.

### Out of scope

- File-picker / browse-for-file input.
- Drag and drop.
- Resizing or changing image dimensions. The existing compression behaviour
  (quality-reduce to under 500KB, original dimensions preserved) is kept as-is.
- Any change to the existing `pasteImageModal` flow for existing words.
- Any change to `app.py`.

## Decisions

These were settled during brainstorming and are fixed:

1. **Clipboard paste only.** Screenshots reach the clipboard directly via
   Win+Shift+S; requiring a saved file first would add a step.
2. **Inline in the form**, not a stacked modal. The attachment stays visible
   while the rest of the form is filled in.
3. **Existing compression kept.** No resize, no new dimension cap.
4. **The attach button must be clicked before Ctrl+V works.** There is no
   document-level or modal-level paste handler.
5. **The word is kept if the image upload fails**, with a visible warning.

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
| `static/css/style.css` | Styles for the thumbnail and its armed state |
| `test/test_basic.py` | Markup-presence assertions |

`app.py` is not modified.

### Markup

A new `.form-group` is inserted in `#addWordModal`, after the Example Sentences
group and before `#addWordStatus`:

- `#newWordPasteZone` — a roughly 96×64 thumbnail box with `tabindex="0"` so it
  can receive focus and therefore paste events. Shows a placeholder until an
  image is attached.
- `#newWordThumb` — the `<img>` preview, hidden until an image is attached.
- `#attachScreenshotBtn` — `📷 Attach Screenshot`.
- `#removeScreenshotBtn` — `✕ Remove`, hidden until an image is attached.
- `#newWordPasteHint` — a small hint line used for prompts and errors.

All buttons carry `type="button"` to match the modal's existing buttons and
avoid implicit form submission.

### Interaction

1. Clicking `#attachScreenshotBtn` adds an `.armed` class to
   `#newWordPasteZone`, sets the hint to `Press Ctrl+V`, and focuses the zone.
2. The `paste` listener is bound **to `#newWordPasteZone` only** — never to
   `document` or to the modal. Because a paste event only reaches the zone when
   the zone holds focus, Ctrl+V inside the Word, Translation, or Example
   Sentences fields keeps pasting text normally. This is a structural guarantee,
   not a focus check that could be got wrong.
3. On paste, the handler scans `clipboardData.items` for an `image/*` item. If
   found, the blob is stored, a `FileReader` renders it into `#newWordThumb`,
   the placeholder hides, and `#removeScreenshotBtn` appears. If no image is
   found, the hint reads `❌ No image found in clipboard.` and clears after
   3 seconds, matching the wording and timing of the existing paste modal.
4. `#removeScreenshotBtn` discards the blob and returns the control to its empty
   state.

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
| Clipboard holds text, not an image | Hint shows the "no image" message; nothing is attached |
| Duplicate word (409) | No word created, existing error shown, pending image stays attached so the user can change category and resubmit |
| Validation fails (missing word/translation/category) | Existing early return; image stays attached |
| Modal cancelled, then reopened | Image cleared |
| Image upload fails after word created | Word kept, warning shown (see above) |
| Word added with no screenshot | Identical to today's behaviour |

## Testing

### Automated

`test/test_basic.py` runs without a database and covers structure, not
behaviour. Two assertions are added in that existing style, verifying
`templates/index.html` contains `newWordPasteZone` and `attachScreenshotBtn`.

These guard against the markup being removed. They do not test the paste flow;
clipboard interaction is not reachable from this suite.

### Manual

Run in the `bkdict` conda environment on `http://localhost:5001`:

1. Snip a screenshot (Win+Shift+S). Open Add New Word. Click
   `📷 Attach Screenshot`, press Ctrl+V — thumbnail appears.
2. Click `✕ Remove` — thumbnail clears, Remove hides.
3. Re-attach, fill in word/translation/category, submit — word saves and the
   image shows on the word card.
4. Copy some text. Click into Translation, press Ctrl+V — text pastes normally,
   no screenshot is attached.
5. Click `📷 Attach Screenshot` with text on the clipboard, press Ctrl+V —
   "no image found" hint appears.
6. Attach an image, then Cancel. Reopen the modal — the control is empty.
7. Submit a word that already exists in the chosen category — duplicate error
   shows and the thumbnail is still attached.

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
