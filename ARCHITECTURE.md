# Architecture Documentation

## System Overview

This application streams sensor data from a Raspberry Pi Sense HAT to Snowflake using the **Snowpipe Streaming v2 REST API** (high-performance architecture).

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM ARCHITECTURE                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────┐         ┌──────────────────────────────────────┐
│         RASPBERRY PI (2GB RAM)       │         │           SNOWFLAKE CLOUD            │
│                                      │         │                                      │
│  ┌────────────────────────────────┐  │         │  ┌────────────────────────────────┐  │
│  │         SENSE HAT              │  │         │  │      CONTROL PLANE             │  │
│  │  ┌──────────┐  ┌────────────┐  │  │         │  │  ┌──────────────────────────┐  │  │
│  │  │ Environ  │  │    IMU     │  │  │         │  │  │ /v2/streaming/hostname   │  │  │
│  │  │ Sensors  │  │  9-DOF     │  │  │         │  │  │ Discover ingest endpoint │  │  │
│  │  │ •Temp    │  │ •Accel     │  │  │         │  │  └──────────────────────────┘  │  │
│  │  │ •Humid   │  │ •Gyro      │  │  │         │  │  ┌──────────────────────────┐  │  │
│  │  │ •Press   │  │ •Mag       │  │  │         │  │  │ /oauth/token             │  │  │
│  │  └────┬─────┘  └─────┬──────┘  │  │         │  │  │ Scoped token exchange    │  │  │
│  │       │              │         │  │         │  │  └──────────────────────────┘  │  │
│  └───────┼──────────────┼─────────┘  │         │  └────────────────────────────────┘  │
│          │              │            │         │                                      │
│          ▼              ▼            │         │  ┌────────────────────────────────┐  │
│  ┌────────────────────────────────┐  │         │  │       INGEST PLANE             │  │
│  │     sensehat_sensor.py         │  │         │  │  ┌──────────────────────────┐  │  │
│  │  • Read sensor data            │  │         │  │  │ PUT /channels/{name}     │  │  │
│  │  • Format as dict              │  │         │  │  │ Open streaming channel   │  │  │
│  │  • Simulation mode             │  │         │  │  └──────────────────────────┘  │  │
│  └───────────────┬────────────────┘  │         │  │  ┌──────────────────────────┐  │  │
│                  │                   │         │  │  │ POST /channels/.../rows  │  │  │
│                  ▼                   │         │  │  │ Append NDJSON rows       │◄─┼──┼───┐
│  ┌────────────────────────────────┐  │         │  │  └──────────────────────────┘  │  │   │
│  │         main.py                │  │         │  │  ┌──────────────────────────┐  │  │   │
│  │  • Batch readings              │  │         │  │  │ POST :bulk-channel-status│  │  │   │
│  │  • Signal handling             │  │         │  │  │ Verify commit            │  │  │   │
│  │  • Statistics                  │  │         │  │  └──────────────────────────┘  │  │   │
│  └───────────────┬────────────────┘  │         │  └────────────────────────────────┘  │   │
│                  │                   │         │                                      │   │
│                  ▼                   │         │  ┌────────────────────────────────┐  │   │
│  ┌────────────────────────────────┐  │         │  │       DATA LAYER               │  │   │
│  │  sensehat_streaming_client.py  │  │  HTTPS  │  │  ┌──────────────────────────┐  │  │   │
│  │  • Open channel                │──┼────────►│  │  │ SENSEHAT_STREAMING_PIPE  │  │  │   │
│  │  • Append rows (NDJSON)        │  │  REST   │  │  │ Streaming pipe (v2)      │  │  │   │
│  │  • Token management            │  │  API    │  │  └───────────┬──────────────┘  │  │   │
│  └───────────────┬────────────────┘  │         │  │              │                 │  │   │
│                  │                   │         │  │              ▼                 │  │   │
│                  ▼                   │         │  │  ┌──────────────────────────┐  │  │   │
│  ┌────────────────────────────────┐  │         │  │  │ SENSEHAT_SENSOR_DATA     │  │  │   │
│  │    snowflake_jwt_auth.py       │  │         │  │  │ (Table)                  │  │  │   │
│  │  • Generate JWT                │  │         │  │  │ • Environmental data     │  │  │   │
│  │  • Get scoped token            │  │         │  │  │ • IMU data               │  │  │   │
│  │  • Discover ingest host        │  │         │  │  │ • System metrics         │  │  │   │
│  └────────────────────────────────┘  │         │  │  └──────────────────────────┘  │  │   │
│                                      │         │  └────────────────────────────────┘  │   │
└──────────────────────────────────────┘         └──────────────────────────────────────┘   │
                                                                                            │
                                                 NDJSON Payload ────────────────────────────┘
                                                 {"uuid":"...", "temperature":22.5, ...}
                                                 {"uuid":"...", "temperature":22.6, ...}
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                 DATA FLOW                                            │
└─────────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
    │ Sense   │     │ Sensor   │     │ Batch    │     │ REST     │     │ Snowflake│
    │ HAT     │────►│ Reader   │────►│ Collector│────►│ Client   │────►│ Table    │
    │ I2C     │     │          │     │          │     │          │     │          │
    └─────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
         │               │                │                │                │
         │               │                │                │                │
    ┌────▼────┐     ┌────▼────┐      ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
    │ Raw     │     │ Dict    │      │ List of │      │ NDJSON  │      │ Rows    │
    │ Values  │     │ Reading │      │ Dicts   │      │ Payload │      │ Stored  │
    │ T=22.5C │     │ {temp:  │      │ [row1,  │      │ {...}\n │      │ SELECT  │
    │ H=45%   │     │  22.5,  │      │  row2,  │      │ {...}\n │      │ * FROM  │
    │ P=1013  │     │  humid: │      │  ...]   │      │ {...}   │      │ table   │
    └─────────┘     │  45,..} │      └─────────┘      └─────────┘      └─────────┘
                    └─────────┘
                         │
                    Every 0.5s
                    (configurable)

    ◄───── Reading ─────►◄──── Batching ────►◄──── Streaming ────►◄──── Query ────►
           Phase               Phase               Phase              Phase
