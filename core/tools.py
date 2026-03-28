"""Custom crewAI tools for file system operations."""

from __future__ import annotations

from pathlib import Path

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
