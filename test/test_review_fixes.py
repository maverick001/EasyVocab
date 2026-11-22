"""
Tests for the fixes that followed the codebase review (no database required):

- reviewing a word no longer stamps updated_at 10 hours ahead
- deleting words, deleting a category and merging entries remove image bytes
  that nothing references any more
- text from the database is never inserted into the page as HTML
- a late response cannot replace the word the user has navigated to
"""

import os
import re
import sys

import mysql.connector
import pytest

os.environ['SKIP_DB'] = 'true'

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read_source(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as f:
        return f.read()


def js_function_body(source, name):
    """Text of a top-level JS function, from its declaration to the next one"""
    start = source.index(f'function {name}(')
    following = re.search(r'\n(?:async )?function \w+\(', source[start + 1:])
    return source[start:start + 1 + following.start()] if following else source[start:]


class ScriptedCursor:
    """
    Cursor stand-in that records every statement and answers SELECTs.

    `answers` maps a fragment of SQL to the rows that statement returns; the
    first fragment found in the statement wins. `fail_on` is a fragment whose
    statement raises a MySQL error instead.
    """

    def __init__(self, answers, fail_on=None, rowcount=1):
        self.answers = answers
        self.fail_on = fail_on
        self.rowcount = rowcount
        self.lastrowid = 1
        self.statements = []
        self._rows = []

    def execute(self, sql, params=None):
        flat = ' '.join(sql.split())
        self.statements.append((flat, tuple(params) if params is not None else None))
        if self.fail_on and self.fail_on in flat:
            raise mysql.connector.Error(msg='simulated failure', errno=1205)
        self._rows = []
        for fragment, rows in self.answers.items():
            if fragment in flat:
                self._rows = list(rows)
                break

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows, self._rows = self._rows, []
        return rows

    def callproc(self, name):
        self.statements.append((f'CALL {name}', None))

    def stored_results(self):
        return []

    def close(self):
        pass

    def index_of(self, fragment):
        """Position of the first statement containing fragment, or -1"""
        for position, (sql, _) in enumerate(self.statements):
            if fragment in sql:
                return position
        return -1

    def params_of(self, fragment):
        return self.statements[self.index_of(fragment)][1]


class ScriptedConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, *args, **kwargs):
        return self._cursor

    def commit(self):
        self.commits += 1
        self._cursor.statements.append(('COMMIT', None))

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


@pytest.fixture
def run_route(monkeypatch):
    """Call a route against a scripted cursor; returns (response, cursor, connection)"""
    import app as app_module
    monkeypatch.setitem(app_module.app.config, 'TESTING', True)
    monkeypatch.setitem(app_module.app.config, 'SITE_PASSWORD', None)

    def run(method, path, cursor, **kwargs):
        connection = ScriptedConnection(cursor)
        monkeypatch.setattr(app_module, 'get_db_connection', lambda: connection)
        response = getattr(app_module.app.test_client(), method)(path, **kwargs)
        return response, cursor, connection

    return run


BLOB_DELETE = 'DELETE FROM word_images'


class TestReviewTimestamp:
    """Reviewing a word must use the same clock for updated_at as editing it"""

    def test_review_writes_plain_current_time_to_updated_at(self, run_route):
        cursor = ScriptedCursor({
            'SELECT word FROM words WHERE id': [{'word': 'brunt'}],
            'SELECT word, translation, example_sentence, category, review_count': [{
                'word': 'brunt', 'translation': '冲击', 'example_sentence': None,
                'category': 'AI', 'review_count': 3, 'last_reviewed': None,
            }],
        })
        response, cursor, connection = run_route('post', '/api/words/7/review', cursor)

        assert response.status_code == 200
        assert response.get_json()['review_count'] == 3
        update = cursor.statements[cursor.index_of('SET review_count = review_count + 1')][0]
        assert 'updated_at = CURRENT_TIMESTAMP WHERE word = %s' in update
        assert 'updated_at = DATE_ADD' not in update
        # last_reviewed is a display value in AEST and is left as it was
        assert 'last_reviewed = DATE_ADD(CURRENT_TIMESTAMP, INTERVAL 10 HOUR)' in update
        assert connection.commits == 1

    def test_no_route_stamps_updated_at_ahead(self):
        source = ' '.join(read_source('app.py').split())
        assert 'updated_at = DATE_ADD' not in source


