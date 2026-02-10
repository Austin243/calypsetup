import json
from pathlib import Path

import pytest

from calypso_setup.settings import load_settings


def test_load_settings_reads_json_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "potcar_root": str(tmp_path / "potcars"),
                "calypso_executable": "/opt/calypso/bin/calypso.x",
                "vasp_executable": "/opt/vasp/bin/vasp_std",
            }
        ),
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.potcar_root == tmp_path / "potcars"
    assert settings.calypso_executable == "/opt/calypso/bin/calypso.x"
    assert settings.vasp_executable == "/opt/vasp/bin/vasp_std"


def test_load_settings_raises_for_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_settings(missing_path)
