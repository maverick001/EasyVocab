# Adding a Word to a Second Category

**Date:** 2026-08-06
**Branch:** `feature/word-multi-category` (from `development`, after
`feature/second-word-image` was merged)
**Status:** Approved, pending implementation

## Problem

A word can only be filed under one category at a time. The **Move** button
relocates it, so putting `algorithm` under both `IT_CS` and `Science` is
impossible — moving it into one takes it out of the other.

This feature adds an **Add to Category** button beside Move. It leaves the word
where it is and files it under a second category as well.

## What Already Exists

The database was built for this. `words` stores one row per word-and-category
pair, under `UNIQUE KEY unique_word_category (word, category)`
(`database/init_database.sql:28`) — the constraint's own comment says *"same word
can exist in different categories"*. Several features already assume it:

| Piece | Location |
| --- | --- |
| Translation, IPA and example sentences write **every row sharing the word text** | `app.py:1170-1208`, `WHERE word = %s`, list named `shared_update_fields` |
| Image removal writes every row sharing the word text | `app.py:320-341` `build_image_removal_sql()` |
| Delete asks "this category only, or all of them?" | `app.py:1427-1463` |
| `GET /api/words/<id>` returns `other_categories` and `is_unique` | `app.py:1091-1110` |
| Move (`PUT /api/words/<id>/category`) rejects a duplicate with `duplicate: true` and **409** | `app.py:1327-1346` |
| Word-actions row: one dropdown, Move, Delete | `templates/index.html:215-224` |
| `changeWordCategory()` — auto-saves an in-progress edit, then moves | `static/js/app.js:2583-2650` |
| Both dropdowns are filled by one function | `static/js/app.js:1124-1157` |

So the multi-category concept is already live and partly supported. What is
missing is a way to **create** the second row, plus one bug that becomes visible
once two rows routinely coexist (see "The image-sharing fix").

## Scope

### In scope

- A `POST /api/words/<id>/categories` endpoint that copies a word's row into
  another category.
- An **＋ Add to Category** button in the word-actions row, sharing the existing
  dropdown with Move.
- A small toast notification, used here for the success message.
- Fixing image upload so it writes every row sharing the word text, matching
  translation, IPA and image removal.

### Out of scope

- **Any limit on how many categories a word may belong to.** Considered and
  deliberately dropped; see "Decisions".
- The Add New Word modal and XML import. Neither is touched. Both can already
  create a word in an additional category and will keep doing so.
- Merging or splitting categories, renaming a category, or bulk re-tagging.
- Showing a word's full category list on the word card. The toast names the
  categories after an add; a permanent indicator was considered and dropped as
  unnecessary.
- Removing a word from one of its categories. Delete already does this — its
  "current category only" option is exactly the reverse operation.
- The divergence that follows editing the **word text** of one row. `PUT
  /api/words/<id>` updates the spelling of a single row (`app.py:1210-1234`), so
  renaming one copy breaks the link between them. Pre-existing, unchanged here.

## Decisions

Settled during brainstorming and fixed:

1. **No maximum number of categories.** The design began with a cap of two and
   it was dropped: it bought nothing, and enforcing it honestly would have meant
   policing the Add New Word modal and XML import as well. Without it, no code
   anywhere counts categories.
2. **A dedicated endpoint, not a mode flag on Move.** `PUT
   /api/words/<id>/category` guarantees the row count is unchanged. Adding a
   `copy` mode would break that guarantee and make every future reader check
   which branch they were in. Two verbs, two routes.
3. **Not the existing `POST /api/words`.** That endpoint accepts only word,
   translation, sentence and category, so the copy would lose IPA, both images
   and the review history, and it hardcodes `review_count = 2` (`app.py:879-890`).
4. **The copy inherits the source row's review and SRS state**
   (`review_count`, `last_reviewed`, `next_review_date`, `srs_interval`,
   `srs_repetitions`, `srs_ease_factor`). The two rows are the same word being
   studied, so they should be equally far through the schedule. The cost is
   accepted: the quiz selects rows and does not de-duplicate by spelling
   (`app.py:1965-1968`), so an "All categories" quiz can draw the word twice as
   often as before.
5. **Columns to copy are read from the database, not hardcoded.** See "Copying
   the row".
