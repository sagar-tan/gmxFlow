#!/bin/bash
# Build gmxFlow as a single Linux binary
# Run this on the OLDEST Ubuntu you want to support (20.04 recommended)

set -e

echo "╔═══════════════════════════════════════╗"
echo "║   gmxFlow Binary Builder              ║"
echo "╚═══════════════════════════════════════╝"

# Check if on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "Error: Must build on Linux for Linux binary"
    exit 1
fi

# Create a temporary virtual environment for building
echo "Creating build environment..."
python3 -m venv build_venv
source build_venv/bin/activate

# Install PyInstaller
echo "Installing dependencies..."
pip install pyinstaller rich pyyaml

# Create single file binary
echo "Building binary..."
pyinstaller \
    --onefile \
    --name gmflo \
    --clean \
    --strip \
    --add-data "config.py:." \
    --add-data "utils.py:." \
    --add-data "pipeline.py:." \
    --add-data "analysis.py:." \
    --add-data "visualization.py:." \
    --add-data "settings.py:." \
    --add-data "license_check.py:." \
    --add-data "license_check.py:." \
    --collect-all rich \
    gmxflow.py

# Check output
if [ -f "dist/gmflo" ]; then
    echo ""
    echo "✓ Build successful!"
    echo "  Binary: dist/gmflo"
    echo "  Size: $(du -h dist/gmflo | cut -f1)"
    echo ""
    echo "Cleaning up..."
    deactivate
    rm -rf build_venv build gmxflow.spec
    
    echo "Next steps:"
    echo "  1. Test: ./dist/gmflo --version"
    echo "  2. Upload to GitHub Releases"
    echo "  3. Update install.sh with release URL"
else
    echo "Build failed!"
    exit 1
fi
