FROM python:3.13-slim-trixie

RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
    build-essential cmake ninja-build git libvulkan1 mesa-vulkan-drivers vulkan-tools \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir "VapourSynth==81" numpy build hatchling packaging

ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /work
