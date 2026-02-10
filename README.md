# calypso-setup

`calypso-setup` assembles the boilerplate required to launch CALYPSO + VASP structure searches. If you maintain your own POTCAR library and CALYPSO/VASP binaries, you can point the tool at them via a simple JSON config and let it lay out consistent calculation folders.

Calypso setup script to automate file setup for searches (with lots of config options for 2D searches in particular).

The Python package/module name is `calypso_setup`, so CLI and import paths use `calypso_setup`.

---

## Features

- Collects per-element POTCARs (prefers `_pv`, `_sv`, `_s`) and stitches the RWIGS metadata into a combined file.
- Writes two INCAR templates, optional 2D CALYPSO blocks, and per-formula subdirectories with `input.dat`.
- Prompts for target pressure in GPa and writes `PSTRESS` in kbar into both INCAR templates.
- Generates job scripts (`calypso_fullnode.sh`, `calypso.sh`, `submit.sh`) using paths from `config.json`, with scheduler directives that you can adapt to your cluster.
- Supports both bulk and 2D searches (layer count, layer composition, relax‑z) with sensible defaults.
- Provides a simple CLI (`python -m calypso_setup.cli ...`) to prompt for inputs and queue the setup.

---

## Installation

```bash
git clone <repo-url>
cd calypso-setup
python -m pip install -e .
```

Dependencies: `pymatgen` (for POTCAR handling) and the Python standard library. No CALYPSO/VASP binaries are bundled—point to your own installations.

---

## Testing

Run the lightweight regression suite with:

```bash
python -m pytest
```

---

## Configuration

Copy the example config and edit the paths to match your environment:

```bash
cp config.example.json config.json
```

```json
{
  "potcar_root": "/path/to/vasp/potpaw/PAW_PBE",
  "calypso_executable": "/path/to/CALYPSO_x64/bin/calypso.x",
  "vasp_executable": "/path/to/vasp_std"
}
```

You can keep multiple configs (for different clusters or partitions) and select them with `--config /path/to/other.json`. Command-line overrides are available for `--potcar-root`.

---

## Quick Start (Interactive)

```bash
python -m calypso_setup.cli Fe P --destination ./FeP_run
```

- Enter atom counts and formula multipliers when prompted.
- Opt into 2D mode to specify layer count/compositions.
- The tool creates subdirectories named after the formula multipliers (e.g., `1/`, `2/`) with ready-to-run templates.

For non-interactive usage, import `calypso_setup` in Python and construct a `SetupConfig` manually:

```python
from calypso_setup import SetupConfig, load_settings, setup_calypso

settings = load_settings("config.json")
config = SetupConfig(
    elements=["Fe", "P"],
    atom_counts=[1, 1],
    formula_multipliers=[1, 2],
    destination="FeP_run",
    potcar_root=settings.potcar_root,
    calypso_executable=settings.calypso_executable,
    vasp_executable=settings.vasp_executable,
    is_2d=False,
)
setup_calypso(config)
```

---

## Output Layout

```
FeP_run/
├── 1/
│   ├── INCAR_1, INCAR_2, POTCAR, input.dat
│   ├── calypso.sh, calypso_fullnode.sh
│   └── submit.sh
└── 2/
    └── ...
```

After inspecting/editing the generated files, run CALYPSO/SLURM as usual.

---

## Roadmap / Limitations

- CALYPSO options beyond the ones we use are still manual (e.g., custom PSO tunables, multi-command workflows).
- Currently the CLI remains interactive. Converting it to accept explicit command-line values or YAML configuration is on the to-do list.
- No automatic submission is performed, scripts are staged for review before launch.

Feel free to file issues or PRs if you add new features or find bugs. Happy structure hunting!
