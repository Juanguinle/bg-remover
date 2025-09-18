#!/bin/bash

echo "Installing BG Remover for Linux..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3.8+ using your package manager"
    exit 1
fi

# Install system dependencies
echo "Installing system dependencies..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y python3-venv python3-pip libgl1-mesa-glx libglib2.0-0
elif command -v yum &> /dev/null; then
    sudo yum install -y python3-venv python3-pip mesa-libGL glib2
elif command -v pacman &> /dev/null; then
    sudo pacman -S python-virtualenv python-pip mesa glib2
else
    echo "Warning: Could not detect package manager. You may need to install dependencies manually."
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv bg_remover_env
if [ $? -ne 0 ]; then
    echo "Error: Failed to create virtual environment"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source bg_remover_env/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install PyTorch
echo "Installing PyTorch..."
pip install torch torchvision

# Install bg-remover
echo "Installing bg-remover..."
pip install bg-remover

# Test installation
echo "Testing installation..."
bg-remover info

echo ""
echo "Installation completed successfully!"
echo ""
echo "To use bg-remover:"
echo "1. Activate the environment: source bg_remover_env/bin/activate"
echo "2. Run: bg-remover --help"
echo ""