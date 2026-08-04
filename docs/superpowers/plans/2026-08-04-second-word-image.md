# Second Word Image Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a word hold two images, shown stacked in a scrollable pane with per-image Replace and Remove controls.

**Architecture:** One new nullable column, `words.image_file_2`, added by the codebase's existing self-migration pattern. The upload endpoint gains an optional `slot` field defaulting to `1`; a new `DELETE /api/words/<id>/image/<slot>` empties a slot and compacts in one SQL statement. Slot 1 is always filled before slot 2, which is what lets quiz mode, the Image Only filter and the word card button keep reading `image_file` alone, unchanged.

**Tech Stack:** Python 3 / Flask, MySQL via `mysql-connector-python`, Pillow, vanilla JavaScript (no framework, no build step), pytest.

**Spec:** `docs/superpowers/specs/2026-08-04-second-word-image-design.md`

## Global Constraints

- **All commands run in the `bkdict` conda environment.** Verify with `conda env list` before running anything; activate with `conda activate bkdict`.
- **Local server runs on `http://localhost:5001`.**
- **Test command is `pytest test/test_basic.py -v`.** The suite runs without a database (`SKIP_DB=true` is set at import).
- **The compaction invariant:** `image_file_2` is non-null only when `image_file` is also non-null. Only the upload endpoint and the delete endpoint may write these two columns.
- **Removal scope is every row sharing the word text** (`WHERE word = %s`), matching the existing shared-field behaviour for `translation` and `ipa`. Upload scope stays single-row (`WHERE id = %s`); that asymmetry is pre-existing and deliberately not fixed.
- **Surgical changes only.** Do not reformat, restructure or "tidy" surrounding code. `static/js/quiz.js` and `templates/quiz.html` must not be modified at all.
- **Image slot values are `1` and `2` only.** Never interpolate an unvalidated slot into SQL.
- **Commit after every task.** Work on branch `feature/second-word-image`.

---

## File Structure

| File | Responsibility | Tasks |
| --- | --- | --- |
| `app.py` | Column migration, slot parsing, upload endpoint, delete endpoint, read paths | 1–6 |
| `templates/index.html` | Display modal markup: scroll pane and footer | 7 |
| `static/css/style.css` | Scroll pane, image block, per-image button row | 7 |
| `static/js/app.js` | Block rendering, slot targeting, add/replace/remove handlers | 7–9 |
| `test/test_basic.py` | Structural and pure-function tests | 1, 2, 4, 5, 7 |

`app.py` is 2542 lines and already mixes routes with helpers. This plan follows that existing structure rather than restructuring it: new helpers go beside the existing `ensure_*_column` functions, and the new route goes beside the existing image route.

---

### Task 0: Create the branch

- [ ] **Step 1: Create and switch to the feature branch**

```bash
cd "G:/My Drive/SharedDownloads/bkdict"
git checkout development
git pull
git checkout -b feature/second-word-image
```

- [ ] **Step 2: Confirm the environment**

```bash
conda env list
conda activate bkdict
pytest test/test_basic.py -v
```

Expected: all existing tests PASS. If they do not, stop and report — do not start on a red suite.

---

### Task 1: Add the `image_file_2` column migration

**Files:**
- Modify: `app.py` — insert after `ensure_image_file_column()` (ends line 251), before `ensure_ipa_column()` (line 257); wire into `create_app()` (line 2444) and `__main__` (line 2525)
- Test: `test/test_basic.py`

**Interfaces:**
- Consumes: nothing
- Produces: `ensure_image_file_2_column()` — no arguments, returns `None`. Adds `words.image_file_2 VARCHAR(255) DEFAULT NULL` if absent.

- [ ] **Step 1: Write the failing test**

Append to `test/test_basic.py`:

```python
class TestSecondImageColumn:
    """Tests for the image_file_2 self-migration"""

    def test_ensure_image_file_2_column_exists(self):
        """The migration function should be defined"""
        import app as app_module
        assert hasattr(app_module, 'ensure_image_file_2_column')

    def test_ensure_image_file_2_column_is_callable(self):
        """The migration function should be callable"""
        import app as app_module
        assert callable(app_module.ensure_image_file_2_column)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test/test_basic.py::TestSecondImageColumn -v`
Expected: FAIL with `AssertionError` (the attribute does not exist).

- [ ] **Step 3: Add the migration function**

Insert into `app.py` between `ensure_image_file_column()` and `ensure_ipa_column()`. This mirrors `ensure_ipa_column()` exactly — same structure, same error handling, same print style:

```python
def ensure_image_file_2_column():
    """
    Ensure image_file_2 column exists in words table
    """
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Check if column exists
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'words'
            AND COLUMN_NAME = 'image_file_2'
        """,
            (app.config["DB_NAME"],),
        )

        if cursor.fetchone()[0] == 0:
            print("Adding image_file_2 column to words table...")
            cursor.execute(
                "ALTER TABLE words ADD COLUMN image_file_2 VARCHAR(255) DEFAULT NULL"
            )
            connection.commit()
            print(f"[OK] Second image file column check completed")

        cursor.close()
    except mysql.connector.Error as err:
        print(f"[ERROR] Error ensuring image_file_2 column: {err}")
    finally:
        if connection:
            connection.close()
```

- [ ] **Step 4: Wire it into both startup paths**

In `create_app()` (around line 2444), add the call directly after the existing one:

```python
    Config.init_app(app)
    init_db_pool()
    ensure_image_file_column()
    ensure_image_file_2_column()
    ensure_ipa_column()
    return app
```

