"""
Settings page tests (no database): validation, history zero-fill, debt maths,
the app_tz default, the page and API routes, and a save/load round trip
against an in-memory fake cursor.
"""

import os
import sys
from datetime import date, datetime, timedelta

import pytest

os.environ['SKIP_DB'] = 'true'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.settings import (  # noqa: E402
    DEFAULT_SETTINGS,
    FIXED_AEST,
    calculate_debt,
    parse_settings,
    resolve_timezone,
    validate_settings,
    zero_fill_history,
)


# ============================================
# Pure helpers
# ============================================

class TestValidation:
    def test_valid_payload_is_typed(self):
        clean, errors = validate_settings({
            'daily_target': '150',
            'debt_enabled': False,
            'debt_start_date': '2026-01-31',
            'timezone': 'Australia/Sydney',
        })
        assert errors == {}
        assert clean == {
            'daily_target': 150,
            'debt_enabled': False,
            'debt_start_date': '2026-01-31',
            'timezone': 'Australia/Sydney',
        }

    @pytest.mark.parametrize('bad', [0, -5, 1001, 'abc', '12.5', 3.5, True, None, []])
    def test_daily_target_out_of_range_or_not_a_whole_number(self, bad):
        clean, errors = validate_settings({'daily_target': bad})
        assert 'daily_target' in errors
        assert clean == {}

    @pytest.mark.parametrize('good', [1, 100, 1000, '1000'])
    def test_daily_target_bounds_are_inclusive(self, good):
        clean, errors = validate_settings({'daily_target': good})
        assert errors == {}
        assert clean['daily_target'] == int(good)

    @pytest.mark.parametrize('bad', ['2026-13-01', 'yesterday', '31/01/2026'])
    def test_bad_start_date(self, bad):
        _, errors = validate_settings({'debt_start_date': bad})
        assert 'debt_start_date' in errors

    def test_empty_start_date_and_timezone_mean_default(self):
        clean, errors = validate_settings({'debt_start_date': '', 'timezone': ''})
        assert errors == {}
        assert clean == {'debt_start_date': '', 'timezone': ''}

    @pytest.mark.parametrize('bad', [0, 1, 7, 'x', 2.5])
    def test_quiz_choice_count_must_be_2_to_6(self, bad):
        _, errors = validate_settings({'quiz_choice_count': bad})
        assert 'quiz_choice_count' in errors

    @pytest.mark.parametrize('good', [2, 4, 6, '5'])
    def test_quiz_choice_count_bounds_are_inclusive(self, good):
        clean, errors = validate_settings({'quiz_choice_count': good})
        assert errors == {}
        assert clean['quiz_choice_count'] == int(good)

    def test_unknown_timezone_is_rejected(self):
        _, errors = validate_settings({'timezone': 'Mars/Olympus_Mons'})
        assert 'timezone' in errors

    def test_unknown_key_is_rejected_not_stored(self):
        clean, errors = validate_settings({'hack': 1})
        assert 'hack' in errors
        assert clean == {}

    def test_non_object_payload(self):
        _, errors = validate_settings(None)
        assert errors

    def test_one_bad_value_does_not_hide_the_others(self):
        clean, errors = validate_settings({'daily_target': 50, 'timezone': 'nope/nope'})
        assert clean == {'daily_target': 50}
        assert list(errors) == ['timezone']


class TestParseSettings:
    def test_empty_gives_the_old_behaviour(self):
        assert parse_settings({}) == DEFAULT_SETTINGS
        assert DEFAULT_SETTINGS['daily_target'] == 100
        assert DEFAULT_SETTINGS['debt_enabled'] is True

    def test_stored_strings_become_typed_values(self):
        result = parse_settings({'daily_target': '80', 'debt_enabled': '0'})
        assert result['daily_target'] == 80
        assert result['debt_enabled'] is False

    def test_malformed_rows_fall_back_to_defaults(self):
        result = parse_settings({'daily_target': 'lots', 'timezone': 'x/y', 'junk': '1'})
        assert result == DEFAULT_SETTINGS


