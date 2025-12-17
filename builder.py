"""Core routines for preparing CALYPSO + VASP calculation directories."""
from __future__ import annotations

import math
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union


DEFAULT_POTCAR_ROOT = Path(
    os.environ.get("CALYSETUP_POTCAR_ROOT", "/path/to/vasp/potpaw/PAW_PBE")
)


def _format_pstress_kbar(pressure_gpa: float) -> str:
    """Convert pressure in GPa to kbar for VASP's PSTRESS and return formatted string."""
    pstress_kbar = pressure_gpa * 10.0
    if pstress_kbar < 0:
        raise ValueError("Pressure must be non-negative.")
    # Prefer integer formatting when possible (e.g., 250 GPa -> 2500 kbar).
    if abs(pstress_kbar - round(pstress_kbar)) < 1e-9:
        return str(int(round(pstress_kbar)))
    return f"{pstress_kbar:.6g}"



@dataclass
class SetupConfig:
    """User-specified configuration for generating CALYPSO input directories."""

    elements: List[str]
    atom_counts: List[int]
    formula_multipliers: List[int]
    pressure_gpa: float = 0.0  # GPa, converted to kbar for PSTRESS
    destination: Path = field(default_factory=lambda: Path.cwd())
    potcar_root: Path = DEFAULT_POTCAR_ROOT
    calypso_executable: Union[str, Path] = "/path/to/CALYPSO_x64/bin/calypso.x"
    vasp_executable: Union[str, Path] = "/path/to/vasp_std"
    is_2d: bool = False
    num_layers: int = 1
    relax_z: bool = False
    layer_type_matrix: Optional[List[List[int]]] = None


def find_potcar(
    elements: Sequence[str],
    destination: Path,
    potcar_root: Path = DEFAULT_POTCAR_ROOT,
) -> Tuple[Dict[str, float], Optional[float]]:
    """Concatenate POTCAR files for *elements* into *destination* and return RWIGS data."""

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    potcar_root = Path(potcar_root)

    pair_re = re.compile(
        r"RWIGS\s*=\s*([-+]?\d*\.?\d+)\s*;\s*RWIGS\s*=\s*([-+]?\d*\.?\d+)", re.IGNORECASE
    )
    single_re = re.compile(r"RWIGS\s*=\s*([-+]?\d*\.?\d+)", re.IGNORECASE)

    potcar_content: List[str] = []
    rwigs_values: Dict[str, float] = {}
    picked_rwigs: List[float] = []

    available_dirs = {entry.name for entry in potcar_root.iterdir() if entry.is_dir()}

    for element in elements:
        potcar_path = next(
            (
                potcar_root / f"{element}{suffix}" / "POTCAR"
                for suffix in ("_pv", "_sv", "", "_s")
                if f"{element}{suffix}" in available_dirs
            ),
            None,
        )
        if potcar_path is None:
            raise FileNotFoundError(f"No suitable POTCAR found for {element} in {potcar_root}")

        text = potcar_path.read_text()
        potcar_content.append(text)

        match = pair_re.search(text)
        if match:
            chosen = min(float(match.group(1)), float(match.group(2)))
        else:
            vals = [float(val) for val in single_re.findall(text)]
            if not vals:
                raise ValueError(f"No RWIGS entry found in {potcar_path}")
            chosen = min(vals)

        rwigs_values[element] = chosen
        picked_rwigs.append(chosen)
        print(f"{element}: POTCAR read from {potcar_path}")

    potcar_file = destination / "POTCAR"
    potcar_file.write_text("".join(potcar_content))

    min_latom_dis = min(picked_rwigs) if picked_rwigs else None
    return rwigs_values, min_latom_dis


def create_incar(content: str, directory: Path, filename: str) -> None:
    """Write an INCAR template to *directory*."""

    (Path(directory) / filename).write_text(content)


def create_simple_file(filename: str, content: str, directory: Path) -> None:
    """Write helper submission scripts to *directory*."""

    (Path(directory) / filename).write_text(content)


