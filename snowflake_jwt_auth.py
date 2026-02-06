#!/usr/bin/env python3
"""
JWT Authentication for Snowflake Snowpipe Streaming v2 REST API
Supports both Key-Pair JWT and Programmatic Access Token (PAT) authentication.
Optimized for Raspberry Pi (low memory footprint).
"""

import json
import time
import logging
import hashlib
import base64
from typing import Dict, Optional
from pathlib import Path

import requests

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    import jwt
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

logger = logging.getLogger(__name__)


class SnowflakeJWTAuth:
    """
    Handles JWT and PAT authentication for Snowpipe Streaming v2 REST API.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.account = config['account'].upper()
        self.user = config['user'].upper()
        self.url = config.get('url', f"https://{config['account'].lower()}.snowflakecomputing.com")
        
        self.pat_token = config.get('pat_token')
        self.private_key_file = config.get('private_key_file')
        self.private_key_passphrase = config.get('private_key_passphrase')
        
        self._jwt_token = None
        self._jwt_expiry = 0
        self._scoped_token = None
        self._scoped_expiry = 0
        self._ingest_host = None

        if self.pat_token:
            logger.info("Using PAT authentication")
        elif self.private_key_file:
            if not HAS_CRYPTO:
                raise ImportError("cryptography and PyJWT required for key-pair auth")
            logger.info("Using key-pair JWT authentication")
            self._load_private_key()
        else:
            raise ValueError("Either pat_token or private_key_file must be provided")

    def _load_private_key(self):
        """Load private key from file."""
        key_path = Path(self.private_key_file)
        if not key_path.exists():
            raise FileNotFoundError(f"Private key file not found: {self.private_key_file}")

        with open(key_path, 'rb') as f:
            key_data = f.read()

        passphrase = None
        if self.private_key_passphrase:
            passphrase = self.private_key_passphrase.encode()

        self._private_key = serialization.load_pem_private_key(
            key_data,
            password=passphrase,
            backend=default_backend()
        )
        logger.info("Private key loaded successfully")

    def _get_public_key_fingerprint(self) -> str:
        """Generate SHA256 fingerprint of the public key."""
        public_key = self._private_key.public_key()
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        sha256_hash = hashlib.sha256(public_key_bytes).digest()
        fingerprint = base64.b64encode(sha256_hash).decode('utf-8')
        return f"SHA256:{fingerprint}"

    def _generate_jwt(self) -> str:
        """Generate JWT token for Snowflake authentication."""
        now = int(time.time())
        lifetime = 3600
        expiry = now + lifetime

        qualified_username = f"{self.account}.{self.user}"
        fingerprint = self._get_public_key_fingerprint()

        payload = {
            "iss": f"{qualified_username}.{fingerprint}",
            "sub": qualified_username,
            "iat": now,
            "exp": expiry
        }

        token = jwt.encode(payload, self._private_key, algorithm="RS256")
        self._jwt_expiry = expiry - 60
        logger.debug("JWT token generated")
        return token

    def get_jwt_token(self) -> str:
        """Get valid JWT token, generating new one if needed."""
        if self.pat_token:
            return self.pat_token

        if self._jwt_token is None or time.time() >= self._jwt_expiry:
            self._jwt_token = self._generate_jwt()
        return self._jwt_token

    def _discover_ingest_host(self) -> str:
        """Discover the ingest host from Snowflake."""
        if self._ingest_host:
            return self._ingest_host

        account_lower = self.config['account'].lower()
        control_host = f"https://{account_lower}.snowflakecomputing.com"
        url = f"{control_host}/v2/streaming/hostname"

        token = self.get_jwt_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'X-Snowflake-Authorization-Token-Type': 'KEYPAIR_JWT' if not self.pat_token else 'PROGRAMMATIC_ACCESS_TOKEN'
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            data = response.json()
            self._ingest_host = data.get('hostname') or data.get('ingest_host')
        else:
            self._ingest_host = response.text.strip()

        if '_' in self._ingest_host:
            self._ingest_host = self._ingest_host.replace('_', '-')
            logger.info("Replaced underscores with dashes in ingest host")

        logger.info(f"Discovered ingest host: {self._ingest_host}")
        return self._ingest_host

    def get_scoped_token(self) -> str:
        """Get scoped token for ingest host."""
        if self._scoped_token and time.time() < self._scoped_expiry:
            return self._scoped_token

        ingest_host = self._discover_ingest_host()

        account_lower = self.config['account'].lower()
        control_host = f"https://{account_lower}.snowflakecomputing.com"
        url = f"{control_host}/oauth/token"

        token = self.get_jwt_token()
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Bearer {token}',
            'X-Snowflake-Authorization-Token-Type': 'KEYPAIR_JWT' if not self.pat_token else 'PROGRAMMATIC_ACCESS_TOKEN'
        }

        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'scope': ingest_host
        }

        response = requests.post(url, headers=headers, data=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        self._scoped_token = result.get('access_token')
        expires_in = result.get('expires_in', 3600)
        self._scoped_expiry = time.time() + expires_in - 60

        if not self._scoped_token:
            raise ValueError("No access_token in scoped token response")

        logger.info("Scoped token obtained successfully")
        return self._scoped_token

    def get_ingest_host(self) -> str:
        """Get the ingest host (cached)."""
        if not self._ingest_host:
            self._discover_ingest_host()
        return self._ingest_host
