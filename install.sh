#!/bin/bash
# gmxFlow Binary Installer
# Downloads pre-built binary from GitHub Releases

set -e

VERSION="2026.0.1"
RELEASE_URL="https://github.com/sagar-tan/gmxFlow/releases/download/v${VERSION}/gmflo"
INSTALL_DIR="/usr/local/bin"

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

# Download binary
echo "Downloading gmflo..."
curl -sSL -o /tmp/gmflo "$RELEASE_URL" || {
    echo "Download failed. Falling back to Python scripts..."
    
    # Fallback to Python installation
    REPO_URL="https://github.com/sagar-tan/gmxFlow.git"
    rm -rf /tmp/gmxflow-install
    git clone --depth 1 "$REPO_URL" /tmp/gmxflow-install
    
    mkdir -p /usr/local/gmxflow
    cp /tmp/gmxflow-install/*.py /usr/local/gmxflow/
    
    cat > "$INSTALL_DIR/gmflo" << 'EOF'
#!/bin/bash
python3 /usr/local/gmxflow/gmxflow.py "$@"
EOF
    chmod +x "$INSTALL_DIR/gmflo"
    rm -rf /tmp/gmxflow-install
    
    echo "✓ Installed (Python mode)"
    exit 0
}

# Install binary
echo "Installing..."
mv /tmp/gmflo "$INSTALL_DIR/gmflo"
chmod +x "$INSTALL_DIR/gmflo"

# Create updater
cat > "$INSTALL_DIR/gmflo-update" << 'UPDATEEOF'
#!/bin/bash
echo "Updating gmflo..."
VERSION="2026.0.1"
sudo curl -sSL -o /usr/local/bin/gmflo "https://github.com/sagar-tan/gmxFlow/releases/download/v${VERSION}/gmflo"
sudo chmod +x /usr/local/bin/gmflo
echo "✓ Updated!"
UPDATEEOF
chmod +x "$INSTALL_DIR/gmflo-update"

echo ""
echo "  ✓ gmxFlow installed successfully!"
echo ""
echo "  Usage:"
echo "    gmflo              # Run gmxFlow"
echo "    gmflo --protein    # Protein-only mode"
echo "    gmflo --version    # Show version"
echo ""