def create_input_dat(
    directory: Path,
    elements: Sequence[str],
    atom_counts: Sequence[int],
    distance_of_ion_matrix: Sequence[Sequence[float]],
    min_latom_dis: Optional[float],
    *,
    is_2d: bool = False,
    num_layers: int = 1,
    relax_z: bool = False,
    base_area: Optional[float] = None,
    layer_type_matrix: Optional[Sequence[Sequence[int]]] = None,
    formula_value: int = 1,
) -> None:
    """Generate *input.dat* for CALYPSO."""

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    system_name = "".join(f"{el}{count}" for el, count in zip(elements, atom_counts))
    name_of_atoms = " ".join(elements)
    number_of_atoms = " ".join(str(val) for val in atom_counts)
    distance_of_ion_str = "\n".join(
        " ".join(f"{value:.6f}" for value in row) for row in distance_of_ion_matrix
    )

    layer_type_str = ""
    if layer_type_matrix:
        layer_type_str = "\n".join(" ".join(str(val) for val in layer) for layer in layer_type_matrix)

    two_d_parameters = ""
    if is_2d:
        if base_area is None:
            raise ValueError("base_area must be provided for 2D calculations")
        adjusted_area = base_area * formula_value
        delta_z = 0.1 if relax_z else 0.0
        latom_line = f"LAtom_Dis = {min_latom_dis}" if min_latom_dis is not None else ""
        two_d_parameters = f"""
######### The Parameters For 2D Structure Prediction #############
# If True, a 2D structure prediction is performed.
2D = True
# The number of layers
MultiLayer = {num_layers}
# The Area of 2D system
Area = {adjusted_area}
# The distortion value along the C axis
DeltaZ = {delta_z}
# The gap between two layers
LayerGap=5
# The vacuum gap between the top surface of the slab and the top lattice, and between the bottom surface of the slab and the bottom lattice.
VacuumGap=20
# The number atoms for each layer
@LayerType
{layer_type_str}
@End
# Minimal distance between atoms of each chemical species. Unit is in angstrom.
{latom_line}
########################END 2D Parameters #########################
"""

    input_content = f"""################################ The Basic Parameters of CALYPSO ################################
# A string of one or several words contain a descriptCALYPSOive name of the system (max. 40 characters).
SystemName = {system_name}
# Number of different atomic species in the simulation.
NumberOfSpecies = {len(elements)}
# Element symbols of the different chemical species.
NameOfAtoms = {name_of_atoms}
# Number of atoms for each chemical species in one formula unit.
NumberOfAtoms = {number_of_atoms}
# The range of formula unit per cell in your simulation.
NumberOfFormula = 1 1
# The volume per formula unit. Unit is in angstrom^3.
Volume= 0
# Minimal distance between atoms of each chemical species. Unit is in angstrom.
@DistanceOfIon
{distance_of_ion_str}
@End
# It determines which algorithm should be adopted in the simulation.
Ialgo = 2
# Ialgo = 1 for Global PSO
# Ialgo = 2 for Local PSO (default value)
# The proportion of the structures generated by PSO.
PsoRatio = 0.6
# The popu2ation size. Normally, it has a larger number for larger systems.
PopSize = 40
# It determines which local optimization method should be interfaced in the simulation.
ICode = 1
# ICode= 1 interfaced with VASP
# ICode= 2 interfaced with SIESTA
# ICode= 3 interfaced with GULP
# The number of lbest for local PSO
NumberOfLbest = 4
# The Number of local optimization for each structure.
NumberOfLocalOptim = 2
# The command to perform local optimiztion calculation (e.g., VASP, SIESTA) on your computer.
Command = sh submit.sh
# The Max step for iteration
MaxStep = 50
# If True, a previous calculation will be continued.
PickUp = F
# At which step will the previous calculation be picked up.
PickStep =
MaxTime = 3600
# If True, the local optimizations performed by parallel
Parallel = T
# The number node for parallel
NumberOfParallel= 3
{two_d_parameters}
"""

    (directory / "input.dat").write_text(input_content)


def calculate_distance_of_ion(rwigs_values: Dict[str, float]) -> List[List[float]]:
    """Construct the DistanceOfIon block."""

    elements = list(rwigs_values.keys())
    matrix: List[List[float]] = []
    for element_i in elements:
        row = []
        for element_j in elements:
            row.append((rwigs_values[element_i] + rwigs_values[element_j]) * 0.6)
        matrix.append(row)
    return matrix


def adjust_input_dat(file_path: Path, multiplier: int) -> None:
    """Scale SystemName/NumberOfAtoms by *multiplier* in an existing input.dat."""

    file_path = Path(file_path)
    lines = file_path.read_text().splitlines(True)
    new_content: List[str] = []

    for line in lines:
        if line.startswith("SystemName = "):
            system_name = line.split("=", 1)[1].strip()
            new_content.append(f"SystemName = {system_name}{multiplier}\n")
        elif line.startswith("NumberOfAtoms = "):
            atoms = line.split("=", 1)[1].strip().split()
            scaled = " ".join(str(int(atom) * multiplier) for atom in atoms)
            new_content.append(f"NumberOfAtoms = {scaled}\n")
        else:
            new_content.append(line)

    file_path.write_text("".join(new_content))


