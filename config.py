"""
gmxFlow Configuration Module
Contains pipeline step definitions, UI settings, and constants.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict

# Application metadata
APP_NAME = "gmxFlow"
APP_VERSION = "2026.0.1"
APP_DESCRIPTION = "GROMACS Pipeline Manager"

# Mandatory input files
MANDATORY_FILES = [
    "protein_only.pdb",
    "ligand.gro",
    "ligand.itp",
    "minim.mdp",
    "nvt.mdp",
    "npt.mdp",
    "md.mdp"
]

# ASCII Art Banner
BANNER = r"""
    ██████╗ ███╗   ███╗██╗  ██╗███████╗██╗      ██████╗ ██╗    ██╗
   ██╔════╝ ████╗ ████║╚██╗██╔╝██╔════╝██║     ██╔═══██╗██║    ██║
   ██║  ███╗██╔████╔██║ ╚███╔╝ █████╗  ██║     ██║   ██║██║ █╗ ██║
   ██║   ██║██║╚██╔╝██║ ██╔██╗ ██╔══╝  ██║     ██║   ██║██║███╗██║
   ╚██████╔╝██║ ╚═╝ ██║██╔╝ ██╗██║     ███████╗╚██████╔╝╚███╔███╔╝
    ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝ 
"""


@dataclass
class PipelineStep:
    """Represents a single pipeline step."""
    id: int
    name: str
    command: str
    produces: List[str] = field(default_factory=list)
    user_input_required: bool = False
    blocking: bool = True
    manual_intervention: Optional[Dict] = None
    post_steps: List[str] = field(default_factory=list)


# Pipeline step definitions
PIPELINE_STEPS = [
    PipelineStep(
        id=1,
        name="Generate Protein Topology",
        command="gmx pdb2gmx -f protein_only.pdb -o protein.gro -water spce -ignh",
        produces=["protein.gro", "topol.top"],
        user_input_required=True
    ),
    PipelineStep(
        id=2,
        name="Insert Ligand",
        command="gmx insert-molecules -f protein.gro -ci ligand.gro -o complex.gro -nmol 1",
        produces=["complex.gro"]
    ),
    PipelineStep(
        id=3,
        name="Define Simulation Box",
        command="gmx editconf -f complex.gro -o complex_box.gro -c -d 1.0 -bt cubic",
        produces=["complex_box.gro"]
    ),
    PipelineStep(
        id=4,
        name="Solvate System",
        command="gmx solvate -cp complex_box.gro -cs spc216.gro -o complex_solv.gro -p topol.top",
        produces=["complex_solv.gro"],
        post_steps=["Auto-patch topol.top with ligand"]
    ),
    PipelineStep(
        id=5,
        name="Energy Minimization",
        command="gmx grompp -f minim.mdp -c complex_solv.gro -p topol.top -o em.tpr -maxwarn 1 && gmx mdrun -v -deffnm em",
        produces=["em.gro", "em.edr"]
    ),
    PipelineStep(
        id=6,
        name="Index Generation",
        command="echo -e '1 | 13\\nq' | gmx make_ndx -f em.gro -o index.ndx",
        produces=["index.ndx"],
        post_steps=["Create Protein_LIG index group"]
    ),
    PipelineStep(
        id=7,
        name="NVT Equilibration",
        command="gmx grompp -f nvt.mdp -c em.gro -r em.gro -p topol.top -n index.ndx -o nvt.tpr -maxwarn 1 && gmx mdrun -v -deffnm nvt",
        produces=["nvt.gro", "nvt.edr"]
    ),
    PipelineStep(
        id=8,
        name="NPT Equilibration",
        command="gmx grompp -f npt.mdp -c nvt.gro -r nvt.gro -t nvt.cpt -p topol.top -n index.ndx -o npt.tpr -maxwarn 1 && gmx mdrun -v -deffnm npt",
        produces=["npt.gro", "npt.edr"]
    ),
    PipelineStep(
        id=9,
        name="Production MD",
        command="gmx grompp -f md.mdp -c npt.gro -t npt.cpt -p topol.top -n index.ndx -o md.tpr -maxwarn 1 && gmx mdrun -v -deffnm md",
        produces=["md.xtc", "md.edr", "md.gro"]
    ),
]


@dataclass
class AnalysisStep:
    """Represents an analysis feature."""
    name: str
    command: str
    output_file: str


# Analysis features (for Protein+Ligand mode)
ANALYSIS_STEPS = [
    AnalysisStep(
        name="Trajectory PBC Fix",
        command="echo '1\n0' | gmx trjconv -s md.tpr -f md.xtc -o md_noPBC.xtc -center -pbc mol -ur compact",
        output_file="md_noPBC.xtc"
    ),
    AnalysisStep(
        name="Trajectory Fit",
        command="echo '4\n0' | gmx trjconv -s md.tpr -f md_noPBC.xtc -o md_fit.xtc -fit rot+trans",
        output_file="md_fit.xtc"
    ),
    AnalysisStep(
        name="Backbone RMSD",
        command="echo '4\n4' | gmx rms -s md.tpr -f md_fit.xtc -n index.ndx -o rmsd_backbone.xvg",
        output_file="rmsd_backbone.xvg"
    ),
    AnalysisStep(
        name="Ligand RMSD",
        command="echo '13\n13' | gmx rms -s md.tpr -f md_fit.xtc -n index.ndx -o rmsd_ligand.xvg",
        output_file="rmsd_ligand.xvg"
    ),
    AnalysisStep(
        name="Protein-Ligand Distance",
        command="gmx distance -s md.tpr -f md_fit.xtc -select 'com of group Protein plus com of group UNK' -oall lig_dist.xvg",
        output_file="lig_dist.xvg"
    ),
]


# ============================================================
# PROTEIN-ONLY SIMULATION MODE
# ============================================================

PROTEIN_MANDATORY_FILES = [
    "Protein.pdb",
]

PROTEIN_PIPELINE_STEPS = [
    PipelineStep(
        id=1,
        name="Protein Preprocessing",
        command="grep -v HOH Protein.pdb > clean.pdb",
        produces=["clean.pdb"]
    ),
    PipelineStep(
        id=2,
        name="Protein Topology Generation",
        command="gmx pdb2gmx -f clean.pdb -o protein.gro -water spce -ignh",
        produces=["protein.gro", "topol.top"],
        user_input_required=True
    ),
    PipelineStep(
        id=3,
        name="Define Simulation Box",
        command="gmx editconf -f protein.gro -o box.gro -c -d 1.0 -bt cubic",
        produces=["box.gro"]
    ),
    PipelineStep(
        id=4,
        name="Solvate System",
        command="gmx solvate -cp box.gro -cs spc216.gro -o solve.gro -p topol.top",
        produces=["solve.gro"]
    ),
    PipelineStep(
        id=5,
        name="Add Ions (Neutralize)",
        command="gmx grompp -f ions.mdp -c solve.gro -p topol.top -o ions.tpr -maxwarn 1 && gmx genion -s ions.tpr -o solve_ions.gro -p topol.top -pname NA -nname CL -neutral",
        produces=["solve_ions.gro"],
        user_input_required=True
    ),
    PipelineStep(
        id=6,
        name="Energy Minimization",
        command="gmx grompp -f minim.mdp -c solve_ions.gro -p topol.top -o em.tpr -maxwarn 1 && gmx mdrun -v -deffnm em",
        produces=["em.gro", "em.edr"]
    ),
    PipelineStep(
        id=7,
        name="NVT Equilibration",
        command="gmx grompp -f nvt.mdp -c em.gro -r em.gro -p topol.top -o nvt.tpr -maxwarn 1 && gmx mdrun -v -deffnm nvt",
        produces=["nvt.gro", "nvt.edr"]
    ),
    PipelineStep(
        id=8,
        name="NPT Equilibration",
        command="gmx grompp -f npt.mdp -c nvt.gro -r nvt.gro -t nvt.cpt -p topol.top -o npt.tpr -maxwarn 1 && gmx mdrun -v -deffnm npt",
        produces=["npt.gro", "npt.edr"]
    ),
    PipelineStep(
        id=9,
        name="Production MD",
        command="gmx grompp -f md.mdp -c npt.gro -t npt.cpt -p topol.top -o md.tpr -maxwarn 1 && gmx mdrun -v -deffnm md",
        produces=["md.xtc", "md.edr", "md.gro"]
    ),
]

# Analysis features (for Protein-Only mode)
PROTEIN_ANALYSIS_STEPS = [
    AnalysisStep(
        name="Trajectory Cleaning",
        command="gmx trjconv -f md.xtc -s md.tpr -o md_noPBC.xtc -pbc mol -center",
        output_file="md_noPBC.xtc"
    ),
    AnalysisStep(
        name="Backbone RMSD",
        command="gmx rms -f md_noPBC.xtc -s md.tpr -o rmsd.xvg",
        output_file="rmsd.xvg"
    ),
    AnalysisStep(
        name="RMSD (ns scale)",
        command="gmx rms -f md_noPBC.xtc -s md.tpr -o rmsd_ns.xvg -tu ns",
        output_file="rmsd_ns.xvg"
    ),
    AnalysisStep(
        name="RMSF (C-alpha)",
        command="gmx rmsf -f md_noPBC.xtc -s md.tpr -o rmsf_ca.xvg",
        output_file="rmsf_ca.xvg"
    ),
    AnalysisStep(
        name="RMSF per Residue",
        command="gmx rmsf -f md_noPBC.xtc -s md.tpr -o rmsf_res.xvg -res",
        output_file="rmsf_res.xvg"
    ),
    AnalysisStep(
        name="Radius of Gyration",
        command="gmx gyrate -f md_noPBC.xtc -s md.tpr -o gyrate.xvg",
        output_file="gyrate.xvg"
    ),
]

# UI Colors (for rich library)
UI_COLORS = {
    "header": "bold cyan",
    "menu_item": "white",
    "menu_selected": "bold green",
    "status_pending": "dim white",
    "status_running": "bold yellow",
    "status_complete": "bold green",
    "status_error": "bold red",
    "log_info": "blue",
    "log_warning": "yellow",
    "log_error": "red",
    "border": "cyan",
}

# Status symbols
STATUS_SYMBOLS = {
    "pending": "○",
    "running": "◐",
    "complete": "●",
    "error": "✗",
}

