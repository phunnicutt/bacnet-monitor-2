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
- Uses Python 3.9.2 (fully Python 3 compatible)
- Runs Redis inside the container
- Exposes ports:
  - 47808/UDP (BACnet communication)
  - 6379/TCP (Redis, optional)
- Stores logs in a Docker volume
- Includes comprehensive health checks

## Python 3 Compatibility

This Docker configuration has been specifically designed and tested for Python 3 compatibility:

- **Python Version**: 3.9.2 with proper alternatives configuration
- **Package Dependencies**: All packages verified for Python 3 compatibility
  - redis (Redis client)
  - bacpypes3 (Python 3 BACnet library)
  - bottle (Web framework)
  - simplejson (JSON handling)
  - lxml (XML processing)
- **Code Validation**: All BACmon Python files compile successfully with Python 3
- **Testing**: Comprehensive test suite validates Python 3 functionality

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

Two test scripts are included to verify the Docker container functionality:

### Basic Docker Test
```bash
# Make the script executable
chmod +x test_docker.sh

# Run the tests (requires available ports)
./test_docker.sh
```

### Python 3 Focused Test (Recommended)
```bash
# Make the script executable
chmod +x test_docker_python3.sh

# Run comprehensive Python 3 tests
./test_docker_python3.sh
```

The Python 3 test script (`test_docker_python3.sh`):
- Builds the Docker image
- Validates Python 3.9.2 installation
- Tests all required package imports
- Verifies BACmon code syntax compatibility
- Tests Redis server functionality
- Validates Python 3 Redis client integration
- Tests core module imports
- Runs without port conflicts (recommended for CI/CD)

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

4. **Python 3 Issues**: Run the Python 3 test script to validate configuration:
   ```bash
   ./test_docker_python3.sh
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

5. **Resource Limits**: Consider adding resource limits in production:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 512M
         cpus: '0.5'
   ```

## Docker Configuration Features

### Base Configuration
- **Base Image**: Debian 11 Slim (modern, secure, lightweight)
- **Python Version**: 3.9.2 with proper alternatives setup
- **Package Management**: pip3 with optimized dependency resolution
- **User Security**: Non-root `bacmon` user with proper file permissions

### Service Integration
- **Redis Integration**: Embedded Redis server with optimized configuration
- **Health Checks**: Built-in Redis health monitoring with proper timeouts
- **Port Configuration**: Proper BACnet (47808/UDP) and Redis (6379/TCP) exposure
- **Volume Management**: Persistent log storage with Docker volumes

### Development Features
- **Hot Reload**: Code changes reflected with container restart
- **Debug Access**: Easy container shell access for troubleshooting
- **Test Integration**: Comprehensive test scripts for validation

## Notes on Python 3 Migration

This Docker configuration has been specifically designed and thoroughly tested for Python 3.9+ compatibility, ensuring all BACmon features work correctly with the updated Python environment. The configuration includes:

- Proper Python 3 package installations
- Validated syntax compatibility for all BACmon modules
- Tested Redis integration with Python 3
- Comprehensive test coverage for production readiness

All legacy Python 2 dependencies have been replaced with Python 3 compatible alternatives, and the entire stack has been validated through automated testing. 