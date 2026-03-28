"""CrewFactory: orchestrates crew creation and loading."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from core.agent_factory import AgentFactory, ROLES
from core.config_store import ConfigStore
from core.deployment_scaffold import DeploymentScaffold
from core.exceptions import CrewAlreadyExistsError
from core.git_manager import GitManager
from core.models import AgentConfig, CrewConfig
from integrations.slack import SlackIntegration


class CrewFactory:
    """Orchestrates crew creation, loading, and persistence.

    Args:
        root_dir: Root directory for all crew project directories. Passed to
                  ConfigStore. Defaults to ``Path("crew")``.
        slack: Optional SlackIntegration instance for dependency injection
               (useful in tests). If None, a new instance is created on demand.
        git_manager: Optional GitManager instance for dependency injection.
                     If None, a new instance is created on demand.
    """

    def __init__(
        self,
        root_dir: Path = Path("crew"),
        slack: Optional[SlackIntegration] = None,
        git_manager: Optional[GitManager] = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self._config_store = ConfigStore(root_dir=self.root_dir)
        self._slack = slack
        self._git_manager = git_manager

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_slack(self) -> SlackIntegration:
        if self._slack is None:
            self._slack = SlackIntegration()
        return self._slack

    def _get_git_manager(self) -> GitManager:
        if self._git_manager is None:
            self._git_manager = GitManager()
        return self._git_manager

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(self, name: str, overrides: dict | None = None) -> CrewConfig:
        """Create a new crew with the given name.

        Steps:
        1. Check for duplicate — raise CrewAlreadyExistsError if exists.
        2. Create crew/<name>/ directory (and crew/ root if missing).
        3. Build six crewAI Agent instances via AgentFactory.
        4. Create a Slack channel via SlackIntegration.
        5. Initialize a git repo and make an initial commit via GitManager.
        6. Generate deployment scaffold via DeploymentScaffold.
        7. Build CrewConfig and persist via ConfigStore.
        8. Return the CrewConfig.

        Args:
            name: Unique crew name.
            overrides: Optional dict of per-role config overrides.

        Returns:
            The newly created CrewConfig.

        Raises:
            CrewAlreadyExistsError: If a crew with this name already exists.
        """
        if overrides is None:
            overrides = {}

        # Step 1: duplicate check
        if self._config_store.exists(name):
            raise CrewAlreadyExistsError(
                f"A crew named '{name}' already exists. Use a different name."
            )

        # Step 2: create project directory (crew/ root created automatically via parents=True)
        project_path = self.root_dir / name
        project_path.mkdir(parents=True, exist_ok=True)

        # Step 3: build agents (crewAI Agent instances) and collect AgentConfigs
        agent_factory = AgentFactory()
        agent_factory.build_agents(overrides)  # validates + exercises crewAI Agent construction

        agent_configs: list[AgentConfig] = []
        for role in ROLES:
            config = agent_factory.default_config(role)
            role_overrides = overrides.get(role, {})
            for key, value in role_overrides.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            agent_configs.append(config)

        # Step 4: create Slack channel
        slack = self._get_slack()
        channel_id = slack.create_channel(name)

        # Step 5: init git repo and initial commit
        git = self._get_git_manager()
        git.init_repo(project_path)
        git.initial_commit(project_path, name)

        # Step 6: generate deployment scaffold
        DeploymentScaffold().generate(project_path, name)

        # Step 7: build CrewConfig and persist
        crew_config = CrewConfig(
            name=name,
            slack_channel_id=channel_id,
            slack_channel_name=name,
            project_path=str(project_path),
            agents=agent_configs,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        self._config_store.write(crew_config)

        # Step 8: return
        return crew_config

    def load(self, name: str) -> CrewConfig:
        """Load and return the CrewConfig for the named crew.

        Delegates to ConfigStore.read().

        Raises:
            CrewNotFoundError: If no crew with this name exists.
        """
        return self._config_store.read(name)

    def load_all(self) -> list[CrewConfig]:
        """Load and return all persisted CrewConfig objects.

        Delegates to ConfigStore.read_all().
        """
        return self._config_store.read_all()