In the `if __name__ == "__main__":` block (around line 2525), same placement:

```python
    init_db_pool()
    ensure_word_history_table()
    ensure_image_file_column()
    ensure_image_file_2_column()
    ensure_ipa_column()
    ensure_srs_columns()
    ensure_daily_score_column()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest test/test_basic.py -v`
Expected: all PASS, including the two new tests.

- [ ] **Step 6: Verify the migration actually runs**

```bash
conda activate bkdict
python app.py
```

Expected: on first run the console prints `Adding image_file_2 column to words table...`; on a second run it does not. Stop the server (Ctrl+C) before continuing.

- [ ] **Step 7: Commit**

```bash
git add app.py test/test_basic.py
git commit -m "Add image_file_2 column self-migration"
```

---

### Task 2: Add the `parse_image_slot` helper

A pure function, so it is fully unit-testable without a database. It exists so the upload endpoint's slot handling can be tested at all.

**Files:**
- Modify: `app.py` — insert directly after `ensure_image_file_2_column()` from Task 1
- Test: `test/test_basic.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `VALID_IMAGE_SLOTS` — tuple `(1, 2)`
  - `parse_image_slot(raw)` — takes the raw form value (`str`, or `None` when absent). Returns `1` when `raw` is `None` or `""`; returns `1` or `2` for those values; returns `None` for anything else, which the caller turns into a 400.

- [ ] **Step 1: Write the failing test**

Append to `test/test_basic.py`:

```python
class TestImageSlotParsing:
    """Tests for interpreting the 'slot' field of an image upload"""

    def test_absent_slot_defaults_to_one(self):
        """A request with no slot field targets slot 1"""
        from app import parse_image_slot
        assert parse_image_slot(None) == 1

    def test_empty_slot_defaults_to_one(self):
        """An empty slot field targets slot 1"""
        from app import parse_image_slot
        assert parse_image_slot('') == 1

    def test_slot_one_accepted(self):
        """Slot 1 is accepted"""
        from app import parse_image_slot
        assert parse_image_slot('1') == 1

    def test_slot_two_accepted(self):
        """Slot 2 is accepted"""
        from app import parse_image_slot
        assert parse_image_slot('2') == 2

    def test_integer_input_accepted(self):
        """An int is accepted as well as a string"""
        from app import parse_image_slot
        assert parse_image_slot(2) == 2

    def test_zero_rejected(self):
        """Slot 0 is out of range"""
        from app import parse_image_slot
        assert parse_image_slot('0') is None

    def test_three_rejected(self):
        """Slot 3 is out of range - two images is a hard cap"""
        from app import parse_image_slot
        assert parse_image_slot('3') is None

    def test_non_numeric_rejected(self):
        """A non-numeric slot is rejected rather than raising"""
        from app import parse_image_slot
        assert parse_image_slot('abc') is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test/test_basic.py::TestImageSlotParsing -v`
Expected: FAIL with `ImportError: cannot import name 'parse_image_slot' from 'app'`.

- [ ] **Step 3: Write the implementation**

Insert into `app.py` directly after `ensure_image_file_2_column()`:

```python
# A word holds at most two images. This cap is deliberate: it keeps the data
# model to two columns rather than a one-to-many table.
VALID_IMAGE_SLOTS = (1, 2)


def parse_image_slot(raw):
    """
    Interpret the 'slot' field of an image upload request.

    Absent or empty means slot 1, which keeps every caller written before the
    second slot existed working without modification.

    Returns:
        1 or 2, or None when the value is not a valid slot (caller returns 400)
    """
    if raw is None or raw == "":
        return 1

    try:
        slot = int(raw)
    except (TypeError, ValueError):
        return None

    return slot if slot in VALID_IMAGE_SLOTS else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest test/test_basic.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add app.py test/test_basic.py
