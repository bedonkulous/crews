"""Environment variable management API endpoints."""

from __future__ import annotations

from dotenv import dotenv_values
from flask import Blueprint, jsonify, request

from core.env_manager import ENVManager, REQUIRED_KEYS

env_bp = Blueprint("env", __name__)

_manager = ENVManager()


def _mask(value: str | None) -> str:
    """Return a masked version of a secret value."""
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


@env_bp.route("/env", methods=["GET"])
def list_env():
    """Return all configured keys with masked values, plus required key status."""
    all_values = dotenv_values(_manager.env_file)
    result = []
    configured_keys = set(all_values.keys())
    for key, value in all_values.items():
        result.append({
            "key": key,
            "masked_value": _mask(value),
            "is_required": key in REQUIRED_KEYS,
            "is_set": bool(value),
        })
    # Ensure required keys appear even if not configured yet
    for key in REQUIRED_KEYS:
        if key not in configured_keys:
            result.append({
                "key": key,
                "masked_value": "",
                "is_required": True,
                "is_set": False,
            })
    return jsonify(result)


@env_bp.route("/env/status", methods=["GET"])
def env_status():
    """Return whether all required keys are configured."""
    all_values = dotenv_values(_manager.env_file)
    missing = [k for k in REQUIRED_KEYS if not all_values.get(k)]
    return jsonify({"ok": len(missing) == 0, "missing": missing})


@env_bp.route("/env", methods=["POST"])
def set_env():
    body = request.get_json(silent=True) or {}
    key = (body.get("key") or "").strip()
    value = body.get("value", "")
    if not key:
        return jsonify({"error": "key is required"}), 400
    _manager.set(key, str(value))
    return jsonify({
        "key": key,
        "masked_value": _mask(str(value)),
        "is_set": bool(value),
        "is_required": key in REQUIRED_KEYS,
    })


@env_bp.route("/env/<key>", methods=["DELETE"])
def delete_env(key: str):
    _manager.delete(key)
    return "", 204
