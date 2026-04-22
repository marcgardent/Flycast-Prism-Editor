# --- STAGE 1 : Base PyInstaller for Windows (Modern Python) ---
FROM cdrx/pyinstaller-windows:python3 AS env-base

# --- STAGE 2 : Dependencies ---
FROM env-base AS env-deps
COPY packaging/windows/requirements.txt /tmp/requirements.txt

# Pre-installing requirements to the Wine environment
# tobix image is well configured for wine python
RUN wine python -m pip install --upgrade pip && \
    wine python -m pip install -r /tmp/requirements.txt

# --- STAGE 3 : Project & Build ---
FROM env-deps AS env-project
WORKDIR /src
COPY . /src

# Default build command
CMD ["bash", "/src/packaging/windows/build_windows.sh"]
