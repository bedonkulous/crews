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
