# gmxFlow User Manual

Welcome to **gmxFlow**, an interactive Terminal User Interface (TUI) designed to streamline and automate GROMACS molecular dynamics simulations.

---

## 1. Features
gmxFlow simplifies complex MD pipelines into a numbered, step-by-step checklist. It features:
- **Two Simulation Modes**:
  - **Protein Only**: Simulates a single protein in water with automatically neutralized ions.
  - **Protein + Ligand**: Simulates a protein-ligand complex with automatic topology patching.
- **Dependency Tracking**: Prevents running a step if its prerequisites haven't been met.
- **Resume Capability**: Detects existing output files and allows skipping steps you've already run.
- **Interactive Visualization**: Automatically suggests launching VMD for trajectory viewing or `xmgrace` for graph plotting when steps finish.
- **Full Automation**: The "Full Pipeline" option will run from topology generation through to Production MD without manual intervention.

---

## 2. Installation and First Run

Ensure you have GROMACS installed and added to your `PATH`.

### Prerequisites (Fresh WSL/Linux)
If you are starting from a fresh Linux or WSL environment, you must install Python, `pip`, and `git` first:
```bash
sudo apt update
sudo apt install -y python3 python3-pip git curl
```

### Installing
Run the following script to install gmxFlow on your system:
```bash
curl -sSL https://bit.ly/gmxFlow-1 | sudo bash
```

*(Optional)* For an enhanced visual experience with colored and neatly boxed output, install the `rich` Python library:
```bash
pip3 install rich
```

### First Run & Activation
Start the application from your terminal:
```bash
gmflo
```
Upon your first run, you will be prompted for a workshop license key. Once activated, you will be taken to the mode selection screen.

---

## 3. Starting the Tool

You can start the tool in interactive mode, or bypass the mode selection directly via flags:
- `gmflo` : Starts the app and asks you to select between Protein-Only or Protein+Ligand mode.
- `gmflo --protein` : Directly starts in Protein-Only mode.
- `gmflo --ligand` : Directly starts in Protein+Ligand mode.
- `gmflo --dry-run` : Runs the UI without actually executing the underlying GROMACS commands (useful for safely viewing the intended execution sequence).

---

## 4. Pipeline Execution & Usage

Once in the main interface, gmxFlow displays a system status panel verifying your `gmx` executable and input files. Below this, the 10-step pipeline (or 9 steps in Protein-Only mode) is presented. 

### Mandatory Input Files
Place these in your working directory before beginning:
- **Protein Only mode**: `Protein.pdb`
- **Protein + Ligand mode**: `protein_only.pdb`, `ligand.gro`, `ligand.itp`, `minim.mdp`, `nvt.mdp`, `npt.mdp`, `md.mdp` *(Note: MDP files can be generated from the Settings menu)*.

### Interactive Commands
Use these keys from the main menu:

| Key | Action |
|-----|--------|
| `1-0` | Run the corresponding step individually (Step 10 is accessed by pressing `0`). Dependencies and output overwrites are checked automatically. |
| `P` | Run the full pipeline automatically. You will be prompted upfront for force field choices and ion groups, after which execution requires no input. |
| `A` | Open the Analysis menu to generate RMSD, RMSF, Radius of Gyration, or Ligand Distance plots. |
| `V` | Open the Visualization menu to inspect `.xvg` graphs via `xmgrace`. |
| `S` | Access Settings (adjust MD length, temperature, steps, or auto-generate missing MDP files). |
| `M` | Switch between Protein-Only and Protein-Ligand modes. |
| `R` | Reset all progress flags (doesn't delete files, but allows you to re-run complete steps). |
| `Q` | Quit the application. |

---

## 5. Adjusting Settings

Press `S` from the main menu to open the Simulation Settings. Here you can tweak:
- **MD Length**: Duration of the production run in nanoseconds (ns).
- **NVT / NPT Steps**: Number of steps for equilibration phases.
- **Temperature / Timestep**: Used to update parameters.
- **Generate MDP Files (`G`)**: Automatically scaffolds the necessary GROMACS `.mdp` files based on the values in these settings, ensuring compatibility with your pipeline.

---

## 6. Analysis Tools

When Production MD (Step 10 for Ligand mode, Step 9 for Protein-Only) completes, press `A` to access analysis features tailored to your mode:
- **Protein Only**: Trajectory cleaning (PBC fixes), Backbone RMSD, RMSF (C-alpha and per-residue), and Radius of Gyration.
- **Protein + Ligand**: PBC fixing, trajectory fitting, Ligand RMSD, and Protein-Ligand center-of-mass distance tracking.

- Both menus allow you to press `V` to launch **VMD** (if installed on your system) to visualize the simulation trace (`md.gro` + `md_fit.xtc` / `md.xtc`).