def setup_calypso(config: SetupConfig) -> List[Path]:
    """Generate CALYPSO calculation directories based on *config*."""

    destination = config.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)

    rwigs_values, min_latom_dis = find_potcar(
        config.elements, destination, potcar_root=config.potcar_root
    )

    pstress_kbar_str = _format_pstress_kbar(config.pressure_gpa)

    incar_1_content = f"""SYSTEM = opt
PREC = Accurate
ENCUT = 300
KSPACING = 0.5
EDIFF = 1e-4
EDIFFG = -0.1
IBRION = 2
ISIF = 3
NSW = 60
ISTART = 0
ICHARG = 2
ISMEAR = 1
SIGMA = 0.05
LREAL = Auto
LCHARG = .F.
LWAVE = .F.
POTIM = 0.02
PSTRESS = {pstress_kbar_str}"""
    incar_2_content = f"""SYSTEM = opt
PREC = Accurate
ENCUT = 400
KSPACING = 0.25
EDIFF = 5e-5
EDIFFG = -0.03
IBRION = 2
ISIF = 3
NSW = 60
ISTART = 0
ICHARG = 2
ISMEAR = 1
SIGMA = 0.05
LREAL = Auto
LCHARG = .F.
LWAVE = .F.
POTIM = 0.02
PSTRESS = {pstress_kbar_str}"""

    create_incar(incar_1_content, destination, "INCAR_1")
    create_incar(incar_2_content, destination, "INCAR_2")

    calypso_exec = str(config.calypso_executable)
    vasp_exec = str(config.vasp_executable)

    calypso_fullnode_script = "calypso_fullnode.sh"
    calypso_script = "calypso.sh"

    calypso_fullnode_content = f"""#!/bin/bash
#SBATCH --job-name=caly48
#SBATCH --exclude=node[1-8],gpu[1-2]
#SBATCH --partition=chem352
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=48          # whole node (48 cores)
#SBATCH --cpus-per-task=1             # 1 CPU per MPI rank
#SBATCH --exclusive                   # no other *jobs* on this node
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err

# ‑‑‑ safety limits -----------------------------------------------------------
ulimit -s unlimited
ulimit -c unlimited
ulimit -d unlimited

# (optional) record which host(s) we received
scontrol show hostname "$SLURM_NODELIST" > machinefile

# ‑‑‑ launch CALYPSO driver (single rank, I/O‑bound) --------------------------
{calypso_exec}   > caly.log 2>&1"""

    calypso_content = f"""#!/bin/bash
#SBATCH --job-name=calypso
#SBATCH --exclude=node[1-8],gpu[1-2]
#SBATCH --partition=week-long
#SBATCH -N 1
#SBATCH -n 24
#SBATCH --mail-type=end
#SBATCH --output=%j.out
#SBATCH --error=%j.err

ulimit -s unlimited
#ulimit -m unlimited
ulimit -c unlimited
ulimit -d unlimited

#sleep 60
##for CALYPSO6.0
{calypso_exec}"""

    submit_sh_content = f"""#!/bin/bash
export OMP_NUM_THREADS=1
export I_MPI_PMI_LIBRARY=/usr/lib64/libpmi2.so   # drop if you switch to PMIx

srun --exact --mpi=pmi2 --ntasks=16 --cpus-per-task=1 --mem=80G --cpu-bind=cores \\
        {vasp_exec} > vasp.out  2> vasp.err"""

    create_simple_file(calypso_fullnode_script, calypso_fullnode_content, destination)
    create_simple_file(calypso_script, calypso_content, destination)
    create_simple_file("submit.sh", submit_sh_content, destination)

    distance_of_ion_matrix = calculate_distance_of_ion(rwigs_values)

    base_area: Optional[float] = None
    if config.is_2d:
        element_with_largest_rwigs = max(rwigs_values, key=rwigs_values.get)
        largest_rwigs_value = rwigs_values[element_with_largest_rwigs]
        count_of_element = config.atom_counts[config.elements.index(element_with_largest_rwigs)]
        base_area = count_of_element * math.pi * (largest_rwigs_value**2)

    files_to_copy = [
        "INCAR_1",
        "INCAR_2",
        "POTCAR",
        calypso_fullnode_script,
        calypso_script,
        "submit.sh",
    ]

    created_directories: List[Path] = []

    for formula_value in config.formula_multipliers:
        new_dir_path = destination / f"{formula_value}"
        new_dir_path.mkdir(parents=True, exist_ok=True)

        adjusted_atom_counts = [count * formula_value for count in config.atom_counts]

        adjusted_layer_type_matrix: Optional[List[List[int]]] = None
        if config.is_2d and config.layer_type_matrix:
            adjusted_layer_type_matrix = [
                [count * formula_value for count in layer] for layer in config.layer_type_matrix
            ]

        create_input_dat(
            new_dir_path,
            config.elements,
            adjusted_atom_counts,
            distance_of_ion_matrix,
            min_latom_dis,
            is_2d=config.is_2d,
            num_layers=config.num_layers,
            relax_z=config.relax_z,
            base_area=base_area,
            layer_type_matrix=adjusted_layer_type_matrix,
            formula_value=formula_value,
        )

        for file_name in files_to_copy:
            shutil.copy(destination / file_name, new_dir_path / file_name)

        print(f"Set up directory {new_dir_path}")
        created_directories.append(new_dir_path)

    for file_name in files_to_copy:
        try:
            (destination / file_name).unlink()
        except Exception as exc:  # pragma: no cover - informational
            print(f"Error occurred while deleting {(destination / file_name)}: {exc}")

    return created_directories


__all__ = [
    "DEFAULT_POTCAR_ROOT",
    "SetupConfig",
    "adjust_input_dat",
    "calculate_distance_of_ion",
    "create_input_dat",
    "create_incar",
    "create_simple_file",
    "find_potcar",
    "setup_calypso",
]
