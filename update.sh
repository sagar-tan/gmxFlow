#!/bin/bash
# gmxFlow Updater - Pull latest from repo
# Usage: sudo gmflo-update  OR  sudo ./update.sh

set -e

REPO_URL="https://github.com/USER/gmxFlow.git"  # <-- Update with your repo
INSTALL_DIR="/usr/local/gmxflow"

echo "Updating gmxFlow..."

# Download latest
rm -rf /tmp/gmxflow-update
if command -v git &> /dev/null; then
    git clone --depth 1 "$REPO_URL" /tmp/gmxflow-update
else
    mkdir -p /tmp/gmxflow-update
    wget -qO- https://github.com/USER/gmxFlow/archive/main.tar.gz | tar xz -C /tmp/gmxflow-update --strip-components=1
fi

# Update files
cp /tmp/gmxflow-update/*.py "$INSTALL_DIR/"

# Get new version
NEW_VER=$(grep "APP_VERSION" "$INSTALL_DIR/config.py" | cut -d'"' -f2)

# Cleanup
rm -rf /tmp/gmxflow-update

echo "✓ Updated to gmxFlow $NEW_VER"
