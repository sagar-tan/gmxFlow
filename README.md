# gmxFlow

Terminal UI for GROMACS molecular dynamics simulation pipelines.

**Version: 2026.0.1** | **Workshop Exclusive**

## Installation

```bash
curl -sSL https://bit.ly/gmxFlow-1 | sudo bash
```

> **Note:** Requires a valid license key (provided during workshop).

## Update

```bash
sudo gmflo-update
```

## Usage

```bash
gmflo              # Run (mode selection)
gmflo --protein    # Protein-only mode
gmflo --ligand     # Protein+Ligand mode
gmflo --version    # Show version
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1-9` | Run step |
| `P` | Full pipeline |
| `S` | Settings |
| `A` | Analysis |
| `M` | Switch mode |
| `Q` | Quit |

## Requirements

- Python 3.8+ (for running source)
- GROMACS (`gmx` in PATH)
- License key (workshop exclusive)

## License

Proprietary - Workshop participants only. See LICENSE file.