6. **The new row's history entry is `'created'`.** `word_history.modification_type`
   is `ENUM('created', 'updated', 'moved')` (`database/add_word_history.sql:20`);
   a `'copied'` value would need a schema migration for no practical gain.
7. **The success message is a toast, not an `alert()`.** Every message in the app
   today is a blocking popup (`showError()` at `app.js:549-552` is a bare
   `alert()`). A confirmation the user did not ask for should not need
   dismissing.

## The Sharing Rule

> Rows sharing a word's spelling share its translation, IPA, example sentences
> and images. They differ only in category and in nothing else the user edits.

The first three already hold. Images hold in one direction only, which is the
bug fixed below. Everything in this design either relies on that rule or
restores it.

## The image-sharing fix

Image **removal** clears every row sharing the word text
(`app.py:320-341`, `WHERE word = %s`), but image **upload** writes a single row:

```python
# app.py:2515-2518, today
cursor.execute(
    f"UPDATE words SET {column} = %s WHERE id = %s{guard}",
    (filename, word_id),
)
```

The asymmetry is pre-existing and was explicitly left alone by the second-image
work (`2026-08-04-second-word-image-design.md`, "Out of scope"). It is minor
while few words sit in two categories. It stops being minor here: the very first
thing this feature does is create pairs of rows, and a user who adds an image
while browsing `Science` would find it missing under `IT_CS`.

**The fix:** target the word text, as removal does. The endpoint already selects
`word` for the row it is given (`app.py:2450-2453`), so the change is the `WHERE`
clause and its parameter.

```sql
UPDATE words SET image_file   = %s WHERE word = %s
UPDATE words SET image_file_2 = %s WHERE word = %s
                 AND image_file IS NOT NULL AND image_file != ''
```

The slot-2 guard stays and is now evaluated per row. That is what keeps the
compaction invariant — *slot 2 is filled only if slot 1 is* — true on every row,
including rows that diverged under the old behaviour:

| Row before | Slot-2 upload writes | Valid? |
| --- | --- | --- |
| `A` / `NULL` | `A` / `new` | yes |
| `A` / `B` | `A` / `new` | yes |
| `NULL` / `NULL` | not matched by the guard, left alone | yes |

The existing `rowcount == 0` check (`app.py:2520-2526`) keeps its meaning: zero
rows updated still means no row had slot 1 filled.

Rows that diverged before this fix are **not** backfilled. They converge the
next time an image is uploaded or removed for that word.

## Approach

**One new endpoint that copies a row, one new button that calls it, and the
upload fix above.** No schema change, no migration, no data backfill.

## Design

### Files changed

| File | Change |
| --- | --- |
| `app.py` | `build_category_copy_sql()` helper; `POST /api/words/<id>/categories`; upload `WHERE` clause |
| `templates/index.html` | Relabel the dropdown; add `#addCategoryBtn`; add `#toast` |
| `static/js/app.js` | Cache and wire `addCategoryBtn`; `addWordToCategory()`; `showToast()` |
| `static/css/style.css` | Toast styling; the new button reuses `btn-secondary btn-sm` |
| `test/test_basic.py` | Helper tests, route registration, markup ids |

`quiz.js`, `templates/quiz.html`, `utils/xml_parser.py` and every `database/*.sql`
file are **not** changed.

### Copying the row

`words` has grown by self-migration: `image_file`, `image_file_2`, `ipa`,
`next_review_date`, `srs_interval`, `srs_repetitions` and `srs_ease_factor` are
all added at startup (`app.py:220-412`), not in `init_database.sql`. A hardcoded
column list would go stale the next time a column is added, and the copy would
silently start losing data.

So the column list is read from the catalog, in the same style the migrations
already use:

```sql
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'words'
```

Four columns are excluded, and everything else is copied:

| Excluded | Why |
| --- | --- |
| `id` | The new row gets its own |
| `category` | Replaced by the target category — the point of the operation |
| `created_at` | The copy is new |
| `updated_at` | Same, and it is `ON UPDATE CURRENT_TIMESTAMP` anyway |

**`build_category_copy_sql(columns)`** is a pure function: it takes the column
list and returns SQL. It raises `ValueError` if nothing is left to copy, so a
misread catalog fails loudly rather than inserting a blank row.

