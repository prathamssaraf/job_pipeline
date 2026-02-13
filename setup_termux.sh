#!/bin/bash


# 2. Install core dependencies
echo "Installing system packages..."
pkg update -y && pkg upgrade -y
pkg install -y python git rust binutils build-essential make clang
pkg install -y tur-repo x11-repo libffi openssl-tool openssl
# IMPORTANT: Update repos after adding repos to find chromium
pkg update -y 

pkg install -y python-grpcio python-numpy python-cryptography
pkg install -y chromium chromedriver
pkg install -y libjpeg-turbo libpng

# 3. Setup Python environment
echo "Installing Python dependencies..."
# Export flags to help with building if needed
export FLAGS="-Wno-incompatible-function-pointer-types"
export CFLAGS="-Wno-incompatible-function-pointer-types"
export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1
export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=1
# Fix for cryptography/rust build
export ANDROID_API_LEVEL=24
export CC="clang"
export CXX="clang++"
export CARGO_BUILD_TARGET="aarch64-linux-android"




pip install --upgrade pip
echo "Installing requirements (using pre-built binaries where possible)..."
pip install -r requirements.txt --prefer-binary


echo "Setup complete!"

echo "Run 'python server.py' to start."
