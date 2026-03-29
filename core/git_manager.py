"""GitManager: handles git repository initialization and initial scaffolding."""

import subprocess
from pathlib import Path

from core.exceptions import GitNotFoundError, GitOperationError

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
    def _run_output(self, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
        """Run a git command and return the CompletedProcess result.

        Raises GitNotFoundError if git is not installed.
        Raises GitOperationError if the command exits with a non-zero status.
        """
        try:
            return subprocess.run(
                args, cwd=cwd, check=True, capture_output=True, text=True
            )
        except FileNotFoundError:
            raise GitNotFoundError(
                "git binary not found. Please install git: https://git-scm.com/downloads"
            )
        except subprocess.CalledProcessError as exc:
            raise GitOperationError(exc.stderr.strip() if exc.stderr else str(exc))
    def _require_commits(self, path: Path) -> None:
        """Raise GitOperationError if the repo at path has no commits.

        Runs ``git rev-parse HEAD`` to verify at least one commit exists.
        Called as a precondition by branch-operating methods.
        """
        try:
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=path,
                check=True,
                capture_output=True,
            )
        except FileNotFoundError:
            raise GitNotFoundError(
                "git binary not found. Please install git: https://git-scm.com/downloads"
            )
        except subprocess.CalledProcessError:
            raise GitOperationError(
                "Repository has no commits. Run initial_commit() first."
            )

    def create_branch(self, path: Path, branch_name: str) -> None:
        """Create a new branch and switch to it.

        If the branch already exists, switch to it instead.
        """
        self._require_commits(path)
        try:
            self._run_output(["git", "checkout", "-b", branch_name], cwd=path)
        except GitOperationError:
            self._run_output(["git", "checkout", branch_name], cwd=path)

    def checkout(self, path: Path, branch_name: str) -> None:
        """Switch to an existing branch.

        Raises GitOperationError if the branch does not exist.
        """
        self._require_commits(path)
        self._run_output(["git", "checkout", branch_name], cwd=path)

    def stage_and_commit(self, path: Path, files: list[str], message: str) -> str:
        """Stage the specified files and create a commit.

        Args:
            path: Repository root directory.
            files: List of file paths to stage (relative to *path*).
            message: Commit message.

        Returns:
            The full commit hash of the new commit.

        Raises:
            ValueError: If *files* is empty or *message* is whitespace-only.
        """
        if not files:
            raise ValueError("At least one file path is required.")
        if not message or not message.strip():
            raise ValueError("A non-empty commit message is required.")

        self._run(["git", "add", *files], cwd=path)
        self._run(["git", "commit", "-m", message], cwd=path)
        result = self._run_output(["git", "rev-parse", "HEAD"], cwd=path)
        return result.stdout.strip()

    def diff(self, path: Path, source_branch: str, target_branch: str) -> str:
        """Return the unified diff between target_branch and source_branch.

        Runs ``git diff <target>..<source>`` and returns stdout.

        Args:
            path: Repository root directory.
            source_branch: The branch with new changes.
            target_branch: The branch to compare against.

        Returns:
            The diff text, or an empty string when there are no changes.

        Raises:
            GitOperationError: If the repository has no commits or a branch
                does not exist.
        """
        self._require_commits(path)
        result = self._run_output(
            ["git", "diff", f"{target_branch}..{source_branch}"], cwd=path
        )
        return result.stdout

    def merge(self, path: Path, source_branch: str) -> None:
        """Merge source_branch into the current branch using fast-forward only.

        Raises:
            GitOperationError: If the repo has no commits or fast-forward
                is not possible.
        """
        self._require_commits(path)
        self._run_output(
            ["git", "merge", "--ff-only", source_branch], cwd=path
        )

    def push(self, path: Path, remote: str = "origin") -> None:
        """Push the current branch to the specified remote.

        Raises:
            GitOperationError: If the push fails (e.g. no remote configured).
        """
        self._run_output(["git", "push", remote, "HEAD"], cwd=path)

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
