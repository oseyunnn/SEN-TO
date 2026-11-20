import re


def moderate(text):
    normalized = text.casefold()
    rules = {
        "Threats are not allowed.": r"\b(kill you|kill them|death threat|hurt you|patayin kita)\b",
        "Please discuss ideas without personal harassment.": r"\b(idiot|moron|stupid|bobo|tanga)\b",
        "Hateful or dehumanizing content is not allowed.": r"\b(subhuman|racial inferiority|exterminate|vermin)\b",
        "Avoid spam and repeated promotions.": r"\b(buy now|free money|click here to win)\b",
        "Do not present unsupported accusations as facts.": r"\b(corrupt|criminal|thief|stole|guilty|kurakot|magnanakaw)\b",
    }
    for reason, pattern in rules.items():
        if re.search(pattern, normalized):
            raise ValueError(reason)
    if len(re.findall(r"https?://", normalized)) > 3 or re.search(r"(.)\1{14,}", normalized):
        raise ValueError("Please remove repeated text or excessive links.")


def clean(value, label, max_length):
    value = value.strip()
    if not value or len(value) > max_length:
        raise ValueError(f"{label} must contain 1–{max_length:,} characters.")
    moderate(value)
    return value
