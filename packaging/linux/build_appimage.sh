#!/bin/bash
set -e

# Configuration
APP_NAME="Flycast_G-Buffer_Viewer"
ICON_PATH="/build/source/assets/logo-prism.png"
DESKTOP_FILE="/build/source/packaging/linux/flycast-viewer.desktop"
APPDIR="/build/AppDir"
CONDA_ENV_SOURCE="/opt/conda/envs/flycast-viewer"

# Get version info (injected via env vars or default)
VERSION_STR=""
if [ -n "$GIT_REV" ]; then
    VERSION_STR="-${GIT_REV}"
fi
if [ -n "$BUILD_DATE" ]; then
    VERSION_STR="${VERSION_STR}-${BUILD_DATE}"
fi

echo "--- Preparing AppDir ---"
mkdir -p "$APPDIR"

echo "--- Integrating Conda environment ---"
mkdir -p "$APPDIR/usr/conda-env"
cp -R "$CONDA_ENV_SOURCE"/* "$APPDIR/usr/conda-env/"

# Additional cleanup in AppDir to reduce size
echo "--- Optimizing size ---"
find "$APPDIR/usr/conda-env" -name "*.so*" -exec strip --strip-unneeded {} + || true
find "$APPDIR/usr/conda-env" -name "*.a" -delete
find "$APPDIR/usr/conda-env" -name "__pycache__" -type d -exec rm -rf {} +

echo "--- Copying source files ---"
mkdir -p "$APPDIR"/usr/bin/
cp /build/source/*.py "$APPDIR"/usr/bin/
mkdir -p "$APPDIR"/usr/bin/assets
cp /build/source/assets/* "$APPDIR"/usr/bin/assets/

# Create a launcher that uses the conda-env python
cat > "$APPDIR"/usr/bin/flycast-viewer <<EOF
#!/bin/bash
HERE="\$(dirname "\$(readlink -f "\$0")")"
export PATH="\$HERE/../conda-env/bin:\$PATH"
export LD_LIBRARY_PATH="\$HERE/../conda-env/lib:\$LD_LIBRARY_PATH"
export PYTHONHOME="\$HERE/../conda-env"
exec "\$HERE/../conda-env/bin/python3" "\$HERE/main.py" "\$@"
EOF
chmod +x "$APPDIR"/usr/bin/flycast-viewer

echo "--- Running linuxdeploy ---"
export OUTPUT="${APP_NAME}${VERSION_STR}-x86_64.AppImage"

/usr/local/bin/linuxdeploy \
    --appdir "$APPDIR" \
    --executable "$APPDIR/usr/conda-env/bin/python3" \
    --desktop-file "$DESKTOP_FILE" \
    --icon-file "$ICON_PATH" \
    --output appimage

echo "--- Build completed ---"
mkdir -p /build/output
mv *.AppImage /build/output/
