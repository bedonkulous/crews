"""Unit tests for CrewFactory."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.agent_factory import ROLES
from core.config_store import ConfigStore
from core.crew_factory import CrewFactory
from core.exceptions import CrewAlreadyExistsError, CrewNotFoundError
from core.models import AgentConfig, CrewConfig


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_mock_slack(channel_id: str = "C_TEST_123") -> MagicMock:
    """Return a mock SlackIntegration that returns a fixed channel_id."""
    mock = MagicMock()
    mock.create_channel.return_value = channel_id
    return mock


def _make_mock_git() -> MagicMock:
    """Return a mock GitManager with no-op methods."""
    mock = MagicMock()
    mock.init_repo.return_value = None
    mock.initial_commit.return_value = None
    return mock


@pytest.fixture()
def factory(tmp_path: Path) -> CrewFactory:
    """Return a CrewFactory wired to a temp directory with mocked Slack and git."""
    return CrewFactory(
        root_dir=tmp_path,
        slack=_make_mock_slack(),
        git_manager=_make_mock_git(),
    )


# ---------------------------------------------------------------------------
# Successful crew creation
# ---------------------------------------------------------------------------

class TestCrewCreation:
    def test_create_returns_crew_config(self, factory: CrewFactory) -> None:
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            result = factory.create("alpha")
        assert isinstance(result, CrewConfig)

    def test_create_sets_correct_name(self, factory: CrewFactory) -> None:
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            result = factory.create("my-crew")
        assert result.name == "my-crew"

    def test_create_sets_slack_channel_id(self, tmp_path: Path) -> None:
        mock_slack = _make_mock_slack(channel_id="C_EXPECTED")
        factory = CrewFactory(root_dir=tmp_path, slack=mock_slack, git_manager=_make_mock_git())
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            result = factory.create("beta")
        assert result.slack_channel_id == "C_EXPECTED"

    def test_create_sets_slack_channel_name_to_crew_name(self, factory: CrewFactory) -> None:
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            result = factory.create("gamma")
        assert result.slack_channel_name == "gamma"

    def test_create_agents_list_has_six_entries(self, factory: CrewFactory) -> None:
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            result = factory.create("delta")
        assert len(result.agents) == 6

    def test_create_agents_cover_all_roles(self, factory: CrewFactory) -> None:
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            result = factory.create("epsilon")
        roles = {a.role for a in result.agents}
        assert roles == set(ROLES)

    def test_create_sets_created_at_with_z_suffix(self, factory: CrewFactory) -> None:
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            result = factory.create("zeta")
        assert result.created_at.endswith("Z")

    def test_create_calls_slack_create_channel(self, tmp_path: Path) -> None:
        mock_slack = _make_mock_slack()
        factory = CrewFactory(root_dir=tmp_path, slack=mock_slack, git_manager=_make_mock_git())
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            factory.create("eta")
        mock_slack.create_channel.assert_called_once_with("eta")

    def test_create_calls_git_init_repo(self, tmp_path: Path) -> None:
        mock_git = _make_mock_git()
        factory = CrewFactory(root_dir=tmp_path, slack=_make_mock_slack(), git_manager=mock_git)
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            factory.create("theta")
        mock_git.init_repo.assert_called_once()

    def test_create_calls_git_initial_commit(self, tmp_path: Path) -> None:
        mock_git = _make_mock_git()
        factory = CrewFactory(root_dir=tmp_path, slack=_make_mock_slack(), git_manager=mock_git)
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            factory.create("iota")
        mock_git.initial_commit.assert_called_once()


# ---------------------------------------------------------------------------
# CrewAlreadyExistsError on duplicate name
# ---------------------------------------------------------------------------

class TestDuplicateCrewName:
    def test_raises_crew_already_exists_error_on_duplicate(self, factory: CrewFactory) -> None:
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            factory.create("duplicate")

        with pytest.raises(CrewAlreadyExistsError):
            with patch("core.crew_factory.AgentFactory") as MockAF:
                MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
                MockAF.return_value.default_config.side_effect = _default_config_side_effect()
                factory.create("duplicate")

    def test_error_message_contains_crew_name(self, factory: CrewFactory) -> None:
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            factory.create("my-team")

        with pytest.raises(CrewAlreadyExistsError, match="my-team"):
            with patch("core.crew_factory.AgentFactory") as MockAF:
                MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
                MockAF.return_value.default_config.side_effect = _default_config_side_effect()
                factory.create("my-team")

    def test_existing_config_unchanged_after_duplicate_attempt(
        self, factory: CrewFactory
    ) -> None:
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            original = factory.create("stable")

        with pytest.raises(CrewAlreadyExistsError):
            with patch("core.crew_factory.AgentFactory") as MockAF:
                MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
                MockAF.return_value.default_config.side_effect = _default_config_side_effect()
                factory.create("stable")

        # Config on disk should still match the original
        loaded = factory.load("stable")
        assert loaded.slack_channel_id == original.slack_channel_id
        assert loaded.created_at == original.created_at


# ---------------------------------------------------------------------------
# Project directory creation
# ---------------------------------------------------------------------------

class TestProjectDirectoryCreation:
    def test_project_dir_created_under_root(self, tmp_path: Path) -> None:
        factory = CrewFactory(
            root_dir=tmp_path, slack=_make_mock_slack(), git_manager=_make_mock_git()
        )
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            factory.create("kappa")
        assert (tmp_path / "kappa").is_dir()

    def test_crew_root_created_if_missing(self, tmp_path: Path) -> None:
        root = tmp_path / "nonexistent_root"
        factory = CrewFactory(
            root_dir=root, slack=_make_mock_slack(), git_manager=_make_mock_git()
        )
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            factory.create("lambda")
        assert root.is_dir()
        assert (root / "lambda").is_dir()

    def test_project_path_in_config_contains_crew_name(self, tmp_path: Path) -> None:
        factory = CrewFactory(
            root_dir=tmp_path, slack=_make_mock_slack(), git_manager=_make_mock_git()
        )
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            result = factory.create("mu")
        assert "mu" in result.project_path


# ---------------------------------------------------------------------------
# ConfigStore.write called with correct CrewConfig
# ---------------------------------------------------------------------------

class TestConfigStoreWrite:
    def test_config_store_write_called_with_crew_config(self, tmp_path: Path) -> None:
        factory = CrewFactory(
            root_dir=tmp_path, slack=_make_mock_slack(), git_manager=_make_mock_git()
        )
        with patch.object(factory._config_store, "write", wraps=factory._config_store.write) as mock_write:
            with patch("core.crew_factory.AgentFactory") as MockAF:
                MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
                MockAF.return_value.default_config.side_effect = _default_config_side_effect()
                result = factory.create("nu")
            mock_write.assert_called_once()
            written_config = mock_write.call_args[0][0]
            assert isinstance(written_config, CrewConfig)
            assert written_config.name == "nu"

    def test_persisted_config_readable_after_create(self, tmp_path: Path) -> None:
        factory = CrewFactory(
            root_dir=tmp_path, slack=_make_mock_slack(), git_manager=_make_mock_git()
        )
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            created = factory.create("xi")
        loaded = factory.load("xi")
        assert loaded.name == created.name
        assert loaded.slack_channel_id == created.slack_channel_id


# ---------------------------------------------------------------------------
# load() and load_all() delegation
# ---------------------------------------------------------------------------

class TestLoadDelegation:
    def test_load_delegates_to_config_store_read(self, tmp_path: Path) -> None:
        factory = CrewFactory(
            root_dir=tmp_path, slack=_make_mock_slack(), git_manager=_make_mock_git()
        )
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            factory.create("omicron")

        with patch.object(factory._config_store, "read", wraps=factory._config_store.read) as mock_read:
            factory.load("omicron")
            mock_read.assert_called_once_with("omicron")

    def test_load_raises_crew_not_found_for_missing_crew(self, factory: CrewFactory) -> None:
        from core.exceptions import CrewNotFoundError
        with pytest.raises(CrewNotFoundError):
            factory.load("nonexistent")

    def test_load_all_delegates_to_config_store_read_all(self, tmp_path: Path) -> None:
        factory = CrewFactory(
            root_dir=tmp_path, slack=_make_mock_slack(), git_manager=_make_mock_git()
        )
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            factory.create("pi")
            factory._slack = _make_mock_slack()  # reset for second call
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            factory.create("rho")

        with patch.object(factory._config_store, "read_all", wraps=factory._config_store.read_all) as mock_read_all:
            results = factory.load_all()
            mock_read_all.assert_called_once()
        assert len(results) == 2

    def test_load_all_returns_empty_list_when_no_crews(self, factory: CrewFactory) -> None:
        results = factory.load_all()
        assert results == []

    def test_load_all_returns_list_of_crew_configs(self, tmp_path: Path) -> None:
        factory = CrewFactory(
            root_dir=tmp_path, slack=_make_mock_slack(), git_manager=_make_mock_git()
        )
        with patch("core.crew_factory.AgentFactory") as MockAF:
            MockAF.return_value.build_agents.return_value = [MagicMock()] * 6
            MockAF.return_value.default_config.side_effect = _default_config_side_effect()
            factory.create("sigma")

        results = factory.load_all()
        assert all(isinstance(c, CrewConfig) for c in results)


# ---------------------------------------------------------------------------
# Helper: side_effect factory for AgentFactory.default_config
# ---------------------------------------------------------------------------

def _default_config_side_effect():
    """Return a side_effect callable that produces real AgentConfig objects."""
    from core.agent_factory import AgentFactory as _AF
    real_factory = _AF()

    def _side_effect(role: str) -> AgentConfig:
        return real_factory.default_config(role)

    return _side_effect
