"""
Multiple-choice quiz options: Gemini writes the wrong ones.

The wrong options are other members of the right answer's group, in its format
and word type. The pure helpers live in utils/quiz_options.py and
utils/word_types.py; the Gemini call and the route in app.py are tested here
with fakes, so no database or Gemini is needed.
"""

import os

import pytest

from utils.quiz_options import build_options_prompt, parse_options_reply
from utils.word_types import parse_word_types

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


class TestGeminiOptionsReply:
    def test_prompt_names_the_word_the_answer_and_the_count(self):
        prompt = build_options_prompt("beautiful", "adj. 美丽的", 5)
        assert "beautiful" in prompt and "adj. 美丽的" in prompt
        assert "5 WRONG options" in prompt and "JSON array of 5" in prompt

    def test_prompt_forbids_a_prefix_when_the_answer_has_none(self):
        assert "do NOT write 'n.'" in build_options_prompt("authority", "威权政府", 3)
        assert "do NOT write" not in build_options_prompt("observant", "adj. 善于观察的", 3)

    def test_prompt_asks_for_members_of_the_same_group(self):
        prompt = build_options_prompt("blue", "adj. 蓝色的", 3)
        assert "SAME GROUP" in prompt and "natural set" in prompt
        assert "same topic or field" in prompt

    def test_prompt_takes_the_group_from_the_first_meaning(self):
        assert "FIRST meaning" in build_options_prompt("creamy", "adj. 奶油色的；乳脂状的", 3)

    def test_prompt_forbids_shades_and_near_synonyms(self):
        prompt = build_options_prompt("blue", "adj. 蓝色的", 3)
        assert "shade, sub-type or near-synonym" in prompt

    def test_prompt_passes_the_category_as_a_hint(self):
        assert "Topic hint" in build_options_prompt("blue", "adj. 蓝色的", 3, "颜色")
        assert "颜色" in build_options_prompt("blue", "adj. 蓝色的", 3, "颜色")

    def test_prompt_has_no_hint_without_a_category(self):
        assert "Topic hint" not in build_options_prompt("blue", "adj. 蓝色的", 3)
        assert "Topic hint" not in build_options_prompt("blue", "adj. 蓝色的", 3, None)

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

    def test_shades_of_the_right_answer_are_dropped(self):
        reply = '["adj. 浅蓝色的", "adj. 黄色的", "adj. 天蓝色的", "adj. 红色的"]'
        assert parse_options_reply(reply, "adj. 蓝色的", ("adj",), 3) == ["adj. 黄色的", "adj. 红色的"]

    def test_an_option_repeating_any_meaning_of_the_answer_is_dropped(self):
        reply = '["adj. 机警的；敏捷的", "adj. 严格的；苛刻的"]'
        assert parse_options_reply(reply, "adj. 善于观察的；机警的", ("adj",), 3) == ["adj. 严格的；苛刻的"]

    def test_a_shared_bracketed_tag_is_not_a_repeated_meaning(self):
        reply = '["n. [车辆] 刹车片"]'
        assert parse_options_reply(reply, "n. [车辆] 调光器；光暗掣", ("n",), 3) == ["n. [车辆] 刹车片"]

    def test_short_meanings_never_block_an_option(self):
        # 要求 is in the answer's meanings, but at two characters it is too
        # generic: rejecting on it left some words with no options at all
        reply = '["n.合并要求；调解", "n.租借要求；注册"]'
        assert parse_options_reply(reply, "n.征用；要求；引渡要求", ("n",), 3) == [
            "n.合并要求；调解",
            "n.租借要求；注册",
        ]

    def test_single_character_meanings_never_block_an_option(self):
        assert parse_options_reply('["vt.吃惊"]', "vt.吃", ("v",), 3) == ["vt.吃惊"]

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


GOOD_REPLY = '["adj. 丑的", "adj. 大的", "adj. 小的", "adj. 新的"]'


