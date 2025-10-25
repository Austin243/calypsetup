"""Command-line interface for calypsetup."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

from .builder import SetupConfig, setup_calypso
from .settings import DEFAULT_CONFIG_PATH, load_settings


def _prompt_int_list(prompt: str, *, expected_len: Optional[int] = None) -> List[int]:
    while True:
        raw = input(prompt).strip().split()
        try:
            values = [int(x) for x in raw]
        except ValueError:
            print("Please enter integers separated by spaces.")
            continue

        if expected_len is not None and len(values) != expected_len:
            print(f"Please provide exactly {expected_len} values.")
            continue
        if not values:
            print("Please enter at least one value.")
            continue
        return values


def _prompt_layer_matrix(num_layers: int, elements: List[str]) -> List[List[int]]:
    layer_matrix: List[List[int]] = []
    for layer_idx in range(1, num_layers + 1):
        prompt = f"Layer {layer_idx} composition ({', '.join(elements)}): "
        layer_matrix.append(_prompt_int_list(prompt, expected_len=len(elements)))
    return layer_matrix


def prompt_config(
    args: argparse.Namespace,
    *,
    potcar_root: Path,
    calypso_executable: str,
    vasp_executable: str,
) -> SetupConfig:
    atom_counts = _prompt_int_list(
        f"How many atoms of each species ({', '.join(args.elements)})? ",
        expected_len=len(args.elements),
    )

    is_2d_resp = input("Is this a 2D structure search? (Y/N): ").strip().lower()
    is_2d = is_2d_resp in {"y", "yes"}

    num_layers = 1
    relax_z = False
    layer_matrix: Optional[List[List[int]]] = None

    if is_2d:
        num_layers = int(input("How many layers? ").strip())
        relax_z_resp = input("Should the Z direction relax? (Y/N): ").strip().lower()
        relax_z = relax_z_resp in {"y", "yes"}
        layer_matrix = _prompt_layer_matrix(num_layers, args.elements)
    elif is_2d_resp not in {"n", "no"}:
        raise SystemExit("Invalid response. Please answer Y or N.")

    formula_multipliers = _prompt_int_list(
        "How many formula values for the system? (space-separated integers): "
    )

    return SetupConfig(
        elements=list(args.elements),
        atom_counts=atom_counts,
        formula_multipliers=formula_multipliers,
        destination=Path(args.destination).resolve(),
        potcar_root=potcar_root,
        calypso_executable=calypso_executable,
        vasp_executable=vasp_executable,
        is_2d=is_2d,
        num_layers=num_layers,
        relax_z=relax_z,
        layer_type_matrix=layer_matrix,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare CALYPSO/VASP calculation directories.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "elements",
        nargs="+",
        help="Elements to include (e.g. Fe P).",
    )
    parser.add_argument(
        "--destination",
        default=".",
        help="Output directory for generated setups.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help=f"Path to config JSON (default: {DEFAULT_CONFIG_PATH.name} next to the module).",
    )
    parser.add_argument(
        "--potcar-root",
        default=None,
        help="Override POTCAR directory (defaults to value specified in config).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    config_path = Path(args.config).expanduser() if args.config else DEFAULT_CONFIG_PATH
    tool_settings = load_settings(config_path)

    potcar_root = (
        Path(args.potcar_root).expanduser()
        if args.potcar_root
        else tool_settings.potcar_root
    )

    config = prompt_config(
        args,
        potcar_root=potcar_root,
        calypso_executable=tool_settings.calypso_executable,
        vasp_executable=tool_settings.vasp_executable,
    )
    created = setup_calypso(config)

    if created:
        print("\nGenerated directories:")
        for path in created:
            print(f"  - {path}")


if __name__ == "__main__":
    main()
