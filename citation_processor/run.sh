#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export PYTHONPATH=src

# Run the main script
python src/main.py "$@" 