#!/bin/bash
# Build gmxFlow as a compiled Linux binary using Nuitka
# Run this on Ubuntu 20.04+ for max compatibility

set -e

echo "╔═══════════════════════════════════════╗"
echo "║   gmxFlow Nuitka Builder              ║"
echo "╚═══════════════════════════════════════╝"

# Check if on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "Error: Must build on Linux"
    exit 1
fi

# Check dependencies
echo "Checking dependencies..."
if ! command -v gcc &> /dev/null; then
    echo "Installing build tools..."
    sudo apt install -y gcc patchelf python3-dev
fi

# Create build environment
echo "Creating build environment..."
rm -rf build_venv
python3 -m venv build_venv
source build_venv/bin/activate

# Install Nuitka and dependencies
echo "Installing Nuitka..."
pip install --upgrade pip
pip install nuitka ordered-set rich pyyaml

# Build with Nuitka
echo "Building binary (this may take 5-10 minutes)..."
python3 -m nuitka \
    --standalone \
    --onefile \
    --follow-imports \
    --include-package=rich \
    --include-data-dir=build_venv/lib/python*/site-packages/rich/_unicode_data=rich/_unicode_data \
    --output-filename=gmflo \
    --output-dir=dist \
    --remove-output \
    --assume-yes-for-downloads \
    gmxflow.py

# Check output
if [ -f "dist/gmflo" ]; then
    echo ""
    echo "✓ Build successful!"
    echo "  Binary: dist/gmflo"
    echo "  Size: $(du -h dist/gmflo | cut -f1)"
    echo ""
    
    # Cleanup
    deactivate
    rm -rf build_venv gmxflow.build gmxflow.dist gmxflow.onefile-build
    
    echo "Next steps:"
    echo "  1. Test: ./dist/gmflo --version"
    echo "  2. Upload to GitHub Releases"
else
    echo "Build failed!"
    deactivate
    exit 1
fi
