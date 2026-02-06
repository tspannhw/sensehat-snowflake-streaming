#!/bin/bash
# Run tests for Sense HAT Snowflake streaming
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "Running Tests"
echo "=============================================="

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Create tests directory if not exists
mkdir -p tests

# Run tests based on argument
case "${1:-all}" in
    sensors)
        echo "Running sensor tests..."
        python tests/test_sensors.py
        ;;
    streaming)
        echo "Running streaming client tests..."
        python tests/test_streaming.py
        ;;
    connection)
        echo "Running connection tests..."
        python tests/test_connection.py
        ;;
    quick)
        echo "Running quick validation..."
        python -c "
from sensehat_sensor import SenseHatSensor
sensor = SenseHatSensor(simulate=True)
reading = sensor.read()
print('Sensor test: OK')
print(f'  Temperature: {reading[\"temperature\"]}C')
print(f'  Humidity: {reading[\"humidity\"]}%')
"
        ;;
    all)
        echo "Running all tests..."
        if command -v pytest &> /dev/null; then
            pytest tests/ -v
        else
            echo "pytest not installed, running individual tests..."
            python tests/test_sensors.py
            python tests/test_streaming.py
            if [ -f "snowflake_config.json" ]; then
                python tests/test_connection.py
            else
                echo "Skipping connection test (no config)"
            fi
        fi
        ;;
    *)
        echo "Usage: ./test.sh [sensors|streaming|connection|quick|all]"
        exit 1
        ;;
esac

echo "=============================================="
echo "Tests completed"
echo "=============================================="
