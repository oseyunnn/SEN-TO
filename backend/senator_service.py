import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
UNAVAILABLE = "Not available in the current demonstration dataset."
SECTIONS = {
    "education": "Background & education", "career": "Political experience",
    "legislation": "Legislative contributions", "bills": "Bills & resolutions",
    "committees": "Committee memberships", "votes": "Voting records",
    "statements": "Public statements", "positions": "Documented positions",
}


def read_json(name):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Could not load {name}. Restore the bundled data file and restart.") from exc


class SenatorService:
    def __init__(self):
        self.senators = read_json("senators.json")
        if not self.senators:
            raise ValueError("The senator directory is empty. Add directory records to data/senators.json.")
        self.styles = read_json("personality_configs.json")
        self.questions = read_json("suggested_questions.json")

    def get(self, senator_id):
        for senator in self.senators:
            if senator["id"] == senator_id:
                return senator
        raise ValueError("Please select a senator from the directory.")

    def search(self, query=""):
        return [s for s in self.senators if query.casefold().strip() in s["name"].casefold()]

    def style(self, senator_id):
        self.get(senator_id)
        return self.styles.get(senator_id, self.styles["default"])

    def suggestions(self, senator_id):
        senator = self.get(senator_id)
        return [q.format(name=senator["name"]) for q in self.questions]
