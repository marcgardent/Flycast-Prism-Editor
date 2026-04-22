# --- STAGE 1 : Base PyInstaller for Windows ---
FROM batonogov/pyinstaller-windows:latest AS env-base

# --- STAGE 2 : Dependencies ---
FROM env-base AS env-deps
COPY packaging/windows/requirements.txt /tmp/requirements.txt

# Pre-install dependencies to the image's environment
RUN wine python -m pip install --upgrade pip && \
    wine python -m pip install -r /tmp/requirements.txt

# --- STAGE 3 : Project ---
FROM env-deps AS env-project
WORKDIR /src
COPY . /src

# The batonogov image uses /entrypoint.sh which looks for SPECFILE
ENTRYPOINT ["/entrypoint.sh"]
