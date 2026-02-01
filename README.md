# gmxFlow

Terminal UI for GROMACS molecular dynamics simulation pipelines.

**Version: 2026.0.1**

## Installation

### Option 1: pipx (Recommended for Ubuntu 22.04+)
```bash
# Install pipx (one-time)
sudo apt install pipx
pipx ensurepath
source ~/.bashrc

# Install gmxFlow
pipx install git+https://github.com/sagar-tan/gmxFlow.git
```

### Option 2: pip with --break-system-packages
```bash
pip3 install --user --break-system-packages git+https://github.com/sagar-tan/gmxFlow.git
```

### Option 3: Portable (no install)
```bash
git clone https://github.com/sagar-tan/gmxFlow.git
cd gmxFlow
python3 gmxflow.py
```

## Update
```bash
pipx upgrade gmxflow
# or
pipx install --force git+https://github.com/sagar-tan/gmxFlow.git
```

## Usage

```bash
gmflo              # Run gmxFlow
gmflo --protein    # Protein-only mode
gmflo --ligand     # Protein+Ligand mode
gmflo --dry-run    # Preview commands
gmflo --version    # Show version
```

## Simulation Modes

| Mode | Input Files |
|------|-------------|
| Protein Only | `Protein.pdb` |
| Protein+Ligand | `protein_only.pdb`, `ligand.gro`, `ligand.itp` |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1-9` | Run step |
| `P` | Full pipeline |
| `S` | Settings |
| `A` | Analysis |
| `M` | Switch mode |
| `Q` | Quit |

## Uninstall

```bash
pipx uninstall gmxflow
```
