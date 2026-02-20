import pytest
from unittest.mock import MagicMock, patch
from app.services.session.session_manager import (
    SessionManager, ChatMessage, build_enriched_query,
    get_session_manager, reset_session_manager,
)

@pytest.fixture(autouse=True)
def reset_singleton():
    reset_session_manager()
    yield
    reset_session_manager()

def make_manager():
    mock_store = MagicMock()
    mock_store.get.return_value = None
    return SessionManager(store=mock_store)

def test_create_session_returns_uuid_string():
    mgr = make_manager()
    sid = mgr.create_session()
    assert isinstance(sid, str) and len(sid) == 36

def test_get_history_empty_for_new_session():
    mgr = make_manager()
    assert mgr.get_history("non-existent") == []

def test_append_turn_stores_user_and_assistant():
    mock_store = MagicMock()
    saved = []
    mock_store.get.side_effect = lambda k: saved[-1] if saved else None
    mock_store.set.side_effect = lambda k, v: saved.append(v)
    mgr = SessionManager(store=mock_store)
    mgr.append_turn("sid", "hi", "hello")
    import json
    final = json.loads(saved[-1])
    assert len(final) == 2
    assert final[0]["role"] == "user" and final[0]["content"] == "hi"
    assert final[1]["role"] == "assistant" and final[1]["content"] == "hello"

def test_sliding_window_trims_to_max_pairs():
    """After 11 pairs appended, only 10 pairs (20 msgs) remain."""
    mock_store = MagicMock()
    saved = []
    mock_store.get.side_effect = lambda k: saved[-1] if saved else None
    mock_store.set.side_effect = lambda k, v: saved.append(v)
    mgr = SessionManager(store=mock_store)
    sid = "test-session"
    for i in range(11):
        mgr.append_turn(sid, f"user {i}", f"asst {i}")
    import json
    final = json.loads(saved[-1])
    assert len(final) == 20  # 10 pairs * 2

def test_clear_session_empties_history():
    mock_store = MagicMock()
    saved = ["some_string"]
    mock_store.get.side_effect = lambda k: saved[-1] if saved else None
    mock_store.set.side_effect = lambda k, v: saved.append(v)
    mgr = SessionManager(store=mock_store)
    mgr.clear("sid")
    assert saved[-1] == "[]"

def test_clear_returns_true_when_existed():
    mock_store = MagicMock()
    mock_store.get.return_value = '[{"role": "user", "content": "hi"}]'
    mgr = SessionManager(store=mock_store)
    assert mgr.clear("sid") is True

def test_clear_returns_false_when_not_existed():
    mgr = make_manager()
    assert mgr.clear("sid") is False

def test_build_enriched_query_empty_history_returns_query():
    assert build_enriched_query("hello", []) == "hello"

def test_build_enriched_query_with_history_prepends_context():
    history = [
        ChatMessage("user", "Show me laptops"),
        ChatMessage("assistant", "Here are 5 laptops..."),
    ]
    result = build_enriched_query("Which is cheapest?", history)
    assert "[CONVERSATION HISTORY]" in result
    assert "user: Show me laptops" in result
    assert "[CURRENT QUERY]" in result
    assert "user: Which is cheapest?" in result

def test_get_history_handles_corrupt_json_gracefully():
    mock_store = MagicMock()
    mock_store.get.return_value = "{invalid json}"
    mgr = SessionManager(store=mock_store)
    assert mgr.get_history("sid") == []

def test_append_multiple_turns_ordering_correct():
    mock_store = MagicMock()
    saved = []
    mock_store.get.side_effect = lambda k: saved[-1] if saved else None
    mock_store.set.side_effect = lambda k, v: saved.append(v)
    mgr = SessionManager(store=mock_store)
    mgr.append_turn("sid", "1", "2")
    mgr.append_turn("sid", "3", "4")
    import json
    final = json.loads(saved[-1])
    assert [m["content"] for m in final] == ["1", "2", "3", "4"]

def test_session_ttl_refreshed_on_append():
    mock_store = MagicMock()
    mock_store.get.return_value = None
    mgr = SessionManager(store=mock_store)
    mgr.append_turn("sid", "u", "a")
    mock_store.set.assert_called_once()
