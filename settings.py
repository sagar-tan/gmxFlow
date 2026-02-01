"""
gmxFlow Settings Module
User-configurable settings for simulation parameters.
"""

import os
import json
from typing import Dict, Any, Optional

# Default simulation settings
DEFAULT_SETTINGS = {
    "md_length_ns": 1,           # Production MD length in nanoseconds
    "nvt_steps": 50000,          # NVT equilibration steps (100 ps at 2fs)
    "npt_steps": 50000,          # NPT equilibration steps (100 ps at 2fs)
    "temperature_k": 300,        # Temperature in Kelvin
    "pressure_bar": 1.0,         # Pressure in bar
    "dt_ps": 0.002,              # Timestep in ps (2 fs)
    "simulation_mode": "protein_only",  # "protein_only" or "protein_ligand"
}

SETTINGS_FILE = ".gmxflow_settings.json"


def get_settings_path(directory: str = ".") -> str:
    """Get path to settings file."""
    return os.path.join(directory, SETTINGS_FILE)


def load_settings(directory: str = ".") -> Dict[str, Any]:
    """
    Load settings from file, or return defaults if not found.
    """
    settings_path = get_settings_path(directory)
    
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                loaded = json.load(f)
                # Merge with defaults to handle new settings
                merged = DEFAULT_SETTINGS.copy()
                merged.update(loaded)
                return merged
        except Exception:
            pass
    
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any], directory: str = ".") -> bool:
    """
    Save settings to file.
    
    Returns:
        True if saved successfully
    """
    settings_path = get_settings_path(directory)
    
    try:
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception:
        return False


def calculate_md_steps(md_length_ns: float, dt_ps: float = 0.002) -> int:
    """
    Calculate number of MD steps from desired length in nanoseconds.
    
    Args:
        md_length_ns: Desired simulation length in ns
        dt_ps: Timestep in picoseconds (default 2 fs = 0.002 ps)
    
    Returns:
        Number of steps
    """
    # ns to ps: multiply by 1000
    # steps = time_ps / dt_ps
    time_ps = md_length_ns * 1000
    return int(time_ps / dt_ps)


def get_md_steps(settings: Dict[str, Any]) -> int:
    """Get MD steps from settings."""
    return calculate_md_steps(
        settings.get("md_length_ns", 1),
        settings.get("dt_ps", 0.002)
    )


# MDP file templates
MDP_TEMPLATES = {
    "ions": """; ions.mdp - for ion addition
integrator  = steep
emtol       = 1000.0
emstep      = 0.01
nsteps      = 50000
nstlist     = 1
cutoff-scheme = Verlet
ns_type     = grid
coulombtype = cutoff
rcoulomb    = 1.0
rvdw        = 1.0
pbc         = xyz
""",
    
    "minim": """; minim.mdp - Energy Minimization
integrator  = steep
emtol       = 1000.0
emstep      = 0.01
nsteps      = 50000
nstlist     = 1
cutoff-scheme = Verlet
ns_type     = grid
coulombtype = PME
rcoulomb    = 1.0
rvdw        = 1.0
pbc         = xyz
""",
    
    "nvt": """; nvt.mdp - NVT Equilibration
define      = -DPOSRES
integrator  = md
nsteps      = {nsteps}
dt          = {dt}
nstxout     = 500
nstvout     = 500
nstenergy   = 500
nstlog      = 500
continuation = no
constraint_algorithm = lincs
constraints = h-bonds
lincs_iter  = 1
lincs_order = 4
cutoff-scheme = Verlet
ns_type     = grid
nstlist     = 10
rcoulomb    = 1.0
rvdw        = 1.0
coulombtype = PME
pme_order   = 4
fourierspacing = 0.16
tcoupl      = V-rescale
tc-grps     = System
tau_t       = 0.1
ref_t       = {temperature}
pcoupl      = no
pbc         = xyz
DispCorr    = EnerPres
gen_vel     = yes
gen_temp    = {temperature}
gen_seed    = -1
""",
    
    "npt": """; npt.mdp - NPT Equilibration
define      = -DPOSRES
integrator  = md
nsteps      = {nsteps}
dt          = {dt}
nstxout     = 500
nstvout     = 500
nstenergy   = 500
nstlog      = 500
continuation = yes
constraint_algorithm = lincs
constraints = h-bonds
lincs_iter  = 1
lincs_order = 4
cutoff-scheme = Verlet
ns_type     = grid
nstlist     = 10
rcoulomb    = 1.0
rvdw        = 1.0
coulombtype = PME
pme_order   = 4
fourierspacing = 0.16
tcoupl      = V-rescale
tc-grps     = System
tau_t       = 0.1
ref_t       = {temperature}
pcoupl      = Parrinello-Rahman
pcoupltype  = isotropic
tau_p       = 2.0
ref_p       = {pressure}
compressibility = 4.5e-5
refcoord_scaling = com
pbc         = xyz
DispCorr    = EnerPres
gen_vel     = no
""",
    
    "md": """; md.mdp - Production MD
integrator  = md
nsteps      = {nsteps}
dt          = {dt}
nstxout     = 0
nstvout     = 0
nstfout     = 0
nstenergy   = 5000
nstlog      = 5000
nstxout-compressed = 5000
compressed-x-grps  = System
continuation = yes
constraint_algorithm = lincs
constraints = h-bonds
lincs_iter  = 1
lincs_order = 4
cutoff-scheme = Verlet
ns_type     = grid
nstlist     = 10
rcoulomb    = 1.0
rvdw        = 1.0
coulombtype = PME
pme_order   = 4
fourierspacing = 0.16
tcoupl      = V-rescale
tc-grps     = System
tau_t       = 0.1
ref_t       = {temperature}
pcoupl      = Parrinello-Rahman
pcoupltype  = isotropic
tau_p       = 2.0
ref_p       = {pressure}
compressibility = 4.5e-5
pbc         = xyz
DispCorr    = EnerPres
gen_vel     = no
"""
}


def generate_mdp_file(
    template_name: str,
    settings: Dict[str, Any],
    output_path: str
) -> bool:
    """
    Generate an MDP file from template with settings applied.
    
    Args:
        template_name: Name of template (ions, minim, nvt, npt, md)
        settings: Settings dictionary
        output_path: Path to write MDP file
    
    Returns:
        True if successful
    """
    template = MDP_TEMPLATES.get(template_name)
    if not template:
        return False
    
    try:
        # Calculate steps based on template type
        if template_name == "nvt":
            nsteps = settings.get("nvt_steps", 50000)
        elif template_name == "npt":
            nsteps = settings.get("npt_steps", 50000)
        elif template_name == "md":
            nsteps = get_md_steps(settings)
        else:
            nsteps = 50000
        
        # Format template
        content = template.format(
            nsteps=nsteps,
            dt=settings.get("dt_ps", 0.002),
            temperature=settings.get("temperature_k", 300),
            pressure=settings.get("pressure_bar", 1.0)
        )
        
        with open(output_path, 'w') as f:
            f.write(content)
        
        return True
    except Exception:
        return False


def generate_all_mdp_files(settings: Dict[str, Any], directory: str = ".") -> Dict[str, bool]:
    """
    Generate all required MDP files.
    
    Returns:
        Dict mapping filename to success status
    """
    results = {}
    
    for name in ["ions", "minim", "nvt", "npt", "md"]:
        output_path = os.path.join(directory, f"{name}.mdp")
        results[f"{name}.mdp"] = generate_mdp_file(name, settings, output_path)
    
    return results
