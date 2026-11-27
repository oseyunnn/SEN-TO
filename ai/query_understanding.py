"""Intent-aware query understanding, contextual follow-up resolution, and query expansion."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from ai.intent_classifier import classify


@dataclass(frozen=True)
class QueryAnalysis:
    original_query: str
    resolved_query: str
    expanded_query: str
    intent: str
    topic: str
    is_follow_up: bool
    needs_external_research: bool
    asks_recent_info: bool
    response_guidance: str


_GREETING_RE = re.compile(
    r"^(?:hi|hello|hey|kumusta|kamusta|good\s+(?:morning|afternoon|evening)|"
    r"magandang\s+(?:umaga|hapon|gabi)|yo|hola)[\s!?.]*$",
    re.IGNORECASE,
)
_META_CAPABILITY_RE = re.compile(
    r"\b(?:what\s+can\s+you\s+do|how\s+do\s+you\s+work|who\s+are\s+you|"
    r"ano(?:ng)?\s+(?:kaya|pwede)\s+mo(?:ng)?\s+gawin|sino\s+ka)\b",
    re.IGNORECASE,
)
_GENERAL_CIVIC_RE = re.compile(
    r"\b(?:how\s+does\s+a\s+bill\s+become\s+(?:a\s+)?law|paano\s+nagiging\s+batas|"
    r"what\s+is\s+(?:the\s+)?(?:difference\s+between|meaning\s+of)\s+"
    r"(?:author(?:ing|ed)?|sponsor(?:ing|ed)?|bill|resolution|senate|congress|committee|bicameral|veto|saln|ombudsman|impeachment)|"
    r"how\s+does\s+(?:the\s+)?(?:philippine\s+)?senate\s+work|"
    r"what\s+does\s+(?:the\s+)?(?:senate|blue\s+ribbon\s+committee|ombudsman|coa|comelec)\s+do|"
    r"ano\s+ang\s+(?:kaibahan|ibig\s+sabihin|trabaho|tungkulin)\s+ng\s+(?:senado|senador|komite|batas|bill|resolution|saln))\b",
    re.IGNORECASE,
)
_FOLLOW_UP_RE = re.compile(
    r"^(?:which\s+ones?|what\s+about|how\s+about|and\s+(?:what|how|which)|"
    r"tell\s+me\s+more|more\s+details|explain\s+(?:that|it|this)|"
    r"ano\s+pa|alin\s+(?:doon|dun|sa\s+mga\s+iyon)|tungkol\s+doon|bakit\s+naman)\b|"
    r"\b(?:those\s+bills|that\s+bill|those\s+laws|that\s+issue|that\s+case|previous\s+answer|them|they)\b",
    re.IGNORECASE,
)
_RECENT_RE = re.compile(
    r"\b(?:latest|recent|recently|current|currently|today|this\s+week|this\s+month|"
    r"2026|ngayon|kamakailan|bago(?:ng)?|kasalukuyan)\b",
    re.IGNORECASE,
)
_CONTROVERSY_RE = re.compile(
    r"\b(?:controvers\w*|scandal\w*|allegation\w*|accused|complaint\w*|graft|corrupt\w*|"
    r"plunder|ombudsman|sandiganbayan|kaso|isyu|kontrobersiya|paratang|imbestigasyon|issue\w*)\b",
    re.IGNORECASE,
)
_PERFORMANCE_RE = re.compile(
    r"\b(?:doing\s+(?:their|his|her)\s+job|effective|performance|accomplish\w*|achieved|"
    r"fulfilled|promises?|track\s+record|nagawa|ginawa|nagtatrabaho|attendance)\b",
    re.IGNORECASE,
)
_BILL_EXPLAIN_RE = re.compile(
    r"\b(?:what\s+does\s+(?:this|that|the)\s+(?:bill|law|measure|ra\s+\d+|sbn?\s+\d+)\s+mean|"
    r"ordinary\s+filipinos|practical\s+(?:impact|effect)|ano\s+ang\s+epekto|para\s+sa\s+mga\s+pilipino)\b",
    re.IGNORECASE,
)
_VERIFICATION_RE = re.compile(
    r"\b(?:is\s+this\s+(?:reliable|true|verified)|how\s+reliable|where\s+did\s+you\s+get|"
    r"mapagkakatiwalaan\s+ba|totoo\s+ba|saan\s+galing)\b",
    re.IGNORECASE,
)
_OFF_TOPIC_RE = re.compile(
    r"\b(?:recipe|cook|weather|horoscope|poem|joke|movie|song\s+lyrics|math\s+homework|"
    r"write\s+(?:a\s+)?(?:python|javascript|code|story)|translate\s+this\s+novel)\b",
    re.IGNORECASE,
)

_CONCEPT_EXPANSIONS = (
    (re.compile(r"\b(?:students?|youth|kabataan|iskolar|tuition|school\w*|teacher\w*)\b", re.I),
     "education scholarship CHED DepEd SUCs school teachers youth"),
    (re.compile(r"\b(?:health|hospital\w*|medical|doktor|nurses?|philhealth|kalusugan)\b", re.I),
     "health healthcare PhilHealth hospital medical mental health DOH"),
    (re.compile(r"\b(?:workers?|labor|trabaho|sahod|wage|ofw|employment)\b", re.I),
     "labor workers minimum wage employment DOLE OFW"),
    (re.compile(r"\b(?:farmers?|agriculture|pagkain|rice|bigas|magsasaka)\b", re.I),
     "agriculture farmers food security rice tariffication DA"),
    (re.compile(r"\b(?:corruption|graft|saln|money|wealth|assets?|net\s+worth)\b", re.I),
     "SALN financial disclosure graft controversy Ombudsman COA"),
    (re.compile(r"\b(?:done|accomplish\w*|nagawa|laws?|batas)\b", re.I),
     "authored sponsored Republic Act law bill committee"),
    (re.compile(r"\b(?:stance|position|paninindigan|views?)\b", re.I),
     "policy standpoint public statement vote position"),
)

_INTENT_GUIDANCE = {
    "greeting_or_meta": "Respond warmly and concisely in the user's language, explaining how SEN'TO helps explore the selected senator's public records and Philippine legislative processes.",
    "general_civic": "Explain the Philippine civic or legislative concept clearly in plain language for students and first-time voters, using concrete examples and citing any retrieved official sources.",
    "performance_evaluation": "Present documented legislative activity, enacted laws, committees, and limitations objectively. Do not equate bill filing count with effectiveness or declare a senator good/bad.",
    "controversy_accountability": "Clearly distinguish allegations, complaints, investigations, formal charges, court rulings, and official responses with dates.",
    "bill_explanation": "Explain what the measure proposes, what problem it addresses, who is affected, its actual legislative status (filed bill vs enacted law), and practical implications in plain language.",
    "source_verification": "Explain the source hierarchy, verification status, dates, and what the cited records do or do not establish.",
    "follow_up": "Use the recent conversation context to directly answer the follow-up question while keeping every factual claim grounded in evidence.",
    "off_topic": "Politely note that SEN'TO focuses on Philippine senators, legislation, and civic education, and invite a related question.",
    "factual_senator_inquiry": "Answer the question directly first, then add brief helpful context (such as distinguishing authored vs sponsored or filed vs enacted) and cite evidence.",
}


def _extract_recent_context(history: list[dict] | None) -> str:
    if not history:
        return ""
    snippets: list[str] = []
    for item in history[-4:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role == "user" and isinstance(item.get("content"), str):
            snippets.append(item["content"].strip()[:240])
        elif role == "assistant":
            resp = item.get("response")
            if isinstance(resp, dict) and isinstance(resp.get("answer"), str):
                snippets.append(resp["answer"].strip()[:320])
    return " ".join(snippets).strip()


def analyze_query(
    query: str,
    senator: dict | None = None,
    history: list[dict] | None = None,
) -> QueryAnalysis:
    normalized = " ".join(unicodedata.normalize("NFKC", query).split())
    topic = classify(normalized)
    asks_recent = bool(_RECENT_RE.search(normalized))
    is_follow_up = bool(_FOLLOW_UP_RE.search(normalized)) and bool(history)

    if _GREETING_RE.match(normalized) or _META_CAPABILITY_RE.search(normalized):
        intent = "greeting_or_meta"
    elif _OFF_TOPIC_RE.search(normalized):
        intent = "off_topic"
    elif _GENERAL_CIVIC_RE.search(normalized):
        intent = "general_civic"
    elif _VERIFICATION_RE.search(normalized):
        intent = "source_verification"
    elif _CONTROVERSY_RE.search(normalized):
        intent = "controversy_accountability"
    elif _BILL_EXPLAIN_RE.search(normalized):
        intent = "bill_explanation"
    elif _PERFORMANCE_RE.search(normalized):
        intent = "performance_evaluation"
    elif is_follow_up:
        intent = "follow_up"
    else:
        intent = "factual_senator_inquiry"

    resolved_query = normalized
    if is_follow_up:
        recent = _extract_recent_context(history)
        if recent:
            resolved_query = f"{normalized} (Context: {recent[:360]})"

    expansions: list[str] = []
    for pattern, extra in _CONCEPT_EXPANSIONS:
        if pattern.search(resolved_query):
            expansions.append(extra)
    if senator and isinstance(senator.get("name"), str) and intent not in {"general_civic", "greeting_or_meta", "off_topic"}:
        expansions.append(senator["name"])

    expanded_query = f"{resolved_query} {' '.join(expansions)}".strip() if expansions else resolved_query
    needs_external = asks_recent or intent == "general_civic"

    return QueryAnalysis(
        original_query=normalized,
        resolved_query=resolved_query,
        expanded_query=expanded_query,
        intent=intent,
        topic=topic,
        is_follow_up=is_follow_up,
        needs_external_research=needs_external,
        asks_recent_info=asks_recent,
        response_guidance=_INTENT_GUIDANCE.get(intent, _INTENT_GUIDANCE["factual_senator_inquiry"]),
    )
