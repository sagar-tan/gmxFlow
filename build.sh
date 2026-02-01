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

# Install PyInstaller if needed
if ! command -v pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    pip3 install --user pyinstaller
fi

# Create single file binary
echo "Building binary..."
~/.local/bin/pyinstaller \
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
    --hidden-import=rich \
    --hidden-import=rich.console \
    --hidden-import=rich.panel \
    --hidden-import=rich.table \
    --hidden-import=rich.text \
    --hidden-import=rich.prompt \
    --hidden-import=rich.markdown \
    --hidden-import=rich.box \
    gmxflow.py

# Check output
if [ -f "dist/gmflo" ]; then
    echo ""
    echo "✓ Build successful!"
    echo "  Binary: dist/gmflo"
    echo "  Size: $(du -h dist/gmflo | cut -f1)"
    echo ""
    echo "Next steps:"
    echo "  1. Test: ./dist/gmflo --version"
    echo "  2. Upload to GitHub Releases"
    echo "  3. Update install.sh with release URL"
else
    echo "Build failed!"
    exit 1
fi
