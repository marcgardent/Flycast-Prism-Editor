#!/bin/bash
set -e

# Configuration
APP_NAME="flycast-prism-editor"
VERSION_STR=""

if [ -n "$GIT_REV" ]; then
    VERSION_STR="-${GIT_REV}"
fi
if [ -n "$BUILD_DATE" ]; then
    VERSION_STR="${VERSION_STR}-${BUILD_DATE}"
fi

echo "--- Preparing Windows Build ---"

# PyInstaller command
# Note: In Wine, the path separator for --add-data is usually ';' 
# but it might depend on the PyInstaller version. 
# We use 'assets;assets' to copy the assets folder into the executable.
wine python -m PyInstaller \
    --onefile \
    --windowed \
    --name "${APP_NAME}${VERSION_STR}" \
    --add-data "assets;assets" \
    --icon "assets/logo-prism.ico" \
    --clean \
    main.py

echo "--- Build Completed ---"
mkdir -p /src/output
mv dist/*.exe /src/output/
