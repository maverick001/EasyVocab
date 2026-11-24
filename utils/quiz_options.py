"""
Wrong answers for the multiple-choice quiz, written by Gemini.

A random word from the list makes an easy wrong answer: it rarely looks like
the right one. Gemini is asked for plausible wrong meanings in the same format
as the right one ("adj. 美丽的" -> "adj. 丑陋的"). The reply is checked here;
anything unusable sends the caller back to wrong answers from the database.

Nothing here touches the database or the network.
"""

import json
import re

from utils.word_types import parse_word_types, strip_type_prefixes

# Ask for a spare option in case one is dropped as a repeat or the wrong type.
# More spares cost time (3 -> 5 options took 0.7 s -> 1.0 s); anything still
# missing is topped up from the database.
EXTRA_OPTIONS = 1


def build_options_prompt(word, translation, count, category=None):
    """Prompt asking Gemini for `count` wrong options as a JSON array.

    category is the word's category in the user's list, sent only as a hint
    about its topic.
    """
    if parse_word_types(translation):
        prefix_rule = "the same word-type prefix (such as 'adj.' or 'n.' or 'vt.')"
    else:
        # Without this Gemini adds "n." to every wrong option, which would make
        # the right answer the only one without a prefix
        prefix_rule = "no word-type prefix (the correct meaning has none, so do NOT write 'n.', 'adj.' or similar)"
    topic = f"Topic hint (the word's category in the user's list; it may be general): {category}\n" if category else ""
    return (
        "You write wrong answers for a vocabulary quiz.\n"
        f"English word: {word}\n"
        f"Correct Chinese meaning: {translation}\n"
        f"{topic}\n"
        f"Write {count} WRONG options for the question \"What does '{word}' mean?\".\n"
        "Rules:\n"
        f"- Write each option in exactly the same format as the correct meaning: {prefix_rule}, "
        "the same style of punctuation, and a similar length and number of senses.\n"
        "- Take the options from the SAME GROUP as the correct meaning. If it belongs to a "
        "natural set (colors, animals, body parts, countries, tools, emotions, ...), give other "
        "members of that set: for 蓝色的 give 黄色的, 红色的, 绿色的. If it has no natural set, "
        "give meanings from the same topic or field. Decide the group from the FIRST meaning "
        "listed (the main one), and make the first meaning of each option a member of that "
        "group: for 奶油色的；乳脂状的 the group is colors, so use options like 米色的；象牙色的.\n"
        "- Each option must be the same part of speech as the correct meaning, but it must NOT "
        f"be a correct meaning of '{word}'. Never use a shade, sub-type or near-synonym of the "
        "correct meaning (for 蓝色的 not 浅蓝的 or 天蓝色的), and do not repeat any part of it.\n"
        "- The options must differ from each other.\n"
        f"Reply with only a JSON array of {count} strings, nothing else."
    )


_SENSE_SEPARATORS = re.compile(r"[；;，,、。\n]")
_BRACKETED = re.compile(r"\[[^\]]*\]|\([^)]*\)|（[^）]*）")


# Meanings shorter than this are too generic to count as "repeated": rejecting
# every option that contains 要求 or 红色 emptied the list for some words.
MIN_SENSE_CHARS = 3


def _senses(text):
    """The separate meanings in a translation, at least MIN_SENSE_CHARS each.

    "adj. 善于观察的；机警的" -> ["善于观察的", "机警的"]. Prefixes and bracketed
    tags such as "[车辆]" are not meanings.
    """
    text = _BRACKETED.sub(" ", strip_type_prefixes(text))
    return [s for s in (p.strip() for p in _SENSE_SEPARATORS.split(text)) if len(s) >= MIN_SENSE_CHARS]


def _json_array(text):
    """The first JSON array in a reply, tolerating ``` fences; None if there is none."""
    if not text:
        return None
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except ValueError:
        return None
    return value if isinstance(value, list) else None


def parse_options_reply(text, correct, types, count):
    """Usable wrong options from a Gemini reply, at most `count`.

    Returns None when the reply is not a JSON array, and a list (possibly empty)
    when it is. Dropped: empty or non-text entries, the right answer, repeats,
    and options whose prefix does not fit: when the right answer has a word type
    an option must share one, and when it has none an option must have none
    (otherwise the prefix alone would show which one is right). An option that
    contains one of the right answer's meanings is dropped too: "浅蓝色的" next
    to "蓝色的" is a shade of it, and would be right as well.
    """
    items = _json_array(text)
    if items is None:
        return None
    wanted = set(types)
    right_senses = _senses(correct)
    kept = []
    for item in items:
        if not isinstance(item, str):
            continue
        option = item.strip()
        if not option or option == correct.strip() or option in kept:
            continue
        option_types = set(parse_word_types(option))
        if (wanted and not wanted & option_types) or (not wanted and option_types):
            continue
        body = _BRACKETED.sub(" ", strip_type_prefixes(option))
        if any(sense in body for sense in right_senses):
            continue
        kept.append(option)
        if len(kept) == count:
            break
    return kept
