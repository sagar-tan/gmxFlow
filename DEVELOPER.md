# Developer Guide

## How to Release gmxFlow

To distribute a new version (e.g., `2026.0.1`) as a binary:

### 1. Build the Binary
Run this in WSL (or any Linux machine):
```bash
chmod +x build.sh
./build.sh
```
This creates the binary at: `dist/gmflo`

### 2. Test It
```bash
./dist/gmflo --version
```

### 3. Create GitHub Release
1. Go to: [https://github.com/sagar-tan/gmxFlow/releases/new](https://github.com/sagar-tan/gmxFlow/releases/new)
2. **Tag version**: `v2026.0.1` (Must match VERSION in `config.py` and `install.sh`)
3. **Title**: `gmxFlow v2026.0.1`
4. **Attach binary**: Upload the `dist/gmflo` file
5. Click **Publish release**

### 4. Verify Installation
Users can now install the binary using the standard command:
```bash
curl -sSL https://bit.ly/gmxFlow-1 | sudo bash
```
The script will auto-detect the release and download the binary.

---

## Troubleshooting

- **Binary not found?** The installer falls back to downloading the python source code.
- **Permission denied?** Make sure `build.sh` is executable (`chmod +x build.sh`).
