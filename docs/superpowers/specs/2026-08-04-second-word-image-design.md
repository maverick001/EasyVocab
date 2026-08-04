# A Second Image Per Word

**Date:** 2026-08-04
**Branch:** `feature/second-word-image`
**Status:** Approved, pending implementation

## Problem

A word holds at most one image. Attaching a second screenshot means replacing
the first and losing it.

Two screenshots are often worth keeping together — a dictionary entry and a
sentence showing the word in use, or two senses of the same word. Today the only
way to keep both is to create a duplicate word.

This feature lets a word hold two images, shown stacked in a scrollable pane so
both can be viewed without leaving the modal.

## What Already Exists

| Piece | Location |
| --- | --- |
| `words.image_file` (`VARCHAR(255)`, nullable) and its auto-migration | `app.py:220` `ensure_image_file_column()` |
| Upload endpoint: compresses to JPEG under 500KB, saves to `static/images/word_images/`, writes `image_file` | `app.py:2341` `upload_word_image()` |
| Image removal, via the generic word PATCH with `image_file: ''` | `app.py:1087` / `app.js:778` |
| Shared paste popup (`#pasteImageModal`) with a mode switch | `app.js:606-753` |
| Display modal (`#imageDisplayModal`), one `<img>` plus Change/Remove/Close | `index.html:315` / `app.js:766` |
| Quiz image rendering, reads `image_file` | `quiz.js:326` `showWordImage()` |
| Quiz "Image Only" filter, tests `image_file IS NOT NULL` | `app.py:1899` |

`static/images/word_images` is gitignored, so uploaded files never enter the
repository.

## Scope

### In scope

- A second image slot per word, with a hard cap of two.
- Per-image `Replace` and `Remove` controls in the display modal.
- An `Add Image` action that fills the free slot.
- A vertically scrolling image pane with a native scroll bar on the right.
- Automatic compaction, so slot 1 is always filled before slot 2.
- A filename collision fix that this feature would otherwise make reachable.

### Out of scope

- More than two images. The cap is deliberate; see "Decisions".
- Attaching two images from the Add New Word modal. That flow keeps its single
  attach button and is not modified.
- Deleting orphaned image files from disk. Files are already never deleted on
  replacement today; this change does not widen that, and does not fix it.
- Reordering images, captions, per-image metadata.
- Showing both images in quiz mode.
- Drag and drop, or a file picker. Clipboard paste remains the only input.
- Any change to image compression or dimensions.

## Decisions

These were settled during brainstorming and are fixed:

1. **Exactly two images, not N.** A hard cap keeps the data model to one extra
   column on `words`. An unbounded count would need a `word_images` table and a
   migration of existing data, for a capability that is not currently wanted.
2. **"On top of" means *in addition to*, not layered.** The two images are
   separate and shown one above the other, never composited.
3. **Per-image `Replace` and `Remove` buttons**, sitting directly beneath each
   image, rather than footer buttons that act on whichever image is scrolled
   into view. A destructive action must be unambiguous about its target.
4. **Compaction on removal.** Removing image 1 slides image 2 up into slot 1.
   This is what lets quiz mode, the "Image Only" filter and the word card button
   keep reading `image_file` alone, unchanged.
5. **The Add New Word flow stays at one image.** A second image is added
   afterwards from the word card. This avoids reworking the just-merged
   new-word screenshot feature and avoids inventing a partial-failure path for
   two sequential uploads.
6. **Compaction is enforced on the server**, and `image_file` is removed from
   the generic PATCH endpoint's accepted fields, so no client can produce a word
   whose only image sits in slot 2.

## The Compaction Invariant

> `image_file_2` is non-null only when `image_file` is also non-null.

Equivalently: a word has an image in slot 2 only if it also has one in slot 1.

This single rule is what keeps the change small. Every existing consumer reads
`image_file` and only `image_file`; under this invariant, `image_file` is
non-null whenever the word has any image at all, so every one of those consumers
stays correct without modification.

Only two endpoints may write these columns — the upload endpoint and the delete
endpoint — and both maintain the invariant. Every existing word already
satisfies it, with `image_file_2` null, so no backfill is required.