class TestZeroFillHistory:
    def test_fills_missing_days_oldest_first(self):
        today = date(2026, 11, 22)
        rows = [
            {'date': date(2026, 11, 22), 'review_count': 40},
            {'date': datetime(2026, 11, 20, 0, 0), 'review_count': 120},
        ]
        history = zero_fill_history(rows, today, 7)
        assert [d['date'] for d in history] == [
            '2026-11-16', '2026-11-17', '2026-11-18', '2026-11-19',
            '2026-11-20', '2026-11-21', '2026-11-22',
        ]
        assert [d['review_count'] for d in history] == [0, 0, 0, 0, 120, 0, 40]

    def test_no_rows_is_all_zeros_of_the_right_length(self):
        history = zero_fill_history([], date(2026, 11, 22), 30)
        assert len(history) == 30
        assert all(d['review_count'] == 0 for d in history)

    def test_null_count_counts_as_zero(self):
        history = zero_fill_history(
            [{'date': date(2026, 11, 22), 'review_count': None}], date(2026, 11, 22), 7
        )
        assert history[-1]['review_count'] == 0


class TestCalculateDebt:
    TODAY = date(2026, 11, 22)

    def test_missed_days_add_the_full_target(self):
        total, breakdown = calculate_debt({}, self.TODAY - timedelta(days=3), self.TODAY, 100)
        assert total == 300
        assert [b['debt'] for b in breakdown] == [100, 100, 100]

    def test_a_surplus_pays_debt_down_and_todays_shortfall_is_ignored(self):
        counts = {self.TODAY - timedelta(days=1): 130, self.TODAY: 10}
        total, _ = calculate_debt(counts, self.TODAY - timedelta(days=2), self.TODAY, 100)
        assert total == 100 + (100 - 130)  # day-2 missed, day-1 surplus, today ignored

    def test_todays_surplus_over_target_counts(self):
        counts = {self.TODAY - timedelta(days=1): 0, self.TODAY: 130}
        total, _ = calculate_debt(counts, self.TODAY - timedelta(days=1), self.TODAY, 100)
        assert total == 100 - 30

    def test_surplus_can_take_debt_below_zero(self):
        counts = {self.TODAY - timedelta(days=1): 500}
        total, _ = calculate_debt(counts, self.TODAY - timedelta(days=1), self.TODAY, 100)
        assert total == 100 - 500

    def test_banked_surplus_is_drawn_down_by_a_later_miss(self):
        counts = {self.TODAY - timedelta(days=2): 250}  # day-1 has no reviews
        total, _ = calculate_debt(counts, self.TODAY - timedelta(days=2), self.TODAY, 100)
        assert total == (100 - 250) + 100

    def test_a_different_target_changes_the_debt(self):
        total, _ = calculate_debt({}, self.TODAY - timedelta(days=2), self.TODAY, 25)
        assert total == 50

    def test_start_date_ignores_earlier_days(self):
        total, breakdown = calculate_debt(
            {}, self.TODAY - timedelta(days=10), self.TODAY, 100,
            start_date=self.TODAY - timedelta(days=2),
        )
        assert total == 200
        assert len(breakdown) == 2

    def test_start_date_before_the_first_log_changes_nothing(self):
        total, _ = calculate_debt(
            {}, self.TODAY - timedelta(days=2), self.TODAY, 100,
            start_date=self.TODAY - timedelta(days=50),
        )
        assert total == 200

    def test_breakdown_is_capped_at_20_days(self):
        _, breakdown = calculate_debt({}, self.TODAY - timedelta(days=60), self.TODAY, 100)
        assert len(breakdown) == 20
        assert breakdown[0]['date'] == '2026-11-21'


# ============================================
# app_tz
# ============================================

@pytest.fixture
def app_module(monkeypatch):
    import app as module
    monkeypatch.setitem(module.app.config, 'TESTING', True)
    monkeypatch.setitem(module.app.config, 'SITE_PASSWORD', None)
    module.reset_tz_cache()
    yield module
    module.reset_tz_cache()


