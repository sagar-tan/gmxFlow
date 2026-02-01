# gmxFlow

A terminal user interface (TUI) application for running GROMACS molecular dynamics simulation pipelines.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![GROMACS](https://img.shields.io/badge/GROMACS-Required-green)

## Features

- **9-Step MD Pipeline**: Complete workflow from protein topology to production MD
- **Interactive TUI**: Keyboard-driven menu navigation
- **Real-time Output**: Live command output display
- **Analysis Tools**: Trajectory cleaning, RMSD calculations
- **Visualization**: VMD and xmgrace integration

## Installation

```bash
# Clone or download gmxFlow
git clone <repository-url>
cd gmxFlow

# Install dependencies
pip install -r requirements.txt

# Make executable (Linux/Mac)
chmod +x gmxflow.py

# Optional: Add to PATH
sudo cp gmxflow.py /usr/local/bin/gmxflow
```

## Requirements

- **Python >= 3.8**
- **GROMACS** (gmx available in PATH)
- **Optional**: VMD, xmgrace for visualization

## Usage

```bash
# Navigate to your simulation directory
cd /path/to/your/simulation

# Ensure required input files are present:
# - protein_only.pdb
# - ligand.gro
# - ligand.itp
# - minim.mdp, nvt.mdp, npt.mdp, md.mdp

# Run gmxFlow
python gmxflow.py
# or if installed in PATH:
gmxflow
```

## Pipeline Steps

| Step | Name | Description |
|------|------|-------------|
| 1 | Generate Protein Topology | Run pdb2gmx to create topology |
| 2 | Insert Ligand | Add ligand molecule to system |
| 3 | Define Simulation Box | Create cubic simulation box |
| 4 | Solvate System | Add water molecules |
| 5 | Energy Minimization | Minimize system energy |
| 6 | Index Generation | Create index groups |
| 7 | NVT Equilibration | Temperature equilibration |
| 8 | NPT Equilibration | Pressure equilibration |
| 9 | Production MD | Run production simulation |

## Keyboard Navigation

| Key | Action |
|-----|--------|
| `1-9` | Run pipeline step |
| `A` | Analysis tools |
| `V` | Visualization menu |
| `F` | File check |
| `R` | Reset step status |
| `H` | Help |
| `Q` | Quit |

## Analysis Features

- **Trajectory Cleaning**: Center and fit trajectory
- **Backbone RMSD**: Calculate backbone RMSD
- **Ligand RMSD**: Calculate ligand RMSD
- **Protein-Ligand Distance**: Monitor binding distance

## License

MIT License
