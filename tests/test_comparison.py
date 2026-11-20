import pytest
from backend.comparison_service import ComparisonService


def test_same_criteria_and_missing_data(senators):
    ids = [s["id"] for s in senators.senators[:3]]
    for count in (2, 3):
        records = ComparisonService().compare(ids[:count])
        assert len(records) == count
        assert len({r["period"] for r in records}) == 1
        assert all(len(r["sections"]) == 8 for r in records)
        assert all(v["status"] == "not_available" for r in records for v in r["sections"].values())


@pytest.mark.parametrize("ids", [[], ["risa-hontiveros"], ["risa-hontiveros"] * 2,
                                 ["risa-hontiveros", "missing"]])
def test_invalid_comparison(ids):
    with pytest.raises(ValueError):
        ComparisonService().compare(ids)
