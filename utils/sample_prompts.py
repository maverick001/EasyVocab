"""
Prompts for generating example sentences, chosen by the Gemini model in use.

Only two models are used in the app:
- gemini-4-hydrogen: noun-aware prompt. A noun or noun phrase gets a sentence
  that explains what it is; any other word gets a plain daily-life sentence.
- gemini-3.5-flash-lite: plain IELTS-level sentence, with no noun distinction.

Any other model name (for example from a stale browser tab) gets the plain
prompt, which needs nothing from the model beyond following instructions.
"""

MODEL_HYDROGEN = "gemini-4-hydrogen"
MODEL_FLASH_LITE = "gemini-3.5-flash-lite"

# The word is substituted with str.replace, not str.format, so a word that
# contains braces cannot break the template.
NOUN_AWARE_PROMPT = """You write one example sentence for an English vocabulary learner at an intermediate level (about CEFR B1-B2).

Target word or phrase: "{word}"

Rules:
- Use "{word}" exactly as written, including every word as shown. Do not change its form or use only part of it.
- If "{word}" is a noun or noun phrase (a thing, concept, person, place or technical term), write ONE sentence that explains what it is, so the learner can understand its meaning from the sentence alone. Example for "umbrella": An umbrella is a folding frame covered with fabric that you hold over your head to stay dry in the rain.
- Otherwise (a verb, adjective, adverb, idiom, phrasal verb or any other kind of word), write ONE plain, natural sentence about an everyday situation, where the context makes the meaning clear.
- If the word can be used as both a noun and something else, use its most common meaning.
- Apart from the target, use simple, common vocabulary. Keep the sentence to about 25 words or fewer.
- Output only the sentence, with no quotes, labels or explanation."""

PLAIN_IELTS_PROMPT = """Create a natural English sentence that uses the EXACT word or phrase "{word}" (including all words as shown). You must use "{word}" exactly as written, not variations or partial matches. Write at IELTS level (about band 6-7, CEFR B2): clear and natural, a little more developed than everyday basics, but with no obscure vocabulary. Use a single sentence of about 15 to 25 words. Show the word used naturally in context; do not define it. Only output the sentence, nothing else."""


def build_sample_prompt(model, word):
    """
    Build the example-sentence prompt for a model and a word.

    Args:
        model: Gemini model name from the request or config
        word: The word or phrase to use in the sentence

    Returns:
        The full prompt text
    """
    template = NOUN_AWARE_PROMPT if model == MODEL_HYDROGEN else PLAIN_IELTS_PROMPT
    return template.replace("{word}", word)
