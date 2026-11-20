"""Regenerate bundled, explicitly unverified demonstration fixtures (no network)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ["Risa Hontiveros", "Paolo Benigno Aquino IV", "Francis Pangilinan", "Alan Peter Cayetano",
         "Pia Cayetano", "Ronald dela Rosa", "Joseph Victor Ejercito"]
# The mockup supplies seven names. Do not invent or assert a current 24-member roster.
GUIDES = {
    "education": "To review educational background, look for an institution-issued biography or an official résumé. Record the qualification, institution, year, and original source. No qualification is established in this demonstration.",
    "career": "To review political experience, build a dated timeline from original records. Distinguish elected office, appointed office, and candidacy. No office history is established in this demonstration.",
    "legislation": "Look beyond a bill’s title. Separate what a senator filed, what they sponsored, and what became law. Read the full text, authorship, legislative status, and related journal. Keep the congressional period consistent when comparing records.",
    "bills": "Authorship and sponsorship are different roles. Check the author list and sponsorship record separately, then read the bill text and its latest status. Filing a bill does not establish that it became law. No bill or resolution is attributed to this senator in this demonstration.",
    "committees": "Check a dated committee roster and distinguish chair, vice-chair, and member roles. Membership can change during a congressional period. No committee role is confirmed in this demonstration.",
    "votes": "Check the roll-call record, measure, date, and voting stage together. Absence, abstention, and a vote against a measure are different records. No individual vote is confirmed in this demonstration.",
    "statements": "Read the complete original statement with its date and context. Distinguish a direct quotation from a paraphrase or interpretation. This demonstration contains no quotations attributed to a senator.",
    "positions": "A documented position needs an attributable statement or record about a specific issue. Do not infer a stance from party membership or missing information. No senator’s position is established in this demonstration.",
    "procedures": "When exploring Senate procedures, follow a measure through filing, committee consideration, plenary deliberation, and subsequent action. Use the current rules and the original journal to confirm the exact procedure. This is a generic demonstration guide.",
}


def main():
    data = ROOT / "data"
    data.mkdir(exist_ok=True)
    senators, docs = [], []
    styles = {"default": {"formality": "neutral", "language": "English", "presentation": "paragraphs",
                           "description": "Neutral demonstration style, not a senator’s actual personality."}}
    for i, name in enumerate(NAMES):
        sid = name.lower().replace(" ", "-")
        senators.append({"id": sid, "name": name, "portrait": str(i) if i < 3 else None,
                         "directory_status": "UI reference example; current membership unverified",
                         "minority_membership": "Unverified", "profile": {}})
        styles[sid] = {**styles["default"], "presentation": "numbered" if i == 1 else "paragraphs"}
        for topic, content in GUIDES.items():
            docs.append({"document_id": f"DEMO-{i+1:02d}-{topic.upper()}", "senator_id": sid,
                         "topic": topic, "title": f"Demonstration guide: {topic}", "content": content,
                         "source_type": "simulation", "source_url": None, "publication_date": None,
                         "verification_status": "unverified_demo"})
    payloads = {"senators.json": senators, "mock_documents.json": docs, "personality_configs.json": styles,
                "suggested_questions.json": ["What bills has {name} authored?", "What committees does {name} serve on?",
                                             "What are {name}’s documented positions?", "Explore {name}’s legislative contributions"]}
    for filename, payload in payloads.items():
        (data / filename).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
