#!/bin/bash

echo "Installing Termux dependencies..."
pkg update && pkg upgrade -y
pkg install python git rust binutils build-essential make clang -y
pkg install chromium chromedriver -y
pkg install libjpeg-turbo libpng -y

echo "Setting up Python environment..."
# Install numpy/pandas first if needed, but for this project:
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete!"
echo "Run 'python server.py' to start."
