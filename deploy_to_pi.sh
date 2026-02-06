#!/bin/bash
# Deploy Sense HAT streaming to Raspberry Pi
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default target
PI_TARGET="${1:-pi@raspberrypi.local}"
REMOTE_DIR="${2:-~/sensehat}"

echo "=============================================="
echo "Deploying to Raspberry Pi"
echo "Target: $PI_TARGET:$REMOTE_DIR"
echo "=============================================="

# Files to deploy
FILES=(
    "main.py"
    "sensehat_streaming_client.py"
    "snowflake_jwt_auth.py"
    "sensehat_sensor.py"
    "requirements.txt"
    "pyproject.toml"
    "run.sh"
    "test.sh"
    "generate_keys.sh"
    "setup_snowflake.sql"
    "snowflake_config.json.template"
    "README.md"
    "ARCHITECTURE.md"
)

# Create remote directory
echo "Creating remote directory..."
ssh "$PI_TARGET" "mkdir -p $REMOTE_DIR/tests"

# Copy files
echo "Copying files..."
for file in "${FILES[@]}"; do
    if [ -f "$SCRIPT_DIR/$file" ]; then
        echo "  $file"
        scp "$SCRIPT_DIR/$file" "$PI_TARGET:$REMOTE_DIR/"
    fi
done

# Copy tests
if [ -d "$SCRIPT_DIR/tests" ]; then
    echo "Copying tests..."
    scp "$SCRIPT_DIR/tests/"*.py "$PI_TARGET:$REMOTE_DIR/tests/" 2>/dev/null || true
fi

# Copy config if exists (contains secrets - be careful)
if [ -f "$SCRIPT_DIR/snowflake_config.json" ]; then
    read -p "Copy snowflake_config.json (contains credentials)? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        scp "$SCRIPT_DIR/snowflake_config.json" "$PI_TARGET:$REMOTE_DIR/"
    fi
fi

# Copy private key if exists
if [ -f "$SCRIPT_DIR/rsa_key.p8" ]; then
    read -p "Copy rsa_key.p8 (private key)? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        scp "$SCRIPT_DIR/rsa_key.p8" "$PI_TARGET:$REMOTE_DIR/"
        ssh "$PI_TARGET" "chmod 600 $REMOTE_DIR/rsa_key.p8"
    fi
fi

# Setup on Pi
echo "Setting up on Raspberry Pi..."
ssh "$PI_TARGET" << 'REMOTE_SCRIPT'
cd ~/sensehat

# Make scripts executable
chmod +x run.sh test.sh generate_keys.sh 2>/dev/null || true

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate and install dependencies
source .venv/bin/activate
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install sense-hat 2>/dev/null || echo "sense-hat install (may need sudo)"

echo "Setup complete!"
REMOTE_SCRIPT

echo "=============================================="
echo "Deployment complete!"
echo ""
echo "To run on Pi:"
echo "  ssh $PI_TARGET"
echo "  cd $REMOTE_DIR"
echo "  ./run.sh"
echo "=============================================="