```

## Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            AUTHENTICATION FLOW                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────────────────────┐
    │                         KEY-PAIR AUTHENTICATION                               │
    └──────────────────────────────────────────────────────────────────────────────┘

    1. Generate RSA Key Pair
    ┌─────────────────┐
    │ ./generate_     │──────► rsa_key.p8 (private)
    │    keys.sh      │──────► rsa_key.pub (public)
    └─────────────────┘

    2. Register Public Key in Snowflake
    ┌─────────────────────────────────────────────────────────────────┐
    │ ALTER USER SENSEHAT_USER SET RSA_PUBLIC_KEY='MIIBIjAN...'       │
    └─────────────────────────────────────────────────────────────────┘

    3. Runtime Authentication
    ┌────────────┐         ┌─────────────────┐         ┌─────────────┐
    │ Private    │         │ JWT Token       │         │ Control     │
    │ Key        │────────►│ Generation      │────────►│ Plane       │
    │ rsa_key.p8 │         │ (PyJWT + RSA)   │         │ /oauth/token│
    └────────────┘         └─────────────────┘         └──────┬──────┘
                                                              │
                                                              ▼
    ┌────────────┐         ┌─────────────────┐         ┌─────────────┐
    │ Append     │◄────────│ Scoped Token    │◄────────│ Token       │
    │ Rows       │         │ (Bearer)        │         │ Response    │
    └────────────┘         └─────────────────┘         └─────────────┘

    Token Lifecycle:
    ┌──────────────────────────────────────────────────────────────────────────────┐
    │                                                                              │
    │   JWT Token ────────────────────────────────────────────────► 1 hour expiry  │
    │       │                                                                      │
    │       ▼                                                                      │
    │   Scoped Token ─────────────────────────────────────────────► 1 hour expiry  │
    │       │                                                                      │
    │       │   Auto-refresh at 50 min                                             │
    │       ▼                                                                      │
    │   [Token Refresh] ──────────────────────────────────────────► Seamless       │
    │                                                                              │
    └──────────────────────────────────────────────────────────────────────────────┘
```