class TestAppTz:
    def test_default_is_the_fixed_plus_ten_the_app_always_used(self, app_module, monkeypatch):
        monkeypatch.setattr(app_module, 'get_setting', lambda key, default=None: '')
        tz = app_module.app_tz()
        assert tz == FIXED_AEST
        assert datetime(2026, 1, 1, tzinfo=tz).utcoffset() == timedelta(hours=10)

    def test_a_named_timezone_is_used(self, app_module, monkeypatch):
        monkeypatch.setattr(app_module, 'get_setting', lambda key, default=None: 'UTC')
        tz = app_module.app_tz()
        assert datetime(2026, 1, 1, tzinfo=tz).utcoffset() == timedelta(0)

    def test_database_failure_falls_back_to_the_default(self, app_module, monkeypatch):
        def broken():
            raise RuntimeError('no database')
        monkeypatch.setattr(app_module, 'get_db_connection', broken)
        assert app_module.app_tz() == FIXED_AEST

    def test_unknown_name_falls_back(self):
        assert resolve_timezone('Not/AZone') == FIXED_AEST

    def test_sql_interval_is_the_old_text_by_default(self, app_module, monkeypatch):
        monkeypatch.setattr(app_module, 'get_setting', lambda key, default=None: '')
        assert app_module.tz_interval_sql() == 'INTERVAL 10 HOUR'

    @pytest.mark.parametrize('zone, expected', [
        ('UTC', 'INTERVAL 0 HOUR'),
        ('Asia/Kolkata', 'INTERVAL 19800 SECOND'),
    ])
    def test_sql_interval_follows_the_chosen_zone(self, app_module, monkeypatch, zone, expected):
        monkeypatch.setattr(app_module, 'get_setting', lambda key, default=None: zone)
        assert app_module.tz_interval_sql() == expected

    def test_sql_interval_can_be_negative(self, app_module, monkeypatch):
        monkeypatch.setattr(app_module, 'get_setting', lambda key, default=None: 'America/New_York')
        assert app_module.tz_interval_sql() in ('INTERVAL -5 HOUR', 'INTERVAL -4 HOUR')

    def test_no_route_still_hardcodes_the_plus_ten_shift(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.py')
        with open(path, encoding='utf-8') as handle:
            source = handle.read()
        assert 'timedelta(hours=10)' not in source
        assert 'INTERVAL 10 HOUR)' not in source.replace('"INTERVAL 10 HOUR"', '')

    def test_review_day_is_the_server_date_when_no_zone_is_chosen(self, app_module, monkeypatch):
        monkeypatch.setattr(app_module, 'get_setting', lambda key, default=None: '')
        assert app_module.review_today() == date.today()

    def test_review_day_follows_a_chosen_zone(self, app_module, monkeypatch):
        monkeypatch.setattr(app_module, 'get_setting', lambda key, default=None: 'Pacific/Kiritimati')
        # UTC+14: always a different clock from UTC, so compare to that zone
        from zoneinfo import ZoneInfo
        assert app_module.review_today() == datetime.now(ZoneInfo('Pacific/Kiritimati')).date()

    def test_no_review_path_uses_curdate_or_the_server_date(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.py')
        with open(path, encoding='utf-8') as handle:
            source = handle.read()
        assert 'CURDATE()' not in source
        assert source.count('date.today()') == 1  # only inside review_today()

    def test_result_is_cached_until_reset(self, app_module, monkeypatch):
        calls = []

        def fake_get(key, default=None):
            calls.append(key)
            return ''
        monkeypatch.setattr(app_module, 'get_setting', fake_get)
        app_module.app_tz()
        app_module.app_tz()
        assert len(calls) == 1
        app_module.reset_tz_cache()
        app_module.app_tz()
        assert len(calls) == 2


# ============================================
# Routes
# ============================================

class FakeCursor:
    """In-memory stand-in for the few tables the settings routes touch"""

    def __init__(self, settings=None, log_rows=None, earliest=None):
        self.settings = dict(settings or {})
        self.log_rows = log_rows or []
        self.earliest = earliest
        self.statements = []
        self._result = []

    def execute(self, sql, params=None):
        flat = ' '.join(sql.split())
        self.statements.append((flat, params))
        self._result = []
        if flat.startswith('SELECT setting_key'):
            self._result = [
                {'setting_key': k, 'setting_value': v} for k, v in self.settings.items()
            ]
        elif flat.startswith('INSERT INTO app_settings'):
            self.settings[params[0]] = params[1]
        elif 'MIN(date)' in flat:
            self._result = [{'earliest_date': self.earliest}]
        elif 'FROM daily_study_log' in flat and 'WHERE date >=' in flat:
            since, until = params
            self._result = [r for r in self.log_rows if since <= r['date'] <= until]
        elif 'FROM daily_study_log' in flat and 'WHERE date = %s' in flat:
            self._result = [r for r in self.log_rows if r['date'].strftime('%Y-%m-%d') == params[0]][:1]
        elif flat.startswith('SELECT date, review_count FROM daily_study_log'):
            self._result = list(self.log_rows)

    def fetchall(self):
        return list(self._result)

    def fetchone(self):
        return self._result[0] if self._result else None

    def close(self):
        pass

    def wrote_settings(self):
        return any(s.startswith('INSERT INTO app_settings') for s, _ in self.statements)


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, *args, **kwargs):
        return self._cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


@pytest.fixture
def call(app_module, monkeypatch):
    """call(method, path, cursor, **kwargs) -> (response, connection)"""
    def run(method, path, cursor, **kwargs):
        connection = FakeConnection(cursor)
        monkeypatch.setattr(app_module, 'get_db_connection', lambda: connection)
        response = getattr(app_module.app.test_client(), method)(path, **kwargs)
        return response, connection
    return run


class TestSettingsPage:
    def test_page_renders_when_open_access(self, app_module):
        response = app_module.app.test_client().get('/settings')
        assert response.status_code == 200
        assert b'settings-page' in response.data
        assert b'js/settings.js' in response.data

    def test_page_sends_visitors_to_login_when_a_password_is_set(self, app_module, monkeypatch):
        monkeypatch.setitem(app_module.app.config, 'SITE_PASSWORD', 'secret')
        response = app_module.app.test_client().get('/settings')
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_page_renders_after_login(self, app_module, monkeypatch):
        monkeypatch.setitem(app_module.app.config, 'SITE_PASSWORD', 'secret')
        client = app_module.app.test_client()
        with client.session_transaction() as sess:
            sess['logged_in'] = True
        assert client.get('/settings').status_code == 200

    def test_settings_api_is_login_guarded(self, app_module, monkeypatch):
        monkeypatch.setitem(app_module.app.config, 'SITE_PASSWORD', 'secret')
        client = app_module.app.test_client()
        assert client.get('/api/settings').status_code == 401
        assert client.post('/api/settings', json={'daily_target': 5}).status_code == 401
        assert client.get('/api/review-history?days=7').status_code == 401

    def test_vocab_and_quiz_pages_link_to_settings(self, app_module):
        client = app_module.app.test_client()
        assert b'href="/settings"' in client.get('/').data
        assert b'href="/settings"' in client.get('/quiz').data


class TestSettingsApi:
    def test_get_returns_defaults_when_nothing_is_saved(self, call):
        response, _ = call('get', '/api/settings', FakeCursor())
        body = response.get_json()
        assert response.status_code == 200
        assert body['settings'] == DEFAULT_SETTINGS

    def test_save_then_load_round_trip(self, call):
        cursor = FakeCursor()
        response, connection = call('post', '/api/settings', cursor, json={
            'daily_target': 60,
            'debt_enabled': False,
            'debt_start_date': '2026-10-01',
            'timezone': 'Australia/Sydney',
        })
        assert response.status_code == 200
        assert connection.commits == 1
        assert cursor.settings == {
            'daily_target': '60',
            'debt_enabled': '0',
            'debt_start_date': '2026-10-01',
            'timezone': 'Australia/Sydney',
        }

        response, _ = call('get', '/api/settings', cursor)
        assert response.get_json()['settings'] == {
            'daily_target': 60,
            'debt_enabled': False,
            'debt_start_date': '2026-10-01',
            'timezone': 'Australia/Sydney',
            'quiz_choice_count': 4,  # never saved, so the default
            'quiz_session_size': 0,
        }

    def test_partial_save_keeps_other_settings(self, call):
        cursor = FakeCursor({'daily_target': '60', 'timezone': 'UTC'})
        response, _ = call('post', '/api/settings', cursor, json={'daily_target': 70})
        assert response.status_code == 200
        assert response.get_json()['settings']['daily_target'] == 70
        assert response.get_json()['settings']['timezone'] == 'UTC'

    def test_invalid_value_is_a_400_and_nothing_is_written(self, call):
        cursor = FakeCursor()
        response, connection = call(
            'post', '/api/settings', cursor, json={'daily_target': 5000, 'timezone': 'UTC'}
        )
        assert response.status_code == 400
        body = response.get_json()
        assert body['success'] is False
        assert 'daily_target' in body['errors']
        assert not cursor.wrote_settings()
        assert connection.commits == 0

    def test_empty_or_non_json_body_is_a_400(self, call):
        response, _ = call('post', '/api/settings', FakeCursor(), json={})
        assert response.status_code == 400
        response, _ = call('post', '/api/settings', FakeCursor(), data='nope')
        assert response.status_code == 400

    def test_database_error_is_reported_and_returns_500(self, app_module, monkeypatch):
        reported = []
        monkeypatch.setattr(app_module, 'report_api_error', reported.append)

        def broken():
            raise RuntimeError('db down')
        monkeypatch.setattr(app_module, 'get_db_connection', broken)
        response = app_module.app.test_client().post('/api/settings', json={'daily_target': 5})
        assert response.status_code == 500
        assert len(reported) == 1

    def test_saving_clears_the_timezone_cache(self, app_module, call):
        app_module._tz_cache['tz'] = FIXED_AEST
        app_module._tz_cache['expires'] = 10 ** 12
        call('post', '/api/settings', FakeCursor(), json={'timezone': 'UTC'})
        assert app_module._tz_cache['tz'] is None


class TestReviewHistoryApi:
    @pytest.mark.parametrize('days', ['5', 'abc', '365', '0'])
    def test_only_7_30_or_90_days_are_allowed(self, call, days):
        response, _ = call('get', f'/api/review-history?days={days}', FakeCursor())
        assert response.status_code == 400

    def test_zero_fills_and_includes_the_target(self, app_module, call, monkeypatch):
        today = datetime.now(app_module.app_tz()).date()
        cursor = FakeCursor(
            settings={'daily_target': '40'},
            log_rows=[{'date': today, 'review_count': 25}],
        )
        response, _ = call('get', '/api/review-history?days=7', cursor)
        body = response.get_json()
        assert response.status_code == 200
        assert body['days'] == 7
        assert body['target'] == 40
        assert len(body['history']) == 7
        assert body['history'][-1] == {'date': today.strftime('%Y-%m-%d'), 'review_count': 25}
        assert all(d['review_count'] == 0 for d in body['history'][:-1])

    def test_defaults_to_30_days(self, call):
        response, _ = call('get', '/api/review-history', FakeCursor())
        assert len(response.get_json()['history']) == 30


class TestDebtAndDailyCountUseSettings:
    def test_debt_off_reports_zero(self, call):
        cursor = FakeCursor(settings={'debt_enabled': '0'}, earliest=date(2020, 1, 1))
        response, _ = call('get', '/api/debt', cursor)
        assert response.get_json() == {'success': True, 'total_debt': 0, 'breakdown': []}

    def test_debt_uses_the_saved_target(self, app_module, call):
        today = datetime.now(app_module.app_tz()).date()
        two_days_ago = today - timedelta(days=2)
        cursor = FakeCursor(
            settings={'daily_target': '25'}, earliest=two_days_ago,
            log_rows=[],
        )
        response, _ = call('get', '/api/debt', cursor)
        assert response.get_json()['total_debt'] == 50

    def test_debt_defaults_to_100_a_day(self, app_module, call):
        today = datetime.now(app_module.app_tz()).date()
        cursor = FakeCursor(earliest=today - timedelta(days=2), log_rows=[])
        response, _ = call('get', '/api/debt', cursor)
        assert response.get_json()['total_debt'] == 200

    def test_daily_count_returns_the_target(self, call):
        response, _ = call('get', '/api/daily-count', FakeCursor(settings={'daily_target': '75'}))
        body = response.get_json()
        assert body['target'] == 75
        assert body['count'] == 0


class QuizCursor(FakeCursor):
    """FakeCursor plus the two quiz-mode queries"""

    def execute(self, sql, params=None):
        flat = ' '.join(sql.split())
        if 'FROM words' in flat and 'review_count >= 1' in flat:
            self.statements.append((flat, params))
            self._result = [{'id': 1, 'word': 'brunt', 'translation': 'right',
                             'category': 'AI', 'review_count': 3}]
        elif flat.startswith('SELECT translation FROM words'):
            self.statements.append((flat, params))
            self._result = [{'translation': f'wrong{i}'} for i in range(params[-1])]
        else:
            super().execute(sql, params)


class TestQuizChoiceCount:
    @pytest.fixture(autouse=True)
    def wrong_options(self, app_module, monkeypatch):
        # These tests are about how many choices there are. What Gemini writes is
        # covered in test_word_types.py (and needs no Gemini here).
        monkeypatch.setattr(
            app_module,
            'generate_quiz_distractors',
            lambda word, wrong_count: [f'wrong{i}' for i in range(wrong_count)],
        )

    def test_default_is_four_choices(self, call):
        response, _ = call('get', '/api/quiz/next-word?mode=quiz', QuizCursor())
        options = response.get_json()['word']['options']
        assert len(options) == 4
        assert 'right' in options

    @pytest.mark.parametrize('count', [2, 3, 6])
    def test_saved_count_sets_the_number_of_choices(self, call, count):
        cursor = QuizCursor(settings={'quiz_choice_count': str(count)})
        response, _ = call('get', '/api/quiz/next-word?mode=quiz', cursor)
        options = response.get_json()['word']['options']
        assert len(options) == count
        assert 'right' in options


class TestQuizSessionSize:
    @pytest.mark.parametrize('bad', [-1, 201, 'x', 1.5])
    def test_out_of_range_is_rejected(self, bad):
        _, errors = validate_settings({'quiz_session_size': bad})
        assert 'quiz_session_size' in errors

    @pytest.mark.parametrize('good', [0, 1, 20, 200, '30'])
    def test_zero_means_no_limit_and_bounds_are_inclusive(self, good):
        clean, errors = validate_settings({'quiz_session_size': good})
        assert errors == {}
        assert clean['quiz_session_size'] == int(good)

    def test_default_is_no_limit(self):
        assert DEFAULT_SETTINGS['quiz_session_size'] == 0

    def test_saved_value_round_trips(self, call):
        cursor = FakeCursor()
        call('post', '/api/settings', cursor, json={'quiz_session_size': 25})
        response, _ = call('get', '/api/settings', cursor)
        assert response.get_json()['settings']['quiz_session_size'] == 25

    def test_quiz_script_stops_at_the_limit_and_reads_the_setting(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, 'static', 'js', 'quiz.js'), encoding='utf-8') as handle:
            source = handle.read()
        assert "fetch('/api/settings')" in source
        assert 'sessionLimit > 0 && sessionAnswered >= sessionLimit' in source
        assert 'let sessionLimit = 0' in source  # no limit unless the setting says so

    def test_quiz_page_has_the_session_complete_card(self, app_module):
        html = app_module.app.test_client().get('/quiz').data
        assert b'id="quizSessionDone"' in html
        assert b'id="newSessionBtn"' in html


