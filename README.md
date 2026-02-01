# gmxFlow

Terminal UI for GROMACS molecular dynamics simulation pipelines.

**Version: 2026.0.1**

## Installation

### Option 1: pip install (Recommended - always gets latest)
```bash
pip3 install --user git+https://github.com/sagar-tan/gmxFlow.git

# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Option 2: Clone and install
```bash
git clone https://github.com/sagar-tan/gmxFlow.git
cd gmxFlow
pip3 install --user .
```

### Option 3: Portable (no install)
```bash
git clone https://github.com/sagar-tan/gmxFlow.git
cd gmxFlow
python3 gmxflow.py
```

## Update
```bash
pip3 install --user --upgrade git+https://github.com/sagar-tan/gmxFlow.git
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

## Uninstall

```bash
pip3 uninstall gmxflow
```