## REST API Endpoints

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           REST API ENDPOINTS                                         │
└─────────────────────────────────────────────────────────────────────────────────────┘

    Control Plane (account.snowflakecomputing.com)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    GET  /v2/streaming/hostname
         ├── Headers: Authorization: Bearer {JWT}
         └── Response: ingest host URL

    POST /oauth/token
         ├── Headers: Authorization: Bearer {JWT}
         ├── Body: grant_type=jwt-bearer&scope={ingest_host}
         └── Response: {access_token, expires_in}


    Ingest Plane (region.ingest.snowflakecomputing.com)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    PUT  /v2/streaming/databases/{db}/schemas/{schema}/pipes/{pipe}/channels/{channel}
         ├── Headers: Authorization: Bearer {scoped_token}
         ├── Body: {}
         └── Response: {next_continuation_token, channel_status}

    POST /v2/streaming/data/databases/{db}/schemas/{schema}/pipes/{pipe}/channels/{channel}/rows
         ├── Headers: Authorization: Bearer {scoped_token}
         │            Content-Type: application/x-ndjson
         ├── Query: ?continuationToken={token}&offsetToken={offset}
         ├── Body: NDJSON rows
         └── Response: {next_continuation_token}

    POST /v2/streaming/databases/{db}/schemas/{schema}/pipes/{pipe}:bulk-channel-status
         ├── Headers: Authorization: Bearer {scoped_token}
         ├── Body: {channel_names: [channel]}
         └── Response: {channel_statuses: {channel: {committed_offset_token}}}
```

## Sense HAT Sensors

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            SENSE HAT SENSORS                                         │
└─────────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                           SENSE HAT BOARD                                   │
    │  ┌─────────────────────────────────────────────────────────────────────┐   │
    │  │                        8x8 RGB LED Matrix                            │   │
    │  │    Used for visual feedback (temperature color indication)          │   │
    │  └─────────────────────────────────────────────────────────────────────┘   │
    │                                                                             │
    │  ┌───────────────────────┐    ┌───────────────────────┐                    │
    │  │   ENVIRONMENTAL       │    │   IMU (LSM9DS1)       │                    │
    │  │   ─────────────────   │    │   ─────────────────   │                    │
    │  │                       │    │                       │                    │
    │  │   HTS221              │    │   Accelerometer       │                    │
    │  │   ├─ Temperature      │    │   ├─ X, Y, Z (g)      │                    │
    │  │   └─ Humidity         │    │   └─ Range: ±2/4/8g   │                    │
    │  │                       │    │                       │                    │
    │  │   LPS25H              │    │   Gyroscope           │                    │
    │  │   └─ Pressure         │    │   ├─ X, Y, Z (rad/s)  │                    │
    │  │                       │    │   └─ Range: ±245°/s   │                    │
    │  │                       │    │                       │                    │
    │  │                       │    │   Magnetometer        │                    │
    │  │                       │    │   ├─ X, Y, Z (µT)     │                    │
    │  │                       │    │   └─ Compass heading  │                    │
    │  └───────────────────────┘    └───────────────────────┘                    │
    │                                                                             │
    │  ┌─────────────────────────────────────────────────────────────────────┐   │
    │  │   5-button Joystick (not used in this application)                  │   │
    │  └─────────────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────────┘

    Data Fields Collected:
    ┌──────────────────────┬────────────────┬──────────────────────────────────┐
    │ Field                │ Type           │ Description                       │
    ├──────────────────────┼────────────────┼──────────────────────────────────┤
    │ temperature          │ FLOAT          │ Ambient temperature (°C)         │
    │ humidity             │ FLOAT          │ Relative humidity (%)            │
    │ pressure             │ FLOAT          │ Barometric pressure (mbar)       │
    │ pitch                │ FLOAT          │ Rotation around X-axis (°)       │
    │ roll                 │ FLOAT          │ Rotation around Y-axis (°)       │
    │ yaw                  │ FLOAT          │ Rotation around Z-axis (°)       │
    │ accel_x/y/z          │ FLOAT          │ Acceleration (g)                 │
    │ gyro_x/y/z           │ FLOAT          │ Angular velocity (rad/s)         │
    │ mag_x/y/z            │ FLOAT          │ Magnetic field (µT)              │
    │ compass              │ FLOAT          │ Compass heading (°)              │
    └──────────────────────┴────────────────┴──────────────────────────────────┘
```