class TestSettingsPageFollowsTheGuiTheme:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _read(self, *parts):
        with open(os.path.join(self.ROOT, *parts), encoding='utf-8') as handle:
            return handle.read()

    def test_page_has_the_theme_link_with_every_theme_version(self, app_module):
        import json
        import re
        html = app_module.app.test_client().get('/settings').data.decode('utf-8')
        assert 'id="themeStylesheet"' in html
        versions = json.loads(re.search(r"data-versions='([^']*)'", html).group(1))
        assert {'minimalist', 'cyberpunk', 'glassmorphism', 'duolingo'} <= set(versions)

    def test_theme_link_comes_after_the_base_stylesheet(self, app_module):
        html = app_module.app.test_client().get('/settings').data.decode('utf-8')
        assert html.index('css/style.css') < html.index('id="themeStylesheet"')

    def test_script_uses_the_vocab_pages_storage_key_and_file_names(self):
        source = self._read('static', 'js', 'settings.js')
        assert "'bkdict-gui-theme'" in source
        assert '/static/css/themes/theme-${themeName}.css' in source

    def test_script_only_builds_urls_for_themes_that_exist(self):
        source = self._read('static', 'js', 'settings.js')
        assert 'hasOwnProperty.call(versions, themeName)' in source

    def test_cyberpunk_theme_reaches_the_settings_page(self):
        css = self._read('static', 'css', 'themes', 'theme-cyberpunk.css')
        for fragment in ('body.settings-page {\n    --neon-cyan', 'body.settings-page .btn', 'body.settings-page .settings-card',
                         'body.settings-page .app-title', 'body.settings-page .range-btn.active'):
            assert fragment in css

    def test_settings_card_colours_come_from_theme_variables(self):
        css = self._read('static', 'css', 'style.css')
        block = css[css.index('.settings-page .settings-card {'):]
        block = block[:block.index('}')]
        assert 'var(--bg-card)' in block and 'var(--border-color)' in block


