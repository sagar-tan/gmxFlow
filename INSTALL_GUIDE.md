# gmxFlow Complete Installation Guide

This guide covers the installation process for **gmxFlow** on a completely fresh Linux system (e.g., Ubuntu, Debian, Kali, Mint, or WSL).

## 1. Prerequisites (Prepare your System)

Before installing gmxFlow, ensure your system has the necessary core tools and GROMACS installed.

Open your terminal and run the following commands:

### Step A: Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### Step B: Install GROMACS & Python
gmxFlow requires GROMACS to run simulations and Python to run the interface.

```bash
# Install GROMACS, Python, and basic tools
sudo apt install -y gromacs python3 python3-pip curl git
```

*Verify GROMACS is installed:*
```bash
gmx --version
```
*(You should see GROMACS version information. If not, try `sudo apt install gromacs-gl` or check GROMACS documentation).*

---

## 2. Install gmxFlow

Now that dependencies are ready, install gmxFlow using the one-line installer.

### Run the Installer
```bash
curl -sSL https://bit.ly/gmxFlow-1 | sudo bash
```

This command will:
1. Detect automatically if a binary release is available.
2. Download and install `gmflo` to your system path.
3. Set up the `gmflo-update` command.

---

## 3. Activation (First Run)

The first time you run gmxFlow, you will need your **Workshop License Key**.

1. **Start the tool:**
   ```bash
   gmflo
   ```

2. **Enter License Key:**
   When prompted, enter the key provided during your workshop (e.g., `GMX-WS26-XXXX`).
   
   > *Note: This key grants you lifetime access on this machine.*

---

## 4. Usage

Successfully installed! You can now run simulations.

**Basic Commands:**
- `gmflo` : Start the interactive menu (default)
- `gmflo --protein` : Start directly in Protein-Only mode
- `gmflo --version` : Check installed version

**Updating:**
To get the latest version (including bug fixes):
```bash
sudo gmflo-update
```
