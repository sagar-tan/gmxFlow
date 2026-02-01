# Developer Guide

## 1. Development Workflow (Local Testing)

While developing new features or fixing bugs:

1. **Edit** the Python files (`gmxflow.py`, `pipeline.py`, etc.).
2. **Test** directly with Python:
   ```bash
   python3 gmxflow.py
   python3 gmxflow.py --dry-run
   ```
3. **Verify** new features work as expected.

## 2. Release Procedure (Updating the App)

When you are ready to ship a new version to users:

### Step A: Update Version Number
1. Edit `config.py`: Update `APP_VERSION` (e.g., `2026.0.2`).
2. Edit `install.sh`: Update `VERSION` variable.

### Step B: Build Binary
Run inside WSL:
```bash
./build.sh
```
*This creates the new binary at `dist/gmflo`.*

### Step C: Test Binary (Important!)
Verify the built binary works:
```bash
./dist/gmflo --version
```

### Step D: Publish Release
1. **Commit & Push** your changes:
   ```bash
   git add .
   git commit -m "Release v2026.0.2"
   git push
   ```
2. **Create GitHub Release**:
   - Go to [Releases](https://github.com/sagar-tan/gmxFlow/releases)
   - Draft a new release
   - **Tag**: `v2026.0.2` (Must match the version in steps above)
   - **Assets**: Upload the `dist/gmflo` binary
   - Publish!

## 3. How Users Update
Users simply run:
```bash
sudo gmflo-update
```
*This downloads the binary from the latest release.*

---

## Tools
- `license_check.py`: Run this to generate new workshop keys.
