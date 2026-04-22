#!/bin/bash
set -e

# Build directory path
BUILD_DIR="build_packaging"

echo "--- Configuring the project ---"
cmake -B "$BUILD_DIR" -S .

echo "--- Launching the publication process ---"
cmake --build "$BUILD_DIR" --target publish

echo "--- Build completed ---"
echo "The AppImage is available in the output/ directory"
