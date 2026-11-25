"""Deterministic input and per-session resource controls for chat."""

from __future__ import annotations

import re
import time
import unicodedata
from typing import MutableMapping


MAX_QUESTION_CHARS = 4000
MAX_QUESTION_BYTES = 12000
MAX_SESSION_REQUESTS = 8
SESSION_REQUEST_WINDOW_SECONDS = 60.0

INTERNAL_PROMPT_REFUSAL = (
    "I can’t disclose private system or developer instructions or internal configuration. "
    "I can explain SEN’TO’s public purpose, evidence rules, and limitations."
)
INTERNAL_PROMPT_REFUSAL_FIL = (
    "Hindi ko maibibigay ang pribadong system o developer instructions at internal configuration. "
    "Maaari kong ipaliwanag ang pampublikong layunin, evidence rules, at mga limitasyon ng SEN’TO."
)
BULK_RETRIEVAL_REFUSAL = (
    "I can’t provide a bulk dump of retrieved passages or internal index contents. "
    "Ask a focused question about a specific public record instead."
)
BULK_RETRIEVAL_REFUSAL_FIL = (
    "Hindi ko maibibigay nang maramihan ang retrieved passages o laman ng internal index. "
    "Magtanong tungkol sa isang partikular na public record."
)
NO_EVIDENCE_FIL = (
    "Wala akong nakitang nasuring source sa kasalukuyang dataset na sumasagot sa tanong na ito. "
    "Hindi ito nangangahulugang walang pampublikong rekord."
)
NO_EVIDENCE_LIMITATION_FIL = "Walang nasuring passage sa kasalukuyang corpus na sumusuporta sa sagot na ito."
SERVICE_UNAVAILABLE_FIL = "Pansamantalang hindi available ang source-backed answer service. Walang nabuong sagot."

_FILIPINO_MARKERS = {
    "ang", "ng", "mga", "mo", "mong", "ikaw", "ba", "ako", "hindi", "ito", "iyan",
    "ano", "paano", "pakisabi", "paki", "lahat", "buong", "yung", "iyong", "natin",
    "ninyo", "niyo", "po", "sa", "para", "gusto", "dapat", "huwag", "wag", "ibigay",
    "ipakita", "ilabas", "ibunyag", "nasa", "sino", "kailan", "kumusta", "kamusta",
    "magpanggap", "magkunwari", "sumagot", "magsalita", "bilang", "patunayan", "kurakot",
    "senador", "halalan", "iboboto", "mananalo", "boto", "ko", "niya", "nila", "siya",
    "sila", "naman", "nga", "kahit",
}

_INTERNAL_PROMPT_REQUEST = re.compile(
    r"\b(?:reveal|show|print|repeat|quote|dump|disclose|output|provide|copy|tell me|"
    r"ipakita|pakita|ilabas|ibunyag|ibigay|pakibigay|ulitin|kopyahin|isulat|sabihin|"
    r"ibahagi|i[- ]?reveal|i[- ]?show|i[- ]?print|i[- ]?dump|paki[- ]?share)\b"
    r".{0,100}\b(?:your|iyo(?:ng)?|mo|mong|yung|the\s+(?:hidden|private|internal)|"
    r"internal|developer|system|hidden|lihim|pribado(?:ng)?)\b"
    r".{0,60}\b(?:system\s+|developer\s+)?(?:prompt|instructions?|instruksyon|"
    r"tagubilin|configuration|config|setting|message|mensahe|direktiba)\b",
    re.IGNORECASE | re.DOTALL,
)
_PERSONAL_PROMPT_QUESTION = re.compile(
    r"\bwhat\s+is\s+(?:your|the\s+hidden|the\s+private)\s+(?:system\s+|developer\s+)?"
    r"(?:prompt|instructions?|configuration)\b|"
    r"\bano\s+(?:ba\s+)?(?:(?:ang|yung)\s+)?(?:system|developer)\s+"
    r"(?:prompt|instructions?|instruksyon|configuration)\s+(?:mo|mong|iyo|iyong|ninyo|niyo)\b|"
    r"\bwhat\s+is\s+(?:the\s+)?(?:system|developer)\s+(?:prompt|instructions?)\s+"
    r"(?:of|for)\s+(?:sen['’]?to|this assistant)\b",
    re.IGNORECASE,
)
_BULK_RETRIEVAL_REQUEST = re.compile(
    r"\b(?:dump|export|print|copy|list|reveal|show|repeat|return|give me|"
    r"ipakita|pakita|ibigay|ilabas|kopyahin|ilista|ibahagi|i[- ]?dump|i[- ]?export|"
    r"i[- ]?print|i[- ]?copy|i[- ]?list|paki[- ]?dump)\b"
    r".{0,80}\b(?:all|every|entire|full|raw|verbatim|lahat|buong|kabuuan|bawat|kompleto)\b"
    r".{0,80}\b(?:documents?|passages?|chunks?|knowledge\s+base|index|context|corpus|"
    r"dokumento|mga\s+passage|mga\s+chunk|records?|sources?)\b",
    re.IGNORECASE | re.DOTALL,
)


