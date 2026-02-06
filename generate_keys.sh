#!/bin/bash
# Generate RSA key pair for Snowflake authentication

echo "Generating RSA key pair for Snowflake authentication..."

# Generate private key (PKCS8 format)
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt

# Extract public key
openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub

# Format public key for Snowflake (single line, no headers)
PUBLIC_KEY=$(grep -v "BEGIN\|END" rsa_key.pub | tr -d '\n')

echo ""
echo "========================================"
echo "Keys generated successfully!"
echo "========================================"
echo ""
echo "Private key: rsa_key.p8"
echo "Public key:  rsa_key.pub"
echo ""
echo "Run this SQL in Snowflake to register the public key:"
echo ""
echo "ALTER USER SENSEHAT_STREAMING_USER SET RSA_PUBLIC_KEY='$PUBLIC_KEY';"
echo ""
echo "========================================"

# Secure the private key
chmod 600 rsa_key.p8
