FROM node:22-bookworm-slim

# System packages: Python + ffmpeg + build essentials for Python wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv python3-dev \
      ffmpeg \
      build-essential \
      ca-certificates \
      curl \
      git \
    && rm -rf /var/lib/apt/lists/*

# Create a venv so the image doesn't fight Debian's PEP 668 marker
ENV VENV=/opt/venv
RUN python3 -m venv $VENV
ENV PATH="$VENV/bin:$PATH"

WORKDIR /workspace

# Install Python deps ahead of copy so the cache layer is reusable
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir google-cloud-aiplatform

EXPOSE 3201