## Table Schema

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         SNOWFLAKE TABLE SCHEMA                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘

    DEMO.DEMO.SENSEHAT_SENSOR_DATA
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    ┌──────────────────────┬──────────────────┬─────────────────────────────────────┐
    │ Column               │ Type             │ Description                          │
    ├──────────────────────┼──────────────────┼─────────────────────────────────────┤
    │ IDENTIFIERS          │                  │                                     │
    │ ├─ uuid              │ STRING           │ Unique reading identifier           │
    │ ├─ rowid             │ STRING           │ Row identifier with UUID            │
    │ ├─ hostname          │ STRING           │ Raspberry Pi hostname               │
    │ ├─ ipaddress         │ STRING           │ Device IP address                   │
    │ └─ macaddress        │ STRING           │ Device MAC address                  │
    ├──────────────────────┼──────────────────┼─────────────────────────────────────┤
    │ TIMESTAMPS           │                  │                                     │
    │ ├─ ts                │ NUMBER           │ Unix timestamp (epoch)              │
    │ ├─ datetimestamp     │ TIMESTAMP_NTZ    │ ISO 8601 timestamp                  │
    │ └─ systemtime        │ STRING           │ Human-readable time                 │
    ├──────────────────────┼──────────────────┼─────────────────────────────────────┤
    │ ENVIRONMENTAL        │                  │                                     │
    │ ├─ temperature       │ FLOAT            │ Temperature (°C)                    │
    │ ├─ humidity          │ FLOAT            │ Humidity (%)                        │
    │ └─ pressure          │ FLOAT            │ Pressure (mbar)                     │
    ├──────────────────────┼──────────────────┼─────────────────────────────────────┤
    │ IMU ORIENTATION      │                  │                                     │
    │ ├─ pitch             │ FLOAT            │ Pitch angle (°)                     │
    │ ├─ roll              │ FLOAT            │ Roll angle (°)                      │
    │ └─ yaw               │ FLOAT            │ Yaw angle (°)                       │
    ├──────────────────────┼──────────────────┼─────────────────────────────────────┤
    │ IMU ACCELEROMETER    │                  │                                     │
    │ ├─ accel_x           │ FLOAT            │ X-axis acceleration (g)             │
    │ ├─ accel_y           │ FLOAT            │ Y-axis acceleration (g)             │
    │ └─ accel_z           │ FLOAT            │ Z-axis acceleration (g)             │
    ├──────────────────────┼──────────────────┼─────────────────────────────────────┤
    │ IMU GYROSCOPE        │                  │                                     │
    │ ├─ gyro_x            │ FLOAT            │ X-axis angular velocity (rad/s)    │
    │ ├─ gyro_y            │ FLOAT            │ Y-axis angular velocity (rad/s)    │
    │ └─ gyro_z            │ FLOAT            │ Z-axis angular velocity (rad/s)    │
    ├──────────────────────┼──────────────────┼─────────────────────────────────────┤
    │ IMU MAGNETOMETER     │                  │                                     │
    │ ├─ mag_x             │ FLOAT            │ X-axis magnetic field (µT)         │
    │ ├─ mag_y             │ FLOAT            │ Y-axis magnetic field (µT)         │
    │ ├─ mag_z             │ FLOAT            │ Z-axis magnetic field (µT)         │
    │ └─ compass           │ FLOAT            │ Compass heading (°)                 │
    ├──────────────────────┼──────────────────┼─────────────────────────────────────┤
    │ SYSTEM METRICS       │                  │                                     │
    │ ├─ cpu_percent       │ FLOAT            │ CPU usage (%)                       │
    │ ├─ memory_percent    │ FLOAT            │ Memory usage (%)                    │
    │ ├─ disk_usage_mb     │ FLOAT            │ Disk used (MB)                      │
    │ ├─ cputempc          │ FLOAT            │ CPU temperature (°C)                │
    │ └─ cputempf          │ FLOAT            │ CPU temperature (°F)                │
    ├──────────────────────┼──────────────────┼─────────────────────────────────────┤
    │ METADATA             │                  │                                     │
    │ ├─ simulated         │ BOOLEAN          │ True if simulated data              │
    │ └─ ingestion_timestamp│ TIMESTAMP_NTZ   │ Snowflake ingestion time (auto)    │
    └──────────────────────┴──────────────────┴─────────────────────────────────────┘
