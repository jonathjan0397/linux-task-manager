#!/bin/bash

# PyTask: Linux Task Manager - Automated Runner
# This script handles the virtual environment and dependencies automatically.

# Navigate to script directory
cd "$(dirname "$0")"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Setup Virtual Environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "First-time setup: Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Support setup-only mode used by the Makefile install target.
if [ "$1" = "--setup" ]; then
    echo "Environment setup complete."
    exit 0
fi

# Run the application
python3 app.py "$@"
