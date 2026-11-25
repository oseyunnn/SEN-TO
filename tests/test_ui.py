from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_navigation_chat_and_comparison(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTO_DB_PATH", str(tmp_path / "ui.sqlite3"))
    at = AppTest.from_file(str(APP)).run()
    assert not at.exception
    assert at.radio(key="page").options == ["CHAT", "COMPARE"]
    assert any("No reviewed passages are indexed yet" in element.value for element in at.info)
    at.button(key="suggest_risa-hontiveros_0").click().run()
    assert not at.exception
    assert len(at.session_state["histories"]["risa-hontiveros"]) == 2
    answer = at.session_state["histories"]["risa-hontiveros"][1]["response"]
    assert answer["label"] == "NO REVIEWED EVIDENCE"
    assert answer["citations"] == []
    assert any("No suitable reviewed passage was found" in element.value for element in at.get("caption"))
    at.button(key="select_senator_idfrancis-pangilinan").click().run()
    assert at.session_state["senator_id"] == "francis-pangilinan"
    assert at.session_state["histories"]["francis-pangilinan"] == []
    at.radio(key="page").set_value("COMPARE").run()
    assert not at.exception
    at.radio(key="comparison_count").set_value(2).run()
    assert len(at.session_state["compare_ids"]) == 3
    at.selectbox(key="compare_select_0").select("alan-peter-cayetano").run()
    assert not at.exception
    assert at.session_state["compare_ids"][0] == "alan-peter-cayetano"
    at.radio(key="page").set_value("CHAT").run()
    at.button(key="select_senator_idrisa-hontiveros").click().run()
    assert len(at.session_state["histories"]["risa-hontiveros"]) == 2
    at.radio(key="page").set_value("COMPARE").run()
    assert at.radio(key="comparison_count").value == 2
    assert not at.exception