```sql
INSERT INTO words (`category`, `word`, `translation`, ...)
SELECT %s, `word`, `translation`, ... FROM words WHERE id = %s
```

Two placeholders, in order: the new category, then the source row id. Column
names come from the database catalog and never from a request, so interpolating
them is safe — the same reasoning that lets `build_image_removal_sql()`
interpolate a validated slot (`app.py:315-341`). They are backtick-quoted
regardless.

`INSERT ... SELECT` is a single statement, so a copy cannot be left half-made.

### The endpoint

**`POST /api/words/<int:word_id>/categories`**, body `{"new_category": "Science"}`.

1. Reject a missing or empty `new_category` — **400**.
2. Load the source row. Not found — **404**.
3. Target equals the row's own category — **400**, `"Word is already in this category"`.
4. A row already exists for `(word, new_category)` — **409**, with
   `duplicate: true`. Same shape Move returns (`app.py:1338-1346`), so the client
   can handle both identically.
5. Otherwise run the copy, then `create_history_record(..., "created")` for the
   new row, then commit.
6. Best-effort `update_category_counts` in its own `try`, exactly as Move does
   (`app.py:1367-1372`), so a stored-procedure failure cannot undo a good copy.

Success returns:

```json
{
  "success": true,
  "message": "Added \"algorithm\" to category \"Science\"",
  "new_word_id": 4127,
  "new_category": "Science",
  "categories": ["IT_CS", "Science"]
}
```

`categories` is every category the word now belongs to, sorted, so the toast can
name them without a second request.

Step 4 is a friendly pre-check, not the guarantee. Two simultaneous adds would
both pass it and the second would hit `unique_word_category`. The endpoint
catches the resulting integrity error and returns the same **409**, so the race
and the ordinary case are indistinguishable to the client.

### The word-actions row

```
Category: [ -- Select Category -- v ]  [Move]  [＋ Add to Category]  [🗑️ Delete]
```

The label changes from `Move to Category:` to `Category:`, because the dropdown
now serves both verbs. The new `#addCategoryBtn` sits between Move and Delete and
reuses `btn btn-secondary btn-sm`, so it matches Move without new CSS. Nothing
else in the row moves.

`#changeCategorySelect` keeps its id — Move still reads it, and both buttons read
the same selection.

### Clicking ＋ Add to Category

`addWordToCategory()` mirrors `changeWordCategory()` (`app.js:2583-2650`) step for
step, differing only in the request and in what happens afterwards:

1. Return immediately if no word is loaded.
2. If a translation edit is open, save it first — the same courtesy Move gives,
   so typing is never lost.
3. Validate the selection (see the table below).
4. `POST` to the new endpoint.
5. On success: show the toast, call `incrementDailyCounter()` as Move does,
   reload the categories to refresh the counts, and restore the current
   selection in `#categorySelect` afterwards, since `loadCategories()` rebuilds
   the options.

**The displayed word does not change.** It is still in the category being
browsed, and the current index into that category is still valid, so nothing is
re-fetched or re-rendered beyond the dropdowns.

`incrementDailyCounter()` is client-side and capped at once per word per day
(`app.js:2377-2397`). Filing a word is not studying it, but Move already counts
it, and consistency between two adjacent buttons is worth more than the
distinction.

### The toast

The message names the word and every category it now belongs to, built from the
response's `categories`:

```
Added "algorithm" to Science — now in IT_CS, Science
```

`#toast` is a fixed-position element, empty and hidden, added once to
`index.html`. `showToast(message)` sets the text, adds a `visible` class, and
removes it after 3 seconds; a pending timer is cleared first, so rapid adds
replace the message instead of queueing.

CSS-only motion: a fade and a small slide via `opacity` and `transform`, with
`transition`. No animation library, and nothing to clean up but one timer.

It is deliberately generic — no word-specific markup — so other call sites can
adopt it later. Nothing else is converted to it in this change.

## Error and Edge Cases

### Server responses

| Case | Response |
| --- | --- |
| `new_category` missing or empty | **400** |
| Word id not found | **404** |
| Target is the word's current category | **400**, `"Word is already in this category"` |
| Word already in the target category | **409**, `duplicate: true` |
| Two simultaneous adds of the same pair | Second gets the same **409** |
| Catalog read yields no copyable columns | **500**; nothing inserted |
| `update_category_counts` fails | Copy still succeeds; counts refresh on the next category load |

