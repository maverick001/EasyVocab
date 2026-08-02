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
- Strict image-only validation of pasted content.
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
6. **Only image data is ever accepted.** Pasting text into the armed zone must
   attach nothing and insert nothing. See "Rejecting non-image content".

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
| `static/css/style.css` | Button row layout and focus ring |
| `test/test_basic.py` | Markup-presence assertions |

`app.py` is not modified.

### Markup

> **Revised 2026-08-02.** The control was originally specified as a labelled row
> containing a 96×64 dashed preview box, an attach button and a hint line. In
> review that read as too heavy for an optional field, so it was reduced to a
> single button that carries its own state. The validation behaviour below is
> unchanged; only the presentation and the paste target moved.

A new `.form-group` is inserted in `#addWordModal`, after the Example Sentences
group and before `#addWordStatus`. It contains two buttons and nothing else —
no field label, no placeholder box, no hint line:

- `#attachScreenshotBtn` — the attach control **and** the paste target. Its
  label is the entire state display:

  | State | Label |
  | --- | --- |
  | Idle | `📷 Attach Image` |
  | Armed | `📋 Press Ctrl+V` |
  | Attached | `✅ Image Attached` |
  | Rejected | `❌ Not an image` (reverts after 2s) |

- `#removeScreenshotBtn` — a compact `✕`, hidden until an image is attached.

Both carry `type="button"` to match the modal's existing buttons and avoid
implicit form submission.

There is no thumbnail preview. Attaching the wrong image is corrected by
clicking the button again and pasting a replacement.

### Interaction

1. Clicking `#attachScreenshotBtn` sets its label to `📋 Press Ctrl+V` and
   focuses it. A `<button>` is natively focusable, so no `tabindex` is needed.
2. The `paste` listener is bound **to `#attachScreenshotBtn` only** — never to
   `document` or to the modal. Because a paste event only reaches an element
   while that element holds focus, Ctrl+V inside the Word, Translation, or
   Example Sentences fields keeps pasting text normally. This is a structural
   guarantee, not a focus check that could be got wrong.
3. On paste, the handler calls `event.preventDefault()` and scans
   `clipboardData.items` for a qualifying image (see below). If one is found,
   the blob is stored, the label becomes `✅ Image Attached` and
   `#removeScreenshotBtn` appears. If nothing qualifies, the label becomes
   `❌ Not an image` and reverts after 2 seconds to whichever state applies.
4. `#removeScreenshotBtn` discards the blob and returns the button to idle.

### Rejecting non-image content

Pasting text into the armed zone must attach nothing and insert nothing. Three
independent guards enforce this:

1. **`event.preventDefault()` runs first, unconditionally** — before any
   inspection of the clipboard, and regardless of whether the paste is later
   accepted. No default paste behaviour of any kind occurs.
2. **The paste target is a `<button>`, not an input or a `contenteditable`.**
   Text pasted onto it has nowhere to render even if a future edit dropped the
   `preventDefault()` call. Do not change this element to an input or add
   `contenteditable` to it — that would silently remove this guard.
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
| Clipboard holds plain text | Nothing attached, nothing inserted; `❌ Not an image` |
| Clipboard holds rich text (`text/html`) | Nothing attached, nothing inserted; `❌ Not an image` |
| Clipboard holds a non-image file (`.pdf`, `.docx`) | Rejected by the type allowlist; `❌ Not an image` |
| Clipboard holds an image *and* text | Image attached, text ignored |
| Clipboard holds an SVG (`image/svg+xml`) | Rejected client-side, before any word is created |
| Clipboard is empty | Nothing attached; `❌ Not an image` |
| Rejected while an image is already attached | Label reverts to `✅ Image Attached`, the existing image is kept |
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
5. Copy some text. Click `📷 Attach Image`, press Ctrl+V — label shows
   `❌ Not an image`, no text appears anywhere in the modal, and nothing is
   attached.
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
