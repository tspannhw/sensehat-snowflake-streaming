#!/bin/bash
# Run Sense HAT to Snowflake streaming application
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "Sense HAT → Snowflake Streaming"
echo "Snowpipe Streaming v2 REST API"
echo "=============================================="

# Check for virtual environment
if [ -d ".venv" ]; then
    echo "Using .venv virtual environment"
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "Using venv virtual environment"
    source venv/bin/activate
fi

# Check config exists
if [ ! -f "snowflake_config.json" ]; then
    echo "ERROR: snowflake_config.json not found"
    echo "Copy template: cp snowflake_config.json.template snowflake_config.json"
    exit 1
fi

# Default arguments
ARGS=""

# Pass through all command line arguments
if [ $# -gt 0 ]; then
    ARGS="$@"
fi

echo "Starting streaming..."
echo "Args: $ARGS"
echo "=============================================="

python main.py $ARGS
