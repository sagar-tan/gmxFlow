# gmxFlow Complete Installation Guide

This guide covers the full installation process on a **fresh Ubuntu/Linux system**.

## Prerequisites

Your GROMACS installation already provides most dependencies. Verify you have:

```bash
# Check GCC (required: 11+)
gcc --version

# Check Python (required: 3.8+)
python3 --version
```

If you followed the GROMACS installation guide (with GCC 11 and CMake), you're ready.

---

## 1. Install GROMACS (If Not Done)

Follow your workshop GROMACS installation guide, then verify:
```bash
gmx --version
```

---

## 2. Install gmxFlow

**One-line installer:**
```bash
curl -sSL https://bit.ly/gmxFlow-1 | sudo bash
```

This downloads and installs `gmflo` to your system.

---

## 3. First Run (License Activation)

```bash
gmflo
```

Enter your workshop license key when prompted. 
*(Key provided during the workshop session)*

---

## 4. Usage

| Command | Description |
|---------|-------------|
| `gmflo` | Interactive mode (choose simulation type) |
| `gmflo --protein` | Direct protein-only mode |
| `gmflo --ligand` | Direct protein+ligand mode |
| `gmflo --version` | Show version |

---

## 5. Update

```bash
sudo gmflo-update
```

---

## 6. Uninstall

```bash
sudo rm -rf /usr/local/bin/gmflo /usr/local/bin/gmflo-update /usr/local/gmxflow
rm -f ~/.gmxflow_license ~/.gmxflow_settings.json
```

---

## Optional: Enhanced Output

For colored terminal output:
```bash
pip3 install rich --break-system-packages
```
