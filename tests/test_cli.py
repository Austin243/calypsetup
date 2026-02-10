import json
from pathlib import Path

import pytest

from calypso_setup import cli
from calypso_setup.builder import SetupConfig


def test_build_parser_parses_core_arguments() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "Fe",
            "P",
            "--destination",
            "out",
            "--config",
            "cfg.json",
            "--potcar-root",
            "/tmp/potcars",
        ]
    )

    assert args.elements == ["Fe", "P"]
    assert args.destination == "out"
    assert args.config == "cfg.json"
    assert args.potcar_root == "/tmp/potcars"


def test_main_invokes_setup_with_loaded_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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

    captured = {}

    def fake_prompt_config(args, *, potcar_root, calypso_executable, vasp_executable):
        captured["args"] = args
        captured["potcar_root"] = potcar_root
        captured["calypso_executable"] = calypso_executable
        captured["vasp_executable"] = vasp_executable
        return SetupConfig(
            elements=["Fe"],
            atom_counts=[1],
            formula_multipliers=[1],
            destination=tmp_path / "run",
            potcar_root=potcar_root,
            calypso_executable=calypso_executable,
            vasp_executable=vasp_executable,
        )

    def fake_setup_calypso(config):
        captured["config"] = config
        return [tmp_path / "run" / "1"]

    monkeypatch.setattr(cli, "prompt_config", fake_prompt_config)
    monkeypatch.setattr(cli, "setup_calypso", fake_setup_calypso)

    cli.main(["Fe", "--config", str(config_path)])

    assert captured["potcar_root"] == tmp_path / "potcars"
    assert captured["calypso_executable"] == "/opt/calypso/bin/calypso.x"
    assert captured["vasp_executable"] == "/opt/vasp/bin/vasp_std"
    assert isinstance(captured["config"], SetupConfig)
