# gmxFlow Developer Commands Guide

This document outlines the internal GROMACS commands executed by gmxFlow during its pipeline. It provides developers with testing guidelines to reproduce, debug, or tweak the pipeline without using the gmxFlow TUI.

## Architecture Overview
gmxFlow serves as a Terminal User Interface (TUI) wrapper over the GROMACS suite.
- **`config.py`**: Stores all pipeline steps (`PIPELINE_STEPS` and `PROTEIN_PIPELINE_STEPS`), defining what `gmx` commands to run.
- **`pipeline.py` & `gmxflow.py`**: Handle execution, step tracking, dependency checks, and UI interaction (e.g. `--dry-run`).

---

## Testing Guidelines

### 1. Using Dry-Run Mode
The easiest way to test how commands are generated without executing them is:
```bash
python3 gmxflow.py --dry-run
# or
gmflo --dry-run
```
This mode lets you simulate running each step and will print the exact `gmx` command that would have been executed, substituting in user choices like force fields.

### 2. Manual Command Execution
To debug a failing step, you can run the commands directly in your terminal from the working directory. Below are the commands executed by the application in both simulation modes.

---

## Commands Breakdown

### Mode 1: Protein-Only

| Step | Operation | Internal Command Executed |
|------|-----------|---------------------------|
| **1** | Preprocessing | `grep -v HOH Protein.pdb > clean.pdb` |
| **2** | Topology Gen | `echo '<FF_CHOICE>' \| gmx pdb2gmx -f clean.pdb -o protein.gro -water spce -ignh` |
| **3** | Define Box | `gmx editconf -f protein.gro -o box.gro -c -d 1.0 -bt cubic` |
| **4** | Solvate | `gmx solvate -cp box.gro -cs spc216.gro -o solve.gro -p topol.top` |
| **5** | Add Ions | `gmx grompp -f ions.mdp -c solve.gro -p topol.top -o ions.tpr -maxwarn 1 && echo '<ION_GROUP>' \| gmx genion -s ions.tpr -o solve_ions.gro -p topol.top -pname NA -nname CL -neutral` |
| **6** | Energy Minimization | `gmx grompp -f minim.mdp -c solve_ions.gro -p topol.top -o em.tpr -maxwarn 1 && gmx mdrun -v -deffnm em` |
| **7** | NVT Equilibration | `gmx grompp -f nvt.mdp -c em.gro -r em.gro -p topol.top -o nvt.tpr -maxwarn 1 && gmx mdrun -v -deffnm nvt` |
| **8** | NPT Equilibration | `gmx grompp -f npt.mdp -c nvt.gro -r nvt.gro -t nvt.cpt -p topol.top -o npt.tpr -maxwarn 1 && gmx mdrun -v -deffnm npt` |
| **9** | Production MD | `gmx grompp -f md.mdp -c npt.gro -t npt.cpt -p topol.top -o md.tpr -maxwarn 1 && gmx mdrun -v -deffnm md` |

**Analysis Commands (Protein Only):**
- **Trajectory Cleaning**: `echo '1\n0' \| gmx trjconv -f md.xtc -s md.tpr -o md_noPBC.xtc -pbc mol -center`
- **Backbone RMSD**: `echo '4\n4' \| gmx rms -f md_noPBC.xtc -s md.tpr -o rmsd.xvg`
- **RMSD (ns scale)**: `echo '4\n4' \| gmx rms -f md_noPBC.xtc -s md.tpr -o rmsd_ns.xvg -tu ns`
- **RMSF**: `echo '3' \| gmx rmsf -f md_noPBC.xtc -s md.tpr -o rmsf_ca.xvg`
- **RMSF per residue**: `echo '1' \| gmx rmsf -f md_noPBC.xtc -s md.tpr -o rmsf_res.xvg -res`
- **Radius of Gyration**: `echo '1' \| gmx gyrate -f md_noPBC.xtc -s md.tpr -o gyrate.xvg`

---

### Mode 2: Protein + Ligand Complex

| Step | Operation | Internal Command Executed |
|------|-----------|---------------------------|
| **1** | Topology Gen | `echo '<FF_CHOICE>' \| gmx pdb2gmx -f protein_only.pdb -o protein.gro -water spce -ignh` |
| **2** | Insert Ligand | `gmx insert-molecules -f protein.gro -ci ligand.gro -o complex.gro -nmol 1` |
| **3** | Define Box | `gmx editconf -f complex.gro -o complex_box.gro -c -d 1.0 -bt cubic` |
| **4** | Solvate | `gmx solvate -cp complex_box.gro -cs spc216.gro -o complex_solv.gro -p topol.top` |
| **4.5** | Auto-Patching | *Implicit step: Modifies `topol.top` to include `ligand.itp`* |
| **5** | Energy Minimization | `gmx grompp -f minim.mdp -c complex_solv.gro -p topol.top -o em.tpr -maxwarn 1 && gmx mdrun -v -deffnm em` |
| **6** | Index Generation | `echo -e '1 \| 13\nq' \| gmx make_ndx -f em.gro -o index.ndx` |
| **7** | NVT Equilibration | `gmx grompp -f nvt.mdp -c em.gro -r em.gro -p topol.top -n index.ndx -o nvt.tpr -maxwarn 1 && gmx mdrun -v -deffnm nvt` |
| **8** | NPT Equilibration | `gmx grompp -f npt.mdp -c nvt.gro -r nvt.gro -t nvt.cpt -p topol.top -n index.ndx -o npt.tpr -maxwarn 1 && gmx mdrun -v -deffnm npt` |
| **9** | Production MD | `gmx grompp -f md.mdp -c npt.gro -t npt.cpt -p topol.top -n index.ndx -o md.tpr -maxwarn 1 && gmx mdrun -v -deffnm md` |

**Analysis Commands (Protein + Ligand):**
- **Trajectory PBC Fix**: `echo '1\n0' \| gmx trjconv -s md.tpr -f md.xtc -o md_noPBC.xtc -center -pbc mol -ur compact`
- **Trajectory Fit**: `echo '4\n0' \| gmx trjconv -s md.tpr -f md_noPBC.xtc -o md_fit.xtc -fit rot+trans`
- **Ligand RMSD**: `echo '13\n13' \| gmx rms -s md.tpr -f md_fit.xtc -n index.ndx -o rmsd_ligand.xvg`
- **Protein-Ligand Distance**: `gmx distance -s md.tpr -f md_fit.xtc -select 'com of group Protein plus com of group UNK' -oall lig_dist.xvg`

## Customizing testing
Should you need to change constraints or maxwarnings, you can manually append `-maxwarn X` to `grompp` commands or tweak the respective `.mdp` files before execution. Use the `--dry-run` flag in gmxFlow prior to confirming changes.
