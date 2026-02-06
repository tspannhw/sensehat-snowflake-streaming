-- ============================================================================
-- Snowflake Setup for Raspberry Pi Sense HAT Streaming
-- Snowpipe Streaming v2 REST API - High-Performance Architecture
-- ============================================================================

-- Step 1: Create database and schema
CREATE DATABASE IF NOT EXISTS DEMO;
CREATE SCHEMA IF NOT EXISTS DEMO.DEMO;

-- Step 2: Create role for streaming
CREATE ROLE IF NOT EXISTS SENSEHAT_STREAMING_ROLE;

-- Step 3: Create user for streaming (uncomment and customize password)
-- CREATE USER IF NOT EXISTS SENSEHAT_STREAMING_USER
--     PASSWORD = 'YourSecurePassword123!'
--     DEFAULT_ROLE = SENSEHAT_STREAMING_ROLE
--     DEFAULT_WAREHOUSE = COMPUTE_WH;

-- Step 4: Grant privileges to role
GRANT USAGE ON DATABASE DEMO TO ROLE SENSEHAT_STREAMING_ROLE;
GRANT USAGE ON SCHEMA DEMO.DEMO TO ROLE SENSEHAT_STREAMING_ROLE;
GRANT CREATE TABLE ON SCHEMA DEMO.DEMO TO ROLE SENSEHAT_STREAMING_ROLE;
GRANT INSERT, SELECT ON ALL TABLES IN SCHEMA DEMO.DEMO TO ROLE SENSEHAT_STREAMING_ROLE;
GRANT INSERT, SELECT ON FUTURE TABLES IN SCHEMA DEMO.DEMO TO ROLE SENSEHAT_STREAMING_ROLE;

-- Step 5: Grant role to user
-- GRANT ROLE SENSEHAT_STREAMING_ROLE TO USER SENSEHAT_STREAMING_USER;

-- Step 6: Create target table for Sense HAT data
CREATE OR REPLACE TABLE DEMO.DEMO.SENSEHAT_SENSOR_DATA (
    -- Identifiers
    uuid STRING,
    rowid STRING,
    hostname STRING,
    ipaddress STRING,
    macaddress STRING,
    
    -- Timestamps
    ts NUMBER,
    datetimestamp TIMESTAMP_NTZ,
    systemtime STRING,
    
    -- Environmental sensors
    temperature FLOAT,
    humidity FLOAT,
    pressure FLOAT,
    
    -- IMU - Orientation
    pitch FLOAT,
    roll FLOAT,
    yaw FLOAT,
    
    -- IMU - Accelerometer
    accel_x FLOAT,
    accel_y FLOAT,
    accel_z FLOAT,
    
    -- IMU - Gyroscope
    gyro_x FLOAT,
    gyro_y FLOAT,
    gyro_z FLOAT,
    
    -- IMU - Magnetometer
    mag_x FLOAT,
    mag_y FLOAT,
    mag_z FLOAT,
    compass FLOAT,
    
    -- System metrics
    cpu_percent FLOAT,
    memory_percent FLOAT,
    disk_usage_mb FLOAT,
    cputempc FLOAT,
    cputempf FLOAT,
    
    -- Metadata
    simulated BOOLEAN,
    ingestion_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Step 7: Create streaming pipe (v2 high-performance)
-- The pipe name follows the pattern: TABLE_NAME-STREAMING
CREATE OR REPLACE PIPE DEMO.DEMO.SENSEHAT_STREAMING_PIPE 
    AS COPY INTO DEMO.DEMO.SENSEHAT_SENSOR_DATA;

-- Step 8: Grant streaming privileges
GRANT OPERATE, MONITOR ON PIPE DEMO.DEMO.SENSEHAT_STREAMING_PIPE TO ROLE SENSEHAT_STREAMING_ROLE;

-- Step 9: Set public key for key-pair authentication
-- Run generate_keys.sh first to create rsa_key.p8 and get the public key
-- Then uncomment and run this:
-- ALTER USER SENSEHAT_STREAMING_USER SET RSA_PUBLIC_KEY='YOUR_PUBLIC_KEY_HERE';

-- ============================================================================
-- Verification queries
-- ============================================================================

-- Check pipe exists
SHOW PIPES LIKE 'SENSEHAT_STREAMING_PIPE' IN SCHEMA DEMO.DEMO;

-- Describe pipe
DESC PIPE DEMO.DEMO.SENSEHAT_STREAMING_PIPE;

-- Check table structure
DESC TABLE DEMO.DEMO.SENSEHAT_SENSOR_DATA;

-- ============================================================================
-- Sample queries for analysis
-- ============================================================================

-- Row count
-- SELECT COUNT(*) FROM DEMO.DEMO.SENSEHAT_SENSOR_DATA;

-- Latest readings
-- SELECT * FROM DEMO.DEMO.SENSEHAT_SENSOR_DATA 
-- ORDER BY ingestion_timestamp DESC 
-- LIMIT 100;

-- Temperature trend
-- SELECT 
--     hostname,
--     DATE_TRUNC('minute', datetimestamp) as minute,
--     AVG(temperature) as avg_temp,
--     AVG(humidity) as avg_humidity,
--     COUNT(*) as readings
-- FROM DEMO.DEMO.SENSEHAT_SENSOR_DATA
-- GROUP BY 1, 2
-- ORDER BY 2 DESC;

-- Orientation monitoring
-- SELECT 
--     hostname,
--     datetimestamp,
--     pitch, roll, yaw,
--     compass
-- FROM DEMO.DEMO.SENSEHAT_SENSOR_DATA
-- WHERE ABS(pitch) > 30 OR ABS(roll) > 30
-- ORDER BY datetimestamp DESC
-- LIMIT 50;

-- System health
-- SELECT 
--     hostname,
--     MAX(cputempf) as max_cpu_temp_f,
--     AVG(cpu_percent) as avg_cpu_pct,
--     AVG(memory_percent) as avg_mem_pct
-- FROM DEMO.DEMO.SENSEHAT_SENSOR_DATA
-- GROUP BY hostname;

-- Ingestion latency monitoring
-- SELECT 
--     hostname,
--     datetimestamp as sensor_time,
--     ingestion_timestamp,
--     DATEDIFF('second', datetimestamp, ingestion_timestamp) as latency_sec
-- FROM DEMO.DEMO.SENSEHAT_SENSOR_DATA
-- ORDER BY ingestion_timestamp DESC
-- LIMIT 100;