class TestOrphanedImagesAreRemoved:
    """Image bytes go when the last row that used them goes"""

    def word_cursor(self, others=(), fail_on=None):
        return ScriptedCursor({
            'SELECT word, category FROM words WHERE id': [{'word': 'brunt', 'category': 'AI'}],
            'SELECT category FROM words WHERE word = %s AND id != %s': [
                {'category': name} for name in others
            ],
            'SELECT image_file, image_file_2 FROM words WHERE word = %s': [
                {'image_file': 'img_7_1_10.jpg', 'image_file_2': None},
            ],
        }, fail_on=fail_on)

    def test_deleting_a_word_removes_its_unreferenced_images(self, run_route):
        response, cursor, connection = run_route('delete', '/api/words/7', self.word_cursor())

        assert response.status_code == 200
        assert response.get_json()['success'] is True
        deleted_row = cursor.index_of('DELETE FROM words WHERE id = %s')
        deleted_blob = cursor.index_of(BLOB_DELETE)
        committed = cursor.index_of('COMMIT')
        # After the row is gone (so it no longer counts as a reference) and
        # inside the same transaction (so a rollback restores both)
        assert -1 < deleted_row < deleted_blob < committed
        assert cursor.params_of(BLOB_DELETE) == ('img_7_1_10.jpg',)
        # Only bytes that no remaining row points at are removed
        assert 'filename NOT IN (SELECT image_file FROM words' in cursor.statements[deleted_blob][0]

    def test_images_are_read_before_the_rows_are_deleted(self, run_route):
        _, cursor, _ = run_route('delete', '/api/words/7?scope=all_categories', self.word_cursor(others=['Science']))
        read_images = cursor.index_of('SELECT image_file, image_file_2 FROM words WHERE word = %s')
        deleted_rows = cursor.index_of('DELETE FROM words WHERE word = %s')
        assert -1 < read_images < deleted_rows < cursor.index_of(BLOB_DELETE)

    def test_asking_which_category_deletes_nothing(self, run_route):
        """The confirmation step for a multi-category word must stay read-only"""
        response, cursor, connection = run_route('delete', '/api/words/7', self.word_cursor(others=['Science']))
        assert response.get_json()['requires_confirmation'] is True
        assert cursor.index_of('DELETE') == -1
        assert connection.commits == 0

    def test_word_without_images_runs_no_cleanup(self, run_route):
        cursor = self.word_cursor()
        cursor.answers['SELECT image_file, image_file_2 FROM words WHERE word = %s'] = [
            {'image_file': None, 'image_file_2': None},
        ]
        response, cursor, _ = run_route('delete', '/api/words/7', cursor)
        assert response.status_code == 200
        assert cursor.index_of(BLOB_DELETE) == -1

    def test_cleanup_failure_does_not_block_the_delete(self, run_route, monkeypatch):
        import app as app_module
        reported = []
        monkeypatch.setattr(app_module, 'capture_exception', reported.append)

        response, cursor, connection = run_route(
            'delete', '/api/words/7', self.word_cursor(fail_on=BLOB_DELETE)
        )

        assert response.status_code == 200
        assert response.get_json()['success'] is True
        assert cursor.index_of('DELETE FROM words WHERE id = %s') > -1
        assert connection.commits >= 1
        assert connection.rollbacks == 0
        assert len(reported) == 1

    def test_deleting_a_category_removes_images_of_dropped_copies(self, run_route):
        cursor = ScriptedCursor({
            'SELECT name FROM categories WHERE name': [{'name': 'AI'}],
            'SELECT image_file, image_file_2 FROM words WHERE category = %s': [
                {'image_file': 'img_7_1_10.jpg', 'image_file_2': 'img_7_2_10.jpg'},
            ],
        })
        response, cursor, connection = run_route('delete', '/api/categories/AI', cursor)

        assert response.status_code == 200
        read_images = cursor.index_of('SELECT image_file, image_file_2 FROM words WHERE category = %s')
        dropped = cursor.index_of('DELETE FROM words WHERE category = %s')
        moved = cursor.index_of('UPDATE words SET category = %s WHERE category = %s')
        deleted_blob = cursor.index_of(BLOB_DELETE)
        assert -1 < read_images < dropped < moved < deleted_blob < cursor.index_of('COMMIT')
        assert cursor.params_of(BLOB_DELETE) == ('img_7_1_10.jpg', 'img_7_2_10.jpg')

    def test_merging_entries_removes_images_the_kept_row_did_not_take(self, run_route):
        kept = {
            'id': 7, 'word': 'brunt', 'category': 'AI', 'translation': '冲击',
            'example_sentence': None, 'ipa': None,
            'image_file': 'kept.jpg', 'image_file_2': None,
            'review_count': 2, 'last_reviewed': None,
            'last_sample_review_date': None, 'last_daily_activity_date': None,
        }
        absorbed = dict(kept, id=9, category='Science', image_file='absorbed.jpg')
        cursor = ScriptedCursor({
            'SELECT * FROM words WHERE id = %s': [kept],
            'SELECT * FROM words WHERE word = %s AND category = %s': [absorbed],
        })
        response, cursor, _ = run_route(
            'put', '/api/words/7/category', cursor, json={'new_category': 'Science'}
        )

        assert response.status_code == 200
        assert response.get_json()['merged'] is True
        relabelled = cursor.index_of('UPDATE words SET')
        deleted_blob = cursor.index_of(BLOB_DELETE)
        assert -1 < relabelled < deleted_blob < cursor.index_of('COMMIT')
        assert cursor.params_of(BLOB_DELETE) == ('absorbed.jpg',)

    def test_plain_move_runs_no_cleanup(self, run_route):
        cursor = ScriptedCursor({
            'SELECT * FROM words WHERE id = %s': [{
                'id': 7, 'word': 'brunt', 'category': 'AI', 'translation': '冲击',
                'example_sentence': None, 'image_file': 'kept.jpg', 'image_file_2': None,
            }],
        })
        response, cursor, _ = run_route(
            'put', '/api/words/7/category', cursor, json={'new_category': 'Science'}
        )
        assert response.status_code == 200
        assert response.get_json()['merged'] is False
        assert cursor.index_of(BLOB_DELETE) == -1

    def test_move_counts_as_a_review(self, run_route):
        from datetime import date
        cursor = ScriptedCursor({
            'SELECT * FROM words WHERE id = %s': [{
                'id': 7, 'word': 'brunt', 'category': 'AI', 'translation': '冲击',
                'example_sentence': None, 'image_file': None, 'image_file_2': None,
                'last_sample_review_date': None,
            }],
        })
        response, cursor, _ = run_route(
            'put', '/api/words/7/category', cursor, json={'new_category': 'Science'}
        )
        assert response.status_code == 200
        assert response.get_json()['review_counted'] is True
        assert cursor.index_of('review_count = review_count + 1') > -1
        assert cursor.index_of('last_sample_review_date = %s') > -1
        # the stored date is the review day, passed as a parameter
        assert cursor.params_of('last_sample_review_date = %s')[0] == date.today()

    def test_second_review_the_same_day_is_not_counted(self, run_route):
        from datetime import date
        cursor = ScriptedCursor({
            'SELECT * FROM words WHERE id = %s': [{
                'id': 7, 'word': 'brunt', 'category': 'AI', 'translation': '冲击',
                'example_sentence': None, 'image_file': None, 'image_file_2': None,
                'last_sample_review_date': date.today(),
            }],
        })
        response, cursor, _ = run_route(
            'put', '/api/words/7/category', cursor, json={'new_category': 'Science'}
        )
        assert response.status_code == 200
        assert response.get_json()['review_counted'] is False
        assert cursor.index_of('review_count = review_count + 1') == -1


