from pathlib import Path

from calypso_setup.builder import SetupConfig, setup_calypso


def test_setup_calypso_generates_expected_structure(tmp_path: Path) -> None:
    potcar_root = tmp_path / "potcars"
    (potcar_root / "Fe").mkdir(parents=True)
    (potcar_root / "Fe" / "POTCAR").write_text(
        "Fe POTCAR\nRWIGS = 1.20; RWIGS = 1.10\n",
        encoding="utf-8",
    )

    destination = tmp_path / "run"
    config = SetupConfig(
        elements=["Fe"],
        atom_counts=[1],
        formula_multipliers=[1, 2],
        pressure_gpa=5.0,
        destination=destination,
        potcar_root=potcar_root,
        calypso_executable="/opt/calypso/bin/calypso.x",
        vasp_executable="/opt/vasp/bin/vasp_std",
        is_2d=False,
    )

    created = setup_calypso(config)

    assert created == [destination / "1", destination / "2"]
    for formula_path in created:
        assert (formula_path / "input.dat").is_file()
        assert (formula_path / "POTCAR").is_file()
        assert (formula_path / "INCAR_1").is_file()
        assert (formula_path / "INCAR_2").is_file()
        assert (formula_path / "submit.sh").is_file()

    # setup_calypso writes then deletes temporary top-level files.
    assert not (destination / "INCAR_1").exists()
    assert not (destination / "INCAR_2").exists()
    assert not (destination / "POTCAR").exists()
    assert not (destination / "submit.sh").exists()

    input_one = (destination / "1" / "input.dat").read_text(encoding="utf-8")
    input_two = (destination / "2" / "input.dat").read_text(encoding="utf-8")
    submit_sh = (destination / "1" / "submit.sh").read_text(encoding="utf-8")

    assert "NumberOfAtoms = 1" in input_one
    assert "NumberOfAtoms = 2" in input_two
    assert "/opt/vasp/bin/vasp_std" in submit_sh
