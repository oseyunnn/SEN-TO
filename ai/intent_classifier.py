import re
import unicodedata

KEYWORDS = {
    "education": ("education", "educational", "background", "school", "degree", "university", "edukasyon"),
    "career": ("career", "experience", "political history"),
    "committees": ("committee", "committees", "chair", "komite"),
    "votes": ("voting record", "voted", "votes", "roll call", "boto"),
    "statements": ("statement", "statements", "speech", "speeches", "quote", "said"),
    "positions": ("position", "positions", "stance", "issue", "issues", "paninindigan"),
    "legislation": ("contribution", "contributions", "legislative record", "accomplishments"),
    "bills": ("bill", "bills", "resolution", "resolutions", "authored", "sponsored", "batas"),
    "procedures": ("procedure", "procedures", "senate process", "how does", "become law"),
}


def preprocess(query):
    return " ".join(unicodedata.normalize("NFKC", query).casefold().split())


def classify(query):
    query = preprocess(query)
    scores = {topic: sum(bool(re.search(r"\b" + re.escape(word) + r"\b", query)) for word in words)
              for topic, words in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "unknown"
