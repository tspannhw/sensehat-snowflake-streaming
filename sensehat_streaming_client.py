#!/usr/bin/env python3
"""
Snowpipe Streaming v2 REST API Client for Raspberry Pi Sense HAT
HIGH-PERFORMANCE STREAMING via REST API
Optimized for 2GB RAM Raspberry Pi.
"""

import json
import logging
import time
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from snowflake_jwt_auth import SnowflakeJWTAuth

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('sensehat_streaming.log')
    ]
)
logger = logging.getLogger(__name__)


class SenseHatStreamingClient:
    """
    Snowpipe Streaming v2 REST API Client for Sense HAT data.
    Uses ONLY REST API endpoints - no direct database connections.
    """

    def __init__(self, config_file: str = 'snowflake_config.json'):
        logger.info("=" * 60)
        logger.info("SENSEHAT STREAMING CLIENT - Snowpipe v2 REST API")
        logger.info("=" * 60)

        self.config = self._load_config(config_file)
        self.jwt_auth = SnowflakeJWTAuth(self.config)

        self.ingest_host = None
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_channel = self.config.get('channel_name', 'SENSEHAT_CHNL')
        self.channel_name = f"{base_channel}_{timestamp}"
        self.continuation_token = None
        self.offset_token = 0
        self.scoped_token = None
        self.token_expiry = None

        self.stats = {
            'total_rows_sent': 0,
            'total_batches': 0,
            'total_bytes_sent': 0,
            'errors': 0,
            'start_time': time.time()
        }

        logger.info(f"Database: {self.config['database']}")
        logger.info(f"Schema: {self.config['schema']}")
        logger.info(f"Pipe: {self.config['pipe']}")
        logger.info(f"Channel: {self.channel_name}")

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file."""
        with open(config_file, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded config from {config_file}")
        return config

    def _ensure_valid_token(self):
        """Ensure we have a valid scoped token."""
        if self.scoped_token is None or (self.token_expiry and time.time() >= self.token_expiry):
            logger.info("Obtaining scoped token...")
            self.scoped_token = self.jwt_auth.get_scoped_token()
            self.token_expiry = time.time() + 3000
            logger.info("Scoped token obtained")

    def discover_ingest_host(self) -> str:
        """Discover the ingest host URL."""
        logger.info("Discovering ingest host...")
        self._ensure_valid_token()
        self.ingest_host = self.jwt_auth.get_ingest_host()
        logger.info(f"Ingest host: {self.ingest_host}")
        return self.ingest_host

    def open_channel(self) -> Dict:
        """Open a streaming channel."""
        logger.info(f"Opening channel: {self.channel_name}")

        if not self.ingest_host:
            self.discover_ingest_host()

        self._ensure_valid_token()

        db = self.config['database']
        schema = self.config['schema']
        pipe = self.config['pipe']

        url = (
            f"https://{self.ingest_host}/v2/streaming"
            f"/databases/{db}/schemas/{schema}/pipes/{pipe}/channels/{self.channel_name}"
        )

        headers = {
            'Authorization': f'Bearer {self.scoped_token}',
            'Content-Type': 'application/json'
        }

        response = requests.put(url, headers=headers, json={}, timeout=30)
        response.raise_for_status()

        data = response.json()
        self.continuation_token = data.get('next_continuation_token')
        channel_status = data.get('channel_status', {})
        self.offset_token = channel_status.get('last_committed_offset_token') or 0

        logger.info(f"Channel opened - continuation_token: {self.continuation_token}")
        logger.info(f"Initial offset: {self.offset_token}")

        return data

    def append_rows(self, rows: List[Dict]) -> Dict:
        """Append rows to the streaming channel using NDJSON."""
        if not rows:
            return {}

        logger.info(f"Appending {len(rows)} rows...")

        if not self.ingest_host or not self.continuation_token:
            raise RuntimeError("Channel not opened. Call open_channel() first.")

        self._ensure_valid_token()

        new_offset = self.offset_token + 1

        db = self.config['database']
        schema = self.config['schema']
        pipe = self.config['pipe']

        url = (
            f"https://{self.ingest_host}/v2/streaming/data"
            f"/databases/{db}/schemas/{schema}/pipes/{pipe}/channels/{self.channel_name}/rows"
        )

        params = {
            'continuationToken': self.continuation_token,
            'offsetToken': str(new_offset)
        }

        headers = {
            'Authorization': f'Bearer {self.scoped_token}',
            'Content-Type': 'application/x-ndjson'
        }

        ndjson_data = '\n'.join(json.dumps(row) for row in rows)

        response = requests.post(
            url,
            params=params,
            headers=headers,
            data=ndjson_data.encode('utf-8'),
            timeout=30
        )

        if response.status_code >= 400:
            logger.error(f"Append failed: {response.status_code} - {response.text}")
        response.raise_for_status()

        data = response.json()
        self.continuation_token = data.get('next_continuation_token')
        self.offset_token = new_offset

        self.stats['total_rows_sent'] += len(rows)
        self.stats['total_batches'] += 1
        self.stats['total_bytes_sent'] += len(ndjson_data)

        logger.info(f"Appended {len(rows)} rows, offset: {self.offset_token}")
        return data

    def insert_rows(self, rows: List[Dict]) -> int:
        """Alias for append_rows."""
        if not rows:
            return 0
        self.append_rows(rows)
        return len(rows)

    def get_channel_status(self) -> Dict:
        """Get current channel status."""
        if not self.ingest_host:
            raise RuntimeError("Ingest host not discovered")

        self._ensure_valid_token()

        db = self.config['database']
        schema = self.config['schema']
        pipe = self.config['pipe']

        url = (
            f"https://{self.ingest_host}/v2/streaming"
            f"/databases/{db}/schemas/{schema}/pipes/{pipe}:bulk-channel-status"
        )

        headers = {
            'Authorization': f'Bearer {self.scoped_token}',
            'Content-Type': 'application/json'
        }

        payload = {'channel_names': [self.channel_name]}

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        return data.get('channel_statuses', {}).get(self.channel_name, {})

    def wait_for_commit(self, expected_offset: int, timeout: int = 60, poll_interval: int = 2) -> bool:
        """Wait for data to be committed."""
        logger.info(f"Waiting for offset {expected_offset} to commit...")
        start = time.time()

        while time.time() - start < timeout:
            try:
                status = self.get_channel_status()
                committed = status.get('committed_offset_token', 0)
                if committed >= expected_offset:
                    logger.info(f"Committed at offset {committed}")
                    return True
                time.sleep(poll_interval)
            except Exception as e:
                logger.warning(f"Status check error: {e}")
                time.sleep(poll_interval)

        logger.warning(f"Commit timeout after {timeout}s")
        return False

    def close_channel(self):
        """Close channel (auto-closes after inactivity)."""
        logger.info(f"Closing channel: {self.channel_name}")
        logger.info("Channel will auto-close after inactivity")

    def print_statistics(self):
        """Print ingestion statistics."""
        elapsed = time.time() - self.stats['start_time']
        logger.info("=" * 50)
        logger.info("INGESTION STATISTICS")
        logger.info("=" * 50)
        logger.info(f"Total rows: {self.stats['total_rows_sent']}")
        logger.info(f"Batches: {self.stats['total_batches']}")
        logger.info(f"Bytes sent: {self.stats['total_bytes_sent']:,}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Elapsed: {elapsed:.2f}s")
        if self.stats['total_rows_sent'] > 0:
            logger.info(f"Throughput: {self.stats['total_rows_sent']/elapsed:.2f} rows/sec")
        logger.info("=" * 50)
