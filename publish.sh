#!/bin/bash
set -e

# Build directory path
BUILD_DIR="build_packaging"
TARGET=${1:-linux}

echo "--- Configuring the project ---"
cmake -B "$BUILD_DIR" -S .

case $TARGET in
    linux)
        echo "--- Building Linux AppImage ---"
        cmake --build "$BUILD_DIR" --target publish
        ;;
    windows)
        echo "--- Building Windows EXE ---"
        cmake --build "$BUILD_DIR" --target publish-win
        ;;
    all)
        echo "--- Building ALL targets ---"
        cmake --build "$BUILD_DIR" --target publish
        cmake --build "$BUILD_DIR" --target publish-win
        ;;
    *)
        echo "Invalid target: $TARGET. Use linux, windows, or all."
        exit 1
        ;;
esac

echo "--- Build completed ---"
echo "Results are available in the output/ directory"
