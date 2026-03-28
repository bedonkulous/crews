"""Unit tests for ConfigStore."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from core.config_store import ConfigStore
from core.exceptions import CrewNotFoundError
from core.models import AgentConfig, CrewConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_agent(role: str = "developer") -> AgentConfig:
    return AgentConfig(
        role=role,
        goal="Write clean code",
        backstory="Experienced engineer",
        model="gpt-4o",
        allow_delegation=False,
    )


def make_crew(name: str = "alpha") -> CrewConfig:
    agents = [
        make_agent("dev_manager"),
        make_agent("developer"),
        make_agent("product_manager"),
        make_agent("architect"),
        make_agent("security_engineer"),
        make_agent("devops"),
    ]
    return CrewConfig(
        name=name,
        slack_channel_id="C12345",
        slack_channel_name=name,
        project_path=name,
        agents=agents,
        created_at="2024-01-01T00:00:00Z",
    )


@pytest.fixture()
def store(tmp_path: Path) -> ConfigStore:
    """Return a ConfigStore rooted at a temporary directory."""
    return ConfigStore(root_dir=tmp_path)


# ---------------------------------------------------------------------------
# write / read round-trip
# ---------------------------------------------------------------------------

def test_write_creates_crew_yaml(store: ConfigStore, tmp_path: Path) -> None:
    crew = make_crew("alpha")
    store.write(crew)
    assert (tmp_path / "alpha" / "crew.yaml").exists()


def test_read_returns_equivalent_config(store: ConfigStore) -> None:
    crew = make_crew("alpha")
    store.write(crew)
    loaded = store.read("alpha")
    assert loaded == crew


def test_write_is_atomic_no_partial_file(store: ConfigStore, tmp_path: Path) -> None:
    """After write(), only crew.yaml should exist — no leftover .tmp files."""
    crew = make_crew("beta")
    store.write(crew)
    crew_dir = tmp_path / "beta"
    tmp_files = list(crew_dir.glob("*.tmp"))
    assert tmp_files == [], f"Unexpected temp files: {tmp_files}"


def test_write_overwrites_existing(store: ConfigStore) -> None:
    crew = make_crew("gamma")
    store.write(crew)

    updated = CrewConfig(
        name="gamma",
        slack_channel_id="C99999",
        slack_channel_name="gamma-updated",
        project_path="gamma",
        agents=crew.agents,
        created_at="2025-06-01T00:00:00Z",
    )
    store.write(updated)

    loaded = store.read("gamma")
    assert loaded.slack_channel_id == "C99999"
    assert loaded.slack_channel_name == "gamma-updated"


# ---------------------------------------------------------------------------
# read — error cases
# ---------------------------------------------------------------------------

def test_read_raises_crew_not_found_for_missing_crew(store: ConfigStore) -> None:
    with pytest.raises(CrewNotFoundError):
        store.read("nonexistent")


def test_read_raises_crew_not_found_when_dir_exists_but_no_yaml(
    store: ConfigStore, tmp_path: Path
) -> None:
    (tmp_path / "orphan").mkdir()
    with pytest.raises(CrewNotFoundError):
        store.read("orphan")


# ---------------------------------------------------------------------------
# read_all
# ---------------------------------------------------------------------------

def test_read_all_returns_all_valid_crews(store: ConfigStore) -> None:
    for name in ("alpha", "beta", "gamma"):
        store.write(make_crew(name))

    all_crews = store.read_all()
    assert len(all_crews) == 3
    names = {c.name for c in all_crews}
    assert names == {"alpha", "beta", "gamma"}


def test_read_all_empty_root_returns_empty_list(store: ConfigStore) -> None:
    assert store.read_all() == []


def test_read_all_nonexistent_root_returns_empty_list(tmp_path: Path) -> None:
    store = ConfigStore(root_dir=tmp_path / "does_not_exist")
    assert store.read_all() == []


def test_read_all_skips_malformed_yaml(
    store: ConfigStore, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # Write one valid crew
    store.write(make_crew("good"))

    # Write a malformed crew.yaml manually
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    (bad_dir / "crew.yaml").write_text(":::not valid yaml:::", encoding="utf-8")

    import logging
    with caplog.at_level(logging.WARNING, logger="core.config_store"):
        all_crews = store.read_all()

    assert len(all_crews) == 1
    assert all_crews[0].name == "good"
    assert any("bad" in record.message for record in caplog.records)


def test_read_all_skips_yaml_missing_required_fields(
    store: ConfigStore, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # Valid YAML but missing required fields for CrewConfig
    incomplete_dir = tmp_path / "incomplete"
    incomplete_dir.mkdir()
    (incomplete_dir / "crew.yaml").write_text(
        textwrap.dedent("""\
            name: incomplete
            # missing all other required fields
        """),
        encoding="utf-8",
    )

    import logging
    with caplog.at_level(logging.WARNING, logger="core.config_store"):
        all_crews = store.read_all()

    assert all_crews == []


def test_read_all_ignores_non_directory_entries(
    store: ConfigStore, tmp_path: Path
) -> None:
    store.write(make_crew("real"))
    # Place a stray file at the root level — should be ignored
    (tmp_path / "stray_file.txt").write_text("hello", encoding="utf-8")

    all_crews = store.read_all()
    assert len(all_crews) == 1


# ---------------------------------------------------------------------------
# exists
# ---------------------------------------------------------------------------

def test_exists_returns_true_after_write(store: ConfigStore) -> None:
    store.write(make_crew("alpha"))
    assert store.exists("alpha") is True


def test_exists_returns_false_for_missing_crew(store: ConfigStore) -> None:
    assert store.exists("nonexistent") is False


def test_exists_returns_false_when_dir_exists_but_no_yaml(
    store: ConfigStore, tmp_path: Path
) -> None:
    (tmp_path / "empty_crew").mkdir()
    assert store.exists("empty_crew") is False
