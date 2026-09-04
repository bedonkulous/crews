"""Crew CRUD API endpoints."""

from __future__ import annotations

import shutil

from flask import Blueprint, jsonify, request

from core.agent_factory import ROLES
from core.config_store import ConfigStore
from core.crew_factory import CrewFactory
from core.exceptions import CrewAlreadyExistsError, CrewNotFoundError
from core.models import AgentConfig, CrewConfig

crews_bp = Blueprint("crews", __name__)

_store = ConfigStore()
_factory = CrewFactory()


@crews_bp.route("/crews", methods=["GET"])
def list_crews():
    crews = _factory.load_all()
    return jsonify([c.to_dict() for c in crews])


@crews_bp.route("/crews", methods=["POST"])
def create_crew():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    model = body.get("model", "gpt-4o") or "gpt-4o"
    overrides: dict = {}
    if model != "gpt-4o":
        overrides = {role: {"model": model} for role in ROLES}

    try:
        config = _factory.create(name, overrides)
    except CrewAlreadyExistsError as exc:
        return jsonify({"error": str(exc)}), 409
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(config.to_dict()), 201


@crews_bp.route("/crews/<name>", methods=["GET"])
def get_crew(name: str):
    try:
        config = _factory.load(name)
    except CrewNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(config.to_dict())


@crews_bp.route("/crews/<name>", methods=["PUT"])
def update_crew(name: str):
    """Update the agents list for an existing crew."""
    try:
        config = _store.read(name)
    except CrewNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404

    body = request.get_json(silent=True) or {}
    agents_data = body.get("agents")
    if not isinstance(agents_data, list):
        return jsonify({"error": "'agents' must be a list"}), 400

    if len(agents_data) != len(ROLES):
        return jsonify({"error": f"expected {len(ROLES)} agents, got {len(agents_data)}"}), 400

    try:
        new_agents = []
        for a in agents_data:
            if a.get("role") not in ROLES:
                return jsonify({"error": f"invalid role: {a.get('role')!r}"}), 400
            new_agents.append(AgentConfig(
                role=a["role"],
                goal=str(a.get("goal", "")),
                backstory=str(a.get("backstory", "")),
                model=str(a.get("model", "gpt-4o")),
                allow_delegation=bool(a.get("allow_delegation", False)),
            ))
    except (KeyError, TypeError) as exc:
        return jsonify({"error": f"invalid agent data: {exc}"}), 400

    updated = CrewConfig(
        name=config.name,
        slack_channel_id=config.slack_channel_id,
        slack_channel_name=config.slack_channel_name,
        project_path=config.project_path,
        agents=new_agents,
        created_at=config.created_at,
    )
    _store.write(updated)
    return jsonify(updated.to_dict())


@crews_bp.route("/crews/<name>", methods=["DELETE"])
def delete_crew(name: str):
    crew_dir = _store.root_dir / name
    if not crew_dir.exists():
        return jsonify({"error": f"No crew named '{name}'"}), 404
    shutil.rmtree(crew_dir)
    return "", 204
