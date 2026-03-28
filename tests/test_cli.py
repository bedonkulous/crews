"""Unit tests for cli/main.py using typer.testing.CliRunner."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli.main import app
from core.exceptions import CrewAlreadyExistsError, CrewNotFoundError
from core.models import AgentConfig, CrewConfig

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_crew_config(name: str = "alpha") -> CrewConfig:
    agent = AgentConfig(
        role="dev_manager",
        goal="Orchestrate",
        backstory="Experienced manager",
        model="gpt-4o",
        allow_delegation=True,
    )
    return CrewConfig(
        name=name,
        slack_channel_id="C123",
        slack_channel_name=name,
        project_path=f"crew/{name}",
        agents=[agent],
        created_at="2024-01-01T00:00:00Z",
    )


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------


def test_help_exits_zero():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_crew_help_exits_zero():
    result = runner.invoke(app, ["crew", "--help"])
    assert result.exit_code == 0


def test_env_help_exits_zero():
    result = runner.invoke(app, ["env", "--help"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# crew create
# ---------------------------------------------------------------------------


def test_crew_create_success():
    config = _make_crew_config("alpha")
    with (
        patch("cli.main.ENVManager") as MockENV,
        patch("cli.main.CrewFactory") as MockFactory,
    ):
        MockENV.return_value.validate_required.return_value = None
        MockFactory.return_value.create.return_value = config

        result = runner.invoke(app, ["crew", "create", "alpha"])

    assert result.exit_code == 0, result.output
    assert "alpha" in result.output


def test_crew_create_missing_env_exits_1():
    from core.exceptions import MissingEnvVarError

    with patch("cli.main.ENVManager") as MockENV:
        MockENV.return_value.validate_required.side_effect = MissingEnvVarError(
            "Missing required environment variable(s): OPENAI_API_KEY"
        )
        result = runner.invoke(app, ["crew", "create", "alpha"])

    assert result.exit_code == 1


def test_crew_create_duplicate_exits_1():
    with (
        patch("cli.main.ENVManager") as MockENV,
        patch("cli.main.CrewFactory") as MockFactory,
    ):
        MockENV.return_value.validate_required.return_value = None
        MockFactory.return_value.create.side_effect = CrewAlreadyExistsError("already exists")

        result = runner.invoke(app, ["crew", "create", "alpha"])

    assert result.exit_code == 1
    assert "Error" in result.output


# ---------------------------------------------------------------------------
# crew list
# ---------------------------------------------------------------------------


def test_crew_list_with_crews():
    configs = [_make_crew_config("alpha"), _make_crew_config("beta")]
    with patch("cli.main.CrewFactory") as MockFactory:
        MockFactory.return_value.load_all.return_value = configs
        result = runner.invoke(app, ["crew", "list"])

    assert result.exit_code == 0, result.output
    assert "alpha" in result.output
    assert "beta" in result.output


def test_crew_list_empty():
    with patch("cli.main.CrewFactory") as MockFactory:
        MockFactory.return_value.load_all.return_value = []
        result = runner.invoke(app, ["crew", "list"])

    assert result.exit_code == 0
    assert "No crews found" in result.output


# ---------------------------------------------------------------------------
# crew show
# ---------------------------------------------------------------------------


def test_crew_show_success():
    config = _make_crew_config("alpha")
    with patch("cli.main.CrewFactory") as MockFactory:
        MockFactory.return_value.load.return_value = config
        result = runner.invoke(app, ["crew", "show", "alpha"])

    assert result.exit_code == 0, result.output
    assert "alpha" in result.output


def test_crew_show_not_found():
    with patch("cli.main.CrewFactory") as MockFactory:
        MockFactory.return_value.load.side_effect = CrewNotFoundError("not found")
        result = runner.invoke(app, ["crew", "show", "missing"])

    assert result.exit_code == 1
    assert "Error" in result.output


# ---------------------------------------------------------------------------
# env set
# ---------------------------------------------------------------------------


def test_env_set():
    with patch("cli.main.ENVManager") as MockENV:
        MockENV.return_value.set.return_value = None
        result = runner.invoke(app, ["env", "set", "MY_KEY", "my_value"])

    assert result.exit_code == 0, result.output
    MockENV.return_value.set.assert_called_once_with("MY_KEY", "my_value")


# ---------------------------------------------------------------------------
# env get
# ---------------------------------------------------------------------------


def test_env_get_existing_key():
    with patch("cli.main.ENVManager") as MockENV:
        MockENV.return_value.get.return_value = "secret123"
        result = runner.invoke(app, ["env", "get", "MY_KEY"])

    assert result.exit_code == 0, result.output
    assert "secret123" in result.output


def test_env_get_missing_key_exits_1():
    with patch("cli.main.ENVManager") as MockENV:
        MockENV.return_value.get.return_value = None
        result = runner.invoke(app, ["env", "get", "MISSING"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# env list
# ---------------------------------------------------------------------------


def test_env_list_keys():
    with patch("cli.main.ENVManager") as MockENV:
        MockENV.return_value.list_keys.return_value = ["KEY_A", "KEY_B"]
        result = runner.invoke(app, ["env", "list"])

    assert result.exit_code == 0, result.output
    assert "KEY_A" in result.output
    assert "KEY_B" in result.output


def test_env_list_empty():
    with patch("cli.main.ENVManager") as MockENV:
        MockENV.return_value.list_keys.return_value = []
        result = runner.invoke(app, ["env", "list"])

    assert result.exit_code == 0
    assert "No environment variables" in result.output


# ---------------------------------------------------------------------------
# env delete
# ---------------------------------------------------------------------------


def test_env_delete():
    with patch("cli.main.ENVManager") as MockENV:
        MockENV.return_value.delete.return_value = None
        result = runner.invoke(app, ["env", "delete", "MY_KEY"])

    assert result.exit_code == 0, result.output
    MockENV.return_value.delete.assert_called_once_with("MY_KEY")
