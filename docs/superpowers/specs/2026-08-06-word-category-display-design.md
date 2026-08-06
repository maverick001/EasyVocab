# Showing a Word's Categories on the Word Card

**Date:** 2026-08-06
**Branch:** `feature/word-category-display` (from `development`)
**Status:** Approved, pending implementation

## Problem

A word can now belong to several categories, but the card gives no sign of it.
The Category dropdown shows the category being browsed, which is not the same
question as *where else does this word live*. Today the only way to find out is
to open Delete and read the confirmation prompt, or to add the word to a
category it is already in and read the error.

A row of category pills under the word answers it at a glance.

## What Already Exists

| Piece | Location |
| --- | --- |
| `.word-section`: centred flex column, `min-height: 120px` "to prevent resizing between words" | `static/css/style.css:817-829` |
| `.word-content`: the word, edit/IPA buttons, review badge | `templates/index.html:150-171`, `style.css:994-999` |
| Browse endpoint returns a single row and its position | `app.py:692` `get_word_by_category()`, response built at `app.py:873-878` |
| `displayWord()` renders the card from that response | `static/js/app.js:1196` |
| `.search-result-category`: the pill style to match | `style.css:1879-1888` |
| `escapeHTML()`, used for every rendered word string | `static/js/app.js:2205-2208` |
| `POST /api/words/<id>/categories` already returns the full `categories` list | `app.py`, `add_word_category()` |
| `idx_word` on `words(word)` | `database/init_database.sql:34` |

## Scope

### In scope

- A non-interactive row of category pills beneath `word-content`.
- `categories` added to the browse endpoint's word response.
- The row updating in place after a successful *Add to Category*.

### Out of scope

- Clicking a pill. Considered and dropped: the row is information, not a
  control. Jumping categories on a stray click would lose the reader's place,
  and removal is Delete's job.
- Marking which pill is the category being browsed. The Category dropdown
  directly above already says so.
- The same row on the quiz page. `word-section` belongs to `index.html`.
- Showing categories in search results. Those rows already carry the one
  category the hit came from.
- Restyling `.search-result-category` itself, including its dark-mode problem
  (see "The style").

## Decisions

1. **All categories, styled identically.** Not "the others", and not with the
   current one highlighted.
2. **Display only.** No click target, no hover affordance.
3. **The row is always rendered, even for one category.** See "Why it never
   hides".
4. **The list travels with the word**, rather than being fetched separately.
   See "Approach".
5. **A new CSS class, not a reuse of `.search-result-category`.** Eight
   duplicated declarations are cheaper than coupling the word card's appearance
   to the search panel's, which would make either one unsafe to change.

## Why it never hides

`.word-section` sets `min-height: 120px`, with the comment *"Fixed height to
prevent resizing between words"*. Whoever wrote that was protecting against the
card jumping as you arrow through the vocabulary.

A row that appeared only for multi-category words would reintroduce exactly
that: most words have one category, so the row would flicker in and out during
navigation and shift everything below it. Rendering one pill for a
one-category word costs nothing and keeps the height constant.

A word with enough categories to wrap onto a second line would still shift the
card. That is rare, self-inflicted, and not worth reserving vertical space for.

## Approach

**Attach the category list to the word the browse endpoint already returns.**

The alternative — having the client call `GET /api/words/<id>` after each word
loads, which already returns `other_categories` — needs no backend change, but
costs a round trip on every arrow-key press and makes the pills appear a beat
after the word. Holding down an arrow key through a category would fire one
extra request per word.

The third option, deriving the list in the browser, is impossible: the client
only ever holds the single row it was sent.

## Design

### Files changed

| File | Change |
| --- | --- |
| `app.py` | Attach `categories` to the browse response |
| `templates/index.html` | The row's container, between `word-content` and the History dropdown |
| `static/js/app.js` | Render the pills in `displayWord()`; refresh after an add |
| `static/css/style.css` | `.word-categories` layout, `.word-category-tag` pill |
| `test/test_basic.py` | Markup and response-shape assertions |