## Approach

**Add one column, add a `slot` parameter to the existing upload endpoint, and
add a dedicated delete endpoint that removes and compacts atomically.**

The upload endpoint's `slot` defaults to `1`, so every existing caller — most
importantly the untouched Add New Word flow — keeps working with no edit.

Two alternatives were rejected:

- **Separate endpoints per slot** (`POST .../image/1`, `POST .../image/2`).
  Marginally more RESTful, but either duplicates the ~60-line Pillow
  compression block or forces a refactor of it, for no behavioural gain.
- **Client-orchestrated slots**, with the browser issuing PATCHes to shuffle
  columns. Rejected because compaction would become two round trips that can be
  interrupted between them, leaving a word with a hole in slot 1 — precisely
  the state the invariant forbids.

## Design

### Files changed

| File | Change |
| --- | --- |
| `app.py` | Second column migration; `slot` on upload; new delete endpoint; `image_file` dropped from PATCH; `image_file_2` added to three SELECTs; filename format |
| `templates/index.html` | Display modal body becomes a scroll container; footer buttons change |
| `static/js/app.js` | Render image blocks; per-slot handlers; paste target slot; re-render from server response |
| `static/css/style.css` | Scroll pane, image block, per-image button row |
| `test/test_basic.py` | Three structural assertions |

`quiz.js` and `templates/quiz.html` are **not** changed.

### Storage

```sql
words.image_file    VARCHAR(255) NULL   -- exists today, slot 1
words.image_file_2  VARCHAR(255) NULL   -- new, slot 2
```

`ensure_image_file_column()` (`app.py:220`) already performs an
`INFORMATION_SCHEMA` existence check and issues an `ALTER TABLE` when the column
is missing. It gains a second, identical check for `image_file_2`. The migration
therefore runs itself at startup and is a no-op once applied. No manual SQL.

### Endpoints

**`POST /api/words/<id>/image`** — gains an optional form field `slot`.

| `slot` | Behaviour |
| --- | --- |
| absent | Treated as `1`. Preserves every existing caller. |
| `1` | Writes `image_file`. |
| `2` | Writes `image_file_2`, but only if `image_file` is non-null; otherwise **409**. |
| anything else | **400**. |

All Pillow compression logic is unchanged: RGB conversion, JPEG at quality 95
stepping down by 5 until under 500KB, original dimensions preserved.

Its response gains both slot values, so the client can re-render from server
truth after an upload exactly as it does after a delete:
`{success, message, filename, image_file, image_file_2}`. The existing
`filename` key is kept so the Add New Word flow, which reads it, is unaffected.

**`DELETE /api/words/<id>/image/<slot>`** — new. Empties the slot and compacts:

- Removing slot 2: `SET image_file_2 = NULL`.
- Removing slot 1: `SET image_file = image_file_2, image_file_2 = NULL`. A
  single statement, so compaction cannot be interrupted part-way.

Returns the resulting `{success, image_file, image_file_2}`.

**`PATCH /api/words/<id>`** — `image_file` is removed from the accepted update
fields (`app.py:1087-1091`) and from the endpoint's docstring (`app.py:1048`).
It exists today only to serve image removal, which the delete endpoint now owns.
Removing it leaves exactly one route capable of emptying a slot, which is what
makes the invariant unbreakable. `app.js:960-962`, the client-side branch that
syncs local state when `image_file` appears in an update, is removed with it.

### Read paths

`image_file_2` is added to three `SELECT` lists, so the browser knows whether
slot 2 is filled: `app.py:689`, `app.py:698` (word fetch) and `app.py:992`
(word list).

Three read paths are deliberately left unchanged, and the invariant is what
makes that safe:

- **`quiz.js:327`** reads `currentWord.image_file`. A word always has a slot-1
  image if it has any image, so quiz mode keeps rendering one image.
- **`app.py:1899`**, the "Image Only" filter, tests
  `image_file IS NOT NULL AND image_file != ''`. Still correct, because no word
  can hide its only image in slot 2.
- **`app.py:1886`**, the quiz `SELECT`, does not need `image_file_2`, because
  quiz mode shows a single image.

