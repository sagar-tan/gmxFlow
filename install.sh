#!/bin/bash
# gmxFlow One-Line Installer
# Usage: curl -sSL https://raw.githubusercontent.com/USER/gmxFlow/main/install.sh | sudo bash

set -e

REPO_URL="https://github.com/USER/gmxFlow.git"  # <-- Update with your repo
INSTALL_DIR="/usr/local/gmxflow"
BIN_LINK="/usr/local/bin/gmflo"

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║   gmxFlow Installer v2026.0.1         ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo:"
    echo "  curl -sSL <URL>/install.sh | sudo bash"
    exit 1
fi

# Check Python3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    exit 1
fi

# Clone or download
echo "Downloading gmxFlow..."
rm -rf /tmp/gmxflow-install
if command -v git &> /dev/null; then
    git clone --depth 1 "$REPO_URL" /tmp/gmxflow-install
else
    echo "Git not found, using wget..."
    mkdir -p /tmp/gmxflow-install
    wget -qO- https://github.com/USER/gmxFlow/archive/main.tar.gz | tar xz -C /tmp/gmxflow-install --strip-components=1
fi

# Install to /usr/local/gmxflow
echo "Installing to $INSTALL_DIR..."
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp /tmp/gmxflow-install/*.py "$INSTALL_DIR/"

# Create gmflo command
cat > "$BIN_LINK" << 'EOF'
#!/bin/bash
python3 /usr/local/gmxflow/gmxflow.py "$@"
EOF
chmod +x "$BIN_LINK"

# Create gmflo-update command
cat > "/usr/local/bin/gmflo-update" << 'UPDATEEOF'
#!/bin/bash
# gmxFlow Updater
set -e
REPO_URL="https://github.com/USER/gmxFlow.git"
echo "Updating gmxFlow..."
rm -rf /tmp/gmxflow-update
git clone --depth 1 "$REPO_URL" /tmp/gmxflow-update 2>/dev/null || {
    mkdir -p /tmp/gmxflow-update
    wget -qO- https://github.com/USER/gmxFlow/archive/main.tar.gz | tar xz -C /tmp/gmxflow-update --strip-components=1
}
sudo cp /tmp/gmxflow-update/*.py /usr/local/gmxflow/
rm -rf /tmp/gmxflow-update
echo "✓ Updated! Run: gmflo --version"
UPDATEEOF
chmod +x /usr/local/bin/gmflo-update

# Cleanup
rm -rf /tmp/gmxflow-install

echo ""
echo "  ✓ gmxFlow installed successfully!"
echo ""
echo "  Usage:"
echo "    gmflo              # Run gmxFlow"
echo "    gmflo --protein    # Protein-only mode"
echo "    gmflo --ligand     # Protein+Ligand mode"
echo "    gmflo --version    # Show version (2026.0.1)"
echo ""
echo "  Optional: pip3 install rich  # For colored output"
echo ""