```

## Performance Characteristics

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         PERFORMANCE CHARACTERISTICS                                  │
└─────────────────────────────────────────────────────────────────────────────────────┘

    Memory Usage (Raspberry Pi 2GB RAM)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │ Component              │ Memory Usage  │ Notes                              │
    ├────────────────────────┼───────────────┼────────────────────────────────────┤
    │ Python Runtime         │ ~25 MB        │ Base interpreter                   │
    │ Application Code       │ ~10 MB        │ Modules loaded                     │
    │ Sensor Libraries       │ ~5 MB         │ sense_hat, psutil                  │
    │ Request Buffers        │ ~5 MB         │ HTTP client                        │
    │ Batch Buffer           │ ~5 MB         │ Depends on batch size              │
    │ ─────────────────────  │ ───────────── │                                    │
    │ TOTAL                  │ ~50 MB        │ Well under 2GB limit               │
    └────────────────────────┴───────────────┴────────────────────────────────────┘

    Throughput & Latency
    ━━━━━━━━━━━━━━━━━━━━━
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │ Metric                         │ Value         │ Notes                      │
    ├────────────────────────────────┼───────────────┼────────────────────────────┤
    │ Sensor Read Time               │ ~10 ms        │ Per reading                │
    │ REST API Call (append)         │ ~100-200 ms   │ Network dependent          │
    │ End-to-End Latency             │ 5-10 seconds  │ Sensor → Queryable         │
    │ Default Throughput             │ ~2 rows/sec   │ Batch=10, Interval=5s      │
    │ Max Throughput (burst)         │ ~50 rows/sec  │ Batch=50, Interval=1s      │
    │ Network Bandwidth              │ ~1 KB/row     │ NDJSON payload             │
    └────────────────────────────────┴───────────────┴────────────────────────────┘

    Batching Trade-offs
    ━━━━━━━━━━━━━━━━━━━
    ┌─────────────────┬──────────────┬──────────────┬─────────────────────────────┐
    │ Batch Size      │ Interval     │ Latency      │ Use Case                    │
    ├─────────────────┼──────────────┼──────────────┼─────────────────────────────┤
    │ 5               │ 2s           │ ~2-3s        │ Real-time monitoring        │
    │ 10 (default)    │ 5s           │ ~5-6s        │ Balanced                    │
    │ 20              │ 10s          │ ~10-12s      │ Reduced API calls           │
    │ 50              │ 30s          │ ~30-35s      │ High-volume, cost-efficient │
    └─────────────────┴──────────────┴──────────────┴─────────────────────────────┘
```

