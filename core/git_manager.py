"""GitManager: handles git repository initialization and initial scaffolding."""

import subprocess
from pathlib import Path

from core.exceptions import GitNotFoundError

GITIGNORE_CONTENT = """\
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
venv/
.venv/
*.egg-info/
dist/
build/

# Environment
.env

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
"""


class GitManager:
    def _run(self, args: list[str], cwd: Path) -> None:
        """Run a git command, raising GitNotFoundError if git is not installed."""
        try:
            subprocess.run(args, cwd=cwd, check=True, capture_output=True)
        except FileNotFoundError:
            raise GitNotFoundError(
                "git binary not found. Please install git: https://git-scm.com/downloads"
            )

    def init_repo(self, path: Path) -> None:
        """Initialize a git repository at the given path."""
        self._run(["git", "init"], cwd=path)

    def initial_commit(self, path: Path, crew_name: str) -> None:
        """Create .gitignore and README.md, then stage and commit them."""
        gitignore = path / ".gitignore"
        readme = path / "README.md"

        gitignore.write_text(GITIGNORE_CONTENT)
        readme.write_text(f"# {crew_name}\n\nCreated by crewai-dev-teams.\n")

        self._run(["git", "add", ".gitignore", "README.md"], cwd=path)
        self._run(
            ["git", "commit", "-m", "Initial commit", "--allow-empty-message"],
            cwd=path,
        )

    def scaffold_github_actions(self, path: Path, crew_name: str) -> None:
        """Delegate to DeploymentScaffold — kept here for interface completeness."""
        from core.deployment_scaffold import DeploymentScaffold

        DeploymentScaffold().generate(path, crew_name)
