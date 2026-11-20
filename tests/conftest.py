import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def senators():
    from backend.senator_service import SenatorService
    return SenatorService()


@pytest.fixture
def community(tmp_path):
    from backend.community_service import CommunityService
    return CommunityService(tmp_path / "community.sqlite3", seed=False)
