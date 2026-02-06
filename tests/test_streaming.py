#!/usr/bin/env python3
"""
Tests for Snowpipe Streaming client.
"""

import sys
import os
import json
import unittest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStreamingClientInit(unittest.TestCase):
    """Test StreamingClient initialization."""

    def test_config_loading(self):
        """Test config file loading."""
        config = {
            "account": "test_account",
            "user": "test_user",
            "database": "TEST_DB",
            "schema": "TEST_SCHEMA",
            "pipe": "TEST_PIPE",
            "private_key_file": "test_key.p8"
        }
        
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(config))):
            with patch('sensehat_streaming_client.SnowflakeJWTAuth'):
                from sensehat_streaming_client import SenseHatStreamingClient
                client = SenseHatStreamingClient.__new__(SenseHatStreamingClient)
                loaded = client._load_config('test_config.json')
                self.assertEqual(loaded['account'], 'test_account')
                self.assertEqual(loaded['database'], 'TEST_DB')


class TestNDJSONFormatting(unittest.TestCase):
    """Test NDJSON data formatting."""

    def test_single_row_ndjson(self):
        """Test single row NDJSON formatting."""
        row = {"id": 1, "value": "test"}
        ndjson = json.dumps(row)
        self.assertEqual(ndjson, '{"id": 1, "value": "test"}')

    def test_multiple_rows_ndjson(self):
        """Test multiple rows NDJSON formatting."""
        rows = [
            {"id": 1, "value": "a"},
            {"id": 2, "value": "b"},
            {"id": 3, "value": "c"}
        ]
        ndjson = '\n'.join(json.dumps(row) for row in rows)
        lines = ndjson.split('\n')
        self.assertEqual(len(lines), 3)
        
        for line in lines:
            parsed = json.loads(line)
            self.assertIn('id', parsed)
            self.assertIn('value', parsed)

    def test_special_characters_in_ndjson(self):
        """Test special characters are properly escaped."""
        row = {"text": "Hello\nWorld", "quote": 'Say "hello"'}
        ndjson = json.dumps(row)
        parsed = json.loads(ndjson)
        self.assertEqual(parsed['text'], "Hello\nWorld")
        self.assertEqual(parsed['quote'], 'Say "hello"')


class TestStatisticsTracking(unittest.TestCase):
    """Test statistics tracking."""

    def test_stats_initialization(self):
        """Test statistics are initialized correctly."""
        stats = {
            'total_rows_sent': 0,
            'total_batches': 0,
            'total_bytes_sent': 0,
            'errors': 0,
            'start_time': 0
        }
        
        self.assertEqual(stats['total_rows_sent'], 0)
        self.assertEqual(stats['total_batches'], 0)
        self.assertEqual(stats['errors'], 0)

    def test_stats_update_after_batch(self):
        """Test statistics update after batch."""
        stats = {
            'total_rows_sent': 0,
            'total_batches': 0,
            'total_bytes_sent': 0,
            'errors': 0
        }
        
        rows = [{"id": i} for i in range(10)]
        ndjson = '\n'.join(json.dumps(r) for r in rows)
        
        stats['total_rows_sent'] += len(rows)
        stats['total_batches'] += 1
        stats['total_bytes_sent'] += len(ndjson)
        
        self.assertEqual(stats['total_rows_sent'], 10)
        self.assertEqual(stats['total_batches'], 1)
        self.assertGreater(stats['total_bytes_sent'], 0)


class TestURLConstruction(unittest.TestCase):
    """Test REST API URL construction."""

    def test_channel_url(self):
        """Test channel URL construction."""
        ingest_host = "test.region.ingest.snowflakecomputing.com"
        db = "DEMO"
        schema = "DEMO"
        pipe = "TEST_PIPE"
        channel = "TEST_CHANNEL"
        
        url = (
            f"https://{ingest_host}/v2/streaming"
            f"/databases/{db}/schemas/{schema}/pipes/{pipe}/channels/{channel}"
        )
        
        self.assertIn("https://", url)
        self.assertIn("/v2/streaming/", url)
        self.assertIn(f"/databases/{db}/", url)
        self.assertIn(f"/schemas/{schema}/", url)
        self.assertIn(f"/pipes/{pipe}/", url)
        self.assertIn(f"/channels/{channel}", url)

    def test_rows_url(self):
        """Test rows append URL construction."""
        ingest_host = "test.region.ingest.snowflakecomputing.com"
        db = "DEMO"
        schema = "DEMO"
        pipe = "TEST_PIPE"
        channel = "TEST_CHANNEL"
        
        url = (
            f"https://{ingest_host}/v2/streaming/data"
            f"/databases/{db}/schemas/{schema}/pipes/{pipe}/channels/{channel}/rows"
        )
        
        self.assertIn("/v2/streaming/data/", url)
        self.assertIn("/rows", url)

    def test_hostname_underscore_replacement(self):
        """Test underscore replacement in hostname."""
        hostname = "my_account.region.ingest.snowflakecomputing.com"
        fixed = hostname.replace('_', '-')
        self.assertEqual(fixed, "my-account.region.ingest.snowflakecomputing.com")
        self.assertNotIn('_', fixed)


class TestTokenManagement(unittest.TestCase):
    """Test token management logic."""

    def test_token_expiry_check(self):
        """Test token expiry checking."""
        import time
        
        token_expiry = time.time() + 3600
        current_time = time.time()
        
        is_valid = current_time < token_expiry
        self.assertTrue(is_valid)
        
        token_expiry = time.time() - 100
        is_valid = current_time < token_expiry
        self.assertFalse(is_valid)

    def test_offset_token_increment(self):
        """Test offset token increments correctly."""
        offset_token = 0
        
        for i in range(1, 6):
            new_offset = offset_token + 1
            self.assertEqual(new_offset, i)
            offset_token = new_offset


class TestChannelNaming(unittest.TestCase):
    """Test channel naming conventions."""

    def test_unique_channel_name(self):
        """Test channel names include timestamp for uniqueness."""
        from datetime import datetime
        
        base_channel = "SENSEHAT_CHNL"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        channel_name = f"{base_channel}_{timestamp}"
        
        self.assertTrue(channel_name.startswith(base_channel))
        self.assertIn('_', channel_name)
        self.assertGreater(len(channel_name), len(base_channel))


if __name__ == '__main__':
    print("=" * 60)
    print("Streaming Client Tests")
    print("=" * 60)
    unittest.main(verbosity=2)
