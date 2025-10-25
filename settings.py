"""Configuration loading for calypsetup."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


@dataclass
class ToolSettings:
    potcar_root: Path
    calypso_executable: str
    vasp_executable: str

    @classmethod
    def from_mapping(cls, data: dict) -> "ToolSettings":
        return cls(
            potcar_root=Path(data["potcar_root"]).expanduser(),
            calypso_executable=str(data["calypso_executable"]),
            vasp_executable=str(data["vasp_executable"]),
        )


def load_settings(path: Path | None) -> ToolSettings:
    config_path = path if path is not None else DEFAULT_CONFIG_PATH
    config_path = config_path.expanduser()
    if not config_path.is_file():
        raise FileNotFoundError(
            f"Configuration file not found at {config_path}. "
            "Copy config.example.json to config.json and update the paths."
        )

    data = json.loads(config_path.read_text())
    return ToolSettings.from_mapping(data)


__all__ = ["ToolSettings", "load_settings", "DEFAULT_CONFIG_PATH"]
