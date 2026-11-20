import pytest
from backend.community_service import CommunityService
from database.connection import connect


def test_crud_persistence_and_ownership(community):
    pid = community.create_post("general", "Ana", "A question", "How do bills become law?", "owner")
    fresh = CommunityService(community.path, seed=False)
    assert fresh.list_posts()[0]["id"] == pid
    with pytest.raises(ValueError):
        fresh.edit_post(pid, "other", "Changed", "Changed body")
    with pytest.raises(ValueError):
        fresh.delete_post(pid, "other")
    fresh.edit_post(pid, "owner", "Updated title", "Updated question")
    assert fresh.list_posts()[0]["title"] == "Updated title"
    fresh.add_comment(pid, "Ben", "Read the original journal.", "other")
    assert len(fresh.comments(pid)) == 1
    fresh.toggle_like(pid, "other")
    assert fresh.liked(pid, "other")
    fresh.toggle_like(pid, "other")
    assert not fresh.liked(pid, "other")
    fresh.report(pid, "other", "Misleading content")
    fresh.report(pid, "other", "Spam")
    with connect(community.path) as db:
        assert db.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 1
    fresh.delete_post(pid, "owner")
    assert fresh.list_posts() == []
    assert fresh.comments(pid) == []


def test_filter_and_popular(community):
    a = community.create_post("general", "Ana", "First", "First discussion", "a")
    community.create_post("risa-hontiveros", "Ben", "Second", "Second discussion", "b")
    community.toggle_like(a, "b")
    assert community.list_posts(sort="Popular")[0]["id"] == a
    assert len(community.list_posts("risa-hontiveros")) == 1


@pytest.mark.parametrize("content", ["", "kill you", "You are an idiot", "exterminate them", "buy now", "He is corrupt", "a" * 20])
def test_moderation(community, content):
    with pytest.raises(ValueError):
        community.create_post("general", "Ana", "Topic", content, "a")


def test_sql_injection_is_plain_text(community):
    community.create_post("general", "Ana", "SQL question", "'; DROP TABLE posts; --", "a")
    assert len(community.list_posts()) == 1


def test_seed_once(tmp_path):
    path = tmp_path / "seed.sqlite3"
    initial = CommunityService(path).list_posts()
    assert len(CommunityService(path).list_posts()) == len(initial) == 3
    assert all(p["is_demo"] for p in initial)
