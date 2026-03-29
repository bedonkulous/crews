"""Unit tests for GitManager."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from core.exceptions import GitNotFoundError
from core.git_manager import GitManager


@pytest.fixture
def git_manager():
    return GitManager()


def test_init_repo_creates_git_directory(tmp_path, git_manager):
    """init_repo should create a .git directory in the given path."""
    git_manager.init_repo(tmp_path)
    assert (tmp_path / ".git").is_dir()


def test_initial_commit_creates_gitignore_and_readme(tmp_path, git_manager):
    """initial_commit should create .gitignore and README.md and make a commit."""
    # Need a real git repo first
    git_manager.init_repo(tmp_path)

    # Configure git identity for the temp repo so commit works in CI
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)

    git_manager.initial_commit(tmp_path, "my-crew")

    assert (tmp_path / ".gitignore").exists()
    assert (tmp_path / "README.md").exists()

    readme_text = (tmp_path / "README.md").read_text()
    assert "my-crew" in readme_text

    # Verify a commit was actually made
    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() != ""


def test_init_repo_raises_git_not_found_error(tmp_path, git_manager):
    """init_repo should raise GitNotFoundError when git binary is not found."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(GitNotFoundError):
            git_manager.init_repo(tmp_path)


def test_initial_commit_raises_git_not_found_error(tmp_path, git_manager):
    """initial_commit should raise GitNotFoundError when git binary is not found."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(GitNotFoundError):
            git_manager.initial_commit(tmp_path, "my-crew")


from core.exceptions import GitOperationError


@pytest.fixture
def initialized_repo(tmp_path, git_manager):
    """Create a fully initialized git repo with one commit on 'main'."""
    git_manager.init_repo(tmp_path)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    git_manager.initial_commit(tmp_path, "test-crew")
    # Ensure the default branch is named 'main' regardless of system config
    subprocess.run(["git", "branch", "-M", "main"], cwd=tmp_path, check=True)
    return tmp_path


class TestDiff:
    """Tests for GitManager.diff — Requirements 0.3, 3.1, 3.2, 3.3."""

    def test_diff_returns_changes_between_branches(self, initialized_repo, git_manager):
        """diff should return unified diff text showing changes on the source branch."""
        path = initialized_repo
        git_manager.create_branch(path, "feature-x")
        (path / "new_file.txt").write_text("hello world\n")
        git_manager.stage_and_commit(path, ["new_file.txt"], "add new file")

        result = git_manager.diff(path, "feature-x", "main")

        assert "new_file.txt" in result
        assert "hello world" in result

    def test_diff_returns_empty_string_when_no_changes(self, initialized_repo, git_manager):
        """diff should return empty string when branches are identical."""
        path = initialized_repo
        git_manager.create_branch(path, "no-changes")
        git_manager.checkout(path, "main")

        result = git_manager.diff(path, "no-changes", "main")

        assert result == ""

    def test_diff_raises_for_nonexistent_branch(self, initialized_repo, git_manager):
        """diff should raise GitOperationError for a branch that doesn't exist."""
        path = initialized_repo

        with pytest.raises(GitOperationError):
            git_manager.diff(path, "nonexistent-branch", "main")

    def test_diff_raises_on_repo_with_no_commits(self, tmp_path, git_manager):
        """diff should raise GitOperationError on a repo with no commits."""
        git_manager.init_repo(tmp_path)

        with pytest.raises(GitOperationError, match="no commits"):
            git_manager.diff(tmp_path, "feature", "main")
