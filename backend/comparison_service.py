from backend.senator_service import SECTIONS, UNAVAILABLE, SenatorService


class ComparisonService:
    def __init__(self, senators=None):
        self.senators = senators or SenatorService()

    def compare(self, ids):
        if len(ids) not in (2, 3) or len(set(ids)) != len(ids):
            raise ValueError("Choose two or three different senators.")
        return [{"senator": self.senators.get(sid), "period": "20th Congress · 2025–2028",
                 "sections": {key: self.senators.get(sid).get("profile", {}).get(key, {
                     "status": "not_available", "content": UNAVAILABLE, "sources": []}) for key in SECTIONS}}
                for sid in ids]
