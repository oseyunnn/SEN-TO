from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_navigation_chat_and_comparison(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTO_DB_PATH", str(tmp_path / "ui.sqlite3"))
    at = AppTest.from_file(str(APP)).run()
    assert not at.exception
    assert at.session_state["page"] == "HOME"
    at.button(key="nav_home_start").click().run()
    assert not at.exception
    assert at.radio(key="main_navigation").options == ["CHAT", "COMPARE"]
    at.button(key="suggest_risa-hontiveros_0").click().run()
    assert not at.exception
    assert len(at.session_state["histories"]["risa-hontiveros"]) == 2
    answer = at.session_state["histories"]["risa-hontiveros"][1]["response"]
    assert answer["label"] == "BACKEND CONNECTION PLACEHOLDER"
    assert answer["citations"] == []
    assert "send_chat_message()" in answer["answer"]
    assert "No source lookup was performed" in answer["limitation"]
    at.button(key="select_senator_idfrancis-pangilinan").click().run()
    assert at.session_state["senator_id"] == "francis-pangilinan"
    assert at.session_state["histories"]["francis-pangilinan"] == []
    at.radio(key="main_navigation").set_value("COMPARE").run()
    assert not at.exception
    at.radio(key="comparison_count").set_value(2).run()
    assert len(at.session_state["compare_ids"]) == 3
    at.selectbox(key="compare_select_0").select("alan-peter-cayetano").run()
    assert not at.exception
    assert at.session_state["compare_ids"][0] == "alan-peter-cayetano"
    at.radio(key="main_navigation").set_value("CHAT").run()
    at.button(key="select_senator_idrisa-hontiveros").click().run()
    assert len(at.session_state["histories"]["risa-hontiveros"]) == 2
    at.radio(key="main_navigation").set_value("COMPARE").run()
    assert at.radio(key="comparison_count").value == 2
    assert not at.exception
