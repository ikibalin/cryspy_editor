"""The request of the user in English for the search, without Qt.

The help of CrysPy, the methods and procedures that fit a request
(form_matching_methods_text) and the recipes are found by English words.
The assistant gives no language a preference: a request in another
language is rewritten in English by the loaded model (one short call), the
English text is used for the search and given to the model with the
request, and the history of the chat keeps the words of the user. An
English request is used as it is, without a call.

The module has no Qt and no CrysPy, so PyColl5 can use it unchanged.
"""
import inspect
import re

# letters that also appear in English requests: units and physical symbols
S_SYMBOL_LETTERS = "ÅåµμχΧΓγαβθλσΣπφψωΩρκδΔ"

# function words of English: a request of several words without any of them
# is not English even when written in ASCII letters only
SET_ENGLISH_WORDS = {
    "a", "about", "after", "all", "an", "and", "any", "are", "as", "at", "be",
    "before", "but", "by", "can", "could", "do", "does", "each", "for", "from",
    "give", "has", "have", "how", "i", "if", "in", "into", "is", "it", "its",
    "make", "me", "my", "need", "not", "of", "on", "only", "or", "please",
    "should", "show", "so", "than", "that", "the", "their", "them", "then",
    "there", "these", "this", "to", "use", "was", "what", "when", "where",
    "which", "why", "will", "with", "would", "you", "your",
}

# up to this number of words an ASCII request is taken as English (names of
# parameters, "refine scale", "chi2")
N_SHORT_REQUEST = 3

TRANSLATE_PROMPT = (
    "Rewrite the request of the user in English. Keep technical terms, names of "
    "parameters, chemical formulas, numbers, units, file names and quoted text as they are. "
    "Reply with the English text only, without explanations.")

MAX_TRANSLATION_TOKENS = 200  # longer replies are cut: the request stays short


def is_english(text: str) -> bool:
    """True if the request is English (no translation is needed).

    A request with letters outside the Latin alphabet (except physical
    symbols such as Å, μ, χ, Γ) or with Latin letters with diacritics
    (é, ü, ñ) is not English. A request in ASCII letters of more than
    N_SHORT_REQUEST words is English when it has an English function word
    ("how", "the", "to"); a shorter one is taken as English."""
    for char in text:
        if char.isalpha() and not char.isascii() and char not in S_SYMBOL_LETTERS:
            return False
    l_word = re.findall(r"[A-Za-z]+", text.lower())
    if len(l_word) <= N_SHORT_REQUEST:
        return True
    return any(word in SET_ENGLISH_WORDS for word in l_word)


def take_translation(reply: str, text: str) -> str:
    """The English text from the reply of the model: the first non-empty
    paragraph without quotes and a "Translation:" prefix; the request itself
    when the reply is empty."""
    reply = re.sub(r"<think>.*?</think>", "", reply or "", flags=re.DOTALL).strip()
    reply = reply.split("\n\n")[0].strip()
    reply = re.sub(r"^(english|translation|request)\s*:\s*", "", reply, flags=re.IGNORECASE)
    reply = reply.strip().strip('"\'«»“”').strip()
    return reply if reply else text


def translate_to_english(model, text: str) -> str:
    """The request in English: the text itself when it is English or there
    is no model, else the rewrite by the model (one short call). When the
    model fails, the text is returned as it is: the request goes on."""
    if model is None or is_english(text):
        return text
    messages = [{"role": "system", "content": TRANSLATE_PROMPT},
                {"role": "user", "content": text}]
    kwargs = {}
    try:
        l_parameter = inspect.signature(model.chat).parameters
    except (TypeError, ValueError):
        l_parameter = {}
    if "flag_think" in l_parameter:  # a thinking model answers at once
        kwargs["flag_think"] = False
    if "max_tokens" in l_parameter:
        kwargs["max_tokens"] = MAX_TRANSLATION_TOKENS
    try:
        reply = model.chat(messages, **kwargs)
    except Exception:  # noqa: BLE001 - any failure of the model: the request is used as it is
        return text
    return take_translation(str(reply), text)


def add_english_request(question: str, request_en: str) -> str:
    """The request for the model: the words of the user and, when it was
    translated, the English text after them."""
    if request_en.strip() == question.strip():
        return question
    return f"{question}\n\n(In English: {request_en})"
