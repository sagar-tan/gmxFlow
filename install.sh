#!/bin/bash
# gmxFlow Installer
# Installs Python scripts (binary support coming soon)

set -e

VERSION="2026.0.1"
REPO_URL="https://github.com/sagar-tan/gmxFlow.git"
INSTALL_DIR="/usr/local/gmxflow"
BIN_DIR="/usr/local/bin"

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║   gmxFlow Installer v${VERSION}         ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo:"
    echo "  curl -sSL <URL> | sudo bash"
    exit 1
fi

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    exit 1
fi

# Clone repository
echo "Downloading gmxFlow..."
rm -rf /tmp/gmxflow-install
git clone --depth 1 "$REPO_URL" /tmp/gmxflow-install

# Install Python files
echo "Installing to $INSTALL_DIR..."
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp /tmp/gmxflow-install/*.py "$INSTALL_DIR/"

# Create gmflo command
cat > "$BIN_DIR/gmflo" << 'EOF'
#!/bin/bash
python3 /usr/local/gmxflow/gmxflow.py "$@"
EOF
chmod +x "$BIN_DIR/gmflo"

# Create updater
cat > "$BIN_DIR/gmflo-update" << 'UPDATEEOF'
#!/bin/bash
echo "Updating gmflo..."
rm -rf /tmp/gmxflow-update
git clone --depth 1 https://github.com/sagar-tan/gmxFlow.git /tmp/gmxflow-update
sudo cp /tmp/gmxflow-update/*.py /usr/local/gmxflow/
rm -rf /tmp/gmxflow-update
echo "✓ Updated!"
UPDATEEOF
chmod +x "$BIN_DIR/gmflo-update"

# Cleanup
rm -rf /tmp/gmxflow-install

echo ""
echo "  ✓ gmxFlow installed successfully!"
echo ""
echo "  Usage:"
echo "    gmflo              # Run gmxFlow"
echo "    gmflo --protein    # Protein-only mode"
echo "    gmflo --ligand     # Protein+Ligand mode"
echo "    gmflo --version    # Show version"
echo ""
echo "  Optional: pip3 install rich --break-system-packages"
echo "            (for colored output)"
echo ""
