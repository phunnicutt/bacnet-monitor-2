#!/bin/bash

# Setup Python 3 Environment for BACmon
# This script creates a virtual environment and installs required dependencies

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Print Python version
echo "Using Python version:"
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv env
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Please make sure python3-venv is installed."
        echo "For Ubuntu/Debian: sudo apt install python3-venv"
        exit 1
    fi
else
    echo "Virtual environment already exists at ./env"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source env/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Verify installation
echo "Verifying installations..."
pip list

echo "Python 3 environment setup complete. To activate the environment, run:"
echo "source env/bin/activate" 