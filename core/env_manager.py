"""ENVManager — read/write operations on the .env file using python-dotenv."""

from __future__ import annotations

from pathlib import Path

import typer
from dotenv import dotenv_values, set_key, unset_key

from core.exceptions import MissingEnvVarError

# Keys required for the application to function
REQUIRED_KEYS: list[str] = [
    "SLACK_BOT_TOKEN",
    "SLACK_APP_TOKEN",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_DEFAULT_REGION",
    "OPENAI_API_KEY",
]


class ENVManager:
    """Manages environment variables stored in a .env file."""

    def __init__(self, env_file: Path = Path(".env")) -> None:
        self.env_file = env_file
        # Ensure the file exists so dotenv operations work correctly
        if not self.env_file.exists():
            self.env_file.touch()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def set(self, key: str, value: str) -> None:
        """Write or overwrite *key* in the .env file."""
        set_key(str(self.env_file), key, value, quote_mode="never")

    def get(self, key: str) -> str | None:
        """Return the value for *key*, or ``None`` if absent."""
        return dotenv_values(self.env_file).get(key)

    def list_keys(self) -> list[str]:
        """Return all configured key names — no values."""
        return list(dotenv_values(self.env_file).keys())

    def delete(self, key: str) -> None:
        """Remove *key* from the .env file (no-op if absent)."""
        unset_key(str(self.env_file), key)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_required(self, keys: list[str]) -> None:
        """Raise :class:`MissingEnvVarError` listing every absent key.

        Args:
            keys: The list of required environment variable names.

        Raises:
            MissingEnvVarError: If one or more keys are missing.
        """
        present = dotenv_values(self.env_file)
        missing = [k for k in keys if k not in present or present[k] is None]
        if missing:
            raise MissingEnvVarError(
                f"Missing required environment variable(s): {', '.join(missing)}"
            )

    # ------------------------------------------------------------------
    # Interactive setup
    # ------------------------------------------------------------------

    def setup_interactive(self) -> None:
        """Prompt the user for each required key and persist to .env."""
        for key in REQUIRED_KEYS:
            value = typer.prompt(key)
            self.set(key, value)