@pytest.fixture
def gemini(monkeypatch):
    """Fake Gemini for generate_quiz_distractors.

    `replies` are used in order, then `reply` for every later call; an
    Exception is raised instead of returned. `calls` records each request.
    """
    import app as module

    state = type("State", (), {
        "calls": [], "client_args": [], "efforts": [], "reported": [],
        "replies": [], "reply": GOOD_REPLY,
    })()

    def fake_openai(**kwargs):
        state.client_args.append(kwargs)
        return object()

    def fake_completion(client, model, prompt, trace_name, **kwargs):
        state.calls.append((model, prompt, trace_name))
        state.efforts.append(kwargs.get("effort", "configured"))
        reply = state.replies.pop(0) if state.replies else state.reply
        if isinstance(reply, Exception):
            raise reply
        return FakeGeminiReply(reply)

    monkeypatch.setitem(module.app.config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setitem(module.app.config, "GEMINI_QUIZ_MODEL", "small-fast-model")
    monkeypatch.setattr(module, "OpenAI", fake_openai)
    monkeypatch.setattr(module, "create_gemini_completion", fake_completion)
    monkeypatch.setattr(module, "report_api_error", state.reported.append)
    state.module = module
    return state


def word(translation="adj. 美丽的", text="beautiful"):
    return {"id": 7, "word": text, "translation": translation}


class TestGenerateQuizDistractors:
    def test_returns_the_wrong_options(self, gemini):
        assert gemini.module.generate_quiz_distractors(word(), 3) == ["adj. 丑的", "adj. 大的", "adj. 小的"]

    def test_uses_the_small_model_with_a_short_timeout_and_no_sdk_retries(self, gemini):
        gemini.module.generate_quiz_distractors(word(), 3)
        model, _, trace = gemini.calls[0]
        assert model == "small-fast-model" and trace == "generate-quiz-options"
        client_args = gemini.client_args[0]
        # Long enough for Gemini's slow answers (4-5 s), short enough to fail
        assert client_args["timeout"] == gemini.module.QUIZ_OPTIONS_TIMEOUT_SECONDS
        assert 5.0 < client_args["timeout"] <= 10.0
        # The retry is ours (one more try), so the SDK must not add its own
        assert client_args["max_retries"] == 0

    def test_asks_for_one_spare_option(self, gemini):
        gemini.module.generate_quiz_distractors(word(), 3)
        assert "JSON array of 4" in gemini.calls[0][1]

    def test_the_words_category_is_sent_as_a_topic_hint(self, gemini):
        gemini.module.generate_quiz_distractors({**word(), "category": "颜色"}, 3)
        assert "Topic hint" in gemini.calls[0][1] and "颜色" in gemini.calls[0][1]

    def test_a_word_without_a_category_sends_no_hint(self, gemini):
        gemini.module.generate_quiz_distractors(word(), 3)
        assert "Topic hint" not in gemini.calls[0][1]

    def test_uses_the_models_own_reasoning_effort(self, gemini):
        gemini.module.generate_quiz_distractors(word(), 3)
        assert gemini.efforts == [""]

    def test_shades_of_the_answer_in_the_reply_are_dropped(self, gemini):
        gemini.reply = '["adj. 浅美丽的", "adj. 丑的"]'
        assert gemini.module.generate_quiz_distractors(word(), 3) == ["adj. 丑的"]

    def test_fewer_options_than_asked_for_are_returned_not_an_error(self, gemini):
        gemini.reply = '["adj. 丑的"]'
        assert gemini.module.generate_quiz_distractors(word(), 3) == ["adj. 丑的"]
        assert len(gemini.calls) == 1

    def test_no_api_key_raises_without_calling_gemini(self, gemini, monkeypatch):
        monkeypatch.setitem(gemini.module.app.config, "GEMINI_API_KEY", None)
        with pytest.raises(gemini.module.QuizOptionsError, match="GOOGLE_API_KEY"):
            gemini.module.generate_quiz_distractors(word(), 3)
        assert gemini.calls == []

    def test_one_failure_is_retried_once(self, gemini):
        gemini.replies = [TimeoutError("slow")]
        assert gemini.module.generate_quiz_distractors(word(), 3) == ["adj. 丑的", "adj. 大的", "adj. 小的"]
        assert len(gemini.calls) == 2
        assert gemini.reported == []  # recovered, so nothing to report

    def test_an_unreadable_reply_is_retried_once(self, gemini):
        gemini.replies = ["Sorry, I cannot do that."]
        assert gemini.module.generate_quiz_distractors(word(), 3) == ["adj. 丑的", "adj. 大的", "adj. 小的"]
        assert len(gemini.calls) == 2

    def test_a_reply_where_every_option_is_rejected_is_retried_once(self, gemini):
        gemini.replies = ['["n. 例子"]']
        assert gemini.module.generate_quiz_distractors(word(), 3) == ["adj. 丑的", "adj. 大的", "adj. 小的"]
        assert len(gemini.calls) == 2

    def test_two_failures_raise_and_are_reported_once(self, gemini):
        gemini.reply = TimeoutError("slow")
        with pytest.raises(gemini.module.QuizOptionsError, match="try again"):
            gemini.module.generate_quiz_distractors(word(), 3)
        assert len(gemini.calls) == gemini.module.QUIZ_OPTIONS_ATTEMPTS == 2
        assert len(gemini.reported) == 1

    def test_two_unusable_replies_raise(self, gemini):
        gemini.reply = "not json"
        with pytest.raises(gemini.module.QuizOptionsError):
            gemini.module.generate_quiz_distractors(word(), 3)
        assert len(gemini.calls) == 2


class FakeCursor:
    """Hands back the quiz word and records every statement."""

    def __init__(self, row):
        self.row = row
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append(" ".join(sql.split()))

    def fetchone(self):
        return dict(self.row)


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, *args, **kwargs):
        return self._cursor

    def close(self):
        pass