class TestFrontEndWiring:
    def test_app_js_no_longer_hardcodes_100_for_the_goal(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'static', 'js', 'app.js')
        with open(path, encoding='utf-8') as handle:
            source = handle.read()
        assert 'dailyProgress > 100' not in source
        assert 'dailyProgress >= 100' not in source
        assert 'AppState.dailyTarget' in source

    def test_settings_script_builds_the_chart_without_inner_html(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'static', 'js', 'settings.js')
        with open(path, encoding='utf-8') as handle:
            assert 'innerHTML' not in handle.read()


class TestVocabularyLinkReturnsToWord:
    """The Settings "← Vocabulary" link reopens the word you left, not Welcome."""

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _read(self, *parts):
        with open(os.path.join(self.ROOT, *parts), encoding='utf-8') as handle:
            return handle.read()

    def test_app_and_settings_share_the_same_storage_key(self):
        key = 'bkdict-last-word-id'
        assert key in self._read('static', 'js', 'app.js')
        assert key in self._read('static', 'js', 'settings.js')

    def test_word_is_remembered_when_displayed_and_forgotten_at_welcome(self):
        source = self._read('static', 'js', 'app.js')
        display = source[source.index('function displayWord('):]
        assert 'rememberLastWord(wordData.id)' in display[:400]
        # Both "no category / empty category" Welcome branches clear it
        assert source.count('forgetLastWord();') == 2

    def test_link_has_a_hook_and_falls_back_to_the_plain_page(self):
        html = self._read('templates', 'settings.html')
        assert 'id="vocabLink"' in html and 'href="/"' in html
        js = self._read('static', 'js', 'settings.js')
        assert "'/?word_id=' + lastWordId" in js
        assert r"/^\d+$/.test(" in js  # only a numeric id can reach the URL
