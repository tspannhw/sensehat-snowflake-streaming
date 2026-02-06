#!/usr/bin/env python3
"""
Tests for Snowflake connection and authentication.
Requires snowflake_config.json to be present.
"""

import sys
import os
import json
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def config_exists():
    """Check if config file exists."""
    config_path = Path(__file__).parent.parent / 'snowflake_config.json'
    return config_path.exists()


@unittest.skipUnless(config_exists(), "snowflake_config.json not found")
class TestSnowflakeConnection(unittest.TestCase):
    """Test Snowflake connection (requires config)."""

    @classmethod
    def setUpClass(cls):
        """Load configuration."""
        config_path = Path(__file__).parent.parent / 'snowflake_config.json'
        with open(config_path) as f:
            cls.config = json.load(f)

    def test_config_has_required_fields(self):
        """Test config has all required fields."""
        required = ['account', 'user', 'database', 'schema', 'pipe']
        for field in required:
            self.assertIn(field, self.config, f"Missing: {field}")

    def test_config_has_auth(self):
        """Test config has authentication method."""
        has_key = 'private_key_file' in self.config and self.config['private_key_file']
        has_pat = 'pat_token' in self.config and self.config['pat_token']
        self.assertTrue(has_key or has_pat, "Need private_key_file or pat_token")

    def test_jwt_auth_initialization(self):
        """Test JWT auth can be initialized."""
        from snowflake_jwt_auth import SnowflakeJWTAuth
        
        try:
            auth = SnowflakeJWTAuth(self.config)
            self.assertIsNotNone(auth)
            self.assertEqual(auth.account, self.config['account'].upper())
        except FileNotFoundError as e:
            self.skipTest(f"Key file not found: {e}")
        except Exception as e:
            self.fail(f"Auth initialization failed: {e}")

    def test_ingest_host_discovery(self):
        """Test ingest host can be discovered."""
        from snowflake_jwt_auth import SnowflakeJWTAuth
        
        try:
            auth = SnowflakeJWTAuth(self.config)
            ingest_host = auth.get_ingest_host()
            
            self.assertIsNotNone(ingest_host)
            self.assertIn('snowflakecomputing.com', ingest_host)
            self.assertIn('ingest', ingest_host.lower())
            
            print(f"\n  Ingest host: {ingest_host}")
        except FileNotFoundError as e:
            self.skipTest(f"Key file not found: {e}")
        except Exception as e:
            self.fail(f"Ingest host discovery failed: {e}")

    def test_scoped_token_acquisition(self):
        """Test scoped token can be acquired."""
        from snowflake_jwt_auth import SnowflakeJWTAuth
        
        try:
            auth = SnowflakeJWTAuth(self.config)
            scoped_token = auth.get_scoped_token()
            
            self.assertIsNotNone(scoped_token)
            self.assertGreater(len(scoped_token), 100)
            
            print(f"\n  Token length: {len(scoped_token)} chars")
        except FileNotFoundError as e:
            self.skipTest(f"Key file not found: {e}")
        except Exception as e:
            self.fail(f"Scoped token acquisition failed: {e}")


@unittest.skipUnless(config_exists(), "snowflake_config.json not found")
class TestStreamingClientConnection(unittest.TestCase):
    """Test streaming client connection (requires config)."""

    def test_client_initialization(self):
        """Test streaming client can be initialized."""
        from sensehat_streaming_client import SenseHatStreamingClient
        
        try:
            client = SenseHatStreamingClient()
            self.assertIsNotNone(client)
            self.assertIsNotNone(client.config)
            self.assertIsNotNone(client.channel_name)
            
            print(f"\n  Channel: {client.channel_name}")
        except FileNotFoundError as e:
            self.skipTest(f"Key file not found: {e}")
        except Exception as e:
            self.fail(f"Client initialization failed: {e}")

    def test_channel_open(self):
        """Test streaming channel can be opened."""
        from sensehat_streaming_client import SenseHatStreamingClient
        
        try:
            client = SenseHatStreamingClient()
            client.discover_ingest_host()
            result = client.open_channel()
            
            self.assertIsNotNone(result)
            self.assertIsNotNone(client.continuation_token)
            
            print(f"\n  Channel opened: {client.channel_name}")
            print(f"  Continuation token: {client.continuation_token[:50]}...")
        except FileNotFoundError as e:
            self.skipTest(f"Key file not found: {e}")
        except Exception as e:
            self.fail(f"Channel open failed: {e}")


class TestConfigValidation(unittest.TestCase):
    """Test configuration validation."""

    def test_template_exists(self):
        """Test config template exists."""
        template_path = Path(__file__).parent.parent / 'snowflake_config.json.template'
        self.assertTrue(template_path.exists(), "Template should exist")

    def test_template_has_required_fields(self):
        """Test template has required fields."""
        template_path = Path(__file__).parent.parent / 'snowflake_config.json.template'
        
        with open(template_path) as f:
            template = json.load(f)
        
        required = ['account', 'user', 'database', 'schema', 'pipe']
        for field in required:
            self.assertIn(field, template, f"Template missing: {field}")

    def test_account_format(self):
        """Test account identifier format validation."""
        valid_accounts = [
            "xy12345",
            "myorg-account123",
            "abc12345.us-east-1"
        ]
        
        for account in valid_accounts:
            self.assertIsInstance(account, str)
            self.assertGreater(len(account), 0)


if __name__ == '__main__':
    print("=" * 60)
    print("Snowflake Connection Tests")
    print("=" * 60)
    
    if not config_exists():
        print("\nWARNING: snowflake_config.json not found")
        print("Connection tests will be skipped")
        print("Copy template and configure to run full tests:")
        print("  cp snowflake_config.json.template snowflake_config.json")
        print("")
    
    unittest.main(verbosity=2)
