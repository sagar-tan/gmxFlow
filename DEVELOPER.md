# Developer Guide

## Workflows Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   DEVELOP   │ →  │    BUILD    │ →  │   PUBLISH   │
│  Edit .py   │    │  ./build.sh │    │  GitHub     │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## 1. Development Workflow (Edit & Test)

### Edit Code
Edit files in `c:\Users\tanwa\gmxFlow\`:
- `gmxflow.py` - Main application
- `config.py` - Settings, steps, version
- `pipeline.py` - Pipeline execution
- `license_check.py` - License system

### Test Locally (Python)
```bash
cd /mnt/c/Users/tanwa/gmxFlow
python3 gmxflow.py              # Run app
python3 gmxflow.py --dry-run    # Test without executing GROMACS
python3 gmxflow.py --version    # Check version
```

---

## 2. Build Workflow (Create Binary)

### Prerequisites (One-time)
```bash
sudo apt install -y gcc patchelf python3-dev
```

### Build Binary
```bash
cd /mnt/c/Users/tanwa/gmxFlow
sed -i 's/\r$//' build.sh       # Fix line endings
./build.sh                       # Takes ~5-10 minutes
```

### Test Binary
```bash
./dist/gmflo --version
./dist/gmflo --protein
```

---

## 3. Publish Workflow (Release)

### Step A: Update Version
Edit `config.py`:
```python
APP_VERSION = "2026.0.2"  # Increment
```

### Step B: Commit & Push
```bash
git add .
git commit -m "Release v2026.0.2"
git push
```

### Step C: Create GitHub Release
1. Go to: https://github.com/sagar-tan/gmxFlow/releases/new
2. Tag: `v2026.0.2`
3. Title: `gmxFlow v2026.0.2`
4. Upload: `dist/gmflo`
5. Publish

---

## 4. Test as User (Fresh Install)

```bash
# Remove existing installation
sudo rm -rf /usr/local/bin/gmflo /usr/local/bin/gmflo-update /usr/local/gmxflow
rm -f ~/.gmxflow_license

# Install fresh
curl -sSL https://bit.ly/gmxFlow-1 | sudo bash

# Test
gmflo --version
gmflo
```

---

## 5. License Key Management

### Generate Key Hash
```bash
python3 license_check.py
# Enter new key, copy the hash
```

### Add New Key
Edit `license_check.py`:
```python
VALID_KEY_HASHES = [
    "existing_hash",
    "new_hash_here",  # NEW
]
```

### Current Workshop Keys
See: `WORKSHOP_KEYS_2026.txt`

---

## Quick Reference

| Task | Command |
|------|---------|
| Dev test | `python3 gmxflow.py` |
| Build | `./build.sh` |
| Test binary | `./dist/gmflo` |
| Push | `git add . && git commit -m "msg" && git push` |
| Fresh install | `curl -sSL https://bit.ly/gmxFlow-1 \| sudo bash` |
