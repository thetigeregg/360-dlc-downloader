# Use a minimal base image
FROM debian:bullseye

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive HOME=/root

# Install required packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    git \
    ca-certificates \
    python3 \
    python3-pip \
    p7zip-full \
    aria2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install internetarchive

# Seed a copy of 360-dlc-downloader outside of /app so it can repopulate
# /app on container startup if it's mounted empty (e.g. an empty bind mount)
RUN git clone https://github.com/thetigeregg/360-dlc-downloader.git /opt/dlc-seed/360-dlc-downloader \
    && chmod +x /opt/dlc-seed/360-dlc-downloader/download_dlc.py

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set the working directory for the container
WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]
CMD ["tail", "-f", "/dev/null"]
