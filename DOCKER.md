# BACmon Docker Guide

This document provides instructions for running BACmon in a Docker container, which is the recommended approach for new deployments.

## Prerequisites

- Docker Engine (version 19.03 or later)
- Docker Compose (version 1.27 or later)
- Git (to clone the repository if needed)

## Quick Start

The simplest way to run BACmon is with Docker Compose:

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/yourusername/bacmon.git
cd bacmon

# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f
```

## Docker Container Details

The BACmon Docker container:

- Is based on Debian 11 Slim
- Uses Python 3.9
- Runs Redis inside the container
- Exposes ports:
  - 47808/UDP (BACnet communication)
  - 6379/TCP (Redis, optional)
- Stores logs in a Docker volume

## Configuration

### Environment Variables

The following environment variables can be configured in the `docker-compose.yml` file:

- `TZ`: Timezone (default: UTC)

### Configuration Files

The main configuration file `BACmon.ini` is included in the container. If you need to make changes:

1. Create a modified version of `BACmon.ini`
2. Mount it as a volume in `docker-compose.yml`:

```yaml
volumes:
  - ./BACmon.ini:/home/bacmon/BACmon.ini
```

## Testing

A test script is included to verify the Docker container is working properly:

```bash
# Make the script executable
chmod +x test_docker.sh

# Run the tests
./test_docker.sh
```

The test script:
- Builds the Docker image
- Starts a container
- Verifies Redis is running
- Checks that the BACmon process is active
- Displays container logs

## Monitoring and Maintenance

### Checking Container Status

```bash
# View container status
docker-compose ps

# View logs
docker-compose logs -f
```

### Restarting Services

```bash
# Restart services
docker-compose restart
```

### Updating the Container

```bash
# Pull latest code
git pull

# Rebuild and restart the container
docker-compose down
docker-compose up -d --build
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**: If you encounter port conflicts, modify the port mappings in `docker-compose.yml`

2. **Redis Connection Issues**: Verify Redis is running:
   ```bash
   docker-compose exec bacmon redis-cli ping
   ```

3. **Log Access**: Access logs directly from the Docker volume:
   ```bash
   docker-compose exec bacmon ls -la /home/bacmon/log
   ```

## Production Considerations

For production environments:

1. **Security**: Remove the Redis port mapping (6379) from `docker-compose.yml` if not needed externally

2. **Persistence**: The `bacmon-logs` volume ensures log persistence across container restarts

3. **Backup**: Regularly backup the log volume:
   ```bash
   docker run --rm -v bacmon-logs:/data -v $(pwd):/backup alpine tar -czvf /backup/bacmon-logs-backup.tar.gz /data
   ```

4. **Health Monitoring**: The container includes a health check that verifies Redis is running

## Notes on Python 3 Migration

This Docker configuration has been specifically designed for Python 3.6+ compatibility, ensuring all BACmon features work correctly with the updated Python environment. 