### Client behaviour

| Case | Behaviour |
| --- | --- |
| Nothing selected in the dropdown | `"Please select a category first"`; no request sent |
| Selected the word's current category | `"Word is already in this category"`; no request sent |
| **409** duplicate | Server's message shown in a popup, matching Move's duplicate handling |
| Network failure | `"Network error while adding category"`; nothing changed server-side |
| Translation edit open when clicked | Saved first, then the add proceeds |
| No word loaded | Button does nothing |

### After the copy exists

| Case | Behaviour |
| --- | --- |
| Edit translation, IPA or sentences from either category | Both rows update — existing shared-write behaviour |
| Upload an image from either category | Both rows update, once the upload fix lands |
| Remove an image from either category | Both rows update and compact — unchanged |
| Delete the word, "current category only" | The other copy survives |
| Delete the word, "all categories" | Both go; the prompt already lists the other categories |
| Move one copy to a third category | Allowed. The word is then in two categories, neither of them the original |
| Add the word to a third, fourth, fifth category | Allowed. No cap |
| Quiz on "All" | The word can be drawn from either row, so roughly twice as often |
| Quiz on one category | Unchanged; only that category's row is eligible |
| Rename the word text from one category | The rows stop sharing. Pre-existing, out of scope |

## Testing

### Automated

`test/test_basic.py` runs without a database (`SKIP_DB=true`) and asserts
structure. New assertions in that style:

**`build_category_copy_sql()`** — the real logic, and fully testable here because
it is pure:

1. Copies a column it is given (`word`, `translation`, `ipa`).
2. Never copies `id`, `created_at` or `updated_at`.
3. Names `category` in the `INSERT` list but takes it from a placeholder, not
   from the source row.
4. Produces exactly two placeholders.
5. `INSERT` column count equals `SELECT` expression count.
6. Raises `ValueError` when given only excluded columns.
7. Backtick-quotes column names.

**Route and markup:**

8. `POST /api/words/<id>/categories` is registered in `app.url_map`.
9. `index.html` contains `addCategoryBtn`.
10. `index.html` contains `toast`.

`TestElementIdConsistency` then covers the new ids for free: it fails if
`app.js` looks up an id that `index.html` does not define.

### Manual

In the `bkdict` conda environment on `http://localhost:5001`:

1. Open a word in `IT_CS`. Pick `Science` in the dropdown, click **＋ Add to
   Category**. The toast confirms, the word stays on screen, and both category
   counts go up by one.
2. Switch to `Science` and find the word. Translation, IPA, example sentences and
   images are identical, and the review count matches.
3. Edit the translation from `Science`, then open the word under `IT_CS`. The
   edit is there.
4. Paste an image from `Science`, then open the word under `IT_CS`. **The image
   is there** — this is the upload fix.
5. Remove that image from `IT_CS`, then check `Science`. Gone from both.
6. With the word open in `IT_CS`, try to add it to `IT_CS`. Blocked, no request.
7. Try to add it to `Science` again. The duplicate message appears.
8. Click **Add** with nothing selected. Blocked.
9. Click **Move** — it still moves, exactly as before.
10. Delete the word from `Science` and choose "current category only". The
    `IT_CS` copy survives with everything intact.
11. Add a word to a third and fourth category. All allowed.
12. Start a quiz on "All". The word can appear; run a flashcard round and confirm
    nothing errors.
13. Import an XML file containing a word already in two categories. The import
    behaves exactly as it does today.

## Reversibility

- **All work is on `feature/word-multi-category`.** Deleting the branch, or
  reverting the commits on `development`, removes the feature.
- **No schema change**, so there is nothing to migrate back. `words` and
  `word_history` are untouched.
- **Rows created by the feature survive a revert** as ordinary rows — which is
  exactly what they are. A word in two categories is a state the app already
  handles: it browses, edits, quizzes and deletes correctly, and the Add New Word
  modal could have produced the same rows. Unwanted copies are removed with
  Delete → "current category only".
- **Reverting the upload fix** restores the old single-row behaviour. Images
  uploaded while the fix was live stay correctly shared; only later uploads
  revert to writing one row.
