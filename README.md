# Raspberry Pi Sense HAT Streaming to Snowflake

High-performance streaming of Sense HAT sensor data to Snowflake using **Snowpipe Streaming v2 REST API**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SENSE HAT → SNOWFLAKE                               │
│                   Snowpipe Streaming v2 REST API                            │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐                              ┌──────────────────────┐
    │  Raspberry Pi    │                              │     Snowflake        │
    │  ┌────────────┐  │      HTTPS/REST API          │  ┌────────────────┐  │
    │  │ Sense HAT  │  │  ─────────────────────────►  │  │ Snowpipe v2    │  │
    │  │ • Temp     │  │   JWT Authentication         │  │ REST Endpoint  │  │
    │  │ • Humidity │  │   NDJSON Payload             │  └───────┬────────┘  │
    │  │ • Pressure │  │                              │          │           │
    │  │ • IMU      │  │                              │          ▼           │
    │  └────────────┘  │                              │  ┌────────────────┐  │
    └──────────────────┘                              │  │ SENSEHAT_      │  │
                                                      │  │ SENSOR_DATA    │  │
                                                      │  │ (Table)        │  │
                                                      │  └────────────────┘  │
                                                      └──────────────────────┘
```

## Features

- **Snowpipe Streaming v2 REST API** - High-performance, low-latency ingestion
- **Full Sense HAT Support** - Environmental sensors + 9-DOF IMU
- **JWT & PAT Authentication** - Secure key-pair or token auth
- **Simulation Mode** - Test without hardware
- **Optimized for 2GB RAM** - Minimal memory footprint
- **Graceful Shutdown** - Ensures data commit before exit

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt

# On Raspberry Pi, also install:
pip install sense-hat
```

### 2. Setup Snowflake

Run the SQL in `setup_snowflake.sql` in your Snowflake account:

```sql
-- Creates: database, schema, table, pipe, role, grants
source setup_snowflake.sql
```

### 3. Configure Authentication

**Option A: Key-Pair Authentication (Recommended)**

```bash
# Generate RSA keys
./generate_keys.sh

# Copy the ALTER USER command and run in Snowflake
```

**Option B: Programmatic Access Token (PAT)**

```sql
-- In Snowflake
ALTER USER SENSEHAT_STREAMING_USER 
  ADD PROGRAMMATIC ACCESS TOKEN 
  NAME = 'sensehat_pat'
  EXPIRES_IN = 90;
-- Copy the secret immediately
```

### 4. Configure Application

```bash
cp snowflake_config.json.template snowflake_config.json
# Edit with your account details
```

### 5. Run

```bash
# With real Sense HAT
./run.sh

# Simulation mode (no hardware)
./run.sh --simulate

# Custom batch settings
python main.py --batch-size 20 --interval 5.0
```

## Project Structure

```
sensehat/
├── main.py                      # Application entry point
├── sensehat_streaming_client.py # Snowpipe v2 REST client
├── snowflake_jwt_auth.py        # JWT/PAT authentication
├── sensehat_sensor.py           # Sense HAT reader + simulation
├── pyproject.toml               # uv/pip project config
├── requirements.txt             # Dependencies
├── snowflake_config.json.template
├── setup_snowflake.sql          # Snowflake DDL
├── generate_keys.sh             # RSA key generation
├── run.sh                       # Run script
├── test.sh                      # Test runner
├── deploy_to_pi.sh              # Deploy to Raspberry Pi
├── tests/
│   ├── test_sensors.py          # Sensor tests
│   ├── test_streaming.py        # Streaming client tests
│   └── test_connection.py       # Snowflake connection tests
├── README.md                    # This file
└── ARCHITECTURE.md              # Detailed architecture docs
```

## Sensor Data Collected

### Environmental Sensors
| Sensor | Data | Unit |
|--------|------|------|
| Temperature | Ambient temperature | °C |
| Humidity | Relative humidity | % |
| Pressure | Barometric pressure | mbar |

### IMU (Inertial Measurement Unit)
| Sensor | Data | Unit |
|--------|------|------|
| Orientation | pitch, roll, yaw | degrees |
| Accelerometer | x, y, z | g |
| Gyroscope | x, y, z | rad/s |
| Magnetometer | x, y, z | µT |
| Compass | heading | degrees |

### System Metrics
| Metric | Description |
|--------|-------------|
| cpu_percent | CPU usage |
| memory_percent | RAM usage |
| disk_usage_mb | Disk used |
| cputempc/f | CPU temperature |

## Command Line Options