## Error Handling

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ERROR HANDLING                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘

    Retry Logic
    ━━━━━━━━━━━
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                                                                             │
    │   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐              │
    │   │ Request │────►│ Success │     │ Retry   │────►│ Success │              │
    │   └────┬────┘     └─────────┘     └────┬────┘     └─────────┘              │
    │        │                               │                                    │
    │        │ 4xx/5xx                       │ Max retries                        │
    │        ▼                               ▼                                    │
    │   ┌─────────┐                     ┌─────────┐                              │
    │   │ Token   │                     │ Log     │                              │
    │   │ Refresh │                     │ Error   │                              │
    │   └────┬────┘                     └─────────┘                              │
    │        │                                                                    │
    │        ▼                                                                    │
    │   ┌─────────┐                                                              │
    │   │ Retry   │                                                              │
    │   └─────────┘                                                              │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘

    Error Types
    ━━━━━━━━━━━
    ┌──────────────────┬─────────────────────────┬────────────────────────────────┐
    │ Error            │ HTTP Code               │ Action                          │
    ├──────────────────┼─────────────────────────┼────────────────────────────────┤
    │ Invalid Token    │ 401                     │ Refresh token, retry           │
    │ Rate Limited     │ 429                     │ Exponential backoff            │
    │ Server Error     │ 5xx                     │ Retry with backoff             │
    │ Bad Request      │ 400                     │ Log error, skip batch          │
    │ Not Found        │ 404                     │ Check config, fail             │
    │ Network Error    │ Connection Error        │ Retry with backoff             │
    └──────────────────┴─────────────────────────┴────────────────────────────────┘

    Graceful Shutdown
    ━━━━━━━━━━━━━━━━━
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                                                                             │
    │   SIGINT/SIGTERM ────► Set shutdown_requested = True                        │
    │                              │                                              │
    │                              ▼                                              │
    │                        ┌───────────┐                                        │
    │                        │ Complete  │                                        │
    │                        │ Current   │                                        │
    │                        │ Batch     │                                        │
    │                        └─────┬─────┘                                        │
    │                              │                                              │
    │                              ▼                                              │
    │                        ┌───────────┐                                        │
    │                        │ Print     │                                        │
    │                        │ Statistics│                                        │
    │                        └─────┬─────┘                                        │
    │                              │                                              │
    │                              ▼                                              │
    │                        ┌───────────┐                                        │
    │                        │ Close     │                                        │
    │                        │ Channel   │                                        │
    │                        └─────┬─────┘                                        │
    │                              │                                              │
    │                              ▼                                              │
    │                        ┌───────────┐                                        │
    │                        │ Exit      │                                        │
    │                        │ Cleanly   │                                        │
    │                        └───────────┘                                        │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘
```

## Security Model

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SECURITY MODEL                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘

    Credential Storage
    ━━━━━━━━━━━━━━━━━━
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                                                                             │
    │   Local Files (chmod 600)                                                   │
    │   ├── rsa_key.p8           Private key (NEVER commit to git)               │
    │   └── snowflake_config.json Configuration with account details             │
    │                                                                             │
    │   .gitignore                                                                │
    │   ├── rsa_key.p8                                                           │
    │   ├── rsa_key.pub                                                          │
    │   ├── snowflake_config.json                                                │
    │   └── *.log                                                                │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘

    Privilege Model
    ━━━━━━━━━━━━━━━
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                                                                             │
    │   SENSEHAT_STREAMING_ROLE                                                   │
    │   ├── USAGE on DATABASE DEMO                                               │
    │   ├── USAGE on SCHEMA DEMO.DEMO                                            │
    │   ├── INSERT on TABLE SENSEHAT_SENSOR_DATA                                 │
    │   ├── OPERATE on PIPE SENSEHAT_STREAMING_PIPE                              │
    │   └── MONITOR on PIPE SENSEHAT_STREAMING_PIPE                              │
    │                                                                             │
    │   Principle of Least Privilege:                                             │
    │   • No SELECT (write-only from device)                                     │
    │   • No DDL (cannot modify schema)                                          │
    │   • Scoped to single pipe/table                                            │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘
```
