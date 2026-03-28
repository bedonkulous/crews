"""Unit tests for ENVManager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from core.env_manager import ENVManager, REQUIRED_KEYS
from core.exceptions import MissingEnvVarError


@pytest.fixture()
def env_manager(tmp_path: Path) -> ENVManager:
    """Return an ENVManager backed by a temporary .env file."""
    return ENVManager(env_file=tmp_path / ".env")


# ---------------------------------------------------------------------------
# set / get round-trip
# ---------------------------------------------------------------------------

def test_set_get_round_trip(env_manager: ENVManager) -> None:
    env_manager.set("MY_KEY", "my_value")
    assert env_manager.get("MY_KEY") == "my_value"


def test_get_returns_none_for_missing_key(env_manager: ENVManager) -> None:
    assert env_manager.get("NONEXISTENT") is None


def test_set_overwrites_existing_value(env_manager: ENVManager) -> None:
    env_manager.set("TOKEN", "first")
    env_manager.set("TOKEN", "second")
    assert env_manager.get("TOKEN") == "second"


# ---------------------------------------------------------------------------
# list_keys — no values
# ---------------------------------------------------------------------------

def test_list_keys_returns_only_keys(env_manager: ENVManager) -> None:
    env_manager.set("KEY_A", "value_a")
    env_manager.set("KEY_B", "value_b")
    keys = env_manager.list_keys()
    assert "KEY_A" in keys
    assert "KEY_B" in keys
    # Values must not appear in the key list
    assert "value_a" not in keys
    assert "value_b" not in keys


def test_list_keys_empty_file(env_manager: ENVManager) -> None:
    assert env_manager.list_keys() == []


def test_list_keys_count_matches_entries(env_manager: ENVManager) -> None:
    for i in range(5):
        env_manager.set(f"KEY_{i}", f"val_{i}")
    assert len(env_manager.list_keys()) == 5


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

def test_delete_removes_key(env_manager: ENVManager) -> None:
    env_manager.set("TO_DELETE", "gone")
    env_manager.delete("TO_DELETE")
    assert env_manager.get("TO_DELETE") is None
    assert "TO_DELETE" not in env_manager.list_keys()


def test_delete_nonexistent_key_is_noop(env_manager: ENVManager) -> None:
    # Should not raise
    env_manager.delete("DOES_NOT_EXIST")


def test_delete_does_not_affect_other_keys(env_manager: ENVManager) -> None:
    env_manager.set("KEEP", "safe")
    env_manager.set("REMOVE", "bye")
    env_manager.delete("REMOVE")
    assert env_manager.get("KEEP") == "safe"


# ---------------------------------------------------------------------------
# validate_required
# ---------------------------------------------------------------------------

def test_validate_required_passes_when_all_present(env_manager: ENVManager) -> None:
    env_manager.set("FOO", "1")
    env_manager.set("BAR", "2")
    # Should not raise
    env_manager.validate_required(["FOO", "BAR"])


def test_validate_required_raises_for_missing_key(env_manager: ENVManager) -> None:
    env_manager.set("PRESENT", "yes")
    with pytest.raises(MissingEnvVarError) as exc_info:
        env_manager.validate_required(["PRESENT", "ABSENT"])
    assert "ABSENT" in str(exc_info.value)


def test_validate_required_lists_all_missing_keys(env_manager: ENVManager) -> None:
    with pytest.raises(MissingEnvVarError) as exc_info:
        env_manager.validate_required(["MISSING_A", "MISSING_B", "MISSING_C"])
    error_msg = str(exc_info.value)
    assert "MISSING_A" in error_msg
    assert "MISSING_B" in error_msg
    assert "MISSING_C" in error_msg


def test_validate_required_empty_list_passes(env_manager: ENVManager) -> None:
    # No keys required — should never raise
    env_manager.validate_required([])


# ---------------------------------------------------------------------------
# setup_interactive — mocked prompts
# ---------------------------------------------------------------------------

def test_setup_interactive_writes_all_required_keys(
    env_manager: ENVManager,
) -> None:
    fake_values = {key: f"fake_{key}" for key in REQUIRED_KEYS}

    with patch("core.env_manager.typer.prompt", side_effect=lambda k: fake_values[k]):
        env_manager.setup_interactive()

    for key in REQUIRED_KEYS:
        assert env_manager.get(key) == f"fake_{key}"


def test_setup_interactive_prompts_for_each_required_key(
    env_manager: ENVManager,
) -> None:
    prompted_keys: list[str] = []

    def capture_prompt(key: str) -> str:
        prompted_keys.append(key)
        return "dummy"

    with patch("core.env_manager.typer.prompt", side_effect=capture_prompt):
        env_manager.setup_interactive()

    assert prompted_keys == REQUIRED_KEYS