def normalize_question(value: str) -> str:
    """Normalize Unicode and reject oversize or hidden-control input."""
    if not isinstance(value, str):
        raise ValueError("Enter a question between 1 and 4,000 characters.")
    question = unicodedata.normalize("NFKC", value).strip()
    if not question or len(question) > MAX_QUESTION_CHARS:
        raise ValueError("Enter a question between 1 and 4,000 characters.")
    if len(question.encode("utf-8")) > MAX_QUESTION_BYTES:
        raise ValueError("The question is too large after Unicode normalization.")
    # Whitespace controls remain useful for ordinary text. Other control and
    # format characters can make visible text differ from what the model sees.
    if any(
        unicodedata.category(char) in {"Cc", "Cf", "Cs"}
        and char not in {"\n", "\r", "\t"}
        for char in question
    ):
        raise ValueError("Remove invisible formatting or control characters from the question.")
    return question


def requests_internal_prompt(question: str) -> bool:
    """Recognize direct requests for this assistant's private instructions."""
    return bool(
        _INTERNAL_PROMPT_REQUEST.search(question)
        or _PERSONAL_PROMPT_QUESTION.search(question)
    )


def requests_bulk_retrieval(question: str) -> bool:
    """Recognize attempts to dump retrieved context or the index wholesale."""
    return bool(_BULK_RETRIEVAL_REQUEST.search(question))


def is_filipino_or_taglish(question: str) -> bool:
    """Use common Filipino markers to select a refusal language when needed."""
    words = set(re.findall(r"[^\W_]+", question.casefold(), flags=re.UNICODE))
    return bool(words & _FILIPINO_MARKERS)


def internal_prompt_refusal(question: str) -> str:
    return INTERNAL_PROMPT_REFUSAL_FIL if is_filipino_or_taglish(question) else INTERNAL_PROMPT_REFUSAL


def internal_prompt_limitation(question: str) -> str:
    if is_filipino_or_taglish(question):
        return "Hindi bahagi ng pampublikong records ang pribadong system/developer instructions at internal configuration."
    return "Private system and developer instructions are not part of the public-record corpus."


def bulk_retrieval_refusal(question: str) -> str:
    return BULK_RETRIEVAL_REFUSAL_FIL if is_filipino_or_taglish(question) else BULK_RETRIEVAL_REFUSAL


def bulk_retrieval_limitation(question: str) -> str:
    if is_filipino_or_taglish(question):
        return "Sinasagot ng SEN’TO ang tiyak na tanong at hindi inilalabas nang maramihan ang retrieved context."
    return "The assistant answers focused questions and does not expose bulk retrieval context."


def localized_text(question: str, english: str, filipino: str) -> str:
    return filipino if is_filipino_or_taglish(question) else english


def no_evidence_response(question: str, english: str) -> str:
    return localized_text(question, english, NO_EVIDENCE_FIL)


def no_evidence_limitation(question: str, english: str) -> str:
    return localized_text(question, english, NO_EVIDENCE_LIMITATION_FIL)


def service_unavailable_response(question: str, english: str) -> str:
    return localized_text(question, english, SERVICE_UNAVAILABLE_FIL)


def allow_session_request(
    state: MutableMapping,
    *,
    now: float | None = None,
    limit: int = MAX_SESSION_REQUESTS,
    window_seconds: float = SESSION_REQUEST_WINDOW_SECONDS,
) -> bool:
    """Apply a small sliding-window limit to a Streamlit session."""
    current = time.monotonic() if now is None else float(now)
    requests = state.setdefault("_sento_chat_request_times", [])
    cutoff = current - window_seconds
    requests[:] = [stamp for stamp in requests if stamp > cutoff]
    if len(requests) >= limit:
        return False
    requests.append(current)
    return True
