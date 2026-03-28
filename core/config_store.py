"""ConfigStore: reads and writes crew.yaml files atomically."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import yaml

from core.exceptions import CrewNotFoundError
from core.models import CrewConfig

logger = logging.getLogger(__name__)


class ConfigStore:
    """Persists CrewConfig objects as YAML files under a root directory.

    Directory layout::

        <root_dir>/
            <crew-name>/
                crew.yaml
    """

    def __init__(self, root_dir: Path | str = Path("crew")) -> None:
        self.root_dir = Path(root_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write(self, crew_config: CrewConfig) -> None:
        """Serialize *crew_config* to YAML and atomically write to disk.

        The file is first written to a sibling temp file, then renamed into
        place so that a crash mid-write never leaves a partial file.
        """
        crew_dir = self.root_dir / crew_config.name
        crew_dir.mkdir(parents=True, exist_ok=True)

        target = crew_dir / "crew.yaml"
        data = crew_config.to_dict()
        yaml_text = yaml.safe_dump(data, default_flow_style=False, allow_unicode=True)

        # Write to a temp file in the same directory, then rename atomically.
        fd, tmp_path = tempfile.mkstemp(dir=crew_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(yaml_text)
            os.replace(tmp_path, target)
        except Exception:
            # Clean up the temp file on failure.
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def read(self, name: str) -> CrewConfig:
        """Deserialize and return the CrewConfig for *name*.

        Raises:
            CrewNotFoundError: if ``crew/<name>/crew.yaml`` does not exist.
        """
        config_path = self.root_dir / name / "crew.yaml"
        if not config_path.exists():
            raise CrewNotFoundError(f"No crew.yaml found for crew '{name}'")

        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        return CrewConfig.from_dict(data)

    def read_all(self) -> list[CrewConfig]:
        """Scan *root_dir* subdirectories and return all valid CrewConfig objects.

        Subdirectories whose ``crew.yaml`` is missing or malformed are skipped
        with a warning rather than raising an exception.
        """
        configs: list[CrewConfig] = []

        if not self.root_dir.exists():
            return configs

        for entry in sorted(self.root_dir.iterdir()):
            if not entry.is_dir():
                continue
            config_path = entry / "crew.yaml"
            if not config_path.exists():
                continue
            try:
                with config_path.open("r", encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                configs.append(CrewConfig.from_dict(data))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping malformed crew.yaml at %s: %s", config_path, exc)

        return configs

    def exists(self, name: str) -> bool:
        """Return True if ``crew/<name>/crew.yaml`` exists on disk."""
        return (self.root_dir / name / "crew.yaml").exists()
