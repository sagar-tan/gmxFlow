# gmxFlow

Terminal UI for GROMACS molecular dynamics simulation pipelines.

## Quick Start (Linux/WSL)

```bash
# 1. Copy gmxflow to your simulation directory
cp -r /path/to/gmxFlow/* /path/to/simulation/

# 2. Ensure GROMACS is available
source /usr/local/gromacs/bin/GMXRC  # or your GROMACS path

# 3. Run gmxFlow
python3 gmxflow.py

# OR install globally (optional)
chmod +x gmxflow.py
sudo cp gmxflow.py /usr/local/bin/gmxflow
```

## Required Input Files

Place these files in your simulation directory:
- `protein_only.pdb` - Protein structure
- `ligand.gro` - Ligand coordinates
- `ligand.itp` - Ligand topology
- `minim.mdp`, `nvt.mdp`, `npt.mdp`, `md.mdp` - Parameter files

## Usage

```bash
# Normal mode
python3 gmxflow.py

# Dry-run mode (shows commands without executing)
python3 gmxflow.py --dry-run

# Check version
python3 gmxflow.py --version
```

## Pipeline Steps

| # | Step | Notes |
|---|------|-------|
| 1 | Generate Topology | **Interactive**: Select force field 15 (OPLS-AA) |
| 2 | Insert Ligand | Automatic |
| 3 | Define Box | Automatic |
| 4 | Solvate | **Manual edit needed after** - see below |
| 5 | Energy Minimization | Automatic |
| 6 | Index Generation | **Interactive**: Create protein+ligand group |
| 7 | NVT Equilibration | Automatic |
| 8 | NPT Equilibration | Automatic |
| 9 | Production MD | Automatic |

## Step Locking

Steps must run in order. Each creates a `.step#.done` flag.
- Step 5 won't run until Steps 1-4 complete
- Analysis won't run until Step 9 completes

## Manual Edit After Step 4

Edit `topol.top`:
```
; Add after #include "forcefield.itp"
#include "ligand.itp"

; Add to [ molecules ] section at bottom
UNK     1
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1-9` | Run pipeline step |
| `P` | **Run full pipeline** |
| `A` | Analysis tools |
| `V` | Visualization (VMD/xmgrace) |
| `F` | File check |
| `R` | Reset all .done flags |
| `Q` | Quit |

## Testing in WSL

```bash
# In WSL, navigate to simulation folder with input files
cd /mnt/c/your/simulation/folder

# Copy gmxFlow files here (or access from Windows path)
cp /path/to/gmxFlow/*.py .

# Run
python3 gmxflow.py
```

## Dependencies

- **Python 3.8+**
- **GROMACS** (`gmx` in PATH)
- **Optional**: `rich` library (falls back to plain text if missing)
- **Optional**: VMD, xmgrace

## No Virtual Environment Required

Works with system Python. Install rich optionally:
```bash
pip3 install rich  # Optional, for colored output
```
