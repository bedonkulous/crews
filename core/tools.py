"""Custom crewAI tools for file system operations and Slack updates."""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import Field


class FileWriterTool(BaseTool):
    """Write content to a file within the crew's project directory."""

    name: str = "file_writer"
    description: str = (
        "Write content to a file in the project directory. "
        "Provide a relative file path and the content to write. "
        "Directories are created automatically. "
        "Use this to save code, configs, docs, etc."
    )
    project_dir: Path = Field(default=Path("."))

    def _run(self, file_path: str, content: str) -> str:
        """Write content to file_path relative to project_dir."""
        target = self.project_dir / file_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"Wrote {len(content)} bytes to {file_path}"


class FileReaderTool(BaseTool):
    """Read content from a file within the crew's project directory."""

    name: str = "file_reader"
    description: str = (
        "Read the contents of a file in the project directory. "
        "Provide a relative file path."
    )
    project_dir: Path = Field(default=Path("."))

    def _run(self, file_path: str) -> str:
        """Read content from file_path relative to project_dir."""
        target = self.project_dir / file_path
        if not target.exists():
            return f"File not found: {file_path}"
        return target.read_text()


# ---------------------------------------------------------------------------
# Activity log — shared across all agents in a crew run
# ---------------------------------------------------------------------------

class ActivityLog:
    """Thread-safe log of agent activity for status reporting."""

    def __init__(self) -> None:
        self._entries: list[dict[str, str]] = []
        self._lock = threading.Lock()

    def add(self, agent_role: str, message: str) -> None:
        with self._lock:
            self._entries.append({
                "time": datetime.utcnow().strftime("%H:%M:%S"),
                "role": agent_role,
                "message": message,
            })

    def summary(self) -> str:
        with self._lock:
            if not self._entries:
                return "No activity yet."
            lines = []
            for e in self._entries:
                lines.append(f"[{e['time']}] {e['role']}: {e['message']}")
            return "\n".join(lines)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


# ---------------------------------------------------------------------------
# SlackUpdateTool — lets any agent post updates to the crew channel
# ---------------------------------------------------------------------------

class SlackUpdateTool(BaseTool):
    """Post a progress update to the crew's Slack channel."""

    name: str = "slack_update"
    description: str = (
        "Post a short progress update to the crew's Slack channel. "
        "Use this to keep the team lead informed about what you're working on, "
        "what you've completed, or any blockers. "
        "Provide a brief message describing your current status."
    )
    slack_integration: Any = Field(default=None)
    channel_id: str = Field(default="")
    agent_role: str = Field(default="agent")
    activity_log: Any = Field(default=None)

    def _run(self, message: str) -> str:
        """Post update to Slack and log it."""
        formatted = f"*{self.agent_role}*: {message}"
        if self.activity_log is not None:
            self.activity_log.add(self.agent_role, message)
        if self.slack_integration is not None and self.channel_id:
            try:
                self.slack_integration.post_message(self.channel_id, formatted)
            except Exception:
                pass  # Don't fail the agent if Slack post fails
        return f"Posted update: {message}"


# ---------------------------------------------------------------------------
# StatusReportTool — lets the product_manager report on all activity
# ---------------------------------------------------------------------------

class StatusReportTool(BaseTool):
    """Read the activity log and produce a status report."""

    name: str = "status_report"
    description: str = (
        "Read the full activity log from all agents and produce a status report. "
        "Use this when asked for a project status update. "
        "Returns a chronological log of all agent activity."
    )
    activity_log: Any = Field(default=None)

    def _run(self) -> str:
        """Return the activity log summary."""
        if self.activity_log is None:
            return "No activity log available."
        return self.activity_log.summary()


# ---------------------------------------------------------------------------
# Git repo validation helper
# ---------------------------------------------------------------------------

import subprocess
import re


