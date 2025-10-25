# calypsetup

`calypsetup` assembles the boilerplate required to launch CALYPSO + VASP structure searches. I built it so everyone in our lab could queue high-depth runs without spending an evening copy‑pasting POTCARs, hand-editing `input.dat`, or formatting new SLURM scripts. If you maintain your own POTCAR library and CALYPSO/VASP binaries, you can point the tool at them via a simple JSON config and let it lay out consistent calculation folders.

Calypso setup script to automate file setup for searches (with lots of config options for 2D searches in particular).

> *“I made this so that I along with people in my lab could launch structure searches for a given system with high depth/accuracy, and not have to spend any time manually configuring the CALYPSO input files. You will have to place your own POTCAR, CALYPSO and VASP executables in the config file, but hopefully it can save you some time as well. Not all CALYPSO features are automated, but I focused on the options we use most often for 2D materials, so those paths are much more fleshed out than the others.”*

---

## Features

- Collects per-element POTCARs (prefers `_pv`, `_sv`, `_s`) and stitches the RWIGS metadata into a combined file.
- Writes two INCAR templates, optional 2D CALYPSO blocks, and per-formula subdirectories with `input.dat`.
- Generates job scripts (`calypso_fullnode.pbs`, `calypso.pbs`, `submit.sh`) using paths from `config.json`.
- Supports both bulk and 2D searches (layer count, layer composition, relax‑z) with sensible defaults.
- Provides a simple CLI (`python -m calypsetup.cli ...`) to prompt for inputs and queue the setup.

---

## Installation

```bash
git clone <repo-url>
cd calypsetup
python -m pip install -e .
```

Dependencies: `pymatgen` (for POTCAR handling) and the Python standard library. No CALYPSO/VASP binaries are bundled—point to your own installations.

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

You can keep multiple configs (e.g., Hopper vs. R2 nodes) and select them with `--config /path/to/other.json`. Command-line overrides are available for `--potcar-root`.

---

## Quick Start (Interactive)

```bash
python -m calypsetup.cli Fe P --destination ./FeP_run
```

- Enter atom counts and formula multipliers when prompted.
- Opt into 2D mode to specify layer count/compositions.
- The tool creates subdirectories named after the formula multipliers (e.g., `1/`, `2/`) with ready-to-run templates.

For non-interactive usage, import `calypsetup` in Python and construct a `SetupConfig` manually:

```python
from calypsetup import SetupConfig, load_settings, setup_calypso

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
│   ├── calypso.pbs, calypso_fullnode.pbs
│   └── submit.sh
└── 2/
    └── ...
```

After inspecting/editing the generated files, run CALYPSO/SLURM as usual.

---

## Roadmap / Limitations

- CALYPSO options beyond the ones we use are still manual (e.g., custom PSO tunables, multi-command workflows).
- Currently the CLI remains interactive. Converting it to accept explicit command-line values or YAML configuration is on the to-do list.
- No automatic submission is performed—scripts just get staged.

Feel free to file issues or PRs if you add new features or find bugs. Happy structure hunting!
