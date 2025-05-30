FROM debian:11-slim

# Set environment variables to avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TZ=UTC

# Set working directory
WORKDIR /app

# Install system dependencies and Python 3.9
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.9 \
    python3.9-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    gcc \
    redis-server \
    libpcap-dev \
    libxslt1-dev \
    ntp \
    sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.9 as the default python
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.9 1

# Set up Python environment
RUN python3 -m pip install --upgrade pip setuptools wheel

# Create bacmon user and directory structure
RUN useradd --system bacmon && \
    mkdir -p /home/bacmon && \
    mkdir -p /home/bacmon/log && \
    chown -R bacmon:bacmon /home/bacmon && \
    chmod -R 755 /home/bacmon

# Copy requirements first for better caching
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt

# Configure Redis
RUN sed -i 's/bind 127.0.0.1 ::1/bind 0.0.0.0/g' /etc/redis/redis.conf && \
    sed -i 's/protected-mode yes/protected-mode no/g' /etc/redis/redis.conf

# Copy application files
COPY *.py /app/
COPY template /app/template
COPY static /app/static

# Copy configuration to bacmon home
COPY BACmon.ini /home/bacmon/
COPY timeutil.py /home/bacmon/
RUN chown -R bacmon:bacmon /home/bacmon

# Create additional directories
RUN mkdir -p /app/logs && \
    chown -R bacmon:bacmon /app/logs

# Configure the apache directory if needed (for WSGI)
RUN mkdir -p /var/www/bacmon && \
    chown -R bacmon:bacmon /var/www/bacmon

# Create startup script with proper error handling
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Starting Redis server..."\n\
redis-server --daemonize yes\n\
sleep 1\n\
\n\
# Check if Redis is running\n\
if ! redis-cli ping > /dev/null; then\n\
    echo "Error: Redis server failed to start"\n\
    exit 1\n\
fi\n\
\n\
echo "Starting BACmon..."\n\
python3 BACmon.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose Redis port
EXPOSE 6379

# Default port for BACnet
EXPOSE 47808/udp

# Use a health check to verify Redis is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD redis-cli ping || exit 1

# Run the startup script
CMD ["/app/start.sh"]