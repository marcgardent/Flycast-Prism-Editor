# --- STAGE 1 : Requirements---
FROM ubuntu:22.04 AS env-apt

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    wget \
    bzip2 \
    ca-certificates \
    build-essential \
    gcc \
    file \
    binutils \
    fuse \
    libopenimageio-dev \
    libgl1-mesa-glx \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libfontconfig1 \
    libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*

FROM env-apt AS env-anaconda

RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p /opt/conda && \
    rm /tmp/miniconda.sh && \
    /opt/conda/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && \
    /opt/conda/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

ENV PATH="/opt/conda/bin:${PATH}"


FROM env-anaconda AS env-linuxdeploy

# Installer linuxdeploy (extraire pour éviter les problèmes de FUSE dans Docker)
RUN wget https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage -O /usr/local/bin/linuxdeploy.AppImage && \
    chmod +x /usr/local/bin/linuxdeploy.AppImage && \
    cd /usr/local/bin && ./linuxdeploy.AppImage --appimage-extract && \
    mv squashfs-root /usr/local/lib/linuxdeploy && \
    ln -s /usr/local/lib/linuxdeploy/AppRun /usr/local/bin/linuxdeploy && \
    rm /usr/local/bin/linuxdeploy.AppImage

FROM env-linuxdeploy AS  env-project

COPY environment.yml /tmp/environment.yml
RUN conda env create -v -f /tmp/environment.yml -n flycast-viewer && \
    /opt/conda/bin/conda clean -afy && \
    find /opt/conda/envs/flycast-viewer -type d -name "tests" -exec rm -rf {} + && \
    find /opt/conda/envs/flycast-viewer -type d -name "__pycache__" -exec rm -rf {} + && \
    rm -rf /opt/conda/envs/flycast-viewer/include && \
    rm -rf /opt/conda/envs/flycast-viewer/share/man && \
    rm -rf /opt/conda/envs/flycast-viewer/share/doc

WORKDIR /build
COPY . /build/source

# Script de build par défaut
CMD ["bash", "/build/source/packaging/linux/build_appimage.sh"]
