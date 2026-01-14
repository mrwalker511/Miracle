#!/bin/bash

# Script to install pgvector extension for PostgreSQL

echo "Installing pgvector extension for PostgreSQL..."
echo

# Check if running in Docker container
if [ -f /.dockerenv ]; then
    echo "✓ Running in Docker container"

    # Install pgvector
    apt-get update
    apt-get install -y postgresql-server-dev-all git build-essential

    # Clone and build pgvector
    cd /tmp
    git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
    cd pgvector
    make
    make install

    echo "✓ pgvector installed successfully"
else
    echo "This script is intended to run inside a PostgreSQL Docker container"
    echo
    echo "To use pgvector, use the official pgvector Docker image:"
    echo "  docker-compose up -d postgres"
    echo
    echo "The docker-compose.yml is already configured to use pgvector/pgvector:pg16"
fi

echo
echo "Done!"
