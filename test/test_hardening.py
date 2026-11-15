"""
Tests for the hardening changes (no database required):

- SECRET_KEY must be real on Vercel
- static files are cacheable through versioned URLs
- Sentry traces half of the requests by default
- routes that answer with a JSON 500 report the exception
- the backup script covers every table, including the stored images
"""

import importlib
import importlib.util
import datetime
import decimal
import os
import re
import sys

import pytest

os.environ['SKIP_DB'] = 'true'

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read_source(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as f:
        return f.read()


@pytest.fixture
def open_client(monkeypatch):
    """Test client with password protection switched off"""
    import app as app_module
    monkeypatch.setitem(app_module.app.config, 'TESTING', True)
    monkeypatch.setitem(app_module.app.config, 'SITE_PASSWORD', None)
    return app_module.app.test_client()


class TestSecretKey:
    """The session signing key must not be a public value on Vercel"""

    def test_missing_key_is_refused_on_vercel(self):
        from config import resolve_secret_key
        with pytest.raises(RuntimeError, match='SECRET_KEY'):
            resolve_secret_key({'VERCEL': '1'})

    def test_blank_key_is_refused_on_vercel(self):
        from config import resolve_secret_key
        with pytest.raises(RuntimeError):
            resolve_secret_key({'VERCEL': '1', 'SECRET_KEY': '   '})

    @pytest.mark.parametrize('public_value', [
        'dev-secret-key-change-in-production',
        'your-secret-key-here',
    ])
    def test_public_placeholders_are_refused_on_vercel(self, public_value):
        from config import resolve_secret_key
        with pytest.raises(RuntimeError):
            resolve_secret_key({'VERCEL': '1', 'SECRET_KEY': public_value})

    def test_real_key_is_used_on_vercel(self):
        from config import resolve_secret_key
        assert resolve_secret_key({'VERCEL': '1', 'SECRET_KEY': 'a-real-key'}) == 'a-real-key'

    def test_local_run_without_key_keeps_the_dev_fallback(self):
        from config import resolve_secret_key, DEV_SECRET_KEY
        assert resolve_secret_key({}) == DEV_SECRET_KEY

    def test_local_run_uses_its_own_key(self):
        from config import resolve_secret_key
        assert resolve_secret_key({'SECRET_KEY': 'local-key'}) == 'local-key'

    def test_example_placeholder_matches_the_refused_list(self):
        from config import PUBLIC_SECRET_KEYS
        example = re.search(r'^SECRET_KEY=(.*)$', read_source('.env.example'), re.M).group(1).strip()
        assert example in PUBLIC_SECRET_KEYS


class TestStaticCaching:
    """Static files carry a content hash and are cached; pages are not"""

    def test_url_for_static_adds_content_hash(self):
        import app as app_module
        with app_module.app.test_request_context():
            from flask import url_for
            url = url_for('static', filename='css/style.css')
        assert re.fullmatch(r'/static/css/style\.css\?v=[0-9a-f]{10}', url)

    def test_hash_follows_file_content(self, tmp_path, monkeypatch):
        import app as app_module
        monkeypatch.setattr(app_module.app, 'static_folder', str(tmp_path))
        monkeypatch.setattr(app_module, '_static_version_cache', {})
        target = tmp_path / 'a.css'
        target.write_text('body{}', encoding='utf-8')
        first = app_module.static_file_version('a.css')
        assert first == app_module.static_file_version('a.css')
        target.write_text('body{color:red}', encoding='utf-8')
        assert app_module.static_file_version('a.css') != first

    def test_missing_file_has_no_version(self):
        import app as app_module
        assert app_module.static_file_version('css/does-not-exist.css') is None
        with app_module.app.test_request_context():
            from flask import url_for
            assert url_for('static', filename='css/does-not-exist.css') == '/static/css/does-not-exist.css'

    def test_versioned_static_file_is_cached_for_a_year(self, open_client):
        response = open_client.get('/static/css/style.css?v=abc')
        assert response.status_code == 200
        cache = response.headers['Cache-Control']
        assert 'max-age=31536000' in cache
        assert 's-maxage=31536000' in cache
        assert 'immutable' in cache
        assert 'no-store' not in cache
        assert 'Pragma' not in response.headers
        response.close()

    def test_unversioned_static_file_must_be_revalidated(self, open_client):
        response = open_client.get('/static/css/style.css')
        assert response.status_code == 200
        assert response.headers['Cache-Control'] == 'no-cache'
        response.close()

    def test_missing_static_file_is_not_cached(self, open_client):
        response = open_client.get('/static/css/does-not-exist.css?v=abc')
        assert response.status_code == 404
        assert 'no-store' in response.headers['Cache-Control']

    def test_pages_and_api_are_still_never_cached(self, open_client):
        page = open_client.get('/')
        assert page.status_code == 200
        assert 'no-store' in page.headers['Cache-Control']
        api = open_client.get('/api/words/search')  # 400 before any database use
        assert 'no-store' in api.headers['Cache-Control']

    def test_pages_link_versioned_assets(self, open_client):
        html = open_client.get('/').get_data(as_text=True)
        assert re.search(r'/static/css/style\.css\?v=[0-9a-f]{10}"', html)
        assert re.search(r'/static/js/app\.js\?v=[0-9a-f]{10}"', html)
        quiz = open_client.get('/quiz').get_data(as_text=True)
        assert re.search(r'/static/js/quiz\.js\?v=[0-9a-f]{10}"', quiz)
        # A hand-written ?v= after url_for would produce a broken ?v=..?v=.. URL
        assert '?v=' not in read_source('templates', 'index.html')

    def test_theme_versions_reach_the_page(self, open_client):
        import app as app_module
        html = open_client.get('/').get_data(as_text=True)
        tag = re.search(r'<link id="themeStylesheet"[^>]*>', html).group(0)
        for theme in ('cyberpunk', 'duolingo', 'glassmorphism', 'minimalist'):
            version = app_module.static_file_version(f'css/themes/theme-{theme}.css')
            assert version and f'"{theme}": "{version}"' in tag

    def test_app_js_appends_theme_version(self):
        js = read_source('static', 'js', 'app.js')
        assert 'themeLink.dataset.versions' in js
        assert 'theme-${themeName}.css${query}' in js


class TestSentrySampleRate:
    """Half of the requests are traced unless the env var says otherwise"""

    def test_default_rate_is_half(self):
        import config
        old = os.environ.pop('SENTRY_TRACES_SAMPLE_RATE', None)
        try:
            importlib.reload(config)
            assert config.Config.SENTRY_TRACES_SAMPLE_RATE == '0.5'
        finally:
            if old is not None:
                os.environ['SENTRY_TRACES_SAMPLE_RATE'] = old
            importlib.reload(config)

    def test_bad_setting_falls_back_to_half(self, monkeypatch):
        from utils import monitoring
        monkeypatch.setattr(monitoring.Config, 'SENTRY_TRACES_SAMPLE_RATE', 'lots')
        assert monitoring._traces_sampler({'wsgi_environ': {'PATH_INFO': '/'}}) == 0.5

    def test_env_setting_is_respected_and_static_is_skipped(self, monkeypatch):
        from utils import monitoring
        monkeypatch.setattr(monitoring.Config, 'SENTRY_TRACES_SAMPLE_RATE', '0.2')
        assert monitoring._traces_sampler({'wsgi_environ': {'PATH_INFO': '/api/x'}}) == 0.2
        assert monitoring._traces_sampler({'wsgi_environ': {'PATH_INFO': '/static/a.css'}}) == 0


class TestApiErrorsAreReported:
    """A route that turns an exception into a JSON 500 must also report it"""

    def test_database_failure_is_reported_and_response_is_unchanged(self, open_client, monkeypatch):
        import app as app_module
        reported = []

        def broken_connection():
            raise RuntimeError('database is down')

        monkeypatch.setattr(app_module, 'get_db_connection', broken_connection)
        monkeypatch.setattr(app_module, 'capture_exception', reported.append)

        response = open_client.get('/api/categories')

        assert response.status_code == 500
        assert response.get_json() == {'success': False, 'error': 'database is down'}
        assert len(reported) == 1
        assert str(reported[0]) == 'database is down'

    def test_reporting_never_breaks_the_response(self, open_client, monkeypatch):
        import app as app_module

        def broken_connection():
            raise RuntimeError('database is down')

        def broken_traceback():
            raise OSError('stderr is closed')

        monkeypatch.setattr(app_module, 'get_db_connection', broken_connection)
        monkeypatch.setattr(app_module.traceback, 'print_exc', broken_traceback)

        response = open_client.get('/api/daily-count')
        assert response.status_code == 500
        assert response.get_json()['error'] == 'database is down'

    def test_every_handler_that_returns_500_reports(self):
        """Guards new routes: catching Exception and answering 500 needs a report"""
        lines = read_source('app.py').splitlines()
        unreported = []
        for number, line in enumerate(lines):
            if line.strip() != 'except Exception as e:':
                continue
            indent = len(line) - len(line.lstrip())
            block = []
            for following in lines[number + 1:]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                block.append(following)
            body = '\n'.join(block)
            if 'jsonify' in body and '500' in body and 'report_api_error(e)' not in body:
                unreported.append(number + 1)
        assert unreported == []


def load_backup_module():
    spec = importlib.util.spec_from_file_location(
        'backup_db_under_test', os.path.join(ROOT, 'scripts', 'backup_db.py')
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeMissingTable(Exception):
    pass


class FakeImageCursor:
    """Stands in for a dictionary cursor over word_images"""

    def __init__(self, images):
        self.images = images
        self.result = []
        self.closed = False

    def execute(self, sql, params=None):
        if params is None:
            self.result = [
                {'filename': name, 'mime_type': 'image/jpeg',
                 'created_at': datetime.datetime(2026, 11, 1, 9, 30)}
                for name in sorted(self.images)
            ]
        else:
            self.result = [{'data': bytearray(self.images[params[0]])}]

    def fetchall(self):
        return self.result

    def fetchone(self):
        return self.result[0] if self.result else None

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, dictionary=False):
        return self._cursor


class TestBackupScript:
    """The backup must hold everything needed to rebuild the database"""

    def test_covers_every_table(self):
        backup = load_backup_module()
        for table in ('words', 'word_history', 'categories', 'daily_study_log', 'daily_word_reviews'):
            assert table in backup.ROW_TABLES
        assert backup.IMAGE_TABLE == 'word_images'

    def test_never_writes_to_the_database(self):
        source = read_source('scripts', 'backup_db.py')
        for statement in ('INSERT ', 'UPDATE ', 'DELETE ', 'DROP ', 'ALTER ', 'TRUNCATE ', '.commit('):
            assert statement not in source

    def test_values_become_json_friendly(self):
        backup = load_backup_module()
        assert backup.serialize_value(datetime.date(2026, 11, 15)) == '2026-11-15'
        assert backup.serialize_value(datetime.datetime(2026, 11, 15, 8, 5)) == '2026-11-15T08:05:00'
        assert backup.serialize_value(decimal.Decimal('2.5')) == 2.5
        assert backup.serialize_value('文化'.encode('utf-8')) == '文化'
        assert backup.serialize_value(b'\xff\xd8') == {'base64': '/9g='}
        assert backup.serialize_value(None) is None
        assert backup.serialize_value(7) == 7

    def test_image_names_cannot_leave_the_folder(self):
        backup = load_backup_module()
        assert backup.safe_image_name('img_1_1_170.jpg') == 'img_1_1_170.jpg'
        assert backup.safe_image_name('../../app.py') == 'app.py'
        assert backup.safe_image_name('..\\..\\app.py') == 'app.py'
        assert backup.safe_image_name('..') is None
        assert backup.safe_image_name('') is None
        assert backup.safe_image_name(None) is None

    def test_images_are_written_as_files_with_metadata(self, tmp_path):
        backup = load_backup_module()
        images = {'img_2_1_10.jpg': b'second', 'img_1_1_10.jpg': b'first-image'}
        cursor = FakeImageCursor(images)
        images_dir = tmp_path / 'images'

        entries = backup.backup_images(FakeConnection(cursor), str(images_dir))

        assert [e['filename'] for e in entries] == ['img_1_1_10.jpg', 'img_2_1_10.jpg']
        assert entries[0] == {
            'filename': 'img_1_1_10.jpg',
            'mime_type': 'image/jpeg',
            'created_at': '2026-11-01T09:30:00',
            'size': 11,
            'saved_as': 'img_1_1_10.jpg',
        }
        assert (images_dir / 'img_1_1_10.jpg').read_bytes() == b'first-image'
        assert (images_dir / 'img_2_1_10.jpg').read_bytes() == b'second'
        assert cursor.closed

    def test_no_images_creates_no_folder(self, tmp_path):
        backup = load_backup_module()
        images_dir = tmp_path / 'images'
        assert backup.backup_images(FakeConnection(FakeImageCursor({})), str(images_dir)) == []
        assert not images_dir.exists()

    def test_missing_table_is_skipped_not_fatal(self):
        backup = load_backup_module()

        class MissingTableCursor:
            def execute(self, sql, params=None):
                raise backup.mysql.connector.Error(msg="Table doesn't exist", errno=1146)

            def close(self):
                pass

        assert backup.backup_rows(MissingTableCursor(), 'daily_word_reviews') is None
        assert backup.backup_images(FakeConnection(MissingTableCursor()), 'unused') is None

    def test_other_database_errors_are_not_swallowed(self):
        backup = load_backup_module()

        class DeniedCursor:
            def execute(self, sql, params=None):
                raise backup.mysql.connector.Error(msg='Access denied', errno=1045)

        with pytest.raises(backup.mysql.connector.Error):
            backup.backup_rows(DeniedCursor(), 'words')