class TestQuizRoute:
    ROW = {"id": 7, "word": "beautiful", "translation": "adj. 美丽的", "category": "Food"}

    def get(self, monkeypatch, generate, mode="quiz"):
        """Call /api/quiz/next-word with the database and Gemini stubbed out."""
        import app as module

        cursor = FakeCursor(self.ROW)
        monkeypatch.setattr(module, "get_db_connection", lambda: FakeConnection(cursor))
        monkeypatch.setattr(module, "load_settings", lambda c: {"quiz_choice_count": 4})
        monkeypatch.setattr(module, "generate_quiz_distractors", generate)
        monkeypatch.setitem(module.app.config, "TESTING", True)
        monkeypatch.setitem(module.app.config, "SITE_PASSWORD", None)
        response = module.app.test_client().get(f"/api/quiz/next-word?mode={mode}&category=All")
        return response, cursor

    def test_options_are_the_wrong_ones_plus_the_right_one(self, monkeypatch):
        response, cursor = self.get(monkeypatch, lambda w, n: ["adj. 丑的", "adj. 大的", "adj. 小的"])
        options = response.get_json()["word"]["options"]
        assert sorted(options) == ["adj. 丑的", "adj. 大的", "adj. 小的", "adj. 美丽的"]
        # No wrong option comes from the database any more
        assert not any(sql.startswith("SELECT translation") for sql in cursor.executed)

    def test_asks_for_one_wrong_option_fewer_than_the_choice_count(self, monkeypatch):
        asked = []

        def generate(w, n):
            asked.append(n)
            return ["adj. 丑的"] * n

        self.get(monkeypatch, generate)
        assert asked == [3]

    def test_fewer_options_when_some_were_rejected(self, monkeypatch):
        response, _ = self.get(monkeypatch, lambda w, n: ["adj. 丑的"])
        assert sorted(response.get_json()["word"]["options"]) == ["adj. 丑的", "adj. 美丽的"]

    def test_gemini_failure_is_a_503_with_a_message_and_no_options(self, monkeypatch):
        import app as module

        def generate(w, n):
            raise module.QuizOptionsError("Couldn't generate the answer options. Please try again.")

        response, _ = self.get(monkeypatch, generate)
        data = response.get_json()
        assert response.status_code == 503
        assert data["success"] is False and "try again" in data["error"]
        assert "word" not in data

    def test_flashcard_mode_never_calls_gemini(self, monkeypatch):
        def generate(w, n):
            raise AssertionError("flashcard mode must not ask Gemini for options")

        response, _ = self.get(monkeypatch, generate, mode="flashcard")
        assert response.get_json()["success"] is True
        assert "options" not in response.get_json()["word"]


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

    def test_a_failed_prefetch_is_never_shown_as_an_error(self, source):
        # A network failure, a 500 or a 503 from Gemini in the background request
        # must fall back to a fresh request when Next is clicked
        assert ".catch(() => null)" in source
        assert "result.status === 404 || result.data.success" in source
        assert "result = await fetchQuestion(url)" in source