### Filenames

`img_{word_id}_{timestamp}.jpg` becomes `img_{word_id}_{slot}_{timestamp}.jpg`.

`timestamp` is `int(time.time())`, at second resolution. Two uploads for the
same word within the same second currently produce the same filename and the
second silently overwrites the first. Today that requires an accidental
double-submit; a deliberate two-image flow makes it reachable. Including the
slot removes the collision.

Existing filenames are untouched and keep resolving. Nothing in the codebase
parses structure out of a filename.

### Display modal

The body of `#imageDisplayModal` becomes a vertically scrolling container
holding one or two **image blocks**. Each block is an image plus a row with that
image's `Replace` and `Remove` buttons, and carries its slot number on a
`data-slot` attribute so handlers never infer the slot from DOM position.

The container is `#imageScrollPane`, and the footer's add button is
`#addAnotherImageBtn`. Both ids are asserted by the automated tests.

The container has a fixed `max-height` of `60vh` with `overflow-y: auto`. This
produces a native browser scroll bar on the right, which drags, responds to the
wheel, and supports Page Up/Down and arrow keys without any custom code.

With one image the content fits and no scroll bar appears. With two it
overflows and the bar appears. The pane is sized so image 1 nearly fills it,
placing image 2 just far enough below that scrolling to it is an obvious,
deliberate action rather than something easily missed.

**Blocks are rendered in JavaScript**, from `AppState.currentWord.image_file`
and `.image_file_2`, rather than pre-written in `index.html` and toggled. One
code path serves the one-image and two-image cases, and no hidden second block
lingers in the DOM holding a `src` from a previously viewed word.

The footer becomes `Add Image` and `Close`. `Change Image` and `Remove` leave
the footer entirely, having become per-image. `Add Image` is hidden when both
slots are filled, so the two-image cap enforces itself in the UI rather than
surfacing as an error.

### Actions

All three actions reuse `#pasteImageModal` unchanged, through the mode
mechanism already present. `pasteModalMode` gains a companion module-level
`pasteTargetSlot` holding `1` or `2`. The `'newWord'` mode is not modified.

| Action | Effect |
| --- | --- |
| `Add Image` | Targets the free slot, opens the paste popup, uploads with that `slot` |
| `Replace` | Targets that block's slot, opens the same popup, uploads with that `slot`, overwriting only that column |
| `Remove` | Confirms, then `DELETE /api/words/<id>/image/<slot>` |

After any action, the response's `image_file` and `image_file_2` are written
into `AppState.currentWord` and the modal re-renders from them. **The client
never computes the post-compaction state itself.** Watching image 2 slide up
into slot 1 therefore requires no client-side shuffling logic.

### Word card button

`updateImageButtonState()` (`app.js:1124`) keeps its single argument and its two
states: `Add Image` with no image, `Display Image` with any. A two-image word
shows `Display Image`, the same as a one-image word. Because slot 1 fills
first, passing `image_file` alone remains correct and the function is not
modified.

`handleImageButtonClick()` (`app.js:617`) is also unchanged: an image present
opens the display modal, none opens the paste popup directly.

## Error and Edge Cases

### Server responses

| Case | Response |
| --- | --- |
| `slot=2` while slot 1 is empty | **409**, nothing written |
| `slot` not `1` or `2` | **400** |
| `slot` absent | Treated as `1` |
| `DELETE` on an already-empty slot | **404**, `no image in that slot` |
| Word id not found | **404**, as today |
| Pillow cannot decode the upload | **500** `Image processing failed`, as today; no column written |

The 409 and the empty-slot 404 exist for the two-tabs case: an image removed in
one tab, then acted on from the other tab's stale view. Normal client use
generates neither, because the client re-renders from the server's response
after every action.

### Client behaviour

Every failure leaves the word's images exactly as they were. A column is written
only after compression succeeds, and removal is a single statement, so there is
no partial state to recover from.

