#!/bin/bash
# bootstrap.sh - Quick setup script for dev-container-launcher

set -e

echo "🚀 Dev-Container Launcher Setup"
echo "=============================="

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop first."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10 or later."
    exit 1
fi

if ! command -v cursor &> /dev/null; then
    echo "⚠️  Cursor CLI not found in PATH."
    echo "   Install it from Cursor: Cmd/Ctrl+Shift+P → 'Shell command: Install cursor'"
    echo "   Continuing anyway..."
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check for SSH key
if [ ! -f "$HOME/.ssh/id_rsa.pub" ] && [ ! -f "$HOME/.ssh/id_ed25519.pub" ]; then
    echo "⚠️  No SSH public key found. Generating one..."
    ssh-keygen -t ed25519 -f "$HOME/.ssh/id_ed25519" -N ""
fi

# Copy SSH key
echo "Setting up SSH key..."
if [ -f "$HOME/.ssh/id_ed25519.pub" ]; then
    cp "$HOME/.ssh/id_ed25519.pub" authorized_keys
elif [ -f "$HOME/.ssh/id_rsa.pub" ]; then
    cp "$HOME/.ssh/id_rsa.pub" authorized_keys
fi

# Build base image
echo "Building base Docker image..."
python scripts/devctl.py build

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Run the UI: python app.py"
echo "2. Press 'c' to create your first container"
echo "3. Select it and press Enter to open in Cursor"
echo ""
echo "Optional: Build all language images with 'make build-all'"
