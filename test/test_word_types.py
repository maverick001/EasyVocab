"""
Quiz options are the same kind of word: all adjectives, all nouns ...

The pure helpers live in utils/word_types.py; the database-facing parts in
app.py are tested here with a fake cursor, so no database or Gemini is needed.
"""

import importlib.util
import os
import re

import pytest

from utils.quiz_options import build_options_prompt, parse_options_reply
from utils.word_types import (
    build_batch_prompt,
    build_type_prompt,
    effective_types,
    join_ai_pos,
    parse_batch_reply,
    parse_type_reply,
    parse_word_types,
    split_ai_pos,
    type_match_sql,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestParseWordTypes:
    def test_single_prefix(self):
        assert parse_word_types("n. 例子；示例") == ("n",)
        assert parse_word_types("adj. 美丽的") == ("adj",)

    def test_several_prefixes_are_sorted(self):
        assert parse_word_types("vt. 举例 n. 例子") == ("n", "v")

    def test_transitive_and_intransitive_verbs_are_one_type(self):
        assert parse_word_types("vt. 吃 vi. 进食") == ("v",)

    def test_no_prefix(self):
        assert parse_word_types("例子") == ()
        assert parse_word_types("") == ()
        assert parse_word_types(None) == ()

    def test_n_inside_another_abbreviation_is_not_a_noun(self):
        assert parse_word_types("pron. 他") == ("pron",)
        assert parse_word_types("conj. 和") == ("conj",)

    def test_notes_like_eg_do_not_count(self):
        assert parse_word_types("苹果 e.g. 红色的 sth. 东西") == ()

    def test_abbreviation_entries_are_their_own_type(self):
        assert parse_word_types("abbr. 美国国家航空航天局") == ("abbr",)

    def test_interjection_spellings(self):
        assert parse_word_types("int. 哎呀") == ("int",)
        assert parse_word_types("interj. 哎呀") == ("int",)

    def test_prefix_in_the_middle_of_text(self):
        assert parse_word_types("美丽的 adj.") == ("adj",)


class TestAiPosCache:
    def test_round_trip(self):
        assert split_ai_pos(join_ai_pos(("n", "adj"))) == ("adj", "n")

    def test_empty_means_no_type(self):
        assert split_ai_pos("") == ()
        assert split_ai_pos(None) == ()
        assert join_ai_pos(()) == ""

    def test_unknown_entries_are_dropped(self):
        assert split_ai_pos("n,banana") == ("n",)

    def test_prefix_wins_over_cached_answer(self):
        assert effective_types("n. 例子", "adj") == ("n",)

    def test_cached_answer_used_when_no_prefix(self):
        assert effective_types("例子", "n,v") == ("n", "v")


class TestTypeMatchSql:
    def test_matches_prefix_and_cached_answer(self):
        sql, params = type_match_sql(("adj",))
        assert "REGEXP_LIKE(translation, %s, 'c')" in sql
        assert "FIND_IN_SET(%s, ai_pos)" in sql
        assert params[1:] == ["adj"]

    def test_without_cache_only_the_prefix_is_checked(self):
        sql, params = type_match_sql(("adj",), use_ai_cache=False)
        assert "ai_pos" not in sql
        assert len(params) == 1

    def test_placeholders_match_params(self):
        sql, params = type_match_sql(("n", "v"))
        assert sql.count("%s") == len(params)

    def test_verb_pattern_covers_vt_and_vi(self):
        _, params = type_match_sql(("v",))
        for text in ("v. 跑", "vt. 吃", "vi. 睡", "n. 例子 vt. 吃"):
            assert re.search(params[0], text)
        assert not re.search(params[0], "n. 例子")

    def test_pattern_agrees_with_the_parser(self):
        # The SQL regex and the Python parser must pick the same words
        samples = ["n. 例子", "pron. 他", "adj. 好的", "e.g. 红", "苹果", "vt. 吃 n. 食物", "abbr. 缩写"]
        for kind in ("n", "v", "adj", "pron", "abbr"):
            _, params = type_match_sql((kind,), use_ai_cache=False)
            for text in samples:
                assert bool(re.search(params[0], text)) == (kind in parse_word_types(text)), (kind, text)

    def test_empty_types_are_refused(self):
        with pytest.raises(ValueError):
            type_match_sql(())


class TestGeminiReplies:
    def test_abbreviations(self):
        assert parse_type_reply("n, v") == ("n", "v")
        assert parse_type_reply("adj.") == ("adj",)

    def test_full_names(self):
        assert parse_type_reply("noun") == ("n",)
        assert parse_type_reply("Noun, Verb") == ("n", "v")

    def test_none_is_an_answer(self):
        assert parse_type_reply("none") == ()
        assert parse_type_reply("None.") == ()

    def test_unusable_replies_are_not_answers(self):
        assert parse_type_reply("") is None
        assert parse_type_reply(None) is None
        assert parse_type_reply("I am not sure what you mean by that word") is None
        assert parse_type_reply("banana") is None

    def test_a_sentence_is_not_mistaken_for_types(self):
        long_reply = "The word is used as a noun in most dictionaries and as a verb sometimes"
        assert parse_type_reply(long_reply) is None

    def test_prompts_name_the_word_and_the_allowed_types(self):
        prompt = build_type_prompt("beautiful", "美丽的")
        assert "beautiful" in prompt and "美丽的" in prompt and "adj" in prompt

    def test_batch_prompt_lists_every_word(self):
        prompt = build_batch_prompt([(1, "cat", "猫"), (2, "run", "跑")])
        assert "1|cat|猫" in prompt and "2|run|跑" in prompt

    def test_batch_reply_maps_ids_to_types(self):
        reply = "1|n\n2|v, n\n3|none\nnot a line\n4|???\nx|n"
        assert parse_batch_reply(reply) == {1: ("n",), 2: ("n", "v"), 3: ()}

    def test_batch_reply_tolerates_code_fences(self):
        assert parse_batch_reply("```\n1|adj\n```") == {1: ("adj",)}


class FakeCursor:
    """Hands back canned rows and records every statement."""

    def __init__(self, rows_per_query=(), ai_pos=None):
        self.rows_per_query = list(rows_per_query)
        self.ai_pos = ai_pos
        self.executed = []
        self._rows = []

    def execute(self, sql, params=None):
        flat = " ".join(sql.split())
        self.executed.append((flat, list(params or [])))
        if flat.startswith("SELECT ai_pos FROM words WHERE id"):
            self._rows = [{"ai_pos": self.ai_pos}]
        elif flat.startswith("SELECT translation"):
            self._rows = self.rows_per_query.pop(0) if self.rows_per_query else []

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


def rows(*translations):
    return [{"translation": t, "ai_pos": None} for t in translations]


@pytest.fixture
def app_module(monkeypatch):
    import app as module

    monkeypatch.setitem(module.app.config, "TESTING", True)
    # The Gemini model is never reached unless a test installs a fake
    monkeypatch.setattr(module, "classify_word_types", lambda word, translation: None)
    monkeypatch.setattr(module, "ensure_ai_pos_column", lambda: True)
    return module


def word(translation="adj. 美丽的", text="beautiful"):
    return {"id": 7, "word": text, "translation": translation}


class TestFindSameTypeDistractors:
    def test_wrong_options_are_the_same_type(self, app_module):
        cursor = FakeCursor([rows("adj. 丑的", "adj. 大的", "adj. 小的")])
        result = app_module.find_same_type_distractors(FakeConnection(), cursor, word(), "All", 3)
        assert result == ["adj. 丑的", "adj. 大的", "adj. 小的"]
        sql, params = cursor.executed[0]
        assert "REGEXP_LIKE(translation, %s, 'c')" in sql
        assert any("adj" in str(p) for p in params)

    def test_stays_in_the_category_first_then_widens(self, app_module):
        cursor = FakeCursor([rows("adj. 丑的"), rows("adj. 大的", "adj. 小的")])
        result = app_module.find_same_type_distractors(FakeConnection(), cursor, word(), "Food", 3)
        assert result == ["adj. 丑的", "adj. 大的", "adj. 小的"]
        first_sql, first_params = cursor.executed[0]
        second_sql, second_params = cursor.executed[1]
        assert "AND category = %s" in first_sql and "Food" in first_params
        assert "category" not in second_sql
        assert "adj. 丑的" in second_params  # already chosen, not picked twice

    def test_all_categories_means_one_query(self, app_module):
        cursor = FakeCursor([rows("adj. 丑的", "adj. 大的", "adj. 小的")])
        app_module.find_same_type_distractors(FakeConnection(), cursor, word(), "All", 3)
        assert len(cursor.executed) == 1

    def test_returns_fewer_rather_than_mixing_types(self, app_module):
        cursor = FakeCursor([rows("adj. 丑的"), rows()])
        result = app_module.find_same_type_distractors(FakeConnection(), cursor, word(), "Food", 3)
        assert result == ["adj. 丑的"]

    def test_a_wrong_type_from_the_database_is_rejected(self, app_module):
        # If MySQL's regex ever disagreed with the parser, Python still filters
        cursor = FakeCursor([rows("n. 例子", "adj. 丑的")])
        result = app_module.find_same_type_distractors(FakeConnection(), cursor, word(), "All", 3)
        assert result == ["adj. 丑的"]

    def test_duplicate_translations_are_used_once(self, app_module):
        cursor = FakeCursor([rows("adj. 丑的", "adj. 丑的", "adj. 大的")])
        result = app_module.find_same_type_distractors(FakeConnection(), cursor, word(), "All", 3)
        assert result == ["adj. 丑的", "adj. 大的"]

    def test_a_word_with_two_types_accepts_either(self, app_module):
        cursor = FakeCursor([rows("n. 例子", "vt. 举例", "adj. 丑的")])
        result = app_module.find_same_type_distractors(
            FakeConnection(), cursor, word("n. 工作 vt. 做"), "All", 3
        )
        assert result == ["n. 例子", "vt. 举例"]

    def test_none_when_nothing_of_that_type_exists(self, app_module):
        cursor = FakeCursor([rows(), rows()])
        assert app_module.find_same_type_distractors(FakeConnection(), cursor, word(), "Food", 3) is None

    def test_untyped_word_without_an_answer_falls_back(self, app_module):
        cursor = FakeCursor()
        assert app_module.find_same_type_distractors(FakeConnection(), cursor, word("美丽的"), "All", 3) is None

    def test_works_without_the_ai_column(self, app_module, monkeypatch):
        monkeypatch.setattr(app_module, "ensure_ai_pos_column", lambda: False)
        cursor = FakeCursor([[{"translation": "adj. 丑的"}]])
        result = app_module.find_same_type_distractors(FakeConnection(), cursor, word(), "All", 3)
        assert result == ["adj. 丑的"]
        assert "ai_pos" not in cursor.executed[0][0]


class TestQuizWordTypes:
    def test_prefix_needs_no_database_or_gemini(self, app_module):
        cursor = FakeCursor()
        assert app_module.quiz_word_types(FakeConnection(), cursor, word(), True) == ("adj",)
        assert cursor.executed == []

    def test_cached_answer_is_used(self, app_module):
        cursor = FakeCursor(ai_pos="n,v")
        result = app_module.quiz_word_types(FakeConnection(), cursor, word("工作"), True)
        assert result == ("n", "v")

    def test_new_answer_is_asked_once_and_cached(self, app_module, monkeypatch):
        asked = []

        def fake_classify(text, translation):
            asked.append((text, translation))
            return ("adj",)

        monkeypatch.setattr(app_module, "classify_word_types", fake_classify)
        cursor, conn = FakeCursor(ai_pos=None), FakeConnection()
        result = app_module.quiz_word_types(conn, cursor, word("美丽的"), True)
        assert result == ("adj",)
        assert asked == [("beautiful", "美丽的")]
        update_sql, update_params = cursor.executed[-1]
        assert update_sql.startswith("UPDATE words SET ai_pos")
        assert update_params == ["adj", "beautiful", "美丽的"]
        assert conn.commits == 1

    def test_none_answer_is_cached_as_empty(self, app_module, monkeypatch):
        monkeypatch.setattr(app_module, "classify_word_types", lambda text, translation: ())
        cursor, conn = FakeCursor(ai_pos=None), FakeConnection()
        assert app_module.quiz_word_types(conn, cursor, word("美丽的"), True) == ()
        assert cursor.executed[-1][1][0] == ""

    def test_failed_answer_is_not_cached(self, app_module):
        cursor, conn = FakeCursor(ai_pos=None), FakeConnection()
        assert app_module.quiz_word_types(conn, cursor, word("美丽的"), True) == ()
        assert conn.commits == 0
        assert not any(sql.startswith("UPDATE") for sql, _ in cursor.executed)

    def test_without_the_ai_column_there_is_no_lookup(self, app_module):
        cursor = FakeCursor()
        assert app_module.quiz_word_types(FakeConnection(), cursor, word("美丽的"), False) == ()
        assert cursor.executed == []


class TestClassifyWordTypes:
    def test_no_api_key_means_no_answer(self, monkeypatch):
        import app as module

        monkeypatch.setitem(module.app.config, "GEMINI_API_KEY", None)
        assert module.classify_word_types("beautiful", "美丽的") is None

    def test_reads_the_model_reply(self, monkeypatch):
        import app as module

        class Message:
            content = "adj, adv"

        class Choice:
            message = Message()

        class Response:
            choices = [Choice()]

        used = []

        def fake_completion(client, model, prompt, trace_name, **kwargs):
            used.append(model)
            assert kwargs == {"effort": ""}  # the model's own default effort
            return Response()

        monkeypatch.setitem(module.app.config, "GEMINI_API_KEY", "test-key")
        monkeypatch.setitem(module.app.config, "GEMINI_QUIZ_MODEL", "small-fast-model")
        monkeypatch.setattr(module, "OpenAI", lambda **kw: object())
        monkeypatch.setattr(module, "create_gemini_completion", fake_completion)
        assert module.classify_word_types("fast", "快的") == ("adj", "adv")
        # The type lookup has its own small model, not the translation model
        assert used == ["small-fast-model"]

    def test_default_type_model_is_the_fast_one(self):
        from config import Config

        assert Config.GEMINI_QUIZ_MODEL == "gemini-3.5-flash-lite"

    def test_an_api_error_means_no_answer(self, monkeypatch):
        import app as module

        def boom(*args, **kwargs):
            raise RuntimeError("quota")

        monkeypatch.setitem(module.app.config, "GEMINI_API_KEY", "test-key")
        monkeypatch.setattr(module, "OpenAI", lambda **kw: object())
        monkeypatch.setattr(module, "create_gemini_completion", boom)
        monkeypatch.setattr(module, "report_api_error", lambda e: None)
        assert module.classify_word_types("fast", "快的") is None


class TestQuizRoute:
    def run_route(self, app_module, monkeypatch, distractors, word_row=None, ai=None):
        """Call /api/quiz/next-word with the database stubbed out.

        `ai` is what Gemini's wrong options come back as (None = unavailable).
        """
        monkeypatch.setattr(app_module, "generate_ai_distractors", lambda word, count: ai)
        word_row = word_row or {
            "id": 7, "word": "beautiful", "translation": "adj. 美丽的", "category": "Food",
        }

        class RouteCursor(FakeCursor):
            def execute(self, sql, params=None):
                flat = " ".join(sql.split())
                if flat.startswith("SELECT id, word, translation, example_sentence"):
                    self.executed.append((flat, list(params or [])))
                    self._rows = [dict(word_row)]
                else:
                    super().execute(sql, params)

        cursor = RouteCursor([rows(*distractors)])
        conn = FakeConnection()
        conn.cursor = lambda *a, **kw: cursor
        conn.close = lambda: None
        monkeypatch.setattr(app_module, "get_db_connection", lambda: conn)
        monkeypatch.setattr(app_module, "load_settings", lambda c: {"quiz_choice_count": 4})
        monkeypatch.setitem(app_module.app.config, "SITE_PASSWORD", None)
        client = app_module.app.test_client()
        response = client.get("/api/quiz/next-word?mode=quiz&category=All")
        return response.get_json(), cursor

    def test_all_options_are_the_same_type(self, app_module, monkeypatch):
        data, _ = self.run_route(app_module, monkeypatch, ["adj. 丑的", "adj. 大的", "adj. 小的"])
        options = data["word"]["options"]
        assert len(options) == 4
        assert all("adj." in option for option in options)
        assert "adj. 美丽的" in options

    def test_fewer_options_when_too_few_of_that_type(self, app_module, monkeypatch):
        data, _ = self.run_route(app_module, monkeypatch, ["adj. 丑的"])
        assert sorted(data["word"]["options"]) == ["adj. 丑的", "adj. 美丽的"]

    def test_database_error_falls_back_to_random_options(self, app_module, monkeypatch):
        import mysql.connector

        def broken(*args, **kwargs):
            raise mysql.connector.Error("boom")

        monkeypatch.setattr(app_module, "find_same_type_distractors", broken)
        monkeypatch.setattr(app_module, "report_api_error", lambda e: None)
        monkeypatch.setattr(app_module, "random_distractors", lambda *a: ["x", "y", "z"])
        data, _ = self.run_route(app_module, monkeypatch, [])
        assert sorted(data["word"]["options"]) == ["adj. 美丽的", "x", "y", "z"]

    def test_gemini_options_replace_the_database_lookup(self, app_module, monkeypatch):
        data, cursor = self.run_route(
            app_module, monkeypatch, [], ai=["adj. 丑的", "adj. 大的", "adj. 小的"]
        )
        assert sorted(data["word"]["options"]) == ["adj. 丑的", "adj. 大的", "adj. 小的", "adj. 美丽的"]
        assert not any(sql.startswith("SELECT translation") for sql, _ in cursor.executed)

    def test_missing_options_come_from_the_database(self, app_module, monkeypatch):
        data, _ = self.run_route(
            app_module, monkeypatch, ["adj. 大的", "adj. 小的"], ai=["adj. 丑的"]
        )
        assert sorted(data["word"]["options"]) == ["adj. 丑的", "adj. 大的", "adj. 小的", "adj. 美丽的"]

    def test_an_option_is_never_shown_twice(self, app_module, monkeypatch):
        data, _ = self.run_route(
            app_module, monkeypatch, ["adj. 丑的", "adj. 大的", "adj. 小的"], ai=["adj. 丑的"]
        )
        options = data["word"]["options"]
        assert len(options) == len(set(options))

    def test_gemini_failure_does_not_also_wait_on_gemini_for_the_type(self, app_module, monkeypatch):
        def must_not_run(text, translation):
            raise AssertionError("Gemini was asked for the type after it had just failed")

        monkeypatch.setattr(app_module, "classify_word_types", must_not_run)
        untyped = {"id": 7, "word": "beautiful", "translation": "美丽的", "category": "Food"}
        data, _ = self.run_route(app_module, monkeypatch, ["x", "y", "z"], word_row=untyped, ai=None)
        assert sorted(data["word"]["options"]) == sorted(["美丽的", "x", "y", "z"])


class TestGeminiOptionsReply:
    def test_prompt_names_the_word_the_answer_and_the_count(self):
        prompt = build_options_prompt("beautiful", "adj. 美丽的", 5)
        assert "beautiful" in prompt and "adj. 美丽的" in prompt
        assert "5 WRONG options" in prompt and "JSON array of 5" in prompt

    def test_reads_a_json_array(self):
        reply = '["adj. 丑的", "adj. 大的", "adj. 小的"]'
        assert parse_options_reply(reply, "adj. 美丽的", ("adj",), 3) == ["adj. 丑的", "adj. 大的", "adj. 小的"]

    def test_tolerates_code_fences_and_chatter(self):
        reply = 'Here you go:\n```json\n["adj. 丑的", "adj. 大的"]\n```'
        assert parse_options_reply(reply, "adj. 美丽的", ("adj",), 3) == ["adj. 丑的", "adj. 大的"]

    def test_keeps_multi_line_options(self):
        reply = '["n. 猫\\nvt. 抓", "n. 狗"]'
        assert parse_options_reply(reply, "n. 鸟", ("n",), 2) == ["n. 猫\nvt. 抓", "n. 狗"]

    def test_drops_the_right_answer_repeats_blanks_and_non_text(self):
        reply = '["adj. 美丽的", "adj. 丑的", "adj. 丑的", "  ", 7, null, "adj. 大的"]'
        assert parse_options_reply(reply, "adj. 美丽的", ("adj",), 3) == ["adj. 丑的", "adj. 大的"]

    def test_drops_options_of_another_word_type(self):
        reply = '["n. 例子", "adj. 丑的", "丑的", "vt. 吃"]'
        assert parse_options_reply(reply, "adj. 美丽的", ("adj",), 3) == ["adj. 丑的"]

    def test_a_shared_type_is_enough_for_a_multi_type_answer(self):
        reply = '["vt. 吃", "adj. 丑的", "n. 例子"]'
        assert parse_options_reply(reply, "n. 工作 vt. 做", ("n", "v"), 3) == ["vt. 吃", "n. 例子"]

    def test_options_with_a_prefix_are_dropped_when_the_answer_has_none(self):
        # A prefix on every wrong option would show which one is right
        reply = '["威权的", "n. 例子", "adj. 大的", "军事政府"]'
        assert parse_options_reply(reply, "威权政府", (), 3) == ["威权的", "军事政府"]

    def test_prompt_forbids_a_prefix_when_the_answer_has_none(self):
        assert "do NOT write 'n.'" in build_options_prompt("authority", "威权政府", 3)
        assert "do NOT write" not in build_options_prompt("observant", "adj. 善于观察的", 3)

    def test_stops_at_the_count(self):
        reply = '["adj. a", "adj. b", "adj. c", "adj. d"]'
        assert parse_options_reply(reply, "adj. x", ("adj",), 2) == ["adj. a", "adj. b"]

    @pytest.mark.parametrize("reply", ["", None, "no list here", "[unclosed", '{"a": 1}', "[1, 2"])
    def test_unreadable_replies_are_none(self, reply):
        assert parse_options_reply(reply, "adj. 美丽的", ("adj",), 3) is None

    def test_a_valid_list_with_nothing_usable_is_empty_not_none(self):
        assert parse_options_reply('["n. 例子"]', "adj. 美丽的", ("adj",), 3) == []


class FakeGeminiReply:
    def __init__(self, content):
        message = type("Message", (), {"content": content})
        self.choices = [type("Choice", (), {"message": message})]


@pytest.fixture
def gemini(monkeypatch):
    """Fake Gemini for generate_ai_distractors; `calls` records each request."""
    import app as module

    state = type("State", (), {
        "calls": [], "client_args": [], "efforts": [],
        "reply": '["adj. 丑的", "adj. 大的", "adj. 小的", "adj. 新的"]',
    })()

    def fake_openai(**kwargs):
        state.client_args.append(kwargs)
        return object()

    def fake_completion(client, model, prompt, trace_name, **kwargs):
        state.calls.append((model, prompt, trace_name))
        state.efforts.append(kwargs.get("effort", "configured"))
        if isinstance(state.reply, Exception):
            raise state.reply
        return FakeGeminiReply(state.reply)

    monkeypatch.setitem(module.app.config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setitem(module.app.config, "GEMINI_QUIZ_MODEL", "small-fast-model")
    monkeypatch.setattr(module, "OpenAI", fake_openai)
    monkeypatch.setattr(module, "create_gemini_completion", fake_completion)
    monkeypatch.setattr(module, "report_api_error", lambda e: None)
    monkeypatch.setattr(module, "_quiz_options_paused_until", 0.0)
    state.module = module
    return state


class TestGenerateAiDistractors:
    def test_returns_the_wrong_options(self, gemini):
        assert gemini.module.generate_ai_distractors(word(), 3) == ["adj. 丑的", "adj. 大的", "adj. 小的"]

    def test_uses_the_small_model_with_a_short_timeout_and_no_retries(self, gemini):
        gemini.module.generate_ai_distractors(word(), 3)
        model, _, trace = gemini.calls[0]
        assert model == "small-fast-model" and trace == "generate-quiz-options"
        client_args = gemini.client_args[0]
        assert client_args["timeout"] == gemini.module.QUIZ_OPTIONS_TIMEOUT_SECONDS <= 3.0
        assert client_args["max_retries"] == 0

    def test_asks_for_one_spare_option(self, gemini):
        gemini.module.generate_ai_distractors(word(), 3)
        assert "JSON array of 4" in gemini.calls[0][1]

    def test_uses_the_models_own_reasoning_effort(self, gemini):
        gemini.module.generate_ai_distractors(word(), 3)
        assert gemini.efforts == [""]

    def test_options_of_the_wrong_type_are_dropped(self, gemini):
        gemini.reply = '["n. 例子", "adj. 丑的", "丑的"]'
        assert gemini.module.generate_ai_distractors(word(), 3) == ["adj. 丑的"]

    def test_no_api_key_means_no_call(self, gemini, monkeypatch):
        monkeypatch.setitem(gemini.module.app.config, "GEMINI_API_KEY", None)
        assert gemini.module.generate_ai_distractors(word(), 3) is None
        assert gemini.calls == []

    def test_a_failure_gives_none_and_pauses_gemini(self, gemini):
        gemini.reply = TimeoutError("slow")
        assert gemini.module.generate_ai_distractors(word(), 3) is None
        assert len(gemini.calls) == 1
        # Within the pause Gemini is not called again, so no question waits on it
        gemini.reply = '["adj. 丑的"]'
        assert gemini.module.generate_ai_distractors(word(), 3) is None
        assert len(gemini.calls) == 1

    def test_gemini_is_used_again_after_the_pause(self, gemini):
        gemini.reply = TimeoutError("slow")
        gemini.module.generate_ai_distractors(word(), 3)
        gemini.module._quiz_options_paused_until = 0.0
        gemini.reply = '["adj. 丑的"]'
        assert gemini.module.generate_ai_distractors(word(), 3) == ["adj. 丑的"]

    def test_an_unreadable_reply_gives_none_and_pauses(self, gemini):
        gemini.reply = "Sorry, I cannot do that."
        assert gemini.module.generate_ai_distractors(word(), 3) is None
        assert gemini.module._quiz_options_paused_until > 0

    def test_nothing_usable_is_an_empty_list_without_a_pause(self, gemini):
        gemini.reply = '["n. 例子"]'
        assert gemini.module.generate_ai_distractors(word(), 3) == []
        assert gemini.module._quiz_options_paused_until == 0.0


class TestQuizScriptPrefetch:
    @pytest.fixture
    def source(self):
        with open(os.path.join(ROOT, "static", "js", "quiz.js"), encoding="utf-8") as handle:
            return handle.read()

    def test_next_question_is_fetched_while_the_current_one_is_answered(self, source):
        assert "prefetchNextQuestion(url)" in source
        assert "prefetchedQuestion.url === url" in source

    def test_flashcard_mode_and_the_last_question_do_not_prefetch(self, source):
        body = source.split("function prefetchNextQuestion")[1].split("\n}\n")[0]
        assert "currentMode !== 'quiz'" in body
        assert "sessionAnswered + 1 >= sessionLimit" in body

    def test_a_failed_prefetch_falls_back_to_a_normal_request(self, source):
        assert ".catch(() => null)" in source
        assert "|| await fetchQuestion(url)" in source


def load_script():
    path = os.path.join(ROOT, "scripts", "tag_word_types.py")
    spec = importlib.util.spec_from_file_location("tag_word_types", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestTagScript:
    def test_dry_run_default_never_writes(self):
        source = open(os.path.join(ROOT, "scripts", "tag_word_types.py"), encoding="utf-8").read()
        # Everything that writes sits after the --apply early return
        before_apply = source.split("def main")[1].split("if not args.apply:")[0]
        for statement in ("UPDATE ", "ALTER ", ".commit("):
            assert statement not in before_apply
        assert "UPDATE " not in source.split("def pending_words")[1].split("def ask_gemini")[0]

    def test_pending_skips_prefixed_words_and_duplicates(self):
        script = load_script()

        class Cursor:
            def execute(self, sql, params=None):
                self.sql = sql

            def fetchall(self):
                return [
                    (1, "cat", "n. 猫"),
                    (2, "run", "跑"),
                    (3, "run", "跑"),  # same word in another category
                    (4, "fast", "快的"),
                ]

        pending, total, with_prefix = script.pending_words(Cursor(), True)
        assert pending == [(2, "run", "跑"), (4, "fast", "快的")]
        assert (total, with_prefix) == (4, 1)
