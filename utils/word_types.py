"""
Word types (noun, verb, adjective ...) for the quiz.

A quiz question shows the right translation next to wrong ones. When the right
answer is "adj. 美丽的", the wrong ones should be adjectives too, otherwise the
word type gives the answer away.

Where a word's type comes from:
  1. The prefix in its translation ("n. 例子", "vt. 举例 n. 例子"), parsed here.
  2. Words with no prefix are tagged once by Gemini and cached in the
     words.ai_pos column ("adj,n"; "" means Gemini found no type).

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

# Words Gemini may answer with instead of the abbreviation
TYPE_NAMES = {
    "noun": "n",
    "verb": "v",
    "adjective": "adj",
    "adverb": "adv",
    "preposition": "prep",
    "conjunction": "conj",
    "pronoun": "pron",
    "interjection": "int",
    "numeral": "num",
    "number": "num",
    "article": "art",
    "auxiliary": "aux",
    "abbreviation": "abbr",
    "prefix": "pref",
    "suffix": "suf",
}

# Types listed in the prompt sent to Gemini
PROMPT_TYPES = ("n", "v", "adj", "adv", "prep", "conj", "pron", "int", "num", "art", "aux", "abbr")

# Longest first so "interj" is tried before "int"
_ALTERNATION = "|".join(sorted(TYPE_ALIASES, key=len, reverse=True))

# "n." / "adj." only when the abbreviation is a whole token: the lookbehind keeps
# the "n." inside "pron." and the "e.g." in a note from counting.
_PREFIX_RE = re.compile(rf"(?<![A-Za-z])({_ALTERNATION})\.")

# Longest reply still treated as a list of types rather than a sentence
_MAX_REPLY_CHARS = 40


def parse_word_types(translation):
    """Canonical types named by the prefixes in a translation, sorted.

    "n. 例子 vt. 举例" -> ("n", "v"); a translation with no prefix -> ().
    """
    if not translation:
        return ()
    return tuple(sorted({TYPE_ALIASES[m] for m in _PREFIX_RE.findall(translation)}))


def split_ai_pos(value):
    """Types stored in words.ai_pos ("adj,n") as a tuple; None or "" -> ()."""
    if not value:
        return ()
    return tuple(t for t in value.split(",") if t in TYPE_ALIASES)


def join_ai_pos(types):
    """The words.ai_pos text for a tuple of types ("" when there are none)."""
    return ",".join(sorted(set(types)))


def effective_types(translation, ai_pos):
    """A word's types: the translation prefixes, else the cached Gemini answer."""
    return parse_word_types(translation) or split_ai_pos(ai_pos)


def type_match_sql(types, use_ai_cache=True):
    """SQL condition and parameters for "has at least one of these types".

    Matches a prefix in the translation (MySQL regex, case sensitive) and, when
    use_ai_cache is true, a type in the words.ai_pos column. Pass false while
    that column does not exist. Raises ValueError when types is empty.
    """
    if not types:
        raise ValueError("types must not be empty")
    aliases = sorted(a for a, canonical in TYPE_ALIASES.items() if canonical in types)
    pattern = rf"(^|[^A-Za-z])({'|'.join(aliases)})\."
    clauses = ["REGEXP_LIKE(translation, %s, 'c')"]
    params = [pattern]
    if use_ai_cache:
        for canonical in sorted(set(types)):
            clauses.append("FIND_IN_SET(%s, ai_pos)")
            params.append(canonical)
    return "(" + " OR ".join(clauses) + ")", params


def build_type_prompt(word, translation):
    """Prompt asking Gemini for the type(s) of one word."""
    return (
        f"What part of speech is the English word or phrase '{word}' "
        f"(Chinese meaning: {translation})? "
        f"Answer with only the abbreviations that apply, separated by commas, "
        f"chosen from: {', '.join(PROMPT_TYPES)}. "
        f"If none fits, answer: none."
    )


def parse_type_reply(text):
    """Types in a Gemini reply such as "n, v", "adj." or "noun".

    Returns a tuple of types, () when Gemini says "none", and None when the
    reply is unusable (empty, a sentence, no known type). Only a tuple is worth
    caching: None means "ask again later".
    """
    if not text or len(text.strip()) > _MAX_REPLY_CHARS:
        return None
    tokens = re.findall(r"[a-z]+", text.lower())
    found = {TYPE_ALIASES.get(t) or TYPE_NAMES.get(t) for t in tokens} - {None}
    if found:
        return tuple(sorted(found))
    return () if "none" in tokens else None


def build_batch_prompt(items):
    """Prompt asking Gemini for the types of many words at once.

    items: list of (word_id, word, translation). Each answer line is
    "id|types" so the replies can be matched back to the words.
    """
    lines = "\n".join(f"{word_id}|{word}|{translation}" for word_id, word, translation in items)
    return (
        "Give the part of speech of each English word or phrase below. "
        "Each input line is: id|word|Chinese meaning.\n"
        f"Reply with one line per input, exactly: id|types, where types are the "
        f"abbreviations that apply separated by commas, chosen from: "
        f"{', '.join(PROMPT_TYPES)}. If none fits, write none. "
        "No other text.\n\n" + lines
    )


def parse_batch_reply(text):
    """{word_id: types} from "id|types" lines.

    Lines that do not parse are skipped, so a word missing from the result got
    no usable answer. A word answered "none" maps to () ("no type").
    """
    result = {}
    for line in (text or "").splitlines():
        line = line.strip().strip("`")
        if "|" not in line:
            continue
        raw_id, _, raw_types = line.partition("|")
        raw_id = raw_id.strip()
        if not raw_id.isdigit():
            continue
        types = parse_type_reply(raw_types)
        if types is not None:
            result[int(raw_id)] = types
    return result
