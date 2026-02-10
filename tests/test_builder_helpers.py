from pathlib import Path

import pytest

from calypso_setup.builder import (
    _format_pstress_kbar,
    adjust_input_dat,
    calculate_distance_of_ion,
    create_input_dat,
    find_potcar,
)


def test_format_pstress_kbar_formats_integer_and_decimal_values() -> None:
    assert _format_pstress_kbar(250.0) == "2500"
    assert _format_pstress_kbar(12.34) == "123.4"


def test_format_pstress_kbar_rejects_negative_pressure() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        _format_pstress_kbar(-1.0)


def test_calculate_distance_of_ion_builds_expected_matrix() -> None:
    matrix = calculate_distance_of_ion({"Fe": 1.0, "O": 2.0})
    assert matrix[0][0] == pytest.approx(1.2)
    assert matrix[0][1] == pytest.approx(1.8)
    assert matrix[1][0] == pytest.approx(1.8)
    assert matrix[1][1] == pytest.approx(2.4)


def test_adjust_input_dat_scales_name_and_atom_counts(tmp_path: Path) -> None:
    input_dat = tmp_path / "input.dat"
    input_dat.write_text(
        "SystemName = Fe1O1\nNumberOfAtoms = 1 1\nOther = keep\n",
        encoding="utf-8",
    )

    adjust_input_dat(input_dat, multiplier=3)
    content = input_dat.read_text(encoding="utf-8")

    assert "SystemName = Fe1O13" in content
    assert "NumberOfAtoms = 3 3" in content
    assert "Other = keep" in content


def test_find_potcar_reads_rwigs_and_writes_combined_file(tmp_path: Path) -> None:
    potcar_root = tmp_path / "potcars"
    (potcar_root / "Fe_pv").mkdir(parents=True)
    (potcar_root / "O").mkdir(parents=True)

    (potcar_root / "Fe_pv" / "POTCAR").write_text(
        "Fe POTCAR\nRWIGS = 1.20; RWIGS = 1.10\n",
        encoding="utf-8",
    )
    (potcar_root / "O" / "POTCAR").write_text(
        "O POTCAR\nRWIGS = 0.80\n",
        encoding="utf-8",
    )

    destination = tmp_path / "dest"
    rwigs_values, min_latom_dis = find_potcar(["Fe", "O"], destination, potcar_root=potcar_root)

    assert rwigs_values == {"Fe": 1.1, "O": 0.8}
    assert min_latom_dis == 0.8
    combined = (destination / "POTCAR").read_text(encoding="utf-8")
    assert "Fe POTCAR" in combined
    assert "O POTCAR" in combined


def test_create_input_dat_requires_base_area_for_2d(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="base_area must be provided"):
        create_input_dat(
            directory=tmp_path,
            elements=["Fe"],
            atom_counts=[1],
            distance_of_ion_matrix=[[1.0]],
            min_latom_dis=1.0,
            is_2d=True,
            num_layers=1,
            relax_z=False,
            base_area=None,
            layer_type_matrix=[[1]],
        )