class TestNoDatabaseTextAsHtml:
    """Words, categories and sentences are set as text, never parsed as HTML"""

    def test_quiz_sentences_are_set_as_text(self):
        body = js_function_body(read_source('static', 'js', 'quiz.js'), 'displayWord')
        assert 'p.textContent = sentence' in body
        assert 'sentencesDisplay.replaceChildren(' in body
        assert '<p>${' not in body

    def test_quiz_never_interpolates_into_inner_html(self):
        for line in read_source('static', 'js', 'quiz.js').splitlines():
            if 'innerHTML' in line:
                assert '${' not in line, line

    def test_duplicate_word_message_is_built_from_nodes(self):
        js = read_source('static', 'js', 'app.js')
        assert 'onclick="navigateToExistingWord' not in js
        assert 'Elements.addWordStatus.innerHTML' not in js
        assert 'Elements.addWordStatus.replaceChildren(' in js
        assert 'navigateToExistingWord(data.existing_category, data.existing_word_id)' in js


class TestStaleWordResponses:
    """Holding an arrow key must not let an old response replace the current word"""

    def test_load_word_ignores_responses_that_are_no_longer_latest(self):
        js = read_source('static', 'js', 'app.js')
        body = js_function_body(js, 'loadWord')
        assert 'const requestId = ++latestWordRequestId;' in body
        # The check sits between receiving the response and showing the word
        received = body.index('await response.json()')
        checked = body.index('if (!isLatest()) return;')
        shown = body.index('displayWord(data.word)')
        assert received < checked < shown

    def test_stale_request_leaves_the_loading_indicator_alone(self):
        body = js_function_body(read_source('static', 'js', 'app.js'), 'loadWord')
        assert 'if (isLatest()) showLoading(false);' in body
        assert body.count('showLoading(false)') == 1