| Case | Behaviour |
| --- | --- |
| Upload fails (network or 4xx/5xx) | Paste popup stays open with the error; display modal underneath unchanged |
| Removal fails | Error shown; both images remain |
| Non-image pasted | Rejected by the three existing guards; unchanged |
| DB references a file missing from disk | Broken image icon, as today; pre-existing and not addressed |

The three existing paste guards — unconditional `preventDefault()`, a
non-input paste target, and a MIME allowlist that excludes `image/svg+xml` —
are unchanged, and now cover all three actions because they share one popup.

### Image state transitions

| Case | Behaviour |
| --- | --- |
| Remove image 2 | Slot 1 untouched, no compaction, one block remains |
| Remove image 1 while image 2 exists | Image 2 moves to slot 1, one block remains, `Add Image` reappears |
| Remove the only image | Both slots null, display modal closes, card button returns to `Add Image` |
| Replace image 1 | Slot 2 untouched and stays in place |
| Replace image 2 | Slot 1 untouched |
| Both slots filled | `Add Image` hidden; no error path needed |
| Word created via Add New Word | One image in slot 1, identical to today |
| Word with a pre-existing image | Slot 1 holds it, slot 2 null; already valid, no backfill |
| Quiz mode, two-image word | Slot-1 image only |

## Testing

### Automated

`test/test_basic.py` runs without a database and asserts structure, not
behaviour. Three assertions are added in the existing style:

1. `templates/index.html` contains `imageScrollPane`.
2. `templates/index.html` contains `addAnotherImageBtn`.
3. `DELETE /api/words/<id>/image/<slot>` is registered in `app.url_map`.

The third is worth having on its own merits: it catches a broken route
registration without needing a database, which the current suite cannot
otherwise reach.

The per-image blocks are rendered in JavaScript, so they cannot be asserted from
markup — the suite has no browser and no clipboard access. That gap is covered
by the manual pass.

### Manual

Run in the `bkdict` conda environment on `http://localhost:5001`:

1. Open a word that has one image. The display modal shows one image with its
   `Replace`/`Remove` row, `Add Image` is visible, and **no scroll bar appears**.
2. Click `Add Image`, press Ctrl+V, confirm. Two blocks are shown, a scroll bar
   appears on the right, and `Add Image` is gone.
3. Drag the scroll bar, then use the mouse wheel. Both images are reachable by
   each method.
4. Click `Replace` on image 2 and paste a different screenshot. Image 2 changes;
   image 1 does not.
5. Click `Remove` on image 1. Image 2 takes its place as the only image, and
   `Add Image` reappears.
6. Add a second image again, then `Remove` image 2. Image 1 is unaffected.
7. Remove the last remaining image. The modal closes and the card button reads
   `Add Image`.
8. Start quiz mode on a category containing a two-image word. The slot-1 image
   renders.
9. Set the quiz filter to `Image Only`. The two-image word appears.
10. Add a new word with an attached image. Behaviour is unchanged and the new
    word opens with exactly one image.
11. Verify the auto-migration. Stop the app, drop `image_file_2`, and restart —
    the column is recreated at startup and the app works.

    **Dropping the column discards every slot-2 reference it holds.** Do this
    step before attaching any second images you want to keep, or run it against
    a scratch database. The images themselves stay on disk, but the words stop
    pointing at them and there is no way to re-link them from the UI.

## Reversibility

- **All work is on `feature/second-word-image`.** Deleting the branch, or
  `git revert`-ing the implementation commit on `development`, removes the
  feature.
- **The migration is additive and reverting is safe.** `image_file_2` remains
  on the table after a revert, unread and unwritten. It can be dropped manually
  or left; neither affects behaviour. No existing column is altered.
- **Existing data is untouched.** Every word already satisfies the invariant, so
  nothing is migrated, rewritten or backfilled.
- **Reverting restores the PATCH image field**, so the old removal path returns
  along with the old removal UI.

Two residues survive a revert. Second images uploaded through this feature
remain on disk in `static/images/word_images/` and become unreferenced, since
nothing reads `image_file_2` after the revert — harmless, and the directory is
gitignored so those files never entered the repository. Images uploaded with the
new `img_{word_id}_{slot}_{timestamp}.jpg` filename keep working, because
nothing parses structure out of a filename.
