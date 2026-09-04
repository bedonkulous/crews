"""Tests for web/api/env.py using Flask test client."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest

from web.app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# GET /api/env
# ---------------------------------------------------------------------------

def test_list_env_includes_required_keys(client):
    """Required keys appear even when the .env file is empty."""
    with patch("web.api.env.dotenv_values", return_value={}):
        r = client.get("/api/env")
    assert r.status_code == 200
    data = r.get_json()
    keys = [e["key"] for e in data]
    from core.env_manager import REQUIRED_KEYS
    for k in REQUIRED_KEYS:
        assert k in keys


def test_list_env_masks_values(client):
    values = {"SLACK_BOT_TOKEN": "xoxb-0123456789abcdef"}
    with patch("web.api.env.dotenv_values", return_value=values):
        r = client.get("/api/env")
    data = r.get_json()
    entry = next(e for e in data if e["key"] == "SLACK_BOT_TOKEN")
    assert entry["masked_value"] != values["SLACK_BOT_TOKEN"]
    assert "****" in entry["masked_value"]
    assert entry["is_set"] is True


def test_list_env_marks_unset_required_keys(client):
    with patch("web.api.env.dotenv_values", return_value={}):
        r = client.get("/api/env")
    data = r.get_json()
    from core.env_manager import REQUIRED_KEYS
    unset = [e for e in data if e["key"] in REQUIRED_KEYS]
    for e in unset:
        assert e["is_set"] is False
        assert e["is_required"] is True


# ---------------------------------------------------------------------------
# GET /api/env/status
# ---------------------------------------------------------------------------

def test_env_status_ok_when_all_required_set(client):
    from core.env_manager import REQUIRED_KEYS
    all_set = {k: "somevalue" for k in REQUIRED_KEYS}
    with patch("web.api.env.dotenv_values", return_value=all_set):
        r = client.get("/api/env/status")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["missing"] == []


def test_env_status_not_ok_when_keys_missing(client):
    with patch("web.api.env.dotenv_values", return_value={}):
        r = client.get("/api/env/status")
    data = r.get_json()
    assert data["ok"] is False
    assert len(data["missing"]) > 0


# ---------------------------------------------------------------------------
# POST /api/env
# ---------------------------------------------------------------------------

def test_set_env_success(client):
    with patch("web.api.env._manager") as mock_mgr:
        mock_mgr.env_file = ".env"
        mock_mgr.set.return_value = None
        r = client.post(
            "/api/env",
            data=json.dumps({"key": "MY_KEY", "value": "my_secret_value"}),
            content_type="application/json",
        )
    assert r.status_code == 200
    data = r.get_json()
    assert data["key"] == "MY_KEY"
    assert data["is_set"] is True
    assert "my_secret_value" not in data["masked_value"]
    mock_mgr.set.assert_called_once_with("MY_KEY", "my_secret_value")


def test_set_env_missing_key_returns_400(client):
    r = client.post(
        "/api/env",
        data=json.dumps({"value": "something"}),
        content_type="application/json",
    )
    assert r.status_code == 400
    assert "key" in r.get_json()["error"]


def test_set_env_blank_key_returns_400(client):
    r = client.post(
        "/api/env",
        data=json.dumps({"key": "   ", "value": "v"}),
        content_type="application/json",
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/env/<key>
# ---------------------------------------------------------------------------

def test_delete_env_success(client):
    with patch("web.api.env._manager") as mock_mgr:
        mock_mgr.delete.return_value = None
        r = client.delete("/api/env/MY_KEY")
    assert r.status_code == 204
    mock_mgr.delete.assert_called_once_with("MY_KEY")


def test_delete_env_nonexistent_key_still_204(client):
    """ENVManager.delete is a no-op for absent keys; we expect 204 regardless."""
    with patch("web.api.env._manager") as mock_mgr:
        mock_mgr.delete.return_value = None
        r = client.delete("/api/env/DOES_NOT_EXIST")
    assert r.status_code == 204


# ---------------------------------------------------------------------------
# Masking helper
# ---------------------------------------------------------------------------

def test_mask_short_value():
    from web.api.env import _mask
    assert _mask("abc") == "***"


def test_mask_long_value_hides_middle():
    from web.api.env import _mask
    result = _mask("sk-abcdefghij1234")
    assert result.startswith("sk-a")
    assert result.endswith("1234")
    assert "****" in result


def test_mask_empty():
    from web.api.env import _mask
    assert _mask("") == ""
    assert _mask(None) == ""
