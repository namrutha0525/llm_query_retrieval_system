#!/bin/bash
# Startup script for LLM Query-Retrieval System

echo "Starting LLM Query-Retrieval System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create data directory
mkdir -p data

# Start the application
echo "Starting FastAPI application..."
python main.py