### The data

After the row is fetched (`app.py:873`), one further query:

```sql
SELECT DISTINCT category FROM words WHERE word = %s ORDER BY category
```

`words(word)` is indexed, so this is a cheap lookup rather than a scan, and it
runs once per word load rather than once per row of a list. The result is
attached as `word["categories"]`, beside the existing `total_in_category` and
`current_index`.

`DISTINCT` is defensive: `unique_word_category` already prevents a word
appearing twice in one category, so it should never collapse anything.

The list is sorted by category name, so the pills keep a stable order between
words and between visits. The category being browsed is not moved to the front:
its position would then change from word to word, which reads as noise.

### The markup

```html
<div id="wordCategories" class="word-categories"></div>
```

Directly after `word-content`, before the History dropdown. Empty in the
template and filled by JavaScript, so there is no placeholder to flash on load
and no stale pill from a previously viewed word.

### The rendering

`displayWord()` (`app.js:1196`) gains a call to `renderWordCategories()`, which
takes the list and writes one span per category. Every name goes through
`escapeHTML()`, as search results already do — category names are user-supplied
through the Add New Word modal and XML import.

`renderWordCategories()` is also called after a successful *Add to Category*,
using the `categories` array that endpoint already returns. Nothing is
refetched.

A missing or empty list clears the row rather than throwing, so an older cached
`app.js` talking to the new server, or the reverse, degrades to a blank row.

### The style

`.word-category-tag` copies `.search-result-category`: transparent background,
`2px solid #e74c3c`, `border-radius: 12px`, `font-size: 0.8rem`,
`padding: 3px 10px`.

One deliberate difference: `.search-result-category` hardcodes
`color: #1e3a5f`, a navy that all but vanishes on the dark-mode background. The
new class uses `var(--text-primary)`, which is defined for both themes. The
search pill keeps its bug; fixing it is a separate change to a separate
component.

`.word-categories` is a centred flex row with a small gap and `flex-wrap: wrap`,
matching the centring of `.word-section`. `margin-right` is not used for
spacing — the flex `gap` handles it, so no trailing margin hangs off the last
pill.

## Error and Edge Cases

| Case | Behaviour |
| --- | --- |
| Word in one category | One pill. The row still occupies its line |
| Word in several | One pill each, alphabetical, wrapping if needed |
| `categories` missing from the response | Row rendered empty; no error |
| Category name contains HTML | Escaped, as in search results |
| Add to Category succeeds | New pill appears immediately, from the response |
| Move | Navigates to the next word, which renders its own row |
| Delete from one category | The list reloads and the row follows |
| Word text renamed | That row no longer shares a spelling with its former twin, so both show one pill each once reloaded |
| Dark mode | Pill text uses `var(--text-primary)` and stays legible |

## Testing

### Automated

In the existing database-free style:

1. `index.html` contains `wordCategories`.
2. The row's container sits after `word-content` and before the History
   dropdown, so the row cannot silently drift elsewhere in the card.
3. `get_word_by_category()` attaches a `categories` key.
4. The category query is by word text, not by id.
5. `.word-category-tag` exists in the stylesheet and does not hardcode the navy
   that breaks dark mode.

`TestElementIdConsistency` covers the new id automatically.

### Manual

1. Open a word in one category. Exactly one pill, matching the search-result
   pill's look.
2. Arrow through several words. The card does not change height.
3. Add the word to a second category. A second pill appears without a reload.
4. Switch to that category and find the word. Both pills again, same order.
5. Switch to dark mode. The pill text is readable.
6. Delete the word from one category. One pill remains.

## Reversibility

All work is on `feature/word-category-display`. Deleting the branch or
reverting the commits removes the feature. No schema change, no migration, no
data written — the feature only reads.