def _validate_repo(project_dir: Path) -> str | None:
    """Check that project_dir is an initialized git repo with at least one commit.

    Returns None if valid, or an error string if not.
    """
    if not (project_dir / ".git").exists():
        return (
            f"Error: {project_dir} is not an initialized git repository. "
            "Ensure CrewFactory.create() has been called."
        )
    try:
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return (
            f"Error: {project_dir} has no commits. "
            "Ensure CrewFactory.create() has been called to initialize the repo."
        )
    return None


# ---------------------------------------------------------------------------
# GitCommitTool — lets the developer commit files to a feature branch
# ---------------------------------------------------------------------------

class GitCommitTool(BaseTool):
    """Stage and commit files, auto-creating a feature branch if on main."""

    name: str = "git_commit"
    description: str = (
        "Stage and commit files in the project directory. "
        "Provide comma-separated file paths and a commit message. "
        "Automatically creates a feature branch if currently on main."
    )
    project_dir: Path = Field(default=Path("."))
    branch_name: str = Field(default="")

    def _run(self, file_paths: str, message: str) -> str:
        error = _validate_repo(self.project_dir)
        if error:
            return error

        from core.git_manager import GitManager
        gm = GitManager()

        try:
            files = [f.strip() for f in file_paths.split(",") if f.strip()]
            if not files:
                return "Error: No file paths provided."

            # Auto-create feature branch if on main
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.project_dir, capture_output=True, text=True, check=True,
            )
            current_branch = result.stdout.strip()

            if current_branch in ("main", "master") and not self.branch_name:
                slug = re.sub(r"[^a-z0-9]+", "-", message.lower().strip())[:40].strip("-")
                self.branch_name = f"feature/{slug}"

            if self.branch_name and current_branch != self.branch_name:
                gm.create_branch(self.project_dir, self.branch_name)

            commit_hash = gm.stage_and_commit(self.project_dir, files, message)
            return f"Committed {len(files)} file(s) on branch '{self.branch_name or current_branch}': {commit_hash}"
        except Exception as exc:
            return f"Error committing files: {exc}"


# ---------------------------------------------------------------------------
# GitDiffTool — lets reviewers see changes on a feature branch
# ---------------------------------------------------------------------------

class GitDiffTool(BaseTool):
    """Show the diff between a feature branch and main."""

    name: str = "git_diff"
    description: str = (
        "Show the unified diff between a feature branch and main. "
        "Optionally provide a branch name; defaults to current branch vs main."
    )
    project_dir: Path = Field(default=Path("."))

    def _run(self, branch: str = "") -> str:
        error = _validate_repo(self.project_dir)
        if error:
            return error

        from core.git_manager import GitManager
        gm = GitManager()

        try:
            if not branch:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=self.project_dir, capture_output=True, text=True, check=True,
                )
                branch = result.stdout.strip()

            diff_text = gm.diff(self.project_dir, branch, "main")
            if not diff_text.strip():
                return "No changes found."
            return diff_text
        except Exception as exc:
            return f"Error getting diff: {exc}"


# ---------------------------------------------------------------------------
# GitPushTool — lets the manager merge and push approved code
# ---------------------------------------------------------------------------

class GitPushTool(BaseTool):
    """Merge a feature branch into main and push to remote."""

    name: str = "git_push"
    description: str = (
        "Merge a feature branch into main and push to the remote. "
        "Optionally provide a branch name; defaults to current branch."
    )
    project_dir: Path = Field(default=Path("."))

    def _run(self, branch: str = "") -> str:
        error = _validate_repo(self.project_dir)
        if error:
            return error

        from core.git_manager import GitManager
        gm = GitManager()

        try:
            if not branch:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=self.project_dir, capture_output=True, text=True, check=True,
                )
                branch = result.stdout.strip()

            if branch in ("main", "master"):
                return "Error: Already on main branch. Nothing to merge."

            gm.checkout(self.project_dir, "main")
            gm.merge(self.project_dir, branch)
            gm.push(self.project_dir)
            return f"Merged '{branch}' into main and pushed to remote."
        except Exception as exc:
            return f"Error pushing: {exc}"
