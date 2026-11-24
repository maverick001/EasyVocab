"""
Word types (noun, verb, adjective ...) read from a translation's prefix.

A word's translation often starts with its type: "n. 例子", "vt. 举例 n. 例子".
The quiz uses this to keep Gemini's wrong options in the same format and word
type as the right answer (see utils/quiz_options.py).

Nothing here touches the database or the network.
"""

import re

# Dictionary abbreviation -> canonical type. vt./vi. count as v.
TYPE_ALIASES = {
    "n": "n",
    "v": "v",
    "vt": "v",
    "vi": "v",
    "adj": "adj",
    "adv": "adv",
    "prep": "prep",
    "conj": "conj",
    "pron": "pron",
    "int": "int",
    "interj": "int",
    "num": "num",
    "art": "art",
    "aux": "aux",
    "abbr": "abbr",
    "pref": "pref",
    "suf": "suf",
}

# Longest first so "interj" is tried before "int"
_ALTERNATION = "|".join(sorted(TYPE_ALIASES, key=len, reverse=True))

# "n." / "adj." only when the abbreviation is a whole token: the lookbehind keeps
# the "n." inside "pron." and the "e.g." in a note from counting.
_PREFIX_RE = re.compile(rf"(?<![A-Za-z])({_ALTERNATION})\.")


def parse_word_types(translation):
    """Canonical types named by the prefixes in a translation, sorted.

    "n. 例子 vt. 举例" -> ("n", "v"); a translation with no prefix -> ().
    """
    if not translation:
        return ()
    return tuple(sorted({TYPE_ALIASES[m] for m in _PREFIX_RE.findall(translation)}))


def strip_type_prefixes(text):
    """The text without its "n." / "vt." / "adj." markers."""
    return _PREFIX_RE.sub(" ", text or "")