```
python main.py [OPTIONS]

Options:
  -c, --config FILE        Config file (default: snowflake_config.json)
  -b, --batch-size N       Readings per batch (default: 10)
  -i, --interval SECONDS   Seconds between batches (default: 5.0)
  -r, --reading-interval   Seconds between readings (default: 0.5)
  -s, --simulate           Use simulated sensor data
  -v, --verbose            Enable debug logging
  --max-batches N          Stop after N batches (0 = unlimited)
  -h, --help               Show help
```

## Configuration

### snowflake_config.json

```json
{
    "account": "xy12345",
    "url": "https://xy12345.snowflakecomputing.com",
    "user": "SENSEHAT_STREAMING_USER",
    "role": "SENSEHAT_STREAMING_ROLE",
    "database": "DEMO",
    "schema": "DEMO",
    "pipe": "SENSEHAT_STREAMING_PIPE",
    "channel_name": "SENSEHAT_CHNL",
    "private_key_file": "rsa_key.p8",
    "pat_token": null
}
```

### Batch Size & Interval Tuning

| Use Case | Batch Size | Interval | Throughput |
|----------|------------|----------|------------|
| High frequency | 5 | 2.0s | ~2.5 rows/sec |
| Balanced (default) | 10 | 5.0s | ~2 rows/sec |
| Low frequency | 20 | 15.0s | ~1.3 rows/sec |
| Burst mode | 50 | 1.0s | ~50 rows/sec |

## Testing

```bash
# Run all tests
./test.sh

# Individual tests
python tests/test_sensors.py      # Test sensor reading
python tests/test_streaming.py    # Test REST client
python tests/test_connection.py   # Test Snowflake auth
```

## Deployment to Raspberry Pi

```bash
# From your dev machine
./deploy_to_pi.sh pi@192.168.1.100

# On the Pi
cd ~/sensehat
./run.sh
```

## Snowflake Queries

```sql
-- Row count
SELECT COUNT(*) FROM DEMO.DEMO.SENSEHAT_SENSOR_DATA;

-- Latest readings
SELECT * FROM DEMO.DEMO.SENSEHAT_SENSOR_DATA 
ORDER BY ingestion_timestamp DESC LIMIT 100;

-- Temperature trends (hourly)
SELECT 
    DATE_TRUNC('hour', datetimestamp) as hour,
    hostname,
    AVG(temperature) as avg_temp,
    AVG(humidity) as avg_humidity,
    COUNT(*) as readings
FROM DEMO.DEMO.SENSEHAT_SENSOR_DATA
GROUP BY 1, 2
ORDER BY 1 DESC;

-- Orientation alerts (device moved)
SELECT hostname, datetimestamp, pitch, roll, yaw
FROM DEMO.DEMO.SENSEHAT_SENSOR_DATA
WHERE ABS(pitch) > 30 OR ABS(roll) > 30
ORDER BY datetimestamp DESC;

-- Ingestion latency
SELECT 
    hostname,
    AVG(DATEDIFF('second', datetimestamp, ingestion_timestamp)) as avg_latency_sec
FROM DEMO.DEMO.SENSEHAT_SENSOR_DATA
GROUP BY hostname;
```

## Systemd Service (Auto-start)

```bash
# Create service file
sudo nano /etc/systemd/system/sensehat-streaming.service
```

```ini
[Unit]
Description=Sense HAT Streaming to Snowflake
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/sensehat
ExecStart=/home/pi/sensehat/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable sensehat-streaming
sudo systemctl start sensehat-streaming
sudo systemctl status sensehat-streaming
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Private key file not found" | Run `./generate_keys.sh` |
| "Failed to get scoped token" | Verify public key registered in Snowflake |
| "No ingest_host returned" | Check account identifier format |
| "Channel open failed" | Verify pipe exists and user has OPERATE privilege |
| "sense_hat not found" | Install with `pip install sense-hat` (Pi only) |
| Simulation mode activates | Normal on non-Pi hardware |

## Performance

- **Ingestion Latency**: 5-10 seconds end-to-end
- **Memory Usage**: ~50MB (optimized for 2GB Pi)
- **CPU Usage**: <5% on Pi 4
- **Network**: ~1KB per reading

## References

- [Snowpipe Streaming v2 REST API](https://docs.snowflake.com/user-guide/snowpipe-streaming/snowpipe-streaming-high-performance-rest-api)
- [Snowpipe Streaming Tutorial](https://docs.snowflake.com/user-guide/snowpipe-streaming/snowpipe-streaming-high-performance-rest-tutorial)
- [Raspberry Pi Sense HAT](https://www.raspberrypi.com/documentation/accessories/sense-hat.html)
- [Key-Pair Authentication](https://docs.snowflake.com/user-guide/key-pair-auth)

## License

MIT License - See LICENSE file
