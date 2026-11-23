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

from utils.word_types import parse_word_types

# Ask for a spare option in case one is dropped as a repeat or the wrong type.
# More spares cost time (3 -> 5 options took 0.7 s -> 1.0 s); anything still
# missing is topped up from the database.
EXTRA_OPTIONS = 1


def build_options_prompt(word, translation, count):
    """Prompt asking Gemini for `count` wrong options as a JSON array."""
    if parse_word_types(translation):
        prefix_rule = "the same word-type prefix (such as 'adj.' or 'n.' or 'vt.')"
    else:
        # Without this Gemini adds "n." to every wrong option, which would make
        # the right answer the only one without a prefix
        prefix_rule = "no word-type prefix (the correct meaning has none, so do NOT write 'n.', 'adj.' or similar)"
    return (
        "You write wrong answers for a vocabulary quiz.\n"
        f"English word: {word}\n"
        f"Correct Chinese meaning: {translation}\n\n"
        f"Write {count} WRONG options for the question \"What does '{word}' mean?\".\n"
        "Rules:\n"
        f"- Write each option in exactly the same format as the correct meaning: {prefix_rule}, "
        "the same style of punctuation, and a similar length and number of senses.\n"
        "- Each option must be the same part of speech as the correct meaning and sound "
        "plausible (a related word or a look-alike), but it must NOT be a correct meaning "
        f"of '{word}' and not a synonym of the correct meaning.\n"
        "- The options must differ from each other.\n"
        f"Reply with only a JSON array of {count} strings, nothing else."
    )


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
    (otherwise the prefix alone would show which one is right).
    """
    items = _json_array(text)
    if items is None:
        return None
    wanted = set(types)
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
        kept.append(option)
        if len(kept) == count:
            break
    return kept
