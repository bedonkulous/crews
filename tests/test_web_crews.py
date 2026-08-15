"""Tests for web/api/crews.py using Flask test client."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from core.agent_factory import ROLES
from core.exceptions import CrewAlreadyExistsError, CrewNotFoundError
from core.models import AgentConfig, CrewConfig
from web.app import create_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent(role: str) -> AgentConfig:
    return AgentConfig(
        role=role,
        goal="Write code",
        backstory="Senior dev",
        model="gpt-4o",
        allow_delegation=False,
    )


def _make_crew(name: str = "alpha") -> CrewConfig:
    return CrewConfig(
        name=name,
        slack_channel_id="C123",
        slack_channel_name=name,
        project_path=f"crew/{name}",
        agents=[_make_agent(r) for r in ROLES],
        created_at="2024-01-01T00:00:00Z",
    )


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# GET /api/crews
# ---------------------------------------------------------------------------

def test_list_crews_empty(client):
    with patch("web.api.crews._factory") as mock_factory:
        mock_factory.load_all.return_value = []
        r = client.get("/api/crews")
    assert r.status_code == 200
    assert r.get_json() == []


def test_list_crews_returns_all(client):
    configs = [_make_crew("alpha"), _make_crew("beta")]
    with patch("web.api.crews._factory") as mock_factory:
        mock_factory.load_all.return_value = configs
        r = client.get("/api/crews")
    data = r.get_json()
    assert r.status_code == 200
    assert len(data) == 2
    assert data[0]["name"] == "alpha"
    assert data[1]["name"] == "beta"


# ---------------------------------------------------------------------------
# POST /api/crews
# ---------------------------------------------------------------------------

def test_create_crew_success(client):
    config = _make_crew("mynewcrew")
    with patch("web.api.crews._factory") as mock_factory:
        mock_factory.create.return_value = config
        r = client.post(
            "/api/crews",
            data=json.dumps({"name": "mynewcrew"}),
            content_type="application/json",
        )
    assert r.status_code == 201
    assert r.get_json()["name"] == "mynewcrew"


def test_create_crew_missing_name_returns_400(client):
    r = client.post("/api/crews", data=json.dumps({}), content_type="application/json")
    assert r.status_code == 400
    assert "name" in r.get_json()["error"]


def test_create_crew_blank_name_returns_400(client):
    r = client.post("/api/crews", data=json.dumps({"name": "  "}), content_type="application/json")
    assert r.status_code == 400


def test_create_crew_duplicate_returns_409(client):
    with patch("web.api.crews._factory") as mock_factory:
        mock_factory.create.side_effect = CrewAlreadyExistsError("already exists")
        r = client.post(
            "/api/crews",
            data=json.dumps({"name": "alpha"}),
            content_type="application/json",
        )
    assert r.status_code == 409
    assert "already exists" in r.get_json()["error"]


# ---------------------------------------------------------------------------
# GET /api/crews/<name>
# ---------------------------------------------------------------------------

def test_get_crew_found(client):
    config = _make_crew("alpha")
    with patch("web.api.crews._factory") as mock_factory:
        mock_factory.load.return_value = config
        r = client.get("/api/crews/alpha")
    assert r.status_code == 200
    assert r.get_json()["name"] == "alpha"
    assert len(r.get_json()["agents"]) == len(ROLES)


def test_get_crew_not_found_returns_404(client):
    with patch("web.api.crews._factory") as mock_factory:
        mock_factory.load.side_effect = CrewNotFoundError("not found")
        r = client.get("/api/crews/missing")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/crews/<name>
# ---------------------------------------------------------------------------

def _full_agents_payload():
    return [
        {
            "role": r,
            "goal": "Updated goal",
            "backstory": "Updated backstory",
            "model": "gpt-4o",
            "allow_delegation": False,
        }
        for r in ROLES
    ]


def test_update_crew_success(client):
    config = _make_crew("alpha")
    with patch("web.api.crews._store") as mock_store:
        mock_store.read.return_value = config
        mock_store.write.return_value = None
        r = client.put(
            "/api/crews/alpha",
            data=json.dumps({"agents": _full_agents_payload()}),
            content_type="application/json",
        )
    assert r.status_code == 200
    data = r.get_json()
    assert data["agents"][0]["goal"] == "Updated goal"
    mock_store.write.assert_called_once()


def test_update_crew_not_found_returns_404(client):
    with patch("web.api.crews._store") as mock_store:
        mock_store.read.side_effect = CrewNotFoundError("not found")
        r = client.put(
            "/api/crews/missing",
            data=json.dumps({"agents": _full_agents_payload()}),
            content_type="application/json",
        )
    assert r.status_code == 404


def test_update_crew_agents_not_list_returns_400(client):
    config = _make_crew("alpha")
    with patch("web.api.crews._store") as mock_store:
        mock_store.read.return_value = config
        r = client.put(
            "/api/crews/alpha",
            data=json.dumps({"agents": "not-a-list"}),
            content_type="application/json",
        )
    assert r.status_code == 400


def test_update_crew_wrong_agent_count_returns_400(client):
    config = _make_crew("alpha")
    with patch("web.api.crews._store") as mock_store:
        mock_store.read.return_value = config
        r = client.put(
            "/api/crews/alpha",
            data=json.dumps({"agents": [_full_agents_payload()[0]]}),
            content_type="application/json",
        )
    assert r.status_code == 400


def test_update_crew_invalid_role_returns_400(client):
    config = _make_crew("alpha")
    bad_agents = _full_agents_payload()
    bad_agents[0]["role"] = "unknown_role"
    with patch("web.api.crews._store") as mock_store:
        mock_store.read.return_value = config
        r = client.put(
            "/api/crews/alpha",
            data=json.dumps({"agents": bad_agents}),
            content_type="application/json",
        )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/crews/<name>
# ---------------------------------------------------------------------------

def test_delete_crew_success(client, tmp_path):
    crew_dir = tmp_path / "alpha"
    crew_dir.mkdir()
    with patch("web.api.crews._store") as mock_store:
        mock_store.root_dir = tmp_path
        r = client.delete("/api/crews/alpha")
    assert r.status_code == 204
    assert not crew_dir.exists()


def test_delete_crew_not_found_returns_404(client, tmp_path):
    with patch("web.api.crews._store") as mock_store:
        mock_store.root_dir = tmp_path
        r = client.delete("/api/crews/ghost")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# HTML page routes
# ---------------------------------------------------------------------------

def test_dashboard_page_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"crewai-dev-teams" in r.data


def test_crews_route_also_renders_dashboard(client):
    r = client.get("/crews")
    assert r.status_code == 200


def test_crew_create_page_renders(client):
    r = client.get("/crews/new")
    assert r.status_code == 200
    assert b"New Crew" in r.data


def test_crew_detail_page_renders(client):
    r = client.get("/crews/alpha")
    assert r.status_code == 200
    assert b"alpha" in r.data


def test_env_page_renders(client):
    r = client.get("/env")
    assert r.status_code == 200
    assert b"Environment" in r.data
