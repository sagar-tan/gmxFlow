# gmxFlow

Terminal UI for GROMACS molecular dynamics simulation pipelines.

**Version: 2026.0.1**

## Installation

### One-Line Install (Linux/WSL)
```bash
curl -sSL https://raw.githubusercontent.com/sagar-tan/gmxFlow/main/install.sh | sudo bash
curl -sSL https://raw.githubusercontent.com/USER/gmxFlow/main/install.sh | sudo bash
```

### Manual Install
```bash
git clone https://github.com/sagar-tan/gmxFlow.git
cd gmxFlow
sudo ./install.sh
```

### Portable (No Install)
```bash
git clone https://github.com/USER/gmxFlow.git
cd gmxFlow
python3 gmxflow.py
```

## Usage

```bash
gmflo              # Run gmxFlow (mode selection)
gmflo --protein    # Protein-only mode
gmflo --ligand     # Protein+Ligand mode
gmflo --dry-run    # Preview commands
gmflo --version    # Show version
```

## Simulation Modes

| Mode | Input Files | Steps |
|------|-------------|-------|
| Protein Only | `Protein.pdb` | 9 (with ion neutralization) |
| Protein+Ligand | `protein_only.pdb`, `ligand.gro`, `ligand.itp` | 9 (auto-patches topology) |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1-9` | Run step |
| `P` | Full pipeline |
| `S` | Settings |
| `G` | Generate MDP |
| `A` | Analysis |
| `M` | Switch mode |
| `R` | Reset flags |
| `Q` | Quit |

## Post-Step Visualizations

- **After EM**: potential.xvg
- **After NVT**: temperature.xvg  
- **After NPT**: pressure.xvg, density.xvg
- **After MD**: Launch VMD

## Dependencies

- Python 3.8+
- GROMACS (`gmx` in PATH)
- Optional: `rich` (colors), VMD, xmgrace

## Update

```bash
sudo gmflo-update
```

## Uninstall

```bash
sudo /usr/local/gmxflow/uninstall.sh
# or
sudo rm -rf /usr/local/gmxflow /usr/local/bin/gmflo
```
