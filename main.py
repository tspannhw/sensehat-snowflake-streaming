#!/usr/bin/env python3
"""
Raspberry Pi Sense HAT to Snowflake Streaming Application
Snowpipe Streaming v2 REST API - High-Performance Architecture
Optimized for 2GB RAM Raspberry Pi.

Usage:
    python main.py                    # Real sensors
    python main.py --simulate         # Simulation mode
    python main.py --batch-size 20 --interval 5.0
"""

import argparse
import logging
import signal
import sys
import time
from datetime import datetime

from sensehat_sensor import SenseHatSensor
from sensehat_streaming_client import SenseHatStreamingClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('sensehat_streaming.log')
    ]
)
logger = logging.getLogger(__name__)

shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global shutdown_requested
    logger.info(f"\nReceived signal {signum}, shutting down...")
    shutdown_requested = True


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Stream Sense HAT data to Snowflake via Snowpipe Streaming v2 REST API'
    )
    parser.add_argument(
        '--config', '-c',
        default='snowflake_config.json',
        help='Path to Snowflake config file (default: snowflake_config.json)'
    )
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=10,
        help='Number of readings per batch (default: 10)'
    )
    parser.add_argument(
        '--interval', '-i',
        type=float,
        default=5.0,
        help='Seconds between batches (default: 5.0)'
    )
    parser.add_argument(
        '--reading-interval', '-r',
        type=float,
        default=0.5,
        help='Seconds between readings within a batch (default: 0.5)'
    )
    parser.add_argument(
        '--simulate', '-s',
        action='store_true',
        help='Use simulated sensor data'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--max-batches',
        type=int,
        default=0,
        help='Maximum batches to send (0 = unlimited)'
    )
    return parser.parse_args()


def main():
    """Main application entry point."""
    global shutdown_requested

    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("=" * 70)
    logger.info("SENSE HAT TO SNOWFLAKE STREAMING")
    logger.info("Snowpipe Streaming v2 REST API - High-Performance Architecture")
    logger.info("=" * 70)
    logger.info(f"Config: {args.config}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Batch interval: {args.interval}s")
    logger.info(f"Reading interval: {args.reading_interval}s")
    logger.info(f"Simulation mode: {args.simulate}")
    logger.info("=" * 70)

    try:
        sensor = SenseHatSensor(simulate=args.simulate)
        logger.info("Sensor initialized")
    except Exception as e:
        logger.error(f"Failed to initialize sensor: {e}")
        return 1

    try:
        client = SenseHatStreamingClient(args.config)
        client.discover_ingest_host()
        client.open_channel()
        logger.info("Snowflake streaming channel opened")
    except Exception as e:
        logger.error(f"Failed to initialize Snowflake client: {e}")
        return 1

    batch_count = 0
    logger.info("Starting data streaming... (Ctrl+C to stop)")

    try:
        while not shutdown_requested:
            if args.max_batches > 0 and batch_count >= args.max_batches:
                logger.info(f"Reached max batches ({args.max_batches})")
                break

            readings = []
            for i in range(args.batch_size):
                if shutdown_requested:
                    break

                try:
                    reading = sensor.read()
                    readings.append(reading)

                    if i == 0:
                        logger.info(
                            f"Sample: Temp={reading['temperature']:.1f}C, "
                            f"Humidity={reading['humidity']:.1f}%, "
                            f"Pressure={reading['pressure']:.1f}mb, "
                            f"CPU={reading['cpu_percent']:.1f}%"
                        )

                    sensor.display_reading(reading)

                    if i < args.batch_size - 1:
                        time.sleep(args.reading_interval)

                except Exception as e:
                    logger.error(f"Error reading sensor: {e}")

            if readings and not shutdown_requested:
                try:
                    client.append_rows(readings)
                    batch_count += 1
                    logger.info(f"[OK] Sent batch {batch_count}: {len(readings)} readings")

                    if batch_count % 10 == 0:
                        client.print_statistics()

                except Exception as e:
                    logger.error(f"Error sending to Snowflake: {e}")

            if not shutdown_requested:
                time.sleep(args.interval)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    finally:
        logger.info("=" * 70)
        logger.info("Shutting down...")
        logger.info("=" * 70)

        client.print_statistics()

        try:
            client.close_channel()
            logger.info("[OK] Channel closed")
        except Exception as e:
            logger.error(f"Error closing channel: {e}")

        sensor.clear_display()
        logger.info("Shutdown complete")

    return 0


if __name__ == '__main__':
    sys.exit(main())