git commit -m "Add parse_image_slot helper for image upload slot handling"
```

---

### Task 3: Accept a `slot` on the upload endpoint

**Files:**
- Modify: `app.py:2341-2427` — replace `upload_word_image()` in full

**Interfaces:**
- Consumes: `parse_image_slot(raw)`, `VALID_IMAGE_SLOTS` (Task 2)
- Produces: `POST /api/words/<id>/image` now accepts optional form field `slot`, and its JSON response gains `image_file` and `image_file_2` alongside the existing `filename`.

Three changes beyond the slot itself:

1. The database row is now read **before** compression, so a slot-2 upload into a word with an empty slot 1 is rejected without wasting work.
2. The filename gains the slot: `time.time()` is second-resolution, so two images for one word in the same second would otherwise collide and silently overwrite.
3. The response carries both slot values so the client can re-render from server truth. `filename` is kept because `uploadNewWordImage()` in `app.js:857` reads it.

- [ ] **Step 1: Replace the endpoint**

Replace the whole of `upload_word_image()` in `app.py` (currently lines 2341-2427) with:

```python
@app.route("/api/words/<int:word_id>/image", methods=["POST"])
def upload_word_image(word_id):
    """
    Upload and process an image for a specific word

    1. Compresses image to JPEG under 500KB
    2. Saves to static/images/word_images with unique name
    3. Updates database

    Accepts an optional 'slot' form field (1 or 2). Absent means slot 1, which
    keeps every caller written before the second slot existed working.
    """
    conn = None
    try:
        if "image" not in request.files:
            return jsonify({"success": False, "error": "No image file provided"}), 400

        file = request.files["image"]

        if file.filename == "":
            return jsonify({"success": False, "error": "No selected file"}), 400

        slot = parse_image_slot(request.form.get("slot"))
        if slot is None:
            return jsonify({"success": False, "error": "Invalid image slot"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT word, image_file, image_file_2 FROM words WHERE id = %s",
            (word_id,),
        )
        word_data = cursor.fetchone()

        if not word_data:
            return jsonify({"success": False, "error": "Word not found"}), 404

        # Slot 1 is always filled before slot 2, so a word with no first image
        # cannot be given a second one. Checked before compression so a rejected
        # upload does no work.
        if slot == 2 and not word_data["image_file"]:
            return jsonify(
                {
                    "success": False,
                    "error": "Cannot fill slot 2 while slot 1 is empty",
                }
            ), 409

        # Process image using Pillow
        try:
            # Open image from stream
            img = Image.open(file.stream)

            # Convert to RGB (required for JPEG)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Compress to ensure size < 500KB without resizing dimensions
            output_buffer = io.BytesIO()
            quality = 95
            img.save(output_buffer, format="JPEG", quality=quality)

            while output_buffer.tell() > 500 * 1024 and quality > 10:
                output_buffer.seek(0)
                output_buffer.truncate()
                quality -= 5
                img.save(output_buffer, format="JPEG", quality=quality)

            # The slot is part of the filename because time.time() is
            # second-resolution: two images for one word saved in the same
            # second would otherwise collide and silently overwrite.
            timestamp = int(time.time())
            filename = f"img_{word_id}_{slot}_{timestamp}.jpg"
            save_path = os.path.join(
                app.root_path, "static", "images", "word_images", filename
            )

            # Ensure directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # Write to file
            with open(save_path, "wb") as f:
                f.write(output_buffer.getvalue())

            # slot has been validated to 1 or 2, so this is not user input.
            column = "image_file" if slot == 1 else "image_file_2"
            cursor.execute(
                f"UPDATE words SET {column} = %s WHERE id = %s",
                (filename, word_id),
            )
            conn.commit()

            image_file = filename if slot == 1 else word_data["image_file"]
            image_file_2 = filename if slot == 2 else word_data["image_file_2"]

            return jsonify(
                {
                    "success": True,
                    "message": "Image uploaded and processed",
                    "filename": filename,
                    "image_file": image_file,
                    "image_file_2": image_file_2,
                }
            )

        except Exception as e:
            return jsonify(
                {"success": False, "error": f"Image processing failed: {str(e)}"}
            ), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()
```

- [ ] **Step 2: Run the suite to confirm nothing regressed**

Run: `pytest test/test_basic.py -v`
Expected: all PASS.

- [ ] **Step 3: Verify the unchanged path still works**

```bash
conda activate bkdict
python app.py
```

In the browser at `http://localhost:5001`, attach an image to a word that has none, using the existing image button. Expected: it saves and displays as before. Confirm the new file in `static/images/word_images/` is named `img_<id>_1_<timestamp>.jpg`. Stop the server.

This is the important check for this task: sending no `slot` must behave exactly as it did before.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "Accept an optional slot on the image upload endpoint"
```

---

### Task 4: Add the `build_image_removal_sql` helper

The compaction rule is the single most important piece of logic in this feature. Extracting it into a pure function makes it reviewable and testable without a database.

**Files:**
- Modify: `app.py` — insert directly after `parse_image_slot()` from Task 2
- Test: `test/test_basic.py`

**Interfaces:**
- Consumes: nothing
- Produces: `build_image_removal_sql(slot)` — takes `1` or `2`, returns a SQL string with one `%s` placeholder for the word text.

- [ ] **Step 1: Write the failing test**

Append to `test/test_basic.py`:

```python
class TestImageRemovalSql:
    """Tests for the SQL that empties a slot and restores compaction"""

    def test_slot_one_pulls_slot_two_down(self):
        """Removing slot 1 must move slot 2 into it, not just blank slot 1"""
        from app import build_image_removal_sql
        sql = build_image_removal_sql(1)
        assert 'image_file = image_file_2' in sql
        assert 'image_file_2 = NULL' in sql

    def test_slot_two_clears_only_slot_two(self):
        """Removing slot 2 must leave slot 1 alone"""
        from app import build_image_removal_sql
        sql = build_image_removal_sql(2)
        assert 'image_file_2 = NULL' in sql
        assert 'image_file = image_file_2' not in sql

    def test_slot_one_targets_all_rows_sharing_the_word(self):
        """Removal is shared across categories, as translation and ipa are"""
        from app import build_image_removal_sql
        assert build_image_removal_sql(1).endswith('WHERE word = %s')

    def test_slot_two_targets_all_rows_sharing_the_word(self):
        """Removal is shared across categories, as translation and ipa are"""
        from app import build_image_removal_sql
        assert build_image_removal_sql(2).endswith('WHERE word = %s')

    def test_statements_carry_exactly_one_placeholder(self):
        """Only the word text is parameterised; the slot is never interpolated"""
        from app import build_image_removal_sql
        assert build_image_removal_sql(1).count('%s') == 1
        assert build_image_removal_sql(2).count('%s') == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test/test_basic.py::TestImageRemovalSql -v`
Expected: FAIL with `ImportError: cannot import name 'build_image_removal_sql' from 'app'`.

- [ ] **Step 3: Write the implementation**

Insert into `app.py` directly after `parse_image_slot()`:

```python
def build_image_removal_sql(slot):
    """
    SQL that empties one image slot and restores the compaction invariant.

    Slot 1 is always filled before slot 2, so removing slot 1 must pull slot 2
    down into it rather than leaving a hole. Both statements are correct row by
    row, which matters because rows sharing a word can hold different images:
    uploads write a single row while removals write every row.

    Args:
        slot: 1 or 2, already validated by the caller

    Returns:
        A SQL string with one %s placeholder, for the word text
    """
    if slot == 1:
        return (
            "UPDATE words SET image_file = image_file_2, image_file_2 = NULL "
            "WHERE word = %s"
        )

    return "UPDATE words SET image_file_2 = NULL WHERE word = %s"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest test/test_basic.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add app.py test/test_basic.py
git commit -m "Add build_image_removal_sql helper encoding the compaction rule"
```

---

### Task 5: Add the image removal endpoint

**Files:**
- Modify: `app.py` — insert directly after `upload_word_image()`, before `def create_app():`
- Test: `test/test_basic.py`

**Interfaces:**
- Consumes: `VALID_IMAGE_SLOTS`, `build_image_removal_sql(slot)` (Tasks 2 and 4)
- Produces: `DELETE /api/words/<id>/image/<slot>` returning `{"success": true, "image_file": <str|null>, "image_file_2": <str|null>}`

- [ ] **Step 1: Write the failing test**

Append to `test/test_basic.py`:

```python
class TestImageDeleteRoute:
    """Tests for the image removal endpoint's registration"""

    def test_delete_image_route_is_registered(self):
        """DELETE /api/words/<id>/image/<slot> should exist"""
        from app import app
        matches = [
            rule for rule in app.url_map.iter_rules()
            if 'DELETE' in rule.methods and '/image/' in str(rule)
        ]
        assert matches, 'DELETE /api/words/<id>/image/<slot> is not registered'

    def test_delete_image_route_takes_a_slot(self):
        """The route should carry both a word id and a slot"""
        from app import app
        matches = [
            str(rule) for rule in app.url_map.iter_rules()
            if 'DELETE' in rule.methods and '/image/' in str(rule)
        ]
        assert any('word_id' in rule and 'slot' in rule for rule in matches)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test/test_basic.py::TestImageDeleteRoute -v`
Expected: FAIL with `AssertionError: DELETE /api/words/<id>/image/<slot> is not registered`.

- [ ] **Step 3: Write the endpoint**

Insert into `app.py` after `upload_word_image()` and before `def create_app():`:

```python
@app.route("/api/words/<int:word_id>/image/<int:slot>", methods=["DELETE"])
def delete_word_image(word_id, slot):
    """
    Remove one image slot from a word and restore the compaction invariant.

    Scope matches the existing shared-field behaviour of PUT /api/words/<id>:
    every row carrying the same word text is updated, exactly as translation
    and ipa already are.

    Returns both slot values after the change, so the client can re-render
    from server truth rather than computing compaction itself.
    """
    conn = None
    try:
        if slot not in VALID_IMAGE_SLOTS:
            return jsonify({"success": False, "error": "Invalid image slot"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT word, image_file, image_file_2 FROM words WHERE id = %s",
            (word_id,),
        )
        word_data = cursor.fetchone()

        if not word_data:
            return jsonify({"success": False, "error": "Word not found"}), 404

        # slot has been validated, so this key is not user input.
        column = "image_file" if slot == 1 else "image_file_2"
        if not word_data[column]:
            return jsonify({"success": False, "error": "No image in that slot"}), 404

        cursor.execute(build_image_removal_sql(slot), (word_data["word"],))
        conn.commit()

        cursor.execute(
            "SELECT image_file, image_file_2 FROM words WHERE id = %s", (word_id,)
        )
        updated = cursor.fetchone()

        return jsonify(
            {
                "success": True,
                "image_file": updated["image_file"],
                "image_file_2": updated["image_file_2"],
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest test/test_basic.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add app.py test/test_basic.py
git commit -m "Add DELETE /api/words/<id>/image/<slot> with compaction"
```

---

### Task 6: Expose `image_file_2` on reads and retire the old removal path

**Files:**
- Modify: `app.py:689`, `app.py:698`, `app.py:992` (SELECT lists)
- Modify: `app.py:1048` (docstring), `app.py:1087-1091` (remove the `image_file` update block)

**Interfaces:**
- Consumes: nothing
- Produces: `GET` word responses now carry `image_file_2`. `PUT /api/words/<id>` no longer accepts `image_file`.

Dropping `image_file` from `PUT` was audited before being accepted: `removeWordImage()` in `app.js` is its only caller, every other reference in the repo is a read, and the field is opt-in (`if "x" in data`) behind a non-empty guard at `app.py:1120`, so a stale client degrades to a silent no-op rather than an error. Full audit is in the spec.

`app.py:1886` (the quiz SELECT) and `app.py:1899` (the Image Only filter) are **left unchanged** — the invariant guarantees `image_file` is non-null whenever a word has any image.

- [ ] **Step 1: Add `image_file_2` to the two word-fetch SELECTs**

At `app.py:689` and `app.py:698`, both currently reading:

```python
                SELECT id, word, translation, category, example_sentence, image_file, ipa,
```

change each to:

```python
                SELECT id, word, translation, category, example_sentence, image_file, image_file_2, ipa,
```

- [ ] **Step 2: Add `image_file_2` to the word list SELECT**

At `app.py:992`, change:

```python
            SELECT id, word, translation, example_sentence, category, review_count, last_reviewed, image_file, created_at, updated_at, ipa
```

to:

```python
            SELECT id, word, translation, example_sentence, category, review_count, last_reviewed, image_file, image_file_2, created_at, updated_at, ipa
```

- [ ] **Step 3: Remove the `image_file` update block**

Delete these five lines at `app.py:1087-1091`:

```python
        if "image_file" in data:
            shared_update_fields.append("image_file = %s")
            # Handle empty string or null to remove image
            image_val = data["image_file"].strip() if data["image_file"] else None
            shared_params.append(image_val)
```

The `if "ipa" in data:` block that follows becomes the first entry.

- [ ] **Step 4: Remove it from the endpoint docstring**

At `app.py:1048`, delete the line:

```python
            "image_file": "image.png"              # optional
```

- [ ] **Step 5: Run the suite**

Run: `pytest test/test_basic.py -v`
Expected: all PASS.

- [ ] **Step 6: Verify reads carry the new field**

```bash
conda activate bkdict
python app.py
```

In the browser, open a word and check the network response for `/api/words/<id>` includes `image_file_2` (null for existing words). Editing a translation must still save correctly. Stop the server.

- [ ] **Step 7: Commit**

```bash
git add app.py
git commit -m "Expose image_file_2 on reads, drop image_file from the word PUT"
```

---

### Task 7: Scroll pane markup, styling, and rendering

The largest task, and deliberately not split: it removes three element ids (`wordImageDisplay`, `changeImageBtn`, `removeImageBtn`) that `app.js` currently looks up unconditionally. Splitting it would leave `Elements.changeImageBtn.addEventListener` throwing on a null, breaking the whole page between tasks.

**Files:**
- Modify: `templates/index.html:314-331` (display modal)
- Modify: `static/css/style.css` — after `.word-image-large` (ends line 2353)
- Modify: `static/js/app.js` — element refs (137-143, 357-363), listeners (502-510), `handleImageButtonClick` (617-624), `pasteModalMode` declaration (612), `openPasteModal` (656-659), `uploadPastedImage` (707-754), `openImageDisplayModal` (766-771), `removeWordImage` (776-788), `updateWord` local sync (960-962)
- Test: `test/test_basic.py`

**Interfaces:**
- Consumes: `POST /api/words/<id>/image` with `slot` (Task 3); `image_file_2` on word reads (Task 6)
- Produces:
  - `renderImageBlocks()` — no arguments, rebuilds `#imageScrollPane` from `AppState.currentWord`
  - `applyImageState(data)` — takes any response carrying `image_file` / `image_file_2`, writes both into `AppState.currentWord`, refreshes the card button
  - `openImageDisplayModal()` — **no longer takes a filename argument**
  - `openPasteModal(slot)` — `slot` defaults to `1`
  - `pasteTargetSlot` — module-level, `1` or `2`

**Removal is unavailable between this task and Task 9.** `removeWordImage()` and its button are deleted here and replaced by `removeImageSlot(slot)` in Task 9. This is intentional: keeping the old path alive would mean keeping a `PUT` field that Task 6 already removed.

- [ ] **Step 1: Write the failing test**

Append to `test/test_basic.py`:

```python
class TestImageDisplayModalMarkup:
    """Tests for the two-image display modal markup"""

    def test_index_has_image_scroll_pane(self):
        """Display modal should contain the scrolling image pane"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates', 'index.html')
        with open(template_path, encoding='utf-8') as f:
            markup = f.read()
        assert 'imageScrollPane' in markup

    def test_index_has_add_another_image_button(self):
        """Display modal footer should contain the add button"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates', 'index.html')
        with open(template_path, encoding='utf-8') as f:
            markup = f.read()
        assert 'addAnotherImageBtn' in markup
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test/test_basic.py::TestImageDisplayModalMarkup -v`
Expected: FAIL with `AssertionError` on `imageScrollPane`.

- [ ] **Step 3: Replace the display modal markup**

In `templates/index.html`, replace lines 314-331 in full:

```html
        <!-- Image Display Modal -->
        <div id="imageDisplayModal" class="modal" style="display: none;">
            <div class="modal-content modal-image-display">
                <div class="modal-header">
                    <h2 id="imageDisplayTitle">Word Image</h2>
                    <button id="closeImageDisplayBtn" class="btn-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div id="imageScrollPane" class="image-scroll-pane"></div>
                </div>
                <div class="modal-footer">
                    <button id="addAnotherImageBtn" class="btn btn-secondary">Add Image</button>
                    <button id="closeImageDisplayFooterBtn" class="btn btn-primary">Close</button>
                </div>
            </div>
        </div>
```

- [ ] **Step 4: Add the styles**

In `static/css/style.css`, insert after the `.word-image-large` rule (which ends at line 2353):

```css
/* Two images stack vertically; the fixed height is what produces the
   native scroll bar on the right. */
.image-scroll-pane {
    max-height: 60vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    padding: var(--spacing-sm);
}

.image-block {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-sm);
}

.image-block-actions {
    display: flex;
    gap: var(--spacing-sm);
    justify-content: center;
}

/* Sized so image 1 nearly fills the pane, putting image 2 just far enough
   below the fold that scrolling to it is a deliberate act. */
.image-scroll-pane .word-image-large {
    max-height: 52vh;
}
```

- [ ] **Step 5: Update the element references**

In `static/js/app.js`, in the `Elements` object (lines 137-143), replace:

```javascript
    imageDisplayModal: null,
    closeImageDisplayBtn: null,
    closeImageDisplayFooterBtn: null,
    wordImageDisplay: null,
    changeImageBtn: null,
    removeImageBtn: null,
    imageDisplayTitle: null,
```

with:

```javascript
    imageDisplayModal: null,
    closeImageDisplayBtn: null,
    closeImageDisplayFooterBtn: null,
    imageScrollPane: null,
    addAnotherImageBtn: null,
    imageDisplayTitle: null,
```

Then in the lookup block (lines 357-363), replace:

```javascript
    Elements.imageDisplayModal = document.getElementById('imageDisplayModal');
    Elements.closeImageDisplayBtn = document.getElementById('closeImageDisplayBtn');
    Elements.closeImageDisplayFooterBtn = document.getElementById('closeImageDisplayFooterBtn');
    Elements.wordImageDisplay = document.getElementById('wordImageDisplay');
    Elements.changeImageBtn = document.getElementById('changeImageBtn');
    Elements.removeImageBtn = document.getElementById('removeImageBtn');
    Elements.imageDisplayTitle = document.getElementById('imageDisplayTitle');
```

with:

```javascript
    Elements.imageDisplayModal = document.getElementById('imageDisplayModal');
    Elements.closeImageDisplayBtn = document.getElementById('closeImageDisplayBtn');
    Elements.closeImageDisplayFooterBtn = document.getElementById('closeImageDisplayFooterBtn');
    Elements.imageScrollPane = document.getElementById('imageScrollPane');
    Elements.addAnotherImageBtn = document.getElementById('addAnotherImageBtn');
    Elements.imageDisplayTitle = document.getElementById('imageDisplayTitle');
```

- [ ] **Step 6: Update the listeners**

In `static/js/app.js`, replace the Display Modal listener block (lines 502-510):

```javascript
    // Display Modal
    Elements.closeImageDisplayBtn.addEventListener('click', () => toggleImageDisplayModal(false));
    Elements.closeImageDisplayFooterBtn.addEventListener('click', () => toggleImageDisplayModal(false));
    Elements.changeImageBtn.addEventListener('click', () => {
        toggleImageDisplayModal(false);
        openPasteModal();
    });
    Elements.removeImageBtn.addEventListener('click', removeWordImage);
}
```

with:

```javascript
    // Display Modal
    Elements.closeImageDisplayBtn.addEventListener('click', () => toggleImageDisplayModal(false));
    Elements.closeImageDisplayFooterBtn.addEventListener('click', () => toggleImageDisplayModal(false));
    Elements.addAnotherImageBtn.addEventListener('click', () => {
        // Slot 1 fills first, so the free slot is 2 only once slot 1 is taken.
        const freeSlot = AppState.currentWord.image_file ? 2 : 1;
        toggleImageDisplayModal(false);
        openPasteModal(freeSlot);
    });
}
```

- [ ] **Step 7: Add slot targeting to the paste modal**

In `static/js/app.js`, below the existing `pasteModalMode` declaration (line 612), add:

```javascript
// Which slot the paste modal will write to, in 'existing' mode.
let pasteTargetSlot = 1;
```

Then replace `openPasteModal()` (lines 656-659):

```javascript
function openPasteModal() {
    pasteModalMode = 'existing';
    togglePasteModal(true);
}
```

with:

```javascript
function openPasteModal(slot = 1) {
    pasteModalMode = 'existing';
    pasteTargetSlot = slot;
    togglePasteModal(true);
}
```

- [ ] **Step 8: Send the slot and adopt the server's response**

In `static/js/app.js`, inside `uploadPastedImage()`, replace:

```javascript
        const formData = new FormData();
        formData.append('image', currentPastedFile);
```

with:

```javascript
        const formData = new FormData();
        formData.append('image', currentPastedFile);
        formData.append('slot', pasteTargetSlot);
```

Then replace the success branch:

```javascript
        if (data.success) {
            console.log('✅ Image uploaded:', data.filename);

            AppState.currentWord.image_file = data.filename;
            updateImageButtonState(data.filename);
            togglePasteModal(false);

            // Show display modal to confirm
            setTimeout(() => openImageDisplayModal(data.filename), 300);
        } else {
```

with:

```javascript
        if (data.success) {
            console.log('✅ Image uploaded:', data.filename);

            applyImageState(data);
            togglePasteModal(false);

            // Show display modal to confirm
            setTimeout(() => openImageDisplayModal(), 300);
        } else {
```

- [ ] **Step 9: Replace the display functions**

In `static/js/app.js`, replace `openImageDisplayModal()` and `removeWordImage()` — **lines 763-788**, from the `/**` opening the `Open Image Display Modal` comment through the final closing brace of `removeWordImage` — with the code below.

**`toggleImageDisplayModal()` at lines 756-761 must survive.** It sits immediately above the range and is still called by the new code, the close buttons, and `removeImageSlot()` in Task 9. Deleting it breaks the modal entirely.

```javascript
/**
 * Adopt the server's view of both image slots.
 *
 * The client never computes the post-compaction state itself, so image 2
 * sliding up into slot 1 after a removal needs no shuffling logic here.
 *
 * @param {Object} data - any response carrying image_file / image_file_2
 */
function applyImageState(data) {
    AppState.currentWord.image_file = data.image_file || null;
    AppState.currentWord.image_file_2 = data.image_file_2 || null;
    updateImageButtonState(AppState.currentWord.image_file);
}

/**
 * Rebuild the scroll pane from the word currently on screen.
 *
 * Blocks are built from state rather than toggled in markup, so no stale
 * <img> from a previously viewed word can linger in the DOM.
 */
function renderImageBlocks() {
    const filled = [
        { slot: 1, file: AppState.currentWord.image_file },
        { slot: 2, file: AppState.currentWord.image_file_2 }
    ].filter(entry => entry.file);

    Elements.imageScrollPane.innerHTML = '';

    filled.forEach(entry => {
        const block = document.createElement('div');
        block.className = 'image-block';
        block.dataset.slot = entry.slot;

        const img = document.createElement('img');
        img.className = 'word-image-large';
        img.alt = `Image ${entry.slot}`;
        // Timestamp defeats caching when a slot is replaced in place.
        img.src = `/static/images/word_images/${entry.file}?t=${new Date().getTime()}`;

        block.append(img);
        Elements.imageScrollPane.append(block);
    });

    // The two-image cap enforces itself: no free slot, no add button.
    Elements.addAnotherImageBtn.style.display =
        filled.length < 2 ? 'inline-flex' : 'none';
}

/**
 * Open Image Display Modal
 */
function openImageDisplayModal() {
    Elements.imageDisplayTitle.textContent = AppState.currentWord.word;
    renderImageBlocks();
    toggleImageDisplayModal(true);
}
```

- [ ] **Step 10: Fix the remaining callers**

In `handleImageButtonClick()` (around line 621), change:

```javascript
        openImageDisplayModal(currentImage);
```

to:

```javascript
        openImageDisplayModal();
```

In `updateWord()`, delete the now-dead local sync block (lines 960-962):

```javascript
            if ('image_file' in updates) {
                AppState.currentWord.image_file = updates.image_file;
                updateImageButtonState(updates.image_file);
            }
```

- [ ] **Step 11: Run tests**

Run: `pytest test/test_basic.py -v`
Expected: all PASS.

- [ ] **Step 12: Verify in the browser**

```bash
conda activate bkdict
python app.py
```

Hard-refresh (Ctrl+F5) to clear cached JS, then check:

1. A word with one image → modal shows it, `Add Image` visible, **no scroll bar**.
2. Click `Add Image`, Ctrl+V, confirm → two images stacked, **scroll bar appears on the right**, `Add Image` gone.
3. The scroll bar drags and the mouse wheel scrolls; both images are reachable.
4. Open the browser console — no errors.

Stop the server.

- [ ] **Step 13: Commit**

```bash
git add templates/index.html static/css/style.css static/js/app.js test/test_basic.py
git commit -m "Show up to two word images in a scrollable pane"
```

---

### Task 8: Add the per-image Replace button

**Files:**
- Modify: `static/js/app.js` — `renderImageBlocks()` from Task 7

**Interfaces:**
- Consumes: `renderImageBlocks()`, `openPasteModal(slot)`, `toggleImageDisplayModal(show)` (Task 7)
- Produces: `replaceImageSlot(slot)` — closes the display modal and opens the paste popup targeting that slot

- [ ] **Step 1: Add the handler**

In `static/js/app.js`, insert directly above `renderImageBlocks()`:

```javascript
/**
 * Swap one image for a newly pasted one, leaving the other slot alone.
 *
 * @param {number} slot - 1 or 2
 */
function replaceImageSlot(slot) {
    toggleImageDisplayModal(false);
    openPasteModal(slot);
}
```

- [ ] **Step 2: Render the button**

In `renderImageBlocks()`, replace:

```javascript
        block.append(img);
        Elements.imageScrollPane.append(block);
```

with:

```javascript
        const actions = document.createElement('div');
        actions.className = 'image-block-actions';

        const replaceBtn = document.createElement('button');
        replaceBtn.type = 'button';
        replaceBtn.className = 'btn btn-secondary btn-sm';
        replaceBtn.textContent = 'Replace';
        replaceBtn.addEventListener('click', () => replaceImageSlot(entry.slot));

        actions.append(replaceBtn);
        block.append(img, actions);
        Elements.imageScrollPane.append(block);
```

- [ ] **Step 3: Run tests**

Run: `pytest test/test_basic.py -v`
Expected: all PASS.

- [ ] **Step 4: Verify in the browser**

Start the server, hard-refresh, then on a word with two images:

1. Click `Replace` under image 2, paste a different screenshot, confirm.
2. Expected: image 2 changes, **image 1 is unchanged and still first**.
3. Repeat with `Replace` under image 1 — image 1 changes, image 2 stays second.

Stop the server.

- [ ] **Step 5: Commit**

```bash
git add static/js/app.js
git commit -m "Add per-image Replace control to the display modal"
```

---

### Task 9: Add the per-image Remove button

**Files:**
- Modify: `static/js/app.js` — `renderImageBlocks()` from Task 7

**Interfaces:**
- Consumes: `DELETE /api/words/<id>/image/<slot>` (Task 5); `applyImageState(data)`, `renderImageBlocks()`, `toggleImageDisplayModal(show)` (Task 7)
- Produces: `removeImageSlot(slot)` — deletes that slot, then re-renders or closes

- [ ] **Step 1: Add the handler**

In `static/js/app.js`, insert directly above `renderImageBlocks()`, below `replaceImageSlot()`:

```javascript
/**
 * Remove one image. The server compacts, so removing slot 1 while slot 2 is
 * filled leaves the word with the second image in first position.
 *
 * @param {number} slot - 1 or 2
 */
async function removeImageSlot(slot) {
    if (!confirm('Are you sure you want to remove this image?')) return;

    try {
        showLoading(true);

        const response = await fetch(
            `/api/words/${AppState.currentWord.id}/image/${slot}`,
            { method: 'DELETE' }
        );

        const data = await response.json();

        if (!data.success) {
            showError(data.error || 'Failed to remove image');
            return;
        }

        applyImageState(data);

        if (AppState.currentWord.image_file) {
            renderImageBlocks();
        } else {
            toggleImageDisplayModal(false);
        }
    } catch (error) {
        console.error('Error removing image:', error);
        showError('Network error while removing image');
    } finally {
        showLoading(false);
    }
}
```

- [ ] **Step 2: Render the button**

In `renderImageBlocks()`, replace:

```javascript
        actions.append(replaceBtn);
        block.append(img, actions);
```

with:

```javascript
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-danger btn-sm';
        removeBtn.textContent = 'Remove';
        removeBtn.addEventListener('click', () => removeImageSlot(entry.slot));

        actions.append(replaceBtn, removeBtn);
        block.append(img, actions);
```

- [ ] **Step 3: Run tests**

Run: `pytest test/test_basic.py -v`
Expected: all PASS.

- [ ] **Step 4: Verify compaction in the browser**

Start the server, hard-refresh, then on a word with two images:

1. Note which image is second. Click `Remove` under image 1 and confirm.
2. Expected: **the former image 2 is now the only image, in first position**, and `Add Image` is visible again.
3. Add a second image again, then `Remove` the second one — image 1 is untouched.
4. Remove the last image — the modal closes and the card button reads `Add Image`.

Stop the server.

- [ ] **Step 5: Commit**

```bash
git add static/js/app.js
git commit -m "Add per-image Remove control with server-side compaction"
```

---

### Task 10: Full verification pass

Every step from the spec's manual test plan, run in one sitting against the finished feature. No code changes unless a step fails.

**Files:** none

- [ ] **Step 1: Confirm the suite is green**

```bash
conda activate bkdict
pytest test/test_basic.py -v
```

Expected: all PASS, including the tests added in Tasks 1, 2, 4, 5 and 7.

- [ ] **Step 2: Start the server and hard-refresh**

```bash
python app.py
```

Open `http://localhost:5001` and press Ctrl+F5.

- [ ] **Step 3: Work through the spec's manual checklist**

1. Word with one image → one image, its `Replace`/`Remove` row, `Add Image` visible, **no scroll bar**.
2. `Add Image` → Ctrl+V → confirm → two blocks, **scroll bar on the right**, `Add Image` gone.
3. Drag the scroll bar; then use the wheel. Both images reachable by each.
4. `Replace` on image 2 → image 2 changes, image 1 does not.
5. `Remove` on image 1 → image 2 takes its place, `Add Image` reappears.
6. Re-add a second image, `Remove` image 2 → image 1 unaffected.
7. Remove the last image → modal closes, card button reads `Add Image`.
8. Quiz mode on a category with a two-image word → the slot-1 image renders.
9. Quiz filter `Image Only` → the two-image word appears.
10. Add New Word with an attached image → unchanged; new word has exactly one image.
11. A word in two categories with two images: remove image 1 from one category, open the word in the other → **both show image 2 compacted into slot 1** (removal is shared).
12. Auto-migration: stop the app, drop `image_file_2`, restart → the column is recreated and the app works.
    **Dropping the column discards every slot-2 reference.** Do this before attaching second images you want to keep, or use a scratch database.

- [ ] **Step 4: Check the console and filenames**

Browser console shows no errors. New files in `static/images/word_images/` are named `img_<id>_<slot>_<timestamp>.jpg`.

- [ ] **Step 5: Stop the server and confirm a clean tree**

```bash
git status
```

Expected: clean. If any step above required a fix, commit it before finishing.

---

## Self-Review

**Spec coverage** — every spec requirement maps to a task:

| Spec requirement | Task |
| --- | --- |
| `image_file_2` column + self-migration | 1 |
| `slot` on upload, default 1, 400 on invalid | 2, 3 |
| 409 when slot 2 requested with slot 1 empty | 3 |
| Filename collision fix | 3 |
| Upload response carries both slots | 3 |
| Compaction SQL, shared across rows | 4 |
| `DELETE /api/words/<id>/image/<slot>`, 404 on empty slot | 5 |
| `image_file_2` on the three SELECTs | 6 |
| `image_file` dropped from `PUT` and its docstring | 6 |
| Quiz SELECT and Image Only filter untouched | 6 (explicitly not changed) |
| 60vh scroll pane with native scroll bar | 7 |
| Blocks rendered from state, `data-slot` | 7 |
| Footer `Add Image` + `Close`; add hidden when full | 7 |
| Client re-renders from server truth | 7 |
| Per-image `Replace` | 8 |
| Per-image `Remove` | 9 |
| `updateImageButtonState` / `handleImageButtonClick` unchanged in behaviour | 7 (caller signature only) |
| Structural tests | 1, 2, 4, 5, 7 |
| Manual test plan | 10 |

**Placeholder scan:** none. Every code step carries the literal code to write; every test step carries the literal test and the exact command and expected result.

**Type consistency:** `parse_image_slot` returns `int|None` and is used only in Task 3 against a `None` check. `build_image_removal_sql(slot)` takes an `int` and is called only in Task 5. `applyImageState(data)` is defined in Task 7 and called in Tasks 7 and 9 with response objects that both carry `image_file`/`image_file_2` (Tasks 3 and 5 both return them). `renderImageBlocks()` is defined in Task 7 and extended in place by Tasks 8 and 9. `openImageDisplayModal()` loses its argument in Task 7, and both of its callers are updated in that same task. `openPasteModal(slot)` gains a defaulted parameter in Task 7; its pre-existing zero-argument caller in `handleImageButtonClick` stays valid.

**Ordering:** server before client, so every client task has a working endpoint. Task 7 is intentionally large because it removes element ids that `app.js` looks up unconditionally — splitting it would leave the page throwing on a null between commits.